
import glog
import os
from os import path

from gconfig import GConfig


class PathManager:
    def __init__(self, workspace):
        self._workspace = workspace
        self._module_map = self._parse_modules()
        self._third_party_map, self._default_third_party_map = self._parse_third_parties()
        
    def workspace(self):
        return self._workspace
        
    def sources_dir(self):
        return path.join(self._workspace, 'sources')

    def third_parties_dir(self):
        return path.join(self._workspace, 'third_parties')

    def project_name(self):
        return path.basename(path.abspath(self._workspace))
    
    def project_files_dir(self):
        return path.join(self._workspace, GConfig.OUTPUT_DIR)

    def binary_dirs(self):
        return path.join(self._workspace, 'bin')

    def library_dirs(self):
        return path.join(self._workspace, 'lib')

    @property
    def module_map(self):
        return self._module_map
    
    @property
    def third_party_map(self):
        return self._third_party_map

    @property
    def default_third_party_map(self):
        return self._default_third_party_map

    def _parse_modules(self):
        modules = self._parse_build_file(self.sources_dir())
        if modules == None:
            glog.warn('Sources directory does not exists! %s', self.sources_dir())
            return {}
        return modules
   
    def _parse_third_parties(self):
        ''' Prase third parties
        Return:
            return tuple(third_parties, default_third_parties), default_third_parties means that under dir
            third_parties but without build file.
        '''
        empty_modules = {}
        third_parties = self._parse_build_file(self.third_parties_dir(), empty_modules)
        if third_parties == None:
            glog.warn('Third part directory does not exists! %s', self.third_parties_dir())
            third_parties = {}
        return third_parties, empty_modules

    def _parse_build_file(self, parse_dir, empty_modules = None):
        ''' Parse build file under parse_dir
        Args:
            parse_dir: provides a folder and the subdirectories under this folder will be checked for the build.py file.
            Subdirectories do not include grandchild-level directories
            empty_modules: if is not None, it will output the directories without build.py file
        Reture:
            return map { module -> build_file_path }
        '''
        if not path.exists(parse_dir):
            return None

        results = {}
        for subdir, dirs, files in os.walk(parse_dir):
            for dir in dirs:
                build_file = path.join(subdir, dir, 'build.py')
                if path.exists(build_file):
                    results[dir] = str(build_file)
                elif empty_modules is not None:
                    empty_modules[dir] = str(path.join(subdir, dir))
            break
        return results
