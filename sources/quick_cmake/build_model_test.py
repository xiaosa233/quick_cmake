
import copy
from  os import path
import unittest

from config import Config
from build_model import BuildModel
from build_model import ModuleNode
from build_model import ThirdPartyInfo
from path_manager import PathManager

class TestBuildModel(unittest.TestCase):
    def test_import(self):
        configs = self._create_mock_config()
        workspace = path.join(path.dirname(__file__), 'test')
        pmg = PathManager(workspace)
        build_model = BuildModel(configs)

        # import modules
        build_model.import_modules(pmg.module_map)

        # not parse yet
        expected_dependencies = { 'A' :{'B','C'},
                              'B' : {'D'},
                              'C' : {'D'},
                              'D' : set()
                            }
        expected_third_parties = { 'A' :set(),
                              'B' : {'third_party1'},
                              'C' : {'default_party_only_include'},
                              'D' : {'default_party'}
                            }
        self._assert_expected_module_info(build_model, configs, expected_dependencies, expected_third_parties)

        # import third parties
        build_model.import_third_parties(pmg.third_party_map)
        expected_third_party1 = ThirdPartyInfo()
        expected_third_party1.third_party_name = 'third_party1'
        expected_third_parties = {'third_party1':expected_third_party1}

        # import default third_parties
        build_model.import_default_third_parties(pmg.default_third_party_map)
        expected_default_third = ThirdPartyInfo()
        expected_default_third.third_party_name = 'default_party'
        expected_default_third.include_dirs = ['include']
        expected_default_third.lib_dirs = ['lib']
        expected_default_third.bin_dirs = ['bin']
        expected_default_third.libs = ['*.*']
        expected_default_third.bins = ['*.*']
        expected_third_parties['default_party'] = expected_default_third

        expected_default_third = ThirdPartyInfo()
        expected_default_third.third_party_name = 'default_party_only_include'
        expected_default_third.include_dirs = ['include']
        expected_third_parties['default_party_only_include'] = expected_default_third
        test_third_parties  = build_model.third_parties()
        for i in range(len(configs)):
            for k,v in expected_third_parties.items():
                self.assertIn(k, test_third_parties[i])
                self._assert_equal_third_info(v, test_third_parties[i][k])

        for i in range(len(configs)):
            self.assertNotIn('invalid_party', test_third_parties[i])

        # parse
        build_model.parse()
        expected_dependencies = { 'A' :{'B','C', 'D'},
                              'B' : {'D'},
                              'C' : {'D'},
                              'D' : set()
                            }
        expected_third_parties = { 'A' : {'third_party1', 'default_party_only_include', 'default_party'},
                              'B' : {'third_party1', 'default_party'},
                              'C' : {'default_party_only_include', 'default_party'},
                              'D' : {'default_party'}
                            }
        self._assert_expected_module_info(build_model, configs, expected_dependencies, expected_third_parties)

    def test_post_order_traversal(self):
        build_model = BuildModel([])

        ''' test case: parent --> childs
             1 --> 2 3 6
             3 --> 4 5
             4,5 --> 7
             8
        '''
        class TestNode:
            def __init__(self, in_childs):
                self.childs = in_childs

        # create tree
        modules = {}
        modules['1'] = TestNode({'2', '3', '6'})
        modules['2'] = TestNode(set())
        modules['3'] = TestNode({'4', '5'})
        modules['4'] = TestNode({'7'})
        modules['5'] = TestNode({'7', '8'})
        modules['6'] = TestNode(set())
        modules['7'] = TestNode(set())
        modules['8'] = TestNode(set())
        modules['9'] = TestNode(set())

        result = build_model._post_order_traversal(modules)
        self.assertEqual(9, len(result))
        self.assertLess(result.index('6'), result.index('1'))
        self.assertLess(result.index('2'), result.index('1'))
        self.assertLess(result.index('3'), result.index('1'))
        self.assertLess(result.index('4'), result.index('3'))
        self.assertLess(result.index('5'), result.index('3'))
        self.assertLess(result.index('8'), result.index('5'))
        self.assertLess(result.index('7'), result.index('5'))
        self.assertLess(result.index('7'), result.index('4'))

    def _create_mock_config(self):
        configs = [Config()] * 4
        default_config = Config()
        platform_cases = [default_config.Platform.WIN32, default_config.Platform.X64]
        configuration_cases = [default_config.Configuration.DEBUG, default_config.Configuration.RELEASE]
        for i in range(len(platform_cases)):
            for j in range(len(configuration_cases)):
                index = i * len(configuration_cases) + j
                configs[index] = Config()
                configs[index].platform = platform_cases[i]
                configs[index].configuration = configuration_cases[j]
        linux_debug = Config()
        linux_debug.configuration = default_config.Configuration.DEBUG
        linux_debug.system = default_config.System.LINUX
        configs.append(linux_debug)
        return configs

    def _assert_equal_third_info(self, lhs, rhs):
        self.assertEqual(lhs.third_party_name, rhs.third_party_name)
        self.assertListEqual(lhs.include_dirs, rhs.include_dirs)
        self.assertListEqual(lhs.bin_dirs, rhs.bin_dirs)
        self.assertListEqual(lhs.lib_dirs, rhs.lib_dirs)
        self.assertListEqual(lhs.libs, rhs.libs)
        self.assertListEqual(lhs.bins, rhs.bins)

    def _assert_expected_module_info(self, build_model, configs, expected_dependencies, expected_third_parties):
        test_modules = build_model.modules()
        for i in range(len(configs)):
            for case in expected_dependencies:
                self.assertIn(case, test_modules[i])
                if case == 'A' and configs[i].system == Config().System.LINUX and configs[i].configuration == Config().Configuration.DEBUG:
                    tmp_expected_d = copy.deepcopy(expected_dependencies[case])
                    tmp_expected_d.add('only_Linux_Debug')
                    self.assertSetEqual(tmp_expected_d, test_modules[i][case].dependencies)
                elif case == 'A' and configs[i].platform == Config().Platform.X64 and configs[i].configuration == Config().Configuration.RELEASE:
                    tmp_expected_d = copy.deepcopy(expected_dependencies[case])
                    tmp_expected_d.add('only_Release_X64')
                    self.assertSetEqual(tmp_expected_d, test_modules[i][case].dependencies)
                else:
                    self.assertSetEqual(expected_dependencies[case], test_modules[i][case].dependencies)
                self.assertSetEqual(expected_third_parties[case], test_modules[i][case].third_parties)

if __name__ == '__main__':
    unittest.main()