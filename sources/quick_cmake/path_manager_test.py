
from  os import path
import unittest

from path_manager import PathManager

class TestPathManager(unittest.TestCase):
    def test_parse_build_file(self):
        workspace = path.join(path.dirname(__file__), 'test')
        pmg = PathManager(workspace)

        expected_modules = ['A', 'B', 'C', 'D', 'only_Linux_Debug', 'only_Release_X64']
        expected_modules_result = {}
        for m in expected_modules:
            expected_modules_result[m] = path.join(workspace, 'sources', m, 'build.py')
        self.assertDictEqual(pmg.module_map, expected_modules_result)

        expected_third_parties = ['third_party1']
        expected_third_result = {}
        for t in expected_third_parties:
            expected_third_result[t] = path.join(workspace, 'third_parties', t, 'build.py')
        self.assertDictEqual(pmg.third_party_map, expected_third_result)

        expected_default_third_parties = ['default_party', 'default_party_only_include', 'invalid_party']
        expected_default_third_result = {}
        for t in expected_default_third_parties:
            expected_default_third_result[t] = path.join(workspace, 'third_parties', t)
        self.assertDictEqual(pmg.default_third_party_map, expected_default_third_result)


if __name__ == '__main__':
    unittest.main()