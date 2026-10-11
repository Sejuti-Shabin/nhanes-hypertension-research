"""Smoke tests for the public GitHub packaging only (not survey inference)."""
import unittest
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

class PublicReleaseSmokeTests(unittest.TestCase):
    def test_essential_research_assets_present(self):
        for rel in ['README.md','MANUSCRIPT.md','research_protocol.md',
                    'docs/academic_writing_sample_DRAFT.pdf',
                    'src/pipeline.py','r/survey_analysis.R','data/source_manifest.json',
                    'outputs/regression.csv','figures/awareness_by_insurance.png',
                    '.gitignore','CONTRIBUTIONS.md']:
            self.assertTrue((ROOT/rel).is_file(), rel)
    def test_no_archived_or_participant_level_files_shipped(self):
        for rel in ['audit','data/raw/DEMO_J.xpt', 'outputs/design_frame.csv',
                    'outputs/observation_influence.csv', 'outputs/pir_response_diagnostics.csv',
                    'outputs/r_model_objects.rds','.build-libs']:
            self.assertFalse((ROOT/rel).exists(), rel)
    def test_snapshot_estimate_is_unchanged(self):
        r = pd.read_csv(ROOT/'outputs/regression.csv')
        m = r[(r.model=='M3')&(r.term=='uninsured')].iloc[0]
        self.assertAlmostEqual(float(m.odds_ratio),0.60,places=2)
        self.assertEqual(int(m.n),1534)
        self.assertLess(float(m.ci_low),1.0)
        self.assertGreater(float(m.ci_high),1.0)

if __name__ == '__main__':unittest.main()
