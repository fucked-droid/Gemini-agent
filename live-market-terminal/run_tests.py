"""
Comprehensive Test Runner for Live Indian Market Terminal.
Executes all unit and integration test suites.
"""

import sys
import unittest
from pathlib import Path

# Add live-market-terminal to path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def run_all_terminal_tests():
    """Discovers and executes all test suites in tests/."""
    loader = unittest.TestLoader()
    suite = loader.discover(str(PROJECT_ROOT / "tests"), pattern="test_*.py")

    runner = unittest.TextTestRunner(verbosity=2)
    print("=" * 70)
    print("RUNNING LIVE INDIAN MARKET TERMINAL TEST SUITE")
    print("=" * 70)
    result = runner.run(suite)
    print("=" * 70)

    if result.wasSuccessful():
        print(f"ALL TESTS PASSED ({result.testsRun} tests executed successfully).")
        return 0
    else:
        print(f"TESTS FAILED (Failures: {len(result.failures)}, Errors: {len(result.errors)})")
        return 1

if __name__ == "__main__":
    sys.exit(run_all_terminal_tests())
