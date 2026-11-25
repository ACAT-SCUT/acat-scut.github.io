"""Source-validation regression cases; no network or generated-file writes."""
import copy
import unittest
from unittest.mock import patch

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
        self.reject(lambda d: d["homepage"]["featured"].append({"paper": "missing"}), "unknown reference")

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

    def test_update_reference_checked(self):
        self.reject(lambda d: d["homepage"]["updates"][0].update(paper="missing"), "unknown reference")

    def test_invalid_project_metadata_rejected(self):
        self.reject(lambda d: d["projects"][0].update(category="unknown"), "invalid project category")
        self.reject(lambda d: d["projects"][0].update(period="2028.01—2025.01"), "ends before it starts")

    def test_presentation_is_separate_from_venue(self):
        self.reject(lambda d: d["papers"][0].update(venue="ICML · Oral"), "separate from venue")
        self.reject(lambda d: d["papers"][0].update(presentation="Unknown"), "invalid presentation format")

    def test_homepage_recognition_is_separate_from_presentation(self):
        self.reject(lambda d: d["homepage"]["updates"][0].update(recognition=""), "recognition must be nonempty")
        self.reject(lambda d: d["homepage"]["featured"][0].update(format="Oral"), "use paper presentation")

    def test_paper_chinese_explanation_requires_one_secure_url(self):
        self.reject(lambda d: d["papers"][0].update(chineseExplanationUrl=["https://example.org"]),
                    "Chinese explanation: URL must use https")
        self.reject(lambda d: d["papers"][0].update(chineseExplanationUrl="http://example.org/explainer"),
                    "Chinese explanation: URL must use https")
        self.reject(lambda d: d["papers"][0].update(coverage=[]), "select one article for chineseExplanationUrl")

    def test_homepage_title_uses_paper_id(self):
        self.reject(lambda d: d["homepage"]["updates"][0].update(url="https://example.org/report"),
                    "title links use the paper ID")

    def test_unknown_corresponding_author_rejected(self):
        self.reject(lambda d: d["papers"][0].update(correspondingAuthors=["Unknown author"]), "listed paper authors")

    def test_rich_text_cannot_inject_markup(self):
        self.reject(lambda d: d["meta"]["contact"].update(intro=[{"text": "test", "tag": "script"}]), "invalid text segment")

    def test_asset_path_cannot_escape_site(self):
        self.reject(lambda d: d["papers"][0].update(figure="assets/../../private.png"), "site-relative")

    def test_bad_types_are_reported(self):
        self.reject(lambda d: d["papers"][0].update(area=[]), "unknown research area")
        self.reject(lambda d: d["meta"]["identity"].update(affiliation="wrong"), "affiliation must")

    def test_wechat_account_requires_name_and_local_qr_code(self):
        self.reject(lambda d: d["meta"]["wechat"].update(name=""), "team wechat: name must be nonempty")
        self.reject(lambda d: d["meta"]["wechat"].update(qrCode="https://example.org/qr.png"), "team wechat QR code")
        data = copy.deepcopy(self.source)
        del data["meta"]["wechat"]
        self.assertEqual(validate_data(data), [])

    def test_postdoc_notice_requires_secure_url_and_publication_date(self):
        self.reject(lambda d: d["meta"]["contact"].update(postdocNotice={
            "url": "http://example.org/notice", "publishedOn": "2026-02-30"
        }), "team postdoc notice: URL must use https")
        self.reject(lambda d: d["meta"]["contact"].update(postdocNotice={
            "url": "https://example.org/notice", "publishedOn": "2026-02-30"
        }), "team postdoc notice: invalid publishedOn")

    def test_join_page_omits_postdoc_notice_when_removed(self):
        import build

        data = copy.deepcopy(self.source)
        contact = data["meta"]["contact"]
        contact.pop("postdocNotice", None)
        self.assertEqual(validate_data(data), [])
        with patch.object(build, "CONTACT", contact):
            without_notice = build.join_page()
            self.assertIn('id="graduate-admissions"', without_notice)
            self.assertNotIn('id="postdoc"', without_notice)
            self.assertIn('href="join.html"', build.home())
            self.assertIn(f'mailto:{contact["email"]}', build.home())
            contact["postdocNotice"] = {"url": "https://example.org/notice", "publishedOn": "2026-04-09"}
            with_notice = build.join_page()
            self.assertIn('id="postdoc"', with_notice)
            self.assertIn('<time datetime="2026-04-09">2026 年 4 月 9 日</time>', with_notice)
            self.assertIn('href="https://example.org/notice">查看学院原公告', with_notice)

    def test_same_name_does_not_replace_stable_identity(self):
        data = copy.deepcopy(self.source)
        data["members"][1]["name"] = data["members"][0]["name"]
        self.assertEqual(validate_data(data), [])


if __name__ == "__main__":
    unittest.main()
