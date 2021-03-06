
import glob
import glog
import os
from os import path
import subprocess
import sys

import config
from gconfig import GConfig
import utils

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

class CMakeModule:
    def __init__(self):
        self.name = ''
        self.output = 0
        self.include_dirs = set()
        self.libs = [ set() for i in range(CMakeConfig.CONFIG_LEN) ]
        self.has_pre_build = False
        self.has_post_build = False

class CMakeThirdPary:
    def __init__(self):
        self.name = ''
        self.include_dirs = set()
        self.libs = [ set() for i in range(CMakeConfig.CONFIG_LEN) ]
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

    def generate(self):
        # for each modules
        self._parse_cmake_info()

        glog.info('Generate header')
        content = self._generate_quick_cmake_meta_info()
        content.extend(self._generate_header())
        content.extend(self._generate_project_info())

        for module_name in self._get_post_order():
            glog.info('Generate module ' + module_name)
            content.extend(self._generate_module(self._cmake_modules[module_name]))
        
        # write to file
        cmake_dist = path.join(self._path_manager.project_files_dir(), 'CMakeLists.txt')
        glog.info('Write to file:' + cmake_dist)
        utils.write_text(utils.strings_combine(content, '\n'), cmake_dist)

        self._copy_third_party_binaries()

    def exe_cmake(self):
        self._path_manager.project_files_dir()
        run_args = ['cmake', '-S', self._path_manager.project_files_dir(), '-B', self._path_manager.project_files_dir()]
        print(utils.strings_combine(run_args, ' '))
        returncode = subprocess.run(run_args).returncode
        glog.check_eq(0, returncode)

    def _copy_third_party_binaries(self):
        # copy binary file of thirdparties to binary dir
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

    def _parse_cmake_info(self):
        ''' Parse configs to get cmake modules and third parties '''
        for i in range(len(self._configs)):
            self._parse_cmake_third_party(self._configs[i], self._build_models.third_parties()[i])
            self._parse_cmake_module(self._configs[i], self._build_models.modules()[i])

        # Merge third party and module valus under DEBUG and  RELEASE configuration
        # Extract the common value to GENERAL
        for module in self._cmake_modules.values():
            module.libs[CMakeConfig.GENERAL] = module.libs[CMakeConfig.DEBUG] & module.libs[CMakeConfig.RELEASE]
            module.libs[CMakeConfig.DEBUG] = module.libs[CMakeConfig.DEBUG] - module.libs[CMakeConfig.GENERAL]
            module.libs[CMakeConfig.RELEASE] = module.libs[CMakeConfig.RELEASE] - module.libs[CMakeConfig.GENERAL]

        for third_party in self._cmake_third_parties.values():
            third_party.libs[CMakeConfig.GENERAL] = third_party.libs[CMakeConfig.DEBUG] & module.libs[CMakeConfig.RELEASE]
            third_party.libs[CMakeConfig.DEBUG] = third_party.libs[CMakeConfig.DEBUG] - module.libs[CMakeConfig.GENERAL]
            third_party.libs[CMakeConfig.RELEASE] = third_party.libs[CMakeConfig.RELEASE] - module.libs[CMakeConfig.GENERAL]

    def _parse_cmake_third_party(self, config, third_parties):
        config_index = self._get_configuration_index(config)
        for third_party in third_parties.values():
            third_party_workspace = path.join(self._path_manager.third_parties_dir(), third_party.third_party_name)
            if third_party.third_party_name not in self._cmake_third_parties:
                cmake_third_party = CMakeThirdPary()
                cmake_third_party.name = third_party.third_party_name
                cmake_third_party.include_dirs = set(third_party.include_dirs)
                cmake_third_party.libs[config_index] = utils.match_files(third_party_workspace, 
                                                                         third_party.lib_dirs, 
                                                                         third_party.libs, 
                                                                         self._path_manager.workspace())
                cmake_third_party.bins[config_index] = utils.match_files(third_party_workspace, 
                                                                         third_party.bin_dirs, 
                                                                         third_party.bins, 
                                                                         self._path_manager.workspace())

                self._cmake_third_parties[third_party.third_party_name] = cmake_third_party
            else:
                cmake_third_party = self._cmake_third_parties[third_party.third_party_name]
                cmake_third_party.include_dirs.update(set(third_party.include_dirs))
                cmake_third_party.libs[config_index].update(utils.match_files(third_party_workspace, 
                                                                              third_party.lib_dirs, 
                                                                              third_party.libs, 
                                                                              self._path_manager.workspace()))
                cmake_third_party.bins[config_index].update(utils.match_files(third_party_workspace, 
                                                                              third_party.bin_dirs, 
                                                                              third_party.bins, 
                                                                              self._path_manager.workspace()))
        
    def _parse_cmake_module(self, config, modules):
        config_index = self._get_configuration_index(config)
        for module in modules.values():
            if module.module_name not in self._cmake_modules:
                # create new one 
                cmake_module = CMakeModule()
                cmake_module.name = module.module_name
                cmake_module.output = module.output
                cmake_module.include_dirs = self._get_module_include_dirs(module, self._cmake_third_parties)
                cmake_module.libs[config_index] = self._get_module_dependency_libs(module.dependencies)
                for third_party in module.third_parties:
                    glog.check(third_party in self._cmake_third_parties, 
                                'third party {} is not in cmake third parties'.format(third_party))
                    cmake_module.libs[config_index].update(self._cmake_third_parties[third_party].libs[config_index])

                cmake_module.has_pre_build = module.pre_build != None
                cmake_module.has_post_build = module.post_build != None 
                self._cmake_modules[cmake_module.name] = cmake_module
            else:
                # check modules
                cmake_module = self._cmake_modules[module.module_name]
                glog.check_eq(cmake_module.output, module.output, 'Output should be the same value, regardless of the value of config')
                # append include dirs
                cmake_module.include_dirs.update(self._get_module_include_dirs(module, self._cmake_third_parties))
                # for dependencies, we can use the library target name
                cmake_module.libs[config_index].update(self._get_module_dependency_libs(module.dependencies))
                for third_party in module.third_parties:
                    for lib_file in self._cmake_third_parties[third_party].libs[config_index]:
                        if lib_file not in cmake_module.libs[config_index]:
                            cmake_module.libs[config_index].add(lib_file)

    def _get_module_dependency_libs(self, dependencies):
        ''' Return dependencies of module
            If GConfig.ONLY_DEPENDENCY_LIB_EXISTS is true, we need to check if file is exists
            depencies is list
            Return set
        '''
        if GConfig.ONLY_DEPENDENCY_LIB_EXISTS:
            result = set()
            check_dirs = [path.join(self._path_manager.library_dirs(), 'Debug'), path.join(self._path_manager.library_dirs(), 'Release')]
            for dependency in dependencies:
                for check_dir in check_dirs:
                    file_path = path.join(check_dir, dependency + GConfig.LIB_EXTENSION)
                    if path.exists(file_path):
                        result.add(dependency)
                        break
            return result
        else:
            return set(dependencies)

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
        headers.append('set(CMAKE_GENERATOR_PLATFORM \"{}\" CACHE INTERNAL \"\" FORCE)'.format(self._get_generator_platform()))
        headers.append('set(CMAKE_CXX_STANDARD {})'.format(GConfig.STD))
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

    def _generate_quick_cmake_meta_info(self):
        meta_info =['# Generated by quick cmake']
        meta_info.append('\n')
        return meta_info

    def _generate_module(self, module):
        content = ['# module {}'.format(module.name)]
        # get all sources file under modules
        file_globs = {}
        source_groups = {}
        module_dir = path.join(self._path_manager.sources_dir(), module.name)
        unittest_sources = []
        for subdir, dirs, files in os.walk(path.join(self._path_manager.sources_dir(), module.name)):
            file_results = []
            for extension in GConfig.SOURCES_FILTER:
                for file in [path.relpath(f, module_dir) for f in glob.glob(path.join(subdir, extension))]:
                    # remove end with _test files
                    if not path.splitext(file)[0].endswith('_test'):
                        file_results.append(file)
            key = utils.strings_combine(utils.split_path(path.relpath(subdir, self._path_manager.sources_dir())), '_')
            if file_results:
                file_globs[key] = file_results
                relpath = path.relpath(subdir, module_dir).replace('\\','/')
                if relpath != '.':
                    source_groups[key] = path.join('sources', relpath).replace('\\','\\\\')
                else:
                    source_groups[key] = 'sources'

            # For unittest
            if GConfig.ENABLE_UNITTEST:
                for extension in GConfig.UNITTEST_SOURCES_FILTTER:
                    unittest_sources.extend([path.relpath(f, module_dir) for f in glob.glob(path.join(subdir, extension))])

        # write file glob and sources group
        for key, value in file_globs.items():
            value = [ path.join('${SOURCE_DIR}', module.name, v).replace('\\','/') for v in value ]
            content.append('FILE(GLOB {} {})'.format(key, utils.strings_combine(value, ' ')))
        for key, value in source_groups.items():
            content.append('source_group(\"{}\" FILES ${{{}}})'.format(value, key))

        # add target
        sources_part = utils.strings_combine([ '${{{}}} '.format(key) for key in file_globs.keys() ], ' ')
        sources_part += path.join('${SOURCE_DIR}', module.name, 'build.py').replace('\\','/')
        if module.output == config.Output().BINARY:
            content.append('add_executable({} {})'.format(module.name, sources_part))
        elif module.output == config.Output().STATIC_LIB:
            content.append('add_library({} STATIC {})'.format(module.name, sources_part))
        elif module.output == config.Output().DYNAMIC_LIB:
            content.append('add_library({} SHARED {})'.format(module.name, sources_part))
        else:
            glog.fatal('Unknown output type for module {} : {}', module.name, module.output)

        # add target include dirs
        target_include_part = ['PRIVATE ${{SOURCE_DIR}}/{}'.format(module.name)]
        if module.include_dirs:
            target_include_part.append('\n')
            target_include_part.extend([ 'PUBLIC ${PROJECT_DIR}/' + include_dir.replace('\\', '/') for include_dir in module.include_dirs])
        content.append('target_include_directories({} {})'.format(module.name, utils.strings_combine(target_include_part, ' ')))

        # add target link libs
        target_link_value_part = []
        for i in range(CMakeConfig.CONFIG_LEN):
            libs = []
            for x in module.libs[i]:
                # if x is not a path, means that it is a target.
                if '.' in x:
                    libs.append('${PROJECT_DIR}/' + x.replace('\\','/'))
                else:
                    libs.append(x)
            if libs:
                if target_link_value_part:
                    target_link_value_part.append('\n')
                target_link_value_part.extend( [ CMakeConfig.LINK_LIB_MAP[i] + ' ' + lib for lib in libs])
        content.append('target_link_libraries({} {})'.format(module.name, utils.strings_combine(target_link_value_part, ' ')))

        # add pre/post build
        custom_cmd = self._convert_custom_command(sys.argv) + ' --module='+module.name
        if module.has_pre_build:
            pre_build_cmd = '{} --pre_build'.format(custom_cmd)
            content.append('add_custom_command(TARGET {} PRE_BUILD COMMAND {})'.format(module.name, pre_build_cmd))
        if module.has_post_build:
            post_build_cmd = '{} --post_build'.format(custom_cmd)
            content.append('add_custom_command(TARGET {} POST_BUILD COMMAND {})'.format(module.name, post_build_cmd))
        
        content.append('set_target_properties({} PROPERTIES LINKER_LANGUAGE CXX)'.format(module.name))
        content.append('\n')

        if GConfig.ENABLE_UNITTEST and unittest_sources:
            content.extend(self._generate_unittest(unittest_sources, module.name))
        return content

    def _generate_unittest(self, unittest_sources, module_name):
        # Append unit test
        UNITTEST_THIRD_PARTY = 'googletest'
        glog.check(unittest_sources)
        sources_files = [ path.join('${SOURCE_DIR}', module_name, v).replace('\\','/') for v in unittest_sources ]
        unittest_sources_part = utils.strings_combine(sources_files, ' ')
        unittest_name = 'test_' + module_name

        include_dirs = set()
        # google test include dirs
        for include_dir in self._cmake_third_parties[UNITTEST_THIRD_PARTY].include_dirs:
            if not path.isabs(include_dir):
                include_dirs.add(path.relpath(path.join(self._path_manager.third_parties_dir(), UNITTEST_THIRD_PARTY, include_dir), 
                                    self._path_manager.workspace()))
            else:
                include_dirs.add(include_dir)
        include_dirs = [ path.join('${PROJECT_DIR}', x).replace('\\', '/') for x in include_dirs ]
        include_dirs.append('${SOURCE_DIR}/' + module_name)

        # add target link libs
        libs = [ [] for i in range(CMakeConfig.CONFIG_LEN) ]
        libs[CMakeConfig.GENERAL].append(module_name)
        for i in range(CMakeConfig.CONFIG_LEN):
            now_libs = libs[i]
            for x in self._cmake_third_parties[UNITTEST_THIRD_PARTY].libs[i]:
                if '.' in x:
                    now_libs.append('${PROJECT_DIR}/' + x.replace('\\','/'))
                else:
                    now_libs.append(x)
        
        content = []
        content.append('# unittest module {}'.format(unittest_name))
        content.append('add_executable({} {})'.format(unittest_name, unittest_sources_part))
        content.append('target_include_directories({} PRIVATE {})'.format(unittest_name, utils.strings_combine(include_dirs, ' ')))
        target_link_value_part = []
        for i in range(CMakeConfig.CONFIG_LEN):
            now_libs = libs[i]
            if now_libs:
                if target_link_value_part:
                    target_link_value_part.append('\n')
                target_link_value_part.extend([CMakeConfig.LINK_LIB_MAP[i] + ' ' + lib for lib in now_libs])
        content.append('target_link_libraries({} {})'.format(unittest_name, utils.strings_combine(target_link_value_part, ' ')))
        content.append('set_target_properties({} PROPERTIES LINKER_LANGUAGE CXX)'.format(unittest_name))
        content.append('\n')
        return content

    def _convert_custom_command(self, argv):
        #replace first custom
        workspace = '--workspace'
        result = []
        execute_file = path.abspath(argv[0]).replace('\\','/')
        if path.splitext(execute_file)[1] == '.py':
            result.append('python')
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
        return utils.strings_combine(result, ' ')

    def _get_configurations(self):
        # order make sense
        keys = ['Debug', 'Release']
        result = {}
        for k in keys:
            result[k] = True
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
        post_orders = {}
        for i in range(len(self._configs)):
            # merge dependencies
            for name, m in self._build_models.modules()[i].items():
                post_orders.setdefault(name, set()).update(m.dependencies)

        result = []
        for name, dependencies in post_orders.items():
            if name in result:
                continue
            if not dependencies:
                result.append(name)
                continue
            cur = name
            stack = []
            while cur or stack:
                if cur and cur not in result:
                    stack.append(cur)
                    cur = utils.set_to_sorted_list(post_orders[cur])[0] if post_orders[cur] else None
                else:
                    tmp = stack.pop()
                    result.append(tmp)
                    if not stack:
                        break
                    parent = stack[0]
                    # next neighbor
                    neighbors = utils.set_to_sorted_list(post_orders[parent])
                    index = neighbors.index(tmp)
                    cur = neighbors[index+1] if index+1 < len(neighbors) else None
        return result
