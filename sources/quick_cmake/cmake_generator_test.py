
import copy
from os import path
import unittest
import sys

import build_model
from build_model import BuildModel
from config import Config
import cmake_generator
from cmake_generator import CMakeGenerator
from cmake_generator import CMakeConfig
from cmake_generator import CMakeTarget
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

    def has_configuration(self, configuration):
        return self._configs[0].configuration == configuration or self._configs[1].configuration == configuration

    def test_parse_cmake_third_party(self):
        cmake_generator_ = CMakeGenerator(self._configs, self._build_model, self._path_manager)
        for i in range(len(self._configs)):
            cmake_generator_._parse_cmake_third_party(self._configs[i], self._build_model.third_parties()[i])
            
        self.assertIn('default_party', cmake_generator_._cmake_third_parties)
        expected_lib_result = {'/'.join(['${PROJECT_DIR}', 'third_parties', 'default_party', 'lib', 'mock.lib'])}
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
        default_lib = '/'.join(['${PROJECT_DIR}', 'third_parties', 'default_party', 'lib', 'mock.lib'])
        expected_libs = {'A':{'B', 'D', default_lib},
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
        self.assertFalse(cmake_generator_._cmake_modules['A'].head_only)
        self.assertFalse(cmake_generator_._cmake_modules['B'].head_only)
        self.assertTrue(cmake_generator_._cmake_modules['C'].head_only)
        self.assertFalse(cmake_generator_._cmake_modules['D'].head_only)

        # Test whether the common lib is extracted to general
        default_lib = '/'.join(['${PROJECT_DIR}', 'third_parties', 'default_party', 'lib', 'mock.lib'])
        expected_libs = {'A':{'B', 'D', default_lib},
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
        if self._configs[0].system == Config().System.LINUX:
            self.assertLess(test_orders.index('only_Linux_Debug'), test_orders.index('A'))
        self.assertEqual(6, len(test_orders))

        self.assertLess(test_orders.index('D'), test_orders.index('B'))
        self.assertLess(test_orders.index('D'), test_orders.index('C'))
        self.assertLess(test_orders.index('B'), test_orders.index('A'))
        self.assertLess(test_orders.index('C'), test_orders.index('A'))
        self.assertLess(test_orders.index('only_Release_X64'), test_orders.index('A'))

    def test_convert_custom_command(self):
        cmake_generator_ = CMakeGenerator(self._configs, self._build_model, self._path_manager)
        argv = ['./sources/quick_cmake/main.py', '--workspace', 
                self._path_manager.workspace(), '--configuration=DEBUG,RELEASE', '--module', 'mock_module']
        workspace = path.abspath(path.dirname(path.dirname(path.dirname(__file__)))).replace('\\','/')+'/'
        test_cmd = cmake_generator_._convert_custom_command(argv)
        test_cmd = test_cmd.replace(workspace, '')
        python_exe = sys.executable.replace('\\','/')
        expected_cmd = python_exe + ' sources/quick_cmake/main.py --workspace sources/quick_cmake/test --configuration=DEBUG,RELEASE --module mock_module'
        self.assertEqual(expected_cmd, test_cmd)

        # none workspace case
        argv = ['./sources/quick_cmake/main.py']
        test_cmd = cmake_generator_._convert_custom_command(argv)
        test_cmd = test_cmd.replace(workspace, '')
        expected_cmd = python_exe + ' sources/quick_cmake/main.py --workspace sources/quick_cmake/test'
        self.assertEqual(expected_cmd, test_cmd)

    def test_get_target_info(self):
        cmake_generator_ = CMakeGenerator(self._configs, self._build_model, self._path_manager)
        cmake_generator_._parse_cmake_info()
        target_infos = cmake_generator_._get_target_info(cmake_generator_._cmake_modules['A'])
        self.assertEqual(3, len(target_infos))
        self.assertEqual('A', target_infos[0].name)
        self.assertEqual(CMakeTarget.EXECUTABLE, target_infos[0].output)
        self.assertEqual('test_A_some', target_infos[1].name)
        self.assertEqual(CMakeTarget.EXECUTABLE, target_infos[1].output)
        self.assertEqual('test_A', target_infos[2].name)
        self.assertEqual(CMakeTarget.UNITTEST_CUSTOM_TARGET, target_infos[2].output)
        self.assertDictEqual({'test_A_some': path.join('A', 'some_test.cpp')}, target_infos[2].unittest_targets)
        self.assertSetEqual({'test'} , target_infos[0].system_libs[CMakeConfig.GENERAL])

        # test file_group_infos
        expected_dict = {'A' : [path.join('A','test.h'), path.join('A','test.cpp')],
                         'A_folder' : [path.join('A', 'folder', 'test.h'), path.join('A', 'folder', 'test.cc')]}
        self.assertListEqual(expected_dict['A'], target_infos[0].file_group_infos['A'])
        self.assertListEqual(expected_dict['A_folder'], target_infos[0].file_group_infos['A_folder'])

        # test sources_infos
        expected_sources_infos_dict = { 'sources' : ['A'],
                                        'sources\\\\folder': ['A_folder']}
        self.assertListEqual(expected_sources_infos_dict['sources'], target_infos[0].sources_infos['sources'])
        self.assertListEqual(expected_sources_infos_dict['sources\\\\folder'], target_infos[0].sources_infos['sources\\\\folder'])                            

    def test_get_file_info_dir_key(self):
        cmake_generator_ = CMakeGenerator(self._configs, self._build_model, self._path_manager)
        self.assertEqual('mock_module_a_b', cmake_generator_._get_file_info_dir_key('a/b', 'mock_module'))
        self.assertEqual('mock_module', cmake_generator_._get_file_info_dir_key('.', 'mock_module'))
        self.assertEqual('mock_module', cmake_generator_._get_file_info_dir_key('', 'mock_module'))

    def test_get_main_file_info_key(self):
        cmake_generator_ = CMakeGenerator(self._configs, self._build_model, self._path_manager)
        self.assertEqual('main_file_mock_module', cmake_generator_._get_main_file_info_key('mock_module'))

    def test_get_source_info_dir_key(self):
        cmake_generator_ = CMakeGenerator(self._configs, self._build_model, self._path_manager)
        self.assertEqual('sources', cmake_generator_._get_source_info_dir_key(''))
        self.assertEqual('sources', cmake_generator_._get_source_info_dir_key('.'))
        self.assertEqual('sources\\\\a\\\\b', cmake_generator_._get_source_info_dir_key('a/b'))

    def test_generate(self):
        cmake_generator_ = CMakeGenerator(self._configs, self._build_model, self._path_manager)
        cmake_generator_._parse_cmake_info()
        for module_name in cmake_generator_.cached_post_order:
            self.assertTrue(cmake_generator_._generate_module(cmake_generator_._cmake_modules[module_name]))

if __name__ == '__main__':
    unittest.main()
