
import copy
from os import path
import unittest

import build_model
from build_model import BuildModel
from config import Config
import cmake_generator
from cmake_generator import CMakeGenerator
from path_manager import PathManager

class TestCMakeGenerator(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestCMakeGenerator, self).__init__(*args, **kwargs)
        self._configs = [ Config() for i in range(2) ]
        self._configs[0].configuration = Config().Configuration.DEBUG
        self._configs[1].configuration = Config().Configuration.RELEASE

        self._build_model = BuildModel(self._configs)
        workspace = path.join(path.dirname(__file__), 'test')
        self._path_manager = PathManager(workspace)

        self._build_model.import_third_parties(self._path_manager.third_party_map)
        self._build_model.import_default_third_parties(self._path_manager.default_third_party_map)
        self._build_model.import_modules(self._path_manager.module_map)
        self._build_model.parse()

    def test_parse_cmake_third_party(self):
        cmake_generator_ = CMakeGenerator(self._configs, self._build_model, self._path_manager)
        for i in range(len(self._configs)):
            cmake_generator_._parse_cmake_third_party(self._configs[i], self._build_model.third_parties()[i])
            
        self.assertIn('default_party', cmake_generator_._cmake_third_parties)
        expected_lib_result = {path.join('third_parties', 'default_party', 'lib', 'mock.lib')}
        self.assertSetEqual(expected_lib_result, 
                            cmake_generator_._cmake_third_parties['default_party'].libs[cmake_generator.CMakeConfig.DEBUG])
        self.assertSetEqual(expected_lib_result, 
                            cmake_generator_._cmake_third_parties['default_party'].libs[cmake_generator.CMakeConfig.RELEASE])

    def test_parse_cmake_module(self):
        cmake_generator_ = CMakeGenerator(self._configs, self._build_model, self._path_manager)
        for i in range(len(self._configs)):
            # order is make sense, we need to parse third parties first.
            cmake_generator_._parse_cmake_third_party(self._configs[i], self._build_model.third_parties()[i])
            cmake_generator_._parse_cmake_module(self._configs[i], self._build_model.modules()[i])

        default_include = path.join('third_parties', 'default_party', 'include')
        default_only_include = path.join('third_parties', 'default_party_only_include', 'include')
        expected_include_dirs = {'A': {default_include, default_only_include},
                                 'B': {default_include},
                                 'C': {default_include, default_only_include},
                                 'D': {default_include},
                                 'only_Release_X64' : set(),
                                 'only_Linux_Debug' : set()}
        default_lib = path.join('third_parties', 'default_party', 'lib', 'mock.lib')
        expected_libs = {'A':{'B', 'C', 'D', default_lib},
                         'B':{'D', default_lib},
                         'C':{'D', default_lib},
                         'D':{default_lib},
                         'only_Release_X64' : set(),
                         'only_Linux_Debug' : set()}

        for cmake_module in cmake_generator_._cmake_modules.values():
            self.assertSetEqual(expected_include_dirs[cmake_module.name], cmake_module.include_dirs)
            if cmake_module.name == 'A':
                is_test_debug = False
                is_test_release = False
                if self._configs[0].system == Config().System.LINUX:
                    tmp_expected_lib = copy.deepcopy(expected_libs)
                    tmp_expected_lib['A'].add('only_Linux_Debug')
                    self.assertSetEqual(tmp_expected_lib[cmake_module.name], cmake_module.libs[cmake_generator.CMakeConfig.DEBUG])
                    is_test_debug = True
                if self._configs[0].platform == Config().Platform.X64:
                    tmp_expected_lib = copy.deepcopy(expected_libs)
                    tmp_expected_lib['A'].add('only_Release_X64')
                    self.assertSetEqual(tmp_expected_lib[cmake_module.name], cmake_module.libs[cmake_generator.CMakeConfig.RELEASE])
                    is_test_release = True
                if not is_test_debug:
                    self.assertSetEqual(expected_libs[cmake_module.name], cmake_module.libs[cmake_generator.CMakeConfig.DEBUG])
                if not is_test_release:
                    self.assertSetEqual(expected_libs[cmake_module.name], cmake_module.libs[cmake_generator.CMakeConfig.RELEASE])
            else:
                self.assertSetEqual(expected_libs[cmake_module.name], cmake_module.libs[cmake_generator.CMakeConfig.RELEASE])
                self.assertSetEqual(expected_libs[cmake_module.name], cmake_module.libs[cmake_generator.CMakeConfig.DEBUG])
        self.assertTrue(cmake_generator_._cmake_modules['A'].has_pre_build)
        self.assertFalse(cmake_generator_._cmake_modules['A'].has_post_build)

    def test_parse_cmake_info(self):
        cmake_generator_ = CMakeGenerator(self._configs, self._build_model, self._path_manager)
        cmake_generator_._parse_cmake_info()
        # Test whether the common lib is extracted to general
        default_lib = path.join('third_parties', 'default_party', 'lib', 'mock.lib')
        expected_libs = {'A':{'B', 'C', 'D', default_lib},
                         'B':{'D', default_lib},
                         'C':{'D', default_lib},
                         'D':{default_lib},
                         'only_Release_X64' : set(),
                         'only_Linux_Debug' : set()}

        for cmake_module in cmake_generator_._cmake_modules.values():
            if cmake_module.name == 'A':
                self.assertSetEqual(expected_libs[cmake_module.name], cmake_module.libs[cmake_generator.CMakeConfig.GENERAL])
                if self._configs[0].system == Config().System.LINUX:
                    self.assertSetEqual({'only_Linux_Debug'}, cmake_module.libs[cmake_generator.CMakeConfig.DEBUG])
                if self._configs[0].platform == Config().Platform.X64:
                    self.assertSetEqual({'only_Release_X64'}, cmake_module.libs[cmake_generator.CMakeConfig.RELEASE])
                else:
                    self.assertSetEqual({}, cmake_module.libs[cmake_generator.CMakeConfig.RELEASE])
            else:
                self.assertSetEqual(expected_libs[cmake_module.name], cmake_module.libs[cmake_generator.CMakeConfig.GENERAL])
                self.assertSetEqual(set(), cmake_module.libs[cmake_generator.CMakeConfig.DEBUG])
                self.assertSetEqual(set(), cmake_module.libs[cmake_generator.CMakeConfig.RELEASE])

    def test_get_post_order(self):
        cmake_generator_ = CMakeGenerator(self._configs, self._build_model, self._path_manager)
        test_orders = cmake_generator_._get_post_order()
        expected_orders = []
        if self._configs[0].system == Config().System.LINUX and self._configs[0].platform == Config().Platform.X64:
            expected_orders = ['D', 'only_Linux_Debug', 'only_Release_X64', 'B', 'C', 'A']
        elif self._configs[0].system != Config().System.LINUX and self._configs[0].platform == Config().Platform.X64:
            expected_orders = ['D', 'only_Release_X64', 'B', 'C', 'A', 'only_Linux_Debug']
        else:
            expected_orders = ['D', 'B', 'C', 'A', 'only_Linux_Debug', 'only_Release_X64']
            
        self.assertListEqual(expected_orders, test_orders)

    def test_convert_custom_command(self):
        cmake_generator_ = CMakeGenerator(self._configs, self._build_model, self._path_manager)
        argv = ['./sources/quick_cmake/main.py', '--workspace', 
                self._path_manager.workspace(), '--configuration=DEBUG,RELEASE', '--module', 'mock_module']
        workspace = path.abspath(path.dirname(path.dirname(path.dirname(__file__)))).replace('\\','/')+'/'
        test_cmd = cmake_generator_._convert_custom_command(argv)
        test_cmd = test_cmd.replace(workspace, '')
        expected_cmd = 'python sources/quick_cmake/main.py --workspace sources/quick_cmake/test --configuration=DEBUG,RELEASE --module mock_module'
        self.assertEqual(expected_cmd, test_cmd)

        # none workspace case
        argv = ['./sources/quick_cmake/main.py']
        test_cmd = cmake_generator_._convert_custom_command(argv)
        test_cmd = test_cmd.replace(workspace, '')
        expected_cmd = 'python sources/quick_cmake/main.py --workspace sources/quick_cmake/test'
        self.assertEqual(expected_cmd, test_cmd)


if __name__ == '__main__':
    unittest.main()
