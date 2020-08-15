
import unittest

import utils

class UtilsTest(unittest.TestCase):
    def test_strings_combine(self):
        test_case = ['yes', 'no']
        test_result = utils.strings_combine(test_case, ';')
        expected_result = 'yes;no'
        self.assertEqual(expected_result, test_result)

        test_result = utils.strings_combine(['onlyone'], ';;')
        self.assertEqual('onlyone', test_result)

        test_result = utils.strings_combine([], ';;')
        self.assertEqual('', test_result)

if __name__ == '__main__':
    unittest.main()