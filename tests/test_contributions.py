import copy
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from update_contributions import contribution, refresh, START, END


class ContributionTests(unittest.TestCase):
    def setUp(self):
        self.pr = {
            "base": {"repo": {"private": False, "full_name": "upstream/project", "owner": {"login": "upstream"}}},
            "user": {"login": "DatenpflegeNordHL"}, "number": 12,
            "merged_at": "2026-09-04T20:25:13Z", "title": "Fix config",
            "body": "PRIVATE BODY MUST NEVER APPEAR",
        }

    def test_accepts_public_merged_authored_upstream_only(self):
        self.assertIn("upstream/project #12", contribution(self.pr)[1])
        for change in ["private", "unmerged", "other_author", "own_repo", "business_org"]:
            pr = copy.deepcopy(self.pr)
            if change == "private": pr["base"]["repo"]["private"] = True
            if change == "unmerged": pr["merged_at"] = None
            if change == "other_author": pr["user"]["login"] = "someone-else"
            if change == "own_repo": pr["base"]["repo"]["owner"]["login"] = "datenpflegenordhl"
            if change == "business_org": pr["base"]["repo"]["owner"]["login"] = "datenpflegenord-de"
            with self.subTest(change=change): self.assertIsNone(contribution(pr))

    def test_preserves_manual_content_and_omits_bodies(self):
        original = f"Manual skills\n{START}\nold\n{END}\nManual journey"
        updated = refresh(original, [self.pr])
        self.assertTrue(updated.startswith("Manual skills\n"))
        self.assertTrue(updated.endswith("\nManual journey"))
        self.assertNotIn(self.pr["body"], updated)
        self.assertEqual(updated, refresh(updated, [self.pr]))

    def test_escapes_untrusted_titles(self):
        self.pr["title"] = "<img src=x> [click](evil)\n# heading"
        line = contribution(self.pr)[1]
        self.assertNotIn("<img", line)
        self.assertIn(r"\[click\]\(evil\)", line)
        self.assertNotIn("\n", line)

    def test_rejects_missing_duplicate_or_reversed_markers(self):
        for text in ["none", START + START + END, END + START]:
            with self.subTest(text=text), self.assertRaises(ValueError): refresh(text, [self.pr])

    def test_caps_list_at_ten(self):
        prs = []
        for number in range(1, 15):
            pr = copy.deepcopy(self.pr)
            pr["number"] = number
            prs.append(pr)
        output = refresh(START + END, prs)
        self.assertEqual(10, output.count("\n- "))


if __name__ == "__main__":
    unittest.main()
