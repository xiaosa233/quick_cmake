
from  os import path
import unittest

from config import Config
from build_model import BuildModel
from build_model import ThirdPartyInfo
from path_manager import PathManager

class TestBuildModel(unittest.TestCase):
    def _create_mock_config(self):
        configs = [Config()] * 4
        default_config = Config()
        platform_cases = [default_config.Platform.X86, default_config.Platform.X64]
        configuration_cases = [default_config.Configuration.DEBUG, default_config.Configuration.RELEASE]
        for i in range(len(platform_cases)):
            for j in range(len(configuration_cases)):
                index = i * len(configuration_cases) + j
                configs[index].platform = platform_cases[i]
                configs[index].configuration = configuration_cases[j]
        linux_debug = Config()
        linux_debug.configuration = default_config.Configuration.DEBUG
        linux_debug.system = default_config.System.LINUX
        configs.append(linux_debug)
        return configs

    def test_import(self):
        configs = self._create_mock_config()
        build_model = BuildModel(configs)
        workspace = path.join(path.dirname(__file__), 'test')
        pmg = PathManager(workspace)

        # import modules
        build_model.import_modules(pmg.module_map)

        # not parse yet
        expected_dependencies = { 'A' :{'B','C'},
                              'B' : {'D'},
                              'C' : {'D'},
                              'D' : set()
                            }
        test_modules = build_model.modules()
        for i in range(len(configs)):
            for case in expected_dependencies:
                self.assertIn(case, test_modules[i])
                self.assertSetEqual(expected_dependencies[case], test_modules[i][case].dependencies)

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


    def _assert_equal_third_info(self, lhs, rhs):
        self.assertEqual(lhs.third_party_name, rhs.third_party_name)
        self.assertListEqual(lhs.include_dirs, rhs.include_dirs)
        self.assertListEqual(lhs.bin_dirs, rhs.bin_dirs)
        self.assertListEqual(lhs.lib_dirs, rhs.lib_dirs)
        self.assertListEqual(lhs.libs, rhs.libs)
        self.assertListEqual(lhs.bins, rhs.bins)

if __name__ == '__main__':
    unittest.main()