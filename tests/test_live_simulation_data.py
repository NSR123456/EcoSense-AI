import unittest

from src.services.simulator import EnergySimulator


class TestLiveSimulationData(unittest.TestCase):
    def test_simulator_loads_selected_building_rows(self):
        simulator = EnergySimulator(db_manager=None, focus_building=141)

        self.assertFalse(simulator.df.empty)
        self.assertIn("date", simulator.df.columns)
        self.assertIn("consumption_kwh", simulator.df.columns)
        self.assertTrue(simulator.df["building_id"].astype(str).str.strip().eq("141").all())


if __name__ == "__main__":
    unittest.main()
