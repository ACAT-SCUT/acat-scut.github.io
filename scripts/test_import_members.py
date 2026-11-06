"""Exercise CSV updates against isolated local data; never modify website data."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from content import FILES, json_text, load_data
from import_members import apply_import, prepare_import
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class ImportTests(unittest.TestCase):
    def setUp(self):
        work = ROOT / ".local" / "tests"
        work.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=work)
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.data = load_data()
        for key, filename in FILES.items():
            (self.directory / filename).write_text(json_text(self.data[key]), encoding="utf-8", newline="\n")

    def csv(self, text):
        path = self.directory / "reviewed.csv"
        path.write_text(text, encoding="utf-8-sig", newline="\n")
        return path

    def prepare(self, text):
        return prepare_import(self.data, self.csv(text))

    def test_update_preserves_unmentioned_rows_and_blank_fields(self):
        result, changes = self.prepare("id,name,url\nm001,,https://example.org/person\n")
        self.assertEqual(result["members"][0]["name"], self.data["members"][0]["name"])
        self.assertEqual(result["members"][1:], self.data["members"][1:])
        self.assertEqual(len(changes), 1)
        self.assertNotIn("url", self.data["members"][0])

    def test_add_requires_explicit_action_and_complete_fields(self):
        result, _ = self.prepare("action,id,name,role,status,entryYear,researchIds\nadd,m090,测试成员,master,current,2026,power;ts\n")
        self.assertEqual(len(result["members"]), 90)
        self.assertIn("m090", result["research"][0]["memberIds"])
        with self.assertRaises(ValueError):
            self.prepare("id,name\nm090,测试成员\n")
        with self.assertRaises(ValueError):
            self.prepare("action,id,name\nadd,m090,测试成员\n")

    def test_duplicates_rejected_without_partial_writes(self):
        before = (self.directory / "members.json").read_bytes()
        with self.assertRaises(ValueError):
            self.prepare("id,url\nm001,https://example.org\nm001,https://example.com\n")
        self.assertEqual((self.directory / "members.json").read_bytes(), before)

    def test_unknown_direction_and_invalid_url_rejected(self):
        for text in ("id,researchIds\nm001,missing\n", "id,url\nm001,javascript:alert(1)\n", "id,researchIds\nm001,power;power\n"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.prepare(text)

    def test_private_or_unknown_columns_rejected(self):
        with self.assertRaises(ValueError):
            self.prepare("id,departureDate\nm001,2026-01-01\n")

    def test_explicit_clear_and_direction_update(self):
        self.data["members"][0]["url"] = "https://example.org"
        result, _ = self.prepare("id,url,researchIds\nm001,__CLEAR__,__CLEAR__\n")
        self.assertNotIn("url", result["members"][0])
        self.assertTrue(all("m001" not in g["memberIds"] for g in result["research"]))
        with self.assertRaises(ValueError):
            self.prepare("id,name\nm001,__CLEAR__\n")

    def test_invalid_role_status_year_and_required_clear(self):
        for field, value in (("role", "student"), ("status", "graduated"), ("entryYear", "abc"), ("entryYear", "__CLEAR__")):
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.prepare(f"id,{field}\nm001,{value}\n")

    def test_empty_template_is_noop(self):
        result, changes = prepare_import(self.data, ROOT / "content/templates/members.csv")
        self.assertEqual(result, self.data)
        self.assertEqual(changes, [])

    def test_cli_preview_then_apply_and_reload(self):
        csv_path = self.csv("id,url,researchIds\nm001,https://example.org/person,ts\n")
        script = str(ROOT / "scripts/import_members.py")
        command = [sys.executable, "-B", "-X", "utf8", script, str(csv_path), "--content-dir", str(self.directory)]
        before = {filename: (self.directory / filename).read_bytes() for filename in FILES.values()}
        preview = subprocess.run(command, check=True, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(json.loads(preview.stdout)["mode"], "preview")
        self.assertEqual(before, {filename: (self.directory / filename).read_bytes() for filename in FILES.values()})
        subprocess.run(command + ["--apply"], check=True, capture_output=True)
        updated = load_data(self.directory)
        self.assertEqual(updated["members"][0]["url"], "https://example.org/person")
        self.assertEqual(updated["members"][1:], self.data["members"][1:])
        for key in ("meta", "papers", "projects", "homepage"):
            self.assertEqual(updated[key], self.data[key])

    def test_stale_import_refused(self):
        result, _ = self.prepare("id,name\nm001,测试改名\n")
        (self.directory / "research.json").write_text("[]", encoding="utf-8")
        with self.assertRaises(ValueError):
            apply_import(self.directory, self.data, result)

    def test_write_failure_restores_both_files(self):
        result, _ = self.prepare("id,name,researchIds\nm001,测试改名,ts\n")
        originals = {name: (self.directory / name).read_bytes() for name in ("members.json", "research.json")}
        real_replace = Path.replace
        def fail_second(path, destination):
            if Path(destination).name == "research.json":
                raise OSError("simulated write failure")
            return real_replace(path, destination)
        with patch.object(Path, "replace", fail_second), self.assertRaises(OSError):
            apply_import(self.directory, self.data, result)
        self.assertEqual(originals, {name: (self.directory / name).read_bytes() for name in originals})
        self.assertEqual(list(self.directory.glob(".import-*")), [])


if __name__ == "__main__":
    unittest.main()
