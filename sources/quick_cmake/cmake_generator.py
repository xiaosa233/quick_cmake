
import copy
import glob
import glog
import os
from os import path
import subprocess
import sys

import config
from gconfig import GConfig
import utils

CMAKE_SOURCES_DIR = '${SOURCE_DIR}'

class CMakeConfig:
    GENERAL = 0
    DEBUG = 1
    RELEASE = 2
    CONFIG_LEN = 3

    LINK_LIB_MAP = { GENERAL: 'general',
                     DEBUG: 'debug',
                     RELEASE: 'optimized'}

    PLATFORM_MAP = {config.Platform().WIN32 : 'Win32',
                    config.Platform().X64 : 'x64',
                    # I am not sure about this two valus, haven't test
                    config.Platform().ARM : 'ARM',
                    config.Platform().ARM64 : 'ARM64'}

class CMakeTarget:
    EXECUTABLE = 0
    STATIC_LIBRARY = 1
    SHARED_LIBRARY = 2
    UNITTEST_CUSTOM_TARGET = 3 # custom target for unit tests

    ConfigMap = {config.Output().BINARY : EXECUTABLE,
                 config.Output().STATIC_LIB : STATIC_LIBRARY,
                 config.Output().DYNAMIC_LIB : SHARED_LIBRARY}

class TargetInfo:
    def __init__(self):
        self.name = ''
        self.output = CMakeTarget.EXECUTABLE
        self.file_group_infos = {} # key -- > sources files
        self.sources_infos = {} # sources_filter --> [file_groups]
        self.include_dirs = set()
        self.libs = [set() for i in range(CMakeConfig.CONFIG_LEN) ]
        self.system_libs = [ set() for i in range(CMakeConfig.CONFIG_LEN) ]
        self.has_pre_build = False
        self.has_post_build = False
        self.unittest_targets = {} # ut target name --> ut source file
        self.module_name = '' # set when target is custom target

class CMakeModule:
    def __init__(self):
        self.name = ''
        self.output = 0
        self.main_file = ''
        self.include_dirs = set()
        self.libs = [set() for i in range(CMakeConfig.CONFIG_LEN) ]
        self.system_libs = [ set() for i in range(CMakeConfig.CONFIG_LEN) ]
        self.bins = [ set() for i in range(CMakeConfig.CONFIG_LEN) ]
        self.has_pre_build = False
        self.has_post_build = False
        self.head_only = False

        # Following path is relative to the sources dir
        self.file_group_infos = {} # key -- > sources files
        self.sources_infos = {} # sources_filter --> [file_groups]
        self.unittest_exclude_file_infos = [] # file group infos keys to exclude in ut
        self.unittest_sources = []

class CMakeThirdParty:
    def __init__(self):
        self.name = ''
        self.include_dirs = set()
        self.libs = [ set() for i in range(CMakeConfig.CONFIG_LEN) ]
        self.system_libs = [ set() for i in range(CMakeConfig.CONFIG_LEN) ]
        self.bins = [ set() for i in range(CMakeConfig.CONFIG_LEN) ]

class CMakeGenerator:
    ''' cmake is a single compilation system. All the values in config, platform and system can
    only have one and only one. The dependencies of the module and third_parties can have different
    values when the configuration(DEBUG and RELEASE) is different. The values of other fields must
    be consistent in different configs.
    '''
    def __init__(self, configs, build_models, path_manager):
        self._configs = configs
        self._build_models = build_models
        self._path_manager = path_manager
        self._cmake_modules = {}
        self._cmake_third_parties = {}

        self.cached_post_order = self._get_post_order()

    def generate(self):
        # for each modules
        self._parse_cmake_info()

        glog.info('Generate header')
        content = self._generate_quick_cmake_meta_info()
        content.extend(self._generate_header())
        content.extend(self._generate_project_info())
        content.extend(self._generate_compile_options())

        for module_name in self.cached_post_order:
            glog.info('Generate module ' + module_name)
            content.extend(self._generate_module(self._cmake_modules[module_name]))
        
        # write to file
        cmake_dist = path.join(self._path_manager.project_files_dir(), 'CMakeLists.txt')
        glog.info('Write to file:' + cmake_dist)
        utils.write_text('\n'.join(content), cmake_dist)

        self._copy_third_party_binaries()

    def exe_cmake(self):
        self._path_manager.project_files_dir()
        run_args = ['cmake', '-S', self._path_manager.project_files_dir(), '-B', self._path_manager.project_files_dir()]
        returncode = subprocess.run(run_args).returncode
        glog.check_eq(0, returncode)

    def _copy_third_party_binaries(self):
        # copy binary file of third
        # parties to binary dir
        bins = { 'Debug':list(), 'Release':list() }
        for third_party in self._cmake_third_parties.values():
            for i in range(CMakeConfig.CONFIG_LEN):
                if i == CMakeConfig.GENERAL or i == CMakeConfig.DEBUG:
                    bins['Debug'].extend(third_party.bins[i])
                if i == CMakeConfig.GENERAL or i == CMakeConfig.RELEASE:
                    bins['Release'].extend(third_party.bins[i])

        # check conflict files
        for config_dir, files in bins.items():
            if files:
                utils.copy_files(files, path.join(self._path_manager.binary_dirs(), config_dir))

    def _union_libs(self, target_libs):
        target_libs[CMakeConfig.GENERAL] = target_libs[CMakeConfig.DEBUG] & target_libs[CMakeConfig.RELEASE]
        target_libs[CMakeConfig.DEBUG] = target_libs[CMakeConfig.DEBUG] - target_libs[CMakeConfig.GENERAL]
        target_libs[CMakeConfig.RELEASE] = target_libs[CMakeConfig.RELEASE] - target_libs[CMakeConfig.GENERAL]

    def _parse_cmake_info(self):
        ''' Parse configs to get cmake modules and third parties '''
        for i in range(len(self._configs)):
            self._parse_cmake_third_party(self._configs[i], self._build_models.third_parties()[i])
            self._parse_cmake_module(self._configs[i], self._build_models.modules()[i])

        # Merge third party and module valus under DEBUG and  RELEASE configuration
        # Extract the common value to GENERAL
        for module in self._cmake_modules.values():
            self._union_libs(module.libs)
            self._union_libs(module.system_libs)

        for third_party in self._cmake_third_parties.values():
            self._union_libs(third_party.libs)
            self._union_libs(third_party.system_libs)

    def _parse_cmake_third_party(self, config, third_parties):
        config_index = self._get_configuration_index(config)
        for third_party in third_parties.values():
            third_party_workspace = path.join(self._path_manager.third_parties_dir(), third_party.third_party_name)
            cmake_third_party = None
            if third_party.third_party_name not in self._cmake_third_parties:
                cmake_third_party = CMakeThirdParty()
                cmake_third_party.name = third_party.third_party_name
                cmake_third_party.include_dirs = set()
                cmake_third_party.libs[config_index] = set()
                cmake_third_party.system_libs[config_index] = set()
                cmake_third_party.bins[config_index] = set()

                self._cmake_third_parties[third_party.third_party_name] = cmake_third_party
            else:
                cmake_third_party = self._cmake_third_parties[third_party.third_party_name]
            cmake_third_party.include_dirs.update(set(third_party.include_dirs))
            third_libs = utils.match_files(third_party_workspace, 
                                            third_party.lib_dirs, 
                                            third_party.libs, 
                                            self._path_manager.workspace())

            third_libs = ['${PROJECT_DIR}/' + x.replace('\\','/') for x in third_libs ]
            cmake_third_party.libs[config_index].update(third_libs)
            cmake_third_party.system_libs[config_index].update(third_party.system_libs)
            cmake_third_party.bins[config_index].update(utils.match_files(third_party_workspace, 
                                                                            third_party.bin_dirs, 
                                                                            third_party.bins, 
                                                                            self._path_manager.workspace()))
        
    def _parse_cmake_module(self, config, modules):
        config_index = self._get_configuration_index(config)
        for module_name in self.cached_post_order:
            module = modules[module_name]
            cmake_module = None
            if module.module_name not in self._cmake_modules:
                # create new one 
                cmake_module = CMakeModule()
                cmake_module.name = module.module_name
                cmake_module.output = module.output
                cmake_module.main_file = module.main_file
                cmake_module.include_dirs = set()
                cmake_module.libs[config_index] = set()
                cmake_module.system_libs[config_index] = set()
                cmake_module.has_pre_build = module.pre_build != None
                cmake_module.has_post_build = module.post_build != None 
                self._parse_file_infos(cmake_module)
                self._cmake_modules[cmake_module.name] = cmake_module
            else:
                cmake_module = self._cmake_modules[module.module_name]

            # append include dirs
            cmake_module.include_dirs.update(self._get_module_include_dirs(module, self._cmake_third_parties))
            # for dependencies, we can use the library target name
            for x in module.dependencies:
                glog.check(x in self._cmake_modules, x + 'not in ' + str(self._cmake_modules.keys()))
                if not self._cmake_modules[x].head_only:
                    cmake_module.libs[config_index].add(x)
            cmake_module.system_libs[config_index].update(module.system_libs)
            for third_party in module.third_parties:
                glog.check(third_party in self._cmake_third_parties, 
                            'third party {} is not in cmake third parties'.format(third_party))
                cmake_module.libs[config_index].update(self._cmake_third_parties[third_party].libs[config_index])
                cmake_module.system_libs[config_index].update(self._cmake_third_parties[third_party].system_libs[config_index])

    def _get_file_info_dir_key(self, sub_dir, module_name):
        '''
            Return the file info dir key for the sub dir
            sub_dir: relative path to the dir of module
        '''
        if sub_dir == '' or sub_dir == '.':
            return module_name
        return '_'.join(utils.split_path(path.join(module_name, sub_dir)))
    
    def _get_main_file_info_key(self, module_name):
        '''
            Return the file info dir key for main file 
            main_file: relative path to the dir of module
        '''
        return 'main_file_' + module_name

    def _get_source_info_dir_key(self, sub_dir, prefix = 'sources'):
        '''
            Return the source info key.
            sub_dir: relative dir to the dir of module
        '''
        if sub_dir == '' or sub_dir == '.':
            return prefix
        return '\\\\'.join(utils.split_path(path.join(prefix, sub_dir)))

    def _parse_file_infos(self, cmake_module):
        module_dir = path.join(self._path_manager.sources_dir(), cmake_module.name)
        rel_main_file = path.join(cmake_module.name, cmake_module.main_file)
        for subdir, dirs, files in os.walk(module_dir):
            file_results = []
            for extension in GConfig.SOURCES_FILTER:
                for file in [path.relpath(f, self._path_manager.sources_dir()) for f in glob.glob(path.join(subdir, extension))]:
                    if file == rel_main_file:
                        continue
                    # remove end with _test files
                    if not path.splitext(file)[0].endswith('_test'):
                        file_results.append(file)
            key = self._get_file_info_dir_key(path.relpath(subdir, module_dir), cmake_module.name)
            if file_results:
                cmake_module.file_group_infos[key] = file_results
                sources_info_key = self._get_source_info_dir_key(path.relpath(subdir, module_dir))
                cmake_module.sources_infos.setdefault(sources_info_key, [])
                cmake_module.sources_infos[sources_info_key].append(key)
            # For unittest
            if GConfig.ENABLE_UNITTEST:
                for extension in GConfig.UNITTEST_SOURCES_FILTTER:
                    cmake_module.unittest_sources.extend([path.relpath(f, self._path_manager.sources_dir()) for f in glob.glob(path.join(subdir, extension))])
        # For main_file
        real_main_file = path.join(module_dir, cmake_module.main_file)
        if cmake_module.output == config.Output().BINARY and path.exists(real_main_file) and path.isfile(real_main_file):
            key = self._get_main_file_info_key(cmake_module.name)
            cmake_module.file_group_infos[key] = [path.join(cmake_module.name, cmake_module.main_file)]
            sources_info_key = self._get_source_info_dir_key(path.dirname(cmake_module.main_file))
            cmake_module.sources_infos.setdefault(sources_info_key, [])
            cmake_module.sources_infos[sources_info_key].append(key)
            cmake_module.unittest_exclude_file_infos.append(key)
        cmake_module.head_only = True
        for file_group in cmake_module.file_group_infos.values():
            for source_file in file_group:
                if '*' + os.path.splitext(source_file)[1] in GConfig.SOURCE_FILE_FILTER:
                    cmake_module.head_only = False
                    break
            if not cmake_module.head_only:
                break

        build_file_key = self._get_build_file_group_name(cmake_module.name)
        cmake_module.file_group_infos[build_file_key] = [path.join(cmake_module.name, 'build.py').replace('\\', '/')]
        cmake_module.unittest_exclude_file_infos.append(build_file_key)

    def _get_build_file_group_name(self, module_name):
        return module_name + '_BUILD_TARGET_FILE_GROUP'

    def _get_configuration_index(self, config):
        if config.configuration == config.Configuration.DEBUG:
            return CMakeConfig.DEBUG
        elif config.configuration == config.Configuration.RELEASE:
            return CMakeConfig.RELEASE
        else:
            glog.fatal('Unknown configuration type {}', config.configuration)

    def _generate_header(self):
        headers = ['cmake_minimum_required(VERSION 3.2)']
        headers.append('set(CMAKE_SUPPRESS_REGENERATION true)')
        headers.append('set(CMAKE_CONFIGURATION_TYPES \"{}\" CACHE STRING \"\" FORCE)'.format(self._get_configurations()))
        headers.append('set(CMAKE_CXX_STANDARD {})'.format(GConfig.STD))
        headers.append('if("${CMAKE_GENERATOR}" MATCHES "^Visual Studio.*")')
        headers.append('  set(CMAKE_GENERATOR_PLATFORM \"{}\" CACHE INTERNAL \"\" FORCE)'.format(self._get_generator_platform()))
        headers.append('endif()')
        headers.append('\n')
        return headers

    def _generate_project_info(self):
        project_info = ['project({})'.format(self._path_manager.project_name())]
        project_info.append('set (PROJECT_DIR ${CMAKE_CURRENT_SOURCE_DIR}/../)')
        project_info.append('set (SOURCE_DIR ${PROJECT_DIR}/sources)')
        project_info.append('set (CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${PROJECT_DIR}/lib)')
        project_info.append('set (CMAKE_LIBRARY_OUTPUT_DIRECTORY ${PROJECT_DIR}/lib)')
        project_info.append('set (CMAKE_RUNTIME_OUTPUT_DIRECTORY ${PROJECT_DIR}/bin)')
        
        # add sources dir to include
        project_info.append('include_directories(${SOURCE_DIR})')
        project_info.append('\n')
        return project_info

    def _generate_compile_options(self):
        if not GConfig.COMPILE_OPTIONS is None and GConfig.COMPILE_OPTIONS != '':
            return ['add_compile_options({})'.format(GConfig.COMPILE_OPTIONS)]
        return []

    def _generate_quick_cmake_meta_info(self):
        meta_info =['# Generated by quick cmake']
        meta_info.append('\n')
        return meta_info

    def _generate_module(self, module):
        content = []
        for target_info in self._get_target_info(module):
            content.extend(self._generate_target_info(target_info))
        return content

    def _get_target_info(self, module):
        # generate module target info
        target_infos = []
        module_target = TargetInfo()
        module_target.name = module.name
        module_target.output = CMakeTarget.ConfigMap[module.output]
        module_target.file_group_infos = module.file_group_infos
        module_target.sources_infos = module.sources_infos
        module_target.libs = module.libs
        module_target.system_libs = module.system_libs
        module_target.include_dirs = set(['${PROJECT_DIR}/' + include_dir.replace('\\', '/') for include_dir in module.include_dirs])
        module_target.include_dirs.add(path.join(CMAKE_SOURCES_DIR, module.name).replace('\\', '/'))
        module_target.has_pre_build = module.has_pre_build
        module_target.has_post_build = module.has_post_build

        target_infos.append(module_target)

        # deal with unit test
        if GConfig.ENABLE_UNITTEST and module.unittest_sources:
            unittest_names = {}
            ut_file_group = module.file_group_infos
            if module.unittest_exclude_file_infos:
                ut_file_group = dict(module.file_group_infos)
                for x in module.unittest_exclude_file_infos:
                    ut_file_group.pop(x)
            is_binary_module = module.output == config.Output().BINARY

            for ut_file in module.unittest_sources:
                unittest_target = TargetInfo()
                # get ut name
                file_name = path.splitext(path.basename(ut_file))[0]
                glog.check(file_name[-5:] == '_test')
                ut_remove_test_path = path.join(path.dirname(ut_file), file_name[:-5])
                ut_name = 'test_'+'_'.join(utils.split_path(ut_remove_test_path))
                unittest_target.name = ut_name
                unittest_target.output = CMakeTarget.EXECUTABLE
                if is_binary_module:
                    unittest_target.file_group_infos = dict(ut_file_group)
                unittest_target.file_group_infos[ut_name] = [ut_file]
                unittest_target.sources_infos['ut_file'] = [ut_name]
                unittest_target.include_dirs = module_target.include_dirs
                unittest_target.libs = copy.deepcopy(module_target.libs)
                unittest_target.system_libs = copy.deepcopy(module_target.system_libs)
                if not is_binary_module and not module.head_only:
                    unittest_target.libs[CMakeConfig.GENERAL].add(module.name)

                target_infos.append(unittest_target)
                unittest_names[ut_name] = ut_file

            custom_target = TargetInfo()
            custom_target.name = 'test_' + module.name
            custom_target.module_name = module.name
            custom_target.output = CMakeTarget.UNITTEST_CUSTOM_TARGET
            custom_target.unittest_targets = unittest_names
            target_infos.append(custom_target)
        return target_infos

    def _generate_target_info(self, target_info):
        if target_info.output == CMakeTarget.UNITTEST_CUSTOM_TARGET:
            return self._generate_unittest_custom_target(target_info)
        # generate target info
        content = ['# module {}'.format(target_info.name)]
        # write file glob and sources group
        for key, value in target_info.file_group_infos.items():
            value = [ path.join(CMAKE_SOURCES_DIR, v).replace('\\','/') for v in value ]
            assert value, '{} in target {} file group info is empty!'.format(key, target_info.name)
            content.append('FILE(GLOB {} {})'.format(key, ' '.join(value)))
        for key, value in target_info.sources_infos.items():
            assert value, '{} in target {} sources infos is empty!'.format(key, target_info.name)
            content.append('source_group(\"{}\" FILES {})'.format(key, ' '.join(['${'+x+'}' for x in value])))

        # add target
        sources_part = ' '.join([ '${{{}}} '.format(key) for key in target_info.file_group_infos.keys() ])
        if target_info.output == CMakeTarget.EXECUTABLE:
            content.append('add_executable({} {})'.format(target_info.name, sources_part))
        elif target_info.output == CMakeTarget.STATIC_LIBRARY:
            content.append('add_library({} STATIC {})'.format(target_info.name, sources_part))
        elif target_info.output == CMakeTarget.SHARED_LIBRARY:
            content.append('add_library({} SHARED {})'.format(target_info.name, sources_part))
        else:
            glog.fatal('Unknown output type for module {} : {}', target_info.name, target_info.output)

        # add target include dirs
        target_include_part = []
        if target_info.include_dirs:
            target_include_part.append('\n')
            target_include_part.extend(['PUBLIC ' + include_dir for include_dir in target_info.include_dirs])
        content.append('target_include_directories({} {})'.format(target_info.name, ' '.join(target_include_part)))

        # add target link libs
        target_link_value_part = []
        for i in reversed(range(CMakeConfig.CONFIG_LEN)):
            link_part = ''
            for lib_sets in [ target_info.libs, target_info.system_libs]:
                if not lib_sets[i]:
                    continue
                link_part += utils.containers_format(lib_sets[i], ' ' + CMakeConfig.LINK_LIB_MAP[i] + ' {}\n')
            if link_part == '':
                continue
            target_link_value_part.append(link_part)
        if target_link_value_part:
            content.append('target_link_libraries({} {})'.format(target_info.name, ''.join(target_link_value_part)))

        # add pre/post build
        custom_cmd = self._convert_custom_command(sys.argv) + ' --module='+target_info.name if target_info.has_pre_build or target_info.has_post_build else ''
        if target_info.has_pre_build:
            pre_build_cmd = '{} --pre_build'.format(custom_cmd)
            content.append('add_custom_command(TARGET {} PRE_BUILD COMMAND {})'.format(target_info.name, pre_build_cmd))
        if target_info.has_post_build:
            post_build_cmd = '{} --post_build'.format(custom_cmd)
            content.append('add_custom_command(TARGET {} POST_BUILD COMMAND {})'.format(target_info.name, post_build_cmd))
        
        content.append('set_target_properties({} PROPERTIES LINKER_LANGUAGE CXX)'.format(target_info.name))
        content.append('\n')
        return content

    def _generate_unittest_custom_target(self, target_info):
        content = []
        content.append('# run all unittest under folder {}'.format(target_info.module_name))
        cmd = []
        for ut_target_name in sorted(target_info.unittest_targets.keys()):
            source = target_info.unittest_targets[ut_target_name]
            cmd.append('COMMAND echo run unittest files {}'.format(os.path.join(target_info.name, source).replace('\\', '/')))
            cmd.append('COMMAND $<TARGET_FILE:{}>\n'.format(ut_target_name))
        content.append('add_custom_target({} DEPENDS {} {})'.format(target_info.name, ' '.join(sorted(target_info.unittest_targets.keys())), ' '.join(cmd)))
        content.append('\n')
        return content
 
    def _convert_custom_command(self, argv):
        #replace first custom
        workspace = '--workspace'
        result = []
        execute_file = path.abspath(argv[0]).replace('\\','/')
        if path.splitext(execute_file)[1] == '.py':
            result.append(sys.executable.replace('\\','/'))
        result.append(execute_file)
        i = 1
        while i < len(argv):
            cur_argv = argv[i]

            if cur_argv.startswith(workspace):
                result.append(workspace)
                if len(cur_argv ) == len(workspace):
                    i = i+1
                    result.append(path.abspath(argv[i]).replace('\\','/'))
                else:
                    # format is --workspace=xxx
                    glog.check_eq(argv[len(workspace), '='])
                    result.append(path.abspath(argv[len(workspace)+1]).replace('\\','/'))
            else:
                result.append(cur_argv)
            i += 1
        if workspace not in result:
            result.append(workspace)
            result.append(path.abspath(self._path_manager.workspace()).replace('\\','/'))
        return ' '.join(result)

    def _get_configurations(self):
        # order make sense
        keys = ['Debug', 'Release']
        result = {}
        for k in keys:
            result[k] = False
        for config in self._configs:
            if config.configuration == config.Configuration.DEBUG:
                result['Debug'] = True
            elif config.configuration == config.Configuration.RELEASE:
                result['Release'] = True

        configurations = ''
        for k in keys:
            if result[k]:
                configurations += k + ';'
        
        if configurations:
            configurations = configurations[:-1]
        return configurations

    def _get_generator_platform(self):
        platforms = set() # Should only contains a value
        for config in self._configs:
            platforms.add(config.platform)
        glog.check(len(platforms) == 1, 'Platform should has one and only one value!{}'.format(str(platforms)))
        return CMakeConfig.PLATFORM_MAP[platforms.pop()]

    def _get_module_include_dirs(self, module, third_parties):
        include_dirs = set()
        for name in module.third_parties:
            glog.check(name in third_parties, '{} in not in third parties {}'.format(name, str(third_parties.keys())))
            third_party = third_parties[name]
            glog.check_eq(name, third_party.name)
            for include_dir in third_party.include_dirs:
                if not path.isabs(include_dir):
                    include_dirs.add(path.relpath(path.join(self._path_manager.third_parties_dir(), name, include_dir), 
                                     self._path_manager.workspace()))
                else:
                    include_dirs.add(include_dir)
        return include_dirs

    def _get_post_order(self):
        module_to_dep = {}
        for i in range(len(self._configs)):
            # merge dependencies
            for name, m in self._build_models.modules()[i].items():
                module_to_dep.setdefault(name, set()).update(m.dependencies)

        for key, value in module_to_dep.items():
            module_to_dep[key] = utils.set_to_sorted_list(value)

        result = []
        for name, deps in module_to_dep.items():
            if name in result:
                continue
            if not deps:
                result.append(name)
                continue
            cur = name
            stack = []
            while cur or stack:
                if module_to_dep[cur] and cur not in result:
                    stack.append(cur)
                    cur = module_to_dep[cur][0]
                else:
                    if cur not in result:
                        result.append(cur)
                    while stack:
                        parent = stack[-1]
                        index = module_to_dep[parent].index(cur)
                        if index+1 < len(module_to_dep[parent]):
                            cur = module_to_dep[parent][index+1]
                            break
                        else:
                            # cur is None, can not find neighbor
                            cur = stack.pop()
                            if cur not in result:
                                result.append(cur)
                    if not stack:
                        break
        return result

