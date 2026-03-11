import json
import os
import tempfile
import unittest

import openpyxl
import yaml

import refresh_analysis_outputs as rao


class TestRefreshAnalysisOutputs(unittest.TestCase):
    def test_refresh_json_reclassifies_rows_from_overrides(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = os.path.join(tmpdir, "market_analysis_v2.json")
            overrides_path = os.path.join(tmpdir, "domain_overrides.yml")
            data = {
                "organic_results": [
                    {
                        "Link": "https://example.com/a",
                        "Source": "example.com",
                        "Entity_Type": "N/A",
                    },
                    {
                        "Link": "https://reddit.com/r/test",
                        "Source": "reddit.com",
                        "Entity_Type": "N/A",
                    },
                ]
            }
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f)
            with open(overrides_path, "w", encoding="utf-8") as f:
                yaml.safe_dump({"example.com": "counselling"}, f)

            classifier = rao.EntityClassifier(override_file=overrides_path)
            refreshed, updated, changed = rao.refresh_json(json_path, classifier)

            self.assertEqual(updated, 2)
            self.assertEqual(changed, 2)
            self.assertEqual(refreshed["organic_results"][0]["Entity_Type"], "counselling")
            self.assertEqual(refreshed["organic_results"][1]["Entity_Type"], "media")

    def test_refresh_xlsx_updates_entity_type_column(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            xlsx_path = os.path.join(tmpdir, "market_analysis_v2.xlsx")
            overrides_path = os.path.join(tmpdir, "domain_overrides.yml")
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Organic_Results"
            ws.append(["Link", "Source", "Entity_Type"])
            ws.append(["https://example.com/a", "example.com", "N/A"])
            wb.save(xlsx_path)
            with open(overrides_path, "w", encoding="utf-8") as f:
                yaml.safe_dump({"example.com": "legal"}, f)

            classifier = rao.EntityClassifier(override_file=overrides_path)
            updated, changed = rao.refresh_xlsx(xlsx_path, classifier)

            self.assertEqual(updated, 1)
            self.assertEqual(changed, 1)
            wb_check = openpyxl.load_workbook(xlsx_path)
            self.assertEqual(wb_check["Organic_Results"]["C2"].value, "legal")


if __name__ == "__main__":
    unittest.main()
