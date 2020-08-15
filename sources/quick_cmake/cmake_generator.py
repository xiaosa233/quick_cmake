
import glog
from os import path

class CMakeConfig:
    GENERAL = 0
    DEBUG = 1
    RELEASE = 2
    
    CONFIG_LEN = 3
    LINK_LIB_MAP = { CMakeConfig.GENERAL: 'general',
                     CMakeConfig.DEBUG: 'debug',
                     CMakeConfig.RELEASE: 'optimized'}

class CMakeModule:
    def __init__(self):
        self.name = ''
        self.output = 0
        self.include_dirs = []
        self.libs=[ set() for i in range(CMakeConfig.CONFIG_LEN) ]
        self.third_parties = [ set() for i in range(CMakeConfig.CONFIG_LEN) ]

class CMakeThirdPary:
    def __init__(self):
        self.name = ''
        self.include_dirs = []
        self.libs = [ set() for i in range(CMakeConfig.CONFIG_LEN) ]

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

    def generate(self):
        # for each modules

        content = self._generate_header()
        content.extend(self._generate_project_info())

        # write to file
        utils.write_text(utils.strings_combine(content, '\n'), 
                         path.join(self._path_manager.project_files_dir(), 'CMakeLists.txt'))

    def _get_generate_modules(self):

        pass

    def _generate_header(self):
        headers = ['cmake_minimum_required(VERSION 3.2)']
        headers.append('set(CMAKE_CONFIGURATION_TYPES \"{}\" CACHE STRING \"\" FORCE)'.format(self._get_configurations()))
        headers.append('set(CMAKE_GENERATOR_PLATFORM \"{}\" CACHE INTERNAL \"\" FORCE)'.format(self._get_generator_platform()))
        return headers

    def _generate_project_info(self):
        project_info = ['project({})'.format(self._path_manager.project_name())]
        project_info.append('set (PROJECT_DIR ${CMAKE_CURRENT_SOURCE_DIR}/../)')
        project_info.append('set (SOURCE_DIR ${PROJECT_DIR}/sources)')
        return project_info

    def _get_configurations(self):
        # order make sense
        keys = ['Debug', 'Release']
        result = {}
        for k in keys:
            result[k] = True
        for config in self._configs:
            if config.configuration == config.Configuration.DEBUG:
                results['Debug'] = True
            elif config.configuration == config.Configuration.Release:
                results['Release'] = True
        configurations = ''
        for k in keys:
            if result[k]:
                configurations += result[k] + ';'
        
        if configurations:
            configurations = configurations[:-1]
        return configurations

    def _get_generator_platform(self):
        platforms = set() # Should only contains a value
        for config in self._configs:
            platforms.add(config.platform)
        glog.check(len(platforms) != 1, 'Platform should has one and only one value!.{}'.format(str(platform)))
        return platforms.pop()
