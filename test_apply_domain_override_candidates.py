import unittest

import apply_domain_override_candidates as adoc


class TestApplyDomainOverrideCandidates(unittest.TestCase):
    def test_merge_overrides_adds_only_missing_domains(self):
        existing = {
            "psychologytoday.com": "directory",
            "canada.ca": "government",
        }
        high_confidence = [
            {"domain": "reddit.com", "suggested_type": "media"},
            {"domain": "psychologytoday.com", "suggested_type": "directory"},
        ]

        merged, added, skipped = adoc.merge_overrides(existing, high_confidence)

        self.assertEqual(merged["reddit.com"], "media")
        self.assertEqual(merged["psychologytoday.com"], "directory")
        self.assertEqual(added, [("reddit.com", "media")])
        self.assertEqual(skipped, [("psychologytoday.com", "directory", "already_present")])


if __name__ == "__main__":
    unittest.main()
