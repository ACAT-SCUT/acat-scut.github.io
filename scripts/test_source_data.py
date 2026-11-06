"""Source-validation regression cases; no network or generated-file writes."""
import copy
import unittest

from validate import validate_data
from content import load_data


class SourceValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = load_data()

    def reject(self, mutate, message):
        data = copy.deepcopy(self.source)
        mutate(data)
        self.assertTrue(any(message in error for error in validate_data(data)))

    def test_current_source_valid(self):
        self.assertEqual(validate_data(self.source), [])

    def test_unknown_direction_caught(self):
        self.reject(lambda d: d["papers"][0].update(area="missing"), "unknown research area")

    def test_missing_member_reference_caught(self):
        self.reject(lambda d: d["research"][0]["memberIds"].append("missing"), "unknown reference")

    def test_missing_featured_paper_caught(self):
        self.reject(lambda d: d["homepage"]["featured"].append("missing"), "unknown reference")

    def test_duplicate_paper_caught(self):
        self.reject(lambda d: d["papers"].append(copy.deepcopy(d["papers"][0])), "duplicate stable id")

    def test_departure_fields_rejected(self):
        self.reject(lambda d: d["members"][0].update(departureDate="not-for-public-data"), "unsupported member fields")

    def test_unknown_visibility_rejected(self):
        self.reject(lambda d: d["papers"][0].update(codeVisibility="unknown"), "invalid code visibility")

    def test_paper_id_survives_bibliography_changes(self):
        from validate import paper_id
        data = copy.deepcopy(self.source)
        before = paper_id(data["papers"][0])
        data["papers"][0].update(name="Renamed", year=2027)
        self.assertEqual(before, paper_id(data["papers"][0]))
        self.assertEqual(validate_data(data), [])

    def test_invalid_project_link_rejected(self):
        self.reject(lambda d: d["projects"][0].update(url="javascript:alert(1)"), "URL must use https")

    def test_recognition_reference_checked(self):
        self.reject(lambda d: d["homepage"]["recognition"][0].update(paper="missing"), "unknown reference")

    def test_rich_text_cannot_inject_markup(self):
        self.reject(lambda d: d["meta"]["contact"].update(intro=[{"text": "test", "tag": "script"}]), "invalid text segment")

    def test_asset_path_cannot_escape_site(self):
        self.reject(lambda d: d["papers"][0].update(figure="assets/../../private.png"), "site-relative")

    def test_bad_types_are_reported(self):
        self.reject(lambda d: d["papers"][0].update(area=[]), "unknown research area")
        self.reject(lambda d: d["meta"]["identity"].update(affiliation="wrong"), "affiliation must")

    def test_same_name_does_not_replace_stable_identity(self):
        data = copy.deepcopy(self.source)
        data["members"][1]["name"] = data["members"][0]["name"]
        self.assertEqual(validate_data(data), [])


if __name__ == "__main__":
    unittest.main()
