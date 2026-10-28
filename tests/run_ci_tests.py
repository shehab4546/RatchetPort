"""Verbose CI discovery with a stack dump and process exit on a stalled test."""
import faulthandler
import os
from pathlib import Path
import sys
import unittest


class BoundedResult(unittest.TextTestResult):
    # Per-test, not a deadline for the entire suite. Native/child tests normally
    # finish within seconds; give Windows runners two minutes for each test.
    timeout_seconds = 120

    def startTest(self, test):
        super().startTest(test)
        faulthandler.dump_traceback_later(self.timeout_seconds, exit=True)

    def stopTest(self, test):
        faulthandler.cancel_dump_traceback_later()
        super().stopTest(test)


def main():
    tests = Path(__file__).resolve().parent
    os.chdir(tests.parent)
    faulthandler.enable()
    suite = unittest.defaultTestLoader.discover(str(tests))
    result = unittest.TextTestRunner(verbosity=2, resultclass=BoundedResult).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())
