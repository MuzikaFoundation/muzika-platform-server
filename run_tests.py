import os
import sys
import unittest

from tests import test_db_stmt

# initialize the test suite
loader = unittest.TestLoader()
suite = unittest.TestSuite()

# add tests to the test suite
suite.addTests(loader.loadTestsFromModule(test_db_stmt))

if __name__ == '__main__':
    # initialize a runner, pass it your suite and run it
    runner = unittest.TextTestRunner(verbosity=3, warnings='ignore')
    result = runner.run(suite)

    if len(result.failures):
        sys.exit(os.EX_SOFTWARE)
