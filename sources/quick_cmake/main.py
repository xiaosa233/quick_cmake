
import click
import glog

from build_model import BuildModel
from cmake_generator import CMakeGenerator
import config
from gconfig import GConfig
from path_manager import PathManager

def _parse_member(value, str):
    result = getattr(value, str, None)
    object_attributes = [s for s in dir(value) if not (len(s) > 2 and s[0:2] == '__') ]
    glog.check(result != None, 'Parameter \'{}\' should be one of {}'.format(str, object_attributes))
    return result

def _run_unittests(unittests):
    executable_files = unittests.split(',')
    print('Begin to run unit files:', '\n'.join(executable_files))
    for ut_file in executable_files:
        returncode = subprocess.run([ut_file]).returncode
        assert 0 == returncode, ut_file + 'run error!'

@click.command()
@click.option('--configuration', default='DEBUG,RELEASE', help='values can be:DEBUG,RELEASE')
@click.option('--platform', default='X64', help='values can one of:WIN32,X64,ARM,ARM64')
@click.option('--std', default='c++11', help='set std version')
@click.option('--disable_unittest', is_flag=True, help='Disable Unittest for project')
@click.option('--workspace', default='.', help='Workspace dir')
@click.option('--only_generate', is_flag=True, help='Only generate CMakeListst.txt, but not execute cmake to update')
@click.option('--compile_options', default='', help='Add compile options, use `add_compile_options` in cmake.')

# todo: support custom flags in the quick cmake
@click.option('--custom_flags', help='custom_flags, access by config.custom_flags_str and config.custom_flags (dict)')

# for pre/post build event trigger
@click.option('--pre_build', is_flag=True, help='trigger pre build event')
@click.option('--post_build', is_flag=True, help='trigger post build event')
@click.option('--module', help='The module to trigger pre/post build event')

# for run all unittests
@click.option('--unittests', default='', help='unittest binaries:xx,xxxx,xx')
def main(configuration, platform, std, disable_unittest, workspace, only_generate, 
         compile_options,custom_flags,

         pre_build, post_build, module, unittests):
    if unittests != '':
        return _run_unittests(unittests)

    glog.check_eq(std[0:3],'c++')
    GConfig.STD = int(std[3:])
    GConfig.ENABLE_UNITTEST = not disable_unittest
    GConfig.COMPILE_OPTIONS=compile_options
    GConfig.CUSTOM_FLAGS = custom_flags

    v_configurations = configuration.split(',')
    v_platforms = platform.split(',')

    # get configs array
    configs = []
    for v_configuration in v_configurations:
        tmp_configuration = _parse_member(config.Configuration(), v_configuration)
        for v_platform in v_platforms:
            v_config = config.Config()
            v_config.configuration = tmp_configuration
            v_config.platform = _parse_member(config.Platform(), v_platform)
            configs.append(v_config)

    # create path manager instance
    pmg = PathManager(workspace)

    build_model = BuildModel(configs)
    build_model.import_modules(pmg.module_map)
    build_model.import_third_parties(pmg.third_party_map)
    build_model.import_default_third_parties(pmg.default_third_party_map)
    build_model.parse()

    if not pre_build and not post_build:
        if not build_model.modules()[0]:
            glog.warn('There is not modules, skip!')
            return
        cmake_generator = CMakeGenerator(configs, build_model, pmg)
        cmake_generator.generate()
        if not only_generate:
            cmake_generator.exe_cmake()
    else:
        glog.check(module, 'module should not be empty!')
        modules = build_model.modules()[0]
        glog.check(module in modules)
        if pre_build and modules[module].pre_build:
            modules[module].pre_build()
        if post_build and modules[module].post_build:
            modules[module].post_build()

if __name__ == '__main__':
    main()
