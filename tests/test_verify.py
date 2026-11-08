import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import verify_all


class AuditTests(unittest.TestCase):
    def test_distinguishes_absence_skip_and_failure(self):
        entry = {"key": "demo", "kind": "article", "title": "Titolo"}
        with (
            patch.object(verify_all, "query_openalex") as openalex,
            patch.object(verify_all, "query_semantic_scholar", return_value={"total": 0, "data": []}),
            patch.object(verify_all, "query_opac") as opac,
            patch.object(verify_all.time, "sleep"),
        ):
            results = verify_all.audit_entry(entry, "semantic-scholar")
            self.assertEqual(results["openalex"]["status"], "not_queried")
            self.assertEqual(results["semantic-scholar"]["status"], "not_found")
            self.assertEqual(results["opac-sbn"]["status"], "not_queried")
            openalex.assert_not_called()
            opac.assert_not_called()

            results = verify_all.audit_entry({**entry, "title": ""})
            self.assertTrue(all(result["status"] == "not_queried" for result in results.values()))

            opac.return_value = {"error": "HTTP 503"}
            results = verify_all.audit_entry({**entry, "kind": "book"}, "opac-sbn")
            self.assertEqual(results["opac-sbn"], {"status": "error", "info": "HTTP 503"})
            self.assertEqual(results["semantic-scholar"]["status"], "not_queried")

    def test_incomplete_payload_is_not_a_negative_result(self):
        status, _ = verify_all.score_match({}, {"meta": {"count": 8}, "results": []}, "openalex")
        self.assertEqual(status, "error")


if __name__ == "__main__":
    unittest.main()
