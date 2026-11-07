import unittest
import sys
import os

# Ensure package root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run_all_tests():
    """Discovers and runs all tests in the tests directory."""
    print("============================================================")
    print("RUNNING IPO INTELLIGENCE ENGINE TEST SUITE")
    print("============================================================")

    loader = unittest.TestLoader()
    suite = loader.discover(start_dir="tests", pattern="test_*.py")

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("============================================================")
    if result.wasSuccessful():
        print(f"ALL TESTS PASSED ({result.testsRun} tests executed successfully).")
        return 0
    else:
        print(f"TESTS FAILED: {len(result.failures)} failures, {len(result.errors)} errors.")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
