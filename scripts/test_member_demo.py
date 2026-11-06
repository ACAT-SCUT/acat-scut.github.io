"""Local demo workflows, persistence and HTTP checks; no real content writes."""
import copy
import csv
import hashlib
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from member_demo.core import DemoError, ROOT, Store, registry
from member_demo.render import render_members
from member_demo.server import create_server


class DemoTestCase(unittest.TestCase):
    def setUp(self):
        directory = ROOT / ".local/tests/member-demo"
        directory.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=directory)
        self.addCleanup(self.temp.cleanup)
        self.store = Store(self.temp.name)

    def graduation(self):
        return self.store.submit({"kind": "graduate", "name": "示例同学甲", "role": "master", "entryYear": 2021, "graduationAcknowledged": True})

    def update(self, changes=None, clears=None):
        return self.store.submit({"kind": "update", "name": "示例同学乙", "role": "master", "entryYear": 2025, "changes": changes or {}, "clearFields": clears or []})

    def approve_apply(self, request):
        self.store.review(request["id"], "approved")
        preview = self.store.preview(request["id"])
        return self.store.apply(request["id"], preview["token"])


class WorkflowTests(DemoTestCase):
    def test_graduation_changes_only_selected_experience(self):
        before = self.store.read()
        request = self.graduation()
        self.assertEqual(registry(before), registry(self.store.read()))
        self.store.review(request["id"], "approved")
        self.assertEqual(registry(before), registry(self.store.read()))
        preview = self.store.preview(request["id"])
        self.assertEqual(registry(before), registry(self.store.read()))
        self.store.apply(request["id"], preview["token"])
        after = self.store.read()
        self.assertTrue(after["experiences"][0]["graduationConfirmed"])
        self.assertEqual(before["experiences"][1:], after["experiences"][1:])
        self.assertEqual(before["members"], after["members"])

    def test_add_existing_member_experience_preserves_history(self):
        before = self.store.read()
        r = self.store.submit({"kind": "add", "name": "示例同学乙", "role": "phd", "entryYear": 2026, "researchIds": ["ts", "llm"]})
        self.approve_apply(r)
        after = self.store.read()
        self.assertEqual(after["members"], before["members"])
        self.assertEqual(after["experiences"][:-1], before["experiences"])
        self.assertEqual(after["experiences"][-1]["memberId"], "demo-person-002")

    def test_add_new_member(self):
        r = self.store.submit({"kind": "add", "name": "示例新同学", "role": "master", "entryYear": 2026, "researchIds": []})
        self.approve_apply(r)
        after = self.store.read()
        self.assertEqual(len(after["members"]), 5)
        self.assertEqual(after["members"][-1]["displayExperienceId"], after["experiences"][-1]["id"])

    def test_ambiguous_names_require_explicit_selection(self):
        state = self.store.read()
        m = copy.deepcopy(state["members"][1]);m["id"] = "demo-person-099";m["displayExperienceId"] = "demo-exp-099"
        e = copy.deepcopy(state["experiences"][2]);e["id"] = "demo-exp-099";e["memberId"] = m["id"]
        state["members"].append(m);state["experiences"].append(e);self.store._save(state)
        r = self.update({"url": "https://example.org/new"})
        with self.assertRaisesRegex(DemoError, "唯一匹配"):
            self.store.review(r["id"], "approved")
        self.assertEqual(self.store.read()["requests"][0]["review"], "pending")
        self.store.review(r["id"], "approved", target={"memberId": m["id"], "experienceId": e["id"]})
        p = self.store.preview(r["id"]);self.store.apply(r["id"], p["token"])
        self.assertNotIn("url", self.store.read()["members"][1])
        self.assertEqual(self.store.read()["members"][-1]["url"], "https://example.org/new")

    def test_missing_match_and_wrong_target_are_rejected(self):
        r = self.store.submit({"kind": "graduate", "name": "不存在的示例", "role": "phd", "entryYear": 2022, "graduationAcknowledged": True})
        with self.assertRaises(DemoError):self.store.review(r["id"], "approved")
        r = self.graduation()
        with self.assertRaises(DemoError):self.store.review(r["id"], "approved", target={"memberId": "demo-person-002", "experienceId": "demo-exp-003"})

    def test_update_homepage_and_clear(self):
        before = self.store.read()
        self.approve_apply(self.update({"url": "https://example.org/new", "name": ""}))
        after = self.store.read()
        self.assertEqual(after["experiences"], before["experiences"])
        self.assertEqual(after["members"][1]["name"], before["members"][1]["name"])
        self.approve_apply(self.update(clears=["url"]))
        self.assertNotIn("url", self.store.read()["members"][1])

    def test_direction_replacement_and_explicit_clear(self):
        before = copy.deepcopy(self.store.read()["experiences"])
        self.approve_apply(self.update({"researchIds": ["llm", "fl"]}))
        self.assertEqual(self.store.read()["experiences"][2]["researchIds"], ["llm", "fl"])
        self.approve_apply(self.update(clears=["researchIds"]))
        self.assertEqual(self.store.read()["experiences"][2]["researchIds"], [])
        self.assertEqual(before[3], self.store.read()["experiences"][3])

    def test_pending_and_rejected_cannot_apply(self):
        before = registry(self.store.read())
        r = self.graduation()
        for decision in ("pending", "rejected"):
            self.store.review(r["id"], decision, "请补充核对")
            with self.assertRaises(DemoError):self.store.preview(r["id"])
            with self.assertRaises(DemoError):self.store.apply(r["id"], "not-a-token")
            self.assertEqual(registry(self.store.read()), before)

    def test_double_apply_and_changed_review_refused(self):
        r = self.graduation();self.approve_apply(r)
        with self.assertRaisesRegex(DemoError, "重复"):
            self.store.apply(r["id"], "old-token")
        with self.assertRaises(DemoError):self.store.review(r["id"], "pending")

    def test_stale_preview_and_fresh_preview(self):
        r1 = self.graduation();self.store.review(r1["id"], "approved");old = self.store.preview(r1["id"])
        self.approve_apply(self.update({"url": "https://example.org/changed"}))
        with self.assertRaisesRegex(DemoError, "重新预览"):
            self.store.apply(r1["id"], old["token"])
        new = self.store.preview(r1["id"]);self.store.apply(r1["id"], new["token"])
        self.assertTrue(self.store.read()["experiences"][0]["graduationConfirmed"])

    def test_review_changes_invalidate_preview(self):
        r = self.graduation();self.store.review(r["id"], "approved");p = self.store.preview(r["id"])
        self.store.review(r["id"], "pending")
        with self.assertRaises(DemoError):self.store.apply(r["id"], p["token"])

    def test_persists_restart_and_reset_keeps_backup(self):
        r = self.graduation();self.approve_apply(r)
        reloaded = Store(self.temp.name)
        self.assertEqual(reloaded.read(), self.store.read())
        before = reloaded.path.read_bytes()
        with self.assertRaises(DemoError):reloaded.reset()
        reloaded.reset(True)
        self.assertEqual(reloaded.read()["requests"], [])
        self.assertFalse(reloaded.read()["experiences"][0]["graduationConfirmed"])
        self.assertTrue(any(p.read_bytes() == before for p in (reloaded.directory / "backups").glob("*.json")))

    def test_failed_write_keeps_registry_and_request_unchanged(self):
        r = self.graduation();self.store.review(r["id"], "approved");p = self.store.preview(r["id"])
        before = self.store.path.read_bytes()
        with patch("member_demo.core.os.replace", side_effect=OSError("simulated")), self.assertRaises(OSError):
            self.store.apply(r["id"], p["token"])
        self.assertEqual(self.store.path.read_bytes(), before)
        self.assertEqual(list(self.store.directory.glob(".state-*")), [])
        self.store.apply(r["id"], p["token"])

    def test_invalid_inputs_and_private_fields(self):
        for change in ({"url": "javascript:alert(1)"}, {"researchIds": ["missing"]}, {"entryYear": "20.5"}, {"departureReason": "private"}):
            with self.subTest(change=change), self.assertRaises(DemoError):self.update(change)
        with self.assertRaises(DemoError):self.update({"url": ""})
        with self.assertRaises(DemoError):self.update(clears=["name"])
        with self.assertRaises(DemoError):
            self.store.submit({"kind": "graduate", "name": "示例博士后丁", "role": "postdoc", "graduationAcknowledged": True})

    def test_clear_student_year_and_duplicate_experience_fail(self):
        r = self.update(clears=["entryYear"])
        with self.assertRaises(DemoError):self.store.review(r["id"], "approved")
        r = self.store.submit({"kind": "add", "name": "示例同学乙", "role": "master", "entryYear": 2025})
        with self.assertRaises(DemoError):self.store.review(r["id"], "approved")

    def test_csv_keeps_student_and_reviewer_fields_separate(self):
        r = self.graduation();self.store.review(r["id"], "rejected", "=not-a-formula")
        student = list(csv.DictReader(io.StringIO(self.store.export_csv().lstrip("\ufeff"))))
        reviewed = list(csv.DictReader(io.StringIO(self.store.export_csv(True).lstrip("\ufeff"))))
        self.assertNotIn("审核结果", student[0])
        self.assertEqual(reviewed[0]["审核结果"], "退回")
        self.assertEqual(reviewed[0]["审核备注"], "'=not-a-formula")

    def test_native_member_groups_escape_names_and_retain_experiences(self):
        self.approve_apply(self.graduation())
        state = self.store.read();state["members"][0]["name"] = '<script>alert(1)</script>'
        html = render_members(state)
        self.assertIn('class="year-group" open', html)
        self.assertIn('<details class="year-group graduates"><summary>已毕业', html)
        self.assertIn('2024级', html)
        self.assertIn('（21硕）', html)
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertIn('往届成员', html)  # Postdoc is not labelled graduated.

    def test_real_content_and_site_unchanged(self):
        def hashes():
            return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for name in ("content", "site") for p in (ROOT / name).rglob("*") if p.is_file()}
        before = hashes();self.approve_apply(self.graduation());self.store.export_csv(True);self.store.reset(True)
        self.assertEqual(before, hashes())


class HttpTests(DemoTestCase):
    def setUp(self):
        super().setUp()
        self.server = create_server(self.temp.name, 0)
        self.thread = threading.Thread(target=lambda: self.server.serve_forever(poll_interval=.05), daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def stop_server(self):
        self.server.shutdown();self.server.server_close();self.thread.join(timeout=2)

    def call(self, route, payload=None, headers=None):
        request = Request(self.base + route, data=json.dumps(payload).encode() if payload is not None else None, headers={"Content-Type": "application/json", **(headers or {})})
        return urlopen(request, timeout=3)

    def test_http_full_workflow_and_exports(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")
        with self.call("/") as response:self.assertIn('学生填报', response.read().decode())
        with self.call("/api/submit", {"kind": "graduate", "name": "示例同学甲", "role": "master", "entryYear": 2021, "graduationAcknowledged": True}) as response:r = json.load(response)
        with self.call("/api/review", {"requestId": r["id"], "decision": "approved"}) as response:json.load(response)
        with self.call("/api/preview", {"requestId": r["id"]}) as response:p = json.load(response)
        with self.call("/api/apply", {"requestId": r["id"], "token": p["token"]}) as response:json.load(response)
        with self.call("/members") as response:self.assertIn('已毕业', response.read().decode())
        with self.call("/api/export", {"reviewed": True}) as response:export = json.load(response)
        self.assertTrue((ROOT / export["path"]).exists())
        with self.call(export["url"]) as response:self.assertIn('审核结果', response.read().decode('utf-8-sig'))

    def test_errors_no_origin_access_and_no_directory_serving(self):
        for route, payload, headers, status in (
            ("/api/reset", {"confirmed": True}, {"Origin": "https://example.org"}, 403),
            ("/api/reset", {"confirmed": False}, {}, 400),
            ("/content/members.json", None, {}, 404),
            ("/exports/../../state.json", None, {}, 404),
            ("/api/submit", {"kind": []}, {}, 400),
        ):
            with self.subTest(route=route), self.assertRaises(HTTPError) as context:self.call(route, payload, headers)
            self.assertEqual(context.exception.code, status)


if __name__ == "__main__":
    unittest.main()
