import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analyze import cpu_breakdown

class CpuTest(unittest.TestCase):
    def test_separates_iowait_and_steal(self):
        rows = [dict(cpu_total_ticks=1000,cpu_idle_ticks=500,cpu_iowait_ticks=100,cpu_steal_ticks=20),
                dict(cpu_total_ticks=1100,cpu_idle_ticks=550,cpu_iowait_ticks=120,cpu_steal_ticks=30)]
        self.assertEqual(cpu_breakdown(rows),dict(busy_pct=20,iowait_pct=20,steal_pct=10,busy_plus_steal_pct=30))

    def test_legacy_does_not_invent_steal(self):
        rows = [dict(cpu_total_ticks=0,cpu_idle_ticks=0,cpu_iowait_ticks=0),
                dict(cpu_total_ticks=100,cpu_idle_ticks=50,cpu_iowait_ticks=20)]
        result=cpu_breakdown(rows)
        self.assertEqual(result['busy_plus_steal_pct'],30)
        self.assertEqual(result['iowait_pct'],20)
        self.assertIsNone(result['busy_pct'])
        self.assertIsNone(result['steal_pct'])

    def test_no_interval(self):
        self.assertIsNone(cpu_breakdown([])['busy_pct'])
        row=dict(cpu_total_ticks=1,cpu_idle_ticks=1,cpu_iowait_ticks=0)
        self.assertIsNone(cpu_breakdown([row,row])['busy_pct'])

if __name__=='__main__':unittest.main()
