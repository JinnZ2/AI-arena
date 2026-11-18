"""Run the whole suite and print counts: passed / skipped / NOT_RUN / failed.

NOT_RUN = skips whose reason starts with "NOT_RUN" (a pinned file could not be
read as pinned). They are a subset of skipped and are never counted as passed.
--require-zero-skipped makes any skip a nonzero exit. stdlib only.

    python tests/run_counts.py [--require-zero-skipped]
"""
import os
import sys
import unittest


def main(argv):
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    suite = unittest.defaultTestLoader.discover(os.path.join(root, "tests"), top_level_dir=root)
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    skipped = len(result.skipped)
    not_run = sum(1 for _, why in result.skipped if str(why).startswith("NOT_RUN"))
    failed = len(result.failures) + len(result.errors) + len(result.unexpectedSuccesses)
    passed = result.testsRun - skipped - failed - len(result.expectedFailures)
    for test, why in result.skipped:
        print(f"skipped: {test.id()}: {why}")
    print(f"counts: ran {result.testsRun} | passed {passed} | skipped {skipped} | "
          f"NOT_RUN {not_run} | failed {failed}")
    if failed:
        return 1
    if "--require-zero-skipped" in argv and skipped:
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
