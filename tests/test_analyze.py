import unittest
import tempfile
from pathlib import Path

from analyze import analyze, main


class AnalyzerTests(unittest.TestCase):
    def test_input_log_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "log.csv"
            original = "rpm,tps,afr\n4000,20,14.0\n"
            path.write_text(original, encoding="utf-8")
            self.assertEqual(main([str(path), "-o", str(path)]), 2)
            self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_estimated_trim_adds_fuel_when_observed_afr_is_leaner(self):
        rows = [{"rpm": 4000, "tps": 20, "afr": 14.0} for _ in range(5)]
        result = analyze(rows, target_afr=13.0, rpm_bin=500, tps_bin=10, min_samples=5)
        self.assertEqual(result[0]["status"], "review")
        self.assertAlmostEqual(result[0]["estimated_fuel_trim_percent"], 7.69, places=2)

    def test_insufficient_samples_suppresses_trim(self):
        rows = [{"rpm": 4000, "tps": 20, "afr": 14.0}]
        result = analyze(rows, target_afr=13.0, rpm_bin=500, tps_bin=10, min_samples=5)
        self.assertEqual(result[0]["status"], "insufficient samples")
        self.assertEqual(result[0]["estimated_fuel_trim_percent"], "")


if __name__ == "__main__":
    unittest.main()
