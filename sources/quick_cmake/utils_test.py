
from os import path
import unittest

import utils

class UtilsTest(unittest.TestCase):
    def test_match_files(self):
        abs_dir = path.abspath(path.join(path.dirname(__file__), 'test/third_parties/default_party'))
        workspace = path.relpath(abs_dir)
        lib_dirs = ['lib']
        libs = ['mock.lib', 'bad_case.lib']
        test_result = utils.match_files(workspace, lib_dirs, libs)
        expected_result = {path.join(workspace, 'lib', 'mock.lib')}
        self.assertSetEqual(expected_result, test_result)

        # test glob match
        relative_path = path.join(path.dirname(__file__), 'test')
        test_result = utils.match_files(workspace, lib_dirs, ['*.*'], relative_path)
        tmp_expected_result = {path.join('third_parties', 'default_party', 'lib', 'mock.lib')}
        self.assertSetEqual(tmp_expected_result, test_result)

        # test absolute path
        abs_test_lib_dir = path.join(abs_dir, 'lib')
        test_result = utils.match_files(workspace, [abs_test_lib_dir], ['*.*'])
        self.assertSetEqual({path.join(abs_test_lib_dir, 'mock.lib')}, test_result)

    def test_split_path(self):
        self.assertListEqual(['first', 'second', 'third'], utils.split_path('first/second/third'))
        self.assertListEqual(['/', 'second', 'third'], utils.split_path('/second/third'))
        self.assertListEqual(['/', 'second', 'third', 'file.cc'], utils.split_path('/second/third/file.cc'))

    def test_containers_format(self):
        result = utils.containers_format(['12', '234'], '{} ')
        self.assertEqual('12 234 ', result)

if __name__ == '__main__':
    unittest.main()