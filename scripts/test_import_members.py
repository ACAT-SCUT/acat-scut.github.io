"""Reviewed formal requests against isolated copies of the canonical content."""
import copy
import csv
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from content import load_data
from member_registry import load_registry, legacy_members, validate_registry
from member_requests import ROOT, apply_import, prepare_import, recover_pending, restore_batch, runtime
from member_requests import exclusive
from member_demo.core import DemoError
from member_render import render_groups


class ImportTests(unittest.TestCase):
    def setUp(self):
        work = ROOT / ".local/tests/formal-members"
        work.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=work)
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        shutil.copytree(ROOT / "content", self.directory, dirs_exist_ok=True)
        self.state = load_registry(self.directory)
        self.person = self.state["members"][0]
        self.experience = self.state["experiences"][0]

    def row(self, **changes):
        return {"申请编号": "test-1", "申请类型": "修改资料", "姓名": self.person["name"], "身份": self.experience["role"], "入学年份": str(self.experience["entryYear"]), "修改字段": "个人主页", "新值": "https://example.org/new", "审核结果": "通过", **changes}

    def csv(self, rows):
        path = self.directory / "reviewed.csv"
        fields = list(dict.fromkeys(key for row in rows for key in row)) or ["申请编号", "审核结果"]
        with path.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
            writer.writeheader();writer.writerows(rows)
        return path

    def plan(self, rows):
        return prepare_import(self.state, self.csv(rows))

    def test_canonical_projection_and_private_fields(self):
        view = load_data(self.directory)
        self.assertEqual(len(view["members"]), len(self.state["members"]))
        self.assertEqual(view["members"][0]["role"], self.experience["role"])
        state = copy.deepcopy(self.state);state["experiences"][0]["departureDate"] = "private"
        with self.assertRaisesRegex(DemoError, "unsupported"):
            validate_registry(state)

    def test_unknown_direction_and_bad_primary_rejected(self):
        for mutate in (lambda s: s["experiences"][0].update(researchIds=["missing"]), lambda s: s["members"][0].update(displayExperienceId="missing")):
            state = copy.deepcopy(self.state);mutate(state)
            with self.assertRaises(DemoError):validate_registry(state)

    def test_preview_and_apply_keep_unmentioned_people_and_experiences(self):
        before = {name: (self.directory / name).read_bytes() for name in ("members.json", "member-experiences.json")}
        plan = self.plan([self.row()])
        self.assertEqual(before, {name: (self.directory / name).read_bytes() for name in before})
        batch = apply_import(self.directory, plan)
        updated = load_registry(self.directory)
        self.assertEqual(updated["members"][0]["url"], "https://example.org/new")
        self.assertEqual(updated["members"][1:], self.state["members"][1:])
        self.assertEqual(updated["experiences"], self.state["experiences"])
        self.assertTrue((runtime(self.directory) / "batches" / batch / "manifest.json").exists())

    def test_pending_rejected_and_blank_approval_never_apply(self):
        for review in ("", "待核对", "退回"):
            plan = self.plan([self.row(审核结果=review, 新值="javascript:bad")])
            self.assertEqual(plan["changes"], [])
            self.assertIsNone(apply_import(self.directory, plan))
        self.assertEqual(load_registry(self.directory), self.state)

    def test_new_experience_preserves_person_history_and_anchor(self):
        row = self.row(申请类型="新增经历", 身份="master", 入学年份="2027", 研究方向="ts;llm", 个人主页="")
        apply_import(self.directory, self.plan([row]))
        after = load_registry(self.directory)
        self.assertEqual(after["members"], self.state["members"])
        self.assertEqual(after["experiences"][:-1], self.state["experiences"])
        self.assertEqual(after["experiences"][-1]["memberId"], self.person["id"])
        self.assertFalse(after["experiences"][-1]["id"].startswith("demo-"))

    def test_new_person_allocates_stable_non_demo_ids(self):
        row = self.row(申请类型="新增经历", 姓名="测试新增成员", 身份="硕士", 入学年份="2026", 研究方向="", 个人主页="")
        apply_import(self.directory, self.plan([row]))
        after = load_registry(self.directory)
        self.assertEqual(len(after["members"]), len(self.state["members"]) + 1)
        self.assertTrue(after["members"][-1]["id"].startswith("member-"))

    def test_graduation_is_experience_specific(self):
        row = self.row(申请类型="申请毕业", 确认毕业="是")
        apply_import(self.directory, self.plan([row]))
        after = load_registry(self.directory)
        self.assertTrue(after["experiences"][0]["graduationConfirmed"])
        self.assertEqual(after["experiences"][0]["status"], "former")
        self.assertEqual(after["experiences"][1:], self.state["experiences"][1:])
        self.assertEqual(after["members"], self.state["members"])

    def test_ambiguous_person_needs_explicit_target(self):
        s = copy.deepcopy(self.state)
        person = copy.deepcopy(s["members"][0]);person.update(id="person-extra", displayExperienceId="experience-extra")
        exp = copy.deepcopy(s["experiences"][0]);exp.update(id="experience-extra", memberId="person-extra")
        s["members"].append(person);s["experiences"].append(exp)
        path = self.csv([self.row()])
        with self.assertRaisesRegex(DemoError, "唯一匹配"):
            prepare_import(s, path)
        path = self.csv([self.row(匹配人员编号=self.person["id"], 匹配经历编号=self.experience["id"])])
        plan = prepare_import(s, path)
        self.assertEqual(plan["updated"]["members"][-1], person)

    def test_blank_keeps_value_and_clear_is_explicit(self):
        plan = self.plan([self.row(新值="")])
        self.assertEqual(plan["changes"], [])
        row = self.row(修改字段="研究方向", 新值="", 明确清空="是")
        plan = self.plan([row])
        self.assertEqual(plan["updated"]["experiences"][0]["researchIds"], [])
        with self.assertRaises(DemoError):self.plan([self.row(修改字段="入学年份", 新值="", 明确清空="是")])

    def test_duplicate_invalid_and_private_input_stops_whole_batch(self):
        for rows in ([self.row(), self.row()], [self.row(), self.row(申请编号="test-2", 新值="javascript:bad")], [self.row(离组原因="private")], [self.row(申请类型="申请毕业", 确认毕业="")], [self.row(修改字段="研究方向", 新值="missing")]):
            with self.subTest(rows=rows), self.assertRaises(DemoError):self.plan(rows)
        self.assertEqual(load_registry(self.directory), self.state)

    def test_demo_export_cannot_enter_formal_registry(self):
        with self.assertRaisesRegex(DemoError, "演示申请"):
            self.plan([self.row(数据用途="演示")])
        with self.assertRaisesRegex(DemoError, "演示数据"):
            self.plan([self.row(匹配人员编号="demo-person-001", 匹配经历编号="demo-exp-001")])

    def test_ledger_blocks_replay_and_reused_id(self):
        plan = self.plan([self.row()]);apply_import(self.directory, plan)
        ledger = json.loads((runtime(self.directory) / "ledger.json").read_text(encoding="utf-8"))
        s = load_registry(self.directory)
        replay = prepare_import(s, self.csv([self.row()]), ledger)
        self.assertEqual(replay["changes"], [])
        with self.assertRaises(DemoError):prepare_import(s, self.csv([self.row(新值="https://example.org/different")]), ledger)

    def test_stale_plan_does_not_overwrite_other_changes(self):
        plan = self.plan([self.row()])
        people = copy.deepcopy(self.state["members"]);people[1]["name"] += "测试修改"
        (self.directory / "members.json").write_text(json.dumps(people, ensure_ascii=False), encoding="utf-8")
        with self.assertRaisesRegex(DemoError, "重新预览"):
            apply_import(self.directory, plan)
        self.assertEqual(load_registry(self.directory)["members"], people)

    def test_failure_restores_all_files_and_ledger(self):
        plan = self.plan([self.row(申请类型="新增经历", 身份="master", 入学年份="2027", 研究方向="ts")])
        before = {name: (self.directory / name).read_bytes() for name in ("members.json", "member-experiences.json")}
        real_replace = __import__("os").replace
        def fail_second(source, target):
            if Path(target).name == "member-experiences.json":raise OSError("simulated write failure")
            return real_replace(source, target)
        with patch("member_requests.os.replace", fail_second), self.assertRaises(OSError):apply_import(self.directory, plan)
        self.assertEqual(before, {name: (self.directory / name).read_bytes() for name in before})
        self.assertFalse((runtime(self.directory) / "ledger.json").exists())
        self.assertEqual(list(self.directory.glob(".member-update-*")), [])

    def test_restore_batch_and_refuse_to_overwrite_newer_work(self):
        before = {name: (self.directory / name).read_bytes() for name in ("members.json", "member-experiences.json")}
        batch = apply_import(self.directory, self.plan([self.row()]))
        restore_batch(self.directory, batch)
        self.assertEqual(before, {name: (self.directory / name).read_bytes() for name in before})
        self.assertFalse((runtime(self.directory) / "ledger.json").exists())
        batch = apply_import(self.directory, self.plan([self.row()]))
        people = load_registry(self.directory)["members"];people[1]["name"] += "更新"
        (self.directory / "members.json").write_text(json.dumps(people, ensure_ascii=False), encoding="utf-8")
        with self.assertRaisesRegex(DemoError, "已有其他修改"):
            restore_batch(self.directory, batch)

    def test_interrupted_transaction_recovers(self):
        plan = self.plan([self.row()]);batch = apply_import(self.directory, plan)
        manifest_path = runtime(self.directory) / "batches" / batch / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"));manifest["status"] = "prepared"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        recover_pending(self.directory)
        self.assertEqual(load_registry(self.directory), self.state)

    def test_cli_refuses_simultaneous_maintenance(self):
        path = self.csv([self.row()])
        command = [sys.executable, "-B", str(ROOT / "scripts/import_members.py"), str(path), "--content-dir", str(self.directory)]
        with exclusive(self.directory):
            result = subprocess.run(command, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
        self.assertEqual(load_registry(self.directory), self.state)

    def test_blank_template_is_noop(self):
        plan = prepare_import(self.state, ROOT / "content/templates/member-requests.csv")
        self.assertEqual(plan["changes"], [])
        self.assertEqual(plan["updated"], self.state)

    def test_new_direction_uses_source_data_not_demo_constants(self):
        state = copy.deepcopy(self.state)
        state["directions"].append({"id": "new-area", "title": "测试方向"})
        path = self.csv([self.row(修改字段="研究方向", 新值="测试方向")])
        plan = prepare_import(state, path)
        self.assertEqual(plan["updated"]["experiences"][0]["researchIds"], ["new-area"])

    def test_cli_requires_fresh_preview_then_applies_and_restores(self):
        path = self.csv([self.row()])
        command = [sys.executable, "-B", "-X", "utf8", str(ROOT / "scripts/import_members.py"), str(path), "--content-dir", str(self.directory)]
        self.assertNotEqual(subprocess.run(command + ["--apply"], capture_output=True).returncode, 0)
        preview = subprocess.run(command, check=True, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(json.loads(preview.stdout)["mode"], "preview")
        self.assertEqual(load_registry(self.directory), self.state)
        applied = subprocess.run(command + ["--apply"], check=True, capture_output=True, text=True, encoding="utf-8")
        batch = json.loads(applied.stdout)["batchId"]
        subprocess.run([sys.executable, "-B", str(ROOT / "scripts/import_members.py"), "--content-dir", str(self.directory), "--restore", batch], check=True, capture_output=True)
        self.assertEqual(load_registry(self.directory), self.state)

    def test_renderer_keeps_person_and_experience_anchors_unique(self):
        html = render_groups(self.state["members"], self.state["experiences"], self.state["directions"])
        from html.parser import HTMLParser
        class Tags(HTMLParser):
            def __init__(self):super().__init__();self.ids=[]
            def handle_starttag(self, tag, attrs):
                attrs=dict(attrs)
                if "id" in attrs:self.ids.append(attrs["id"])
        tags=Tags();tags.feed(html)
        self.assertEqual(len(tags.ids), len(set(tags.ids)))
        for m in self.state["members"]:self.assertIn("member-" + m["id"], tags.ids)
        for experience in self.state["experiences"]:
            self.assertIn("experience-" + experience["id"], tags.ids)
        self.assertIn("former", tags.ids)
        self.assertNotIn("已毕业", html)
        self.assertNotIn("<details", html)
        for g in self.state["directions"]:self.assertIn("members-"+g["id"], tags.ids)


if __name__ == "__main__":
    unittest.main()
