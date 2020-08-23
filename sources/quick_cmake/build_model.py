
import glog
from os import path
import os
import sys

import utils

class ModuleNode:
    ''' Module Node , internal usage in BuildModel
    Attibutes:
        childs: chlidrens node, type is Module Node
        is_cached: if it is True, then cached result will store in dependencies and third parties
        dependencies and third_parties: result for module
    '''
    def __init__(self):
        self.module_name = ''
        self.childs = {}
        self.output = None
        self.dependencies = set()
        self.third_parties = set()
        self.pre_build = None
        self.post_build = None

class ThirdPartyInfo:
    def __init__(self):
        self.third_party_name = ''
        self.include_dirs = []
        self.bin_dirs = []
        self.lib_dirs = []
        self.libs = []
        self.bins = []

class BuildModel:
    def __init__(self, configs):
        self._configs = configs
        # _modules is an array, length is equal to config, value is a map {name --> ModuleNode}
        self._modules = [ {} for c in configs ]
        # _third_parties is an array, length is equal to config, value is a map {name --> ThirdPartyInfo}
        self._third_parties = [ {} for c in configs ]

    def modules(self):
        return self._modules

    def third_parties(self):
        return self._third_parties

    def import_modules(self, module_map):
        for name, build_file in module_map.items():
            for i in range(len(self._configs)):
                build_object = self._run_build_script(build_file, self._configs[i])
                self._modules[i][name] = self._module_object_to_module_node(build_object)

    def import_third_parties(self, third_party_map):
        for name, build_file in third_party_map.items():
            for i in range(len(self._configs)):
                build_object = self._run_build_script(build_file, self._configs[i])
                self._third_parties[i][name] = self._third_party_object_to_module_node(build_object)

    def import_default_third_parties(self, default_third_parties):
        ''' Import default third parties, that there is no build file in the directory
            1) Must have an include folder
            2) If there is a lib folder, then lib will be added to lib_dirs. Add *,* to libs.
               For bin operation, it is similar
        '''
        for party, dir in default_third_parties.items():
            for i in range(len(self._configs)):
                if not path.exists(path.join(dir, 'include')):
                    glog.warn('Default third party \'%s\' do not contain include dir. Skip it.', dir)
                    continue
                info = ThirdPartyInfo()
                info.third_party_name = party
                info.include_dirs = ['include']
                if path.exists(path.join(dir, 'lib')):
                    lib_dir = path.join(dir, 'lib')
                    files = [ f for f in os.listdir(lib_dir) if path.isfile(path.join(lib_dir, f)) ]
                    if files:
                        libs_debug_info = ''
                        for f in files:
                            libs_debug_info += f+','
                        glog.info('Add lib files for default third party %s : %s', party, libs_debug_info)
                        info.lib_dirs = ['lib']
                        info.libs = ['*.*']

                if path.exists(path.join(dir, 'bin')):
                    bin_dir = path.join(dir, 'bin')
                    files = [ f for f in os.listdir(bin_dir) if path.isfile(path.join(bin_dir, f)) ]
                    if files:
                        bins_debug_info = ''
                        for f in files:
                            bins_debug_info += f+','
                        glog.info('Add binary files for default third party %s : %s', party, bins_debug_info)
                        info.bin_dirs = ['bin']
                        info.bins = ['*.*']

                glog.info('Add default third party %s', party)
                self._third_parties[i][party] = info

    def parse(self):
        for i in range(len(self._configs)):
            self._parse(self._modules[i])

    def _post_order_traversal(self, modules):
        result = []
        if not modules:
            return result
        # find roots
        child_set = set()
        for k in modules:
            child_set.update(modules[k].childs)
        
        for k in modules:
            if k in child_set:
                continue
            stack = []
            cur_node = k
            while cur_node or stack :
                if cur_node and cur_node not in result:
                    stack.append(cur_node)
                    cur_node = utils.set_to_sorted_list(modules[cur_node].childs)[0] if modules[cur_node].childs else None
                else:
                    cur_node = stack.pop()
                    #visit
                    result.append(cur_node)
                    if not stack:
                        break
                    # get neighbors
                    neighbors = utils.set_to_sorted_list(modules[stack[-1]].childs)
                    i = neighbors.index(cur_node)
                    cur_node = neighbors[i+1] if len(neighbors) > i+1 else None
        return result

    def _module_object_to_module_node(self, build_object):
        module_node = ModuleNode()
        module_node.module_name = build_object.__class__.__name__
        module_node.output = build_object.output
        for d in getattr(build_object, 'dependencies', []):
            module_node.dependencies.add(d)
        for third_party in getattr(build_object, 'third_parties', []):
            module_node.third_parties.add(third_party)
        module_node.pre_build = getattr(build_object, 'pre_build', None)
        module_node.post_build = getattr(build_object, 'post_build', None)
        module_node.childs = module_node.dependencies
        return module_node

    def _third_party_object_to_module_node(self, build_object):
        info = ThirdPartyInfo()
        info.third_party_name = build_object.__class__.__name__
        info.include_dirs = getattr(build_object, 'include_dirs', [])
        info.bin_dirs = getattr(build_object, 'include_dirs', [])
        info.libs = getattr(build_object, 'libs', [])
        info.bins = getattr(build_object, 'bins', [])
        return info

    def _run_build_script(self, build_file, config):
        glog.check(path.exists(build_file), 'Build file is not exists!' + build_file)
        build_dir = path.dirname(build_file)
        sys_append_dir = path.dirname(build_dir)
        if sys_append_dir not in sys.path:
            sys.path.append(sys_append_dir)
            
        module_name = path.basename(build_dir)
        build_name = path.splitext(path.basename(build_file))[0]
        build_module = __import__(module_name + '.' + build_name)
        build_obj = getattr(build_module, build_name)

        # Verify class in build.py
        debug_msg = 'build file {} does not define class with module name {}, build object attributes is {}'
        debug_msg = debug_msg.format(build_file, module_name, dir(build_obj))
        glog.check(module_name in dir(build_obj), debug_msg)

        # create class object
        build_class = getattr(build_obj, module_name)
        return build_class(config)

    def _get_attri_or_none(self, object, name):
        ''' Get attribute of an object, or return None if it is not exists'''
        return getattr(object, name)

    def _parse(self, modules):
        for m in self._post_order_traversal(modules):
            cur_module = modules[m]
            append_ds = set()
            append_ts = set()
            for child in cur_module.childs:
                append_ds.update(modules[child].dependencies)
                append_ts.update(modules[child].third_parties)
            cur_module.dependencies.update(append_ds)
            cur_module.third_parties.update(append_ts)

