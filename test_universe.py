import unittest

class TestUniverse(unittest.TestCase):
    def test_meaning_of_life(self):
        self.assertEqual(42, 40 + 2)

    def test_market_universe(self):
        universe = ["NIFTY 50", "NIFTY BANK", "NIFTY IT"]
        self.assertIn("NIFTY 50", universe)
        self.assertEqual(len(universe), 3)

if __name__ == "__main__":
    unittest.main()
