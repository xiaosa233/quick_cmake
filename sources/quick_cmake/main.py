
import click
import glog

from build_model import BuildModel
from cmake_generator import CMakeGenerator
import config
from path_manager import PathManager

def _parse_member(value, str):
    result = getattr(value, str, None)
    object_attributes = [s for s in dir(value) if not (len(s) > 2 and s[0:2] == '__') ]
    glog.check(result != None, 'Parameter \'{}\' should be one of {}'.format(str, object_attributes))
    return result

@click.command()
@click.option('--configuration', default='DEBUG,RELEASE', help='values can be:DEBUG,RELEASE')
@click.option('--platform', default='X64', help='values can one of:WIN32,X64,ARM,ARM64')
@click.option('--std', default='c++11', help='set std version')
@click.option('--workspace', default='.', help='Workspace dir')
@click.option('--only_generate', is_flag=True, help='Only generate CMakeListst.txt, but not execute cmake to update')

# for pre/post build event trigger
@click.option('--pre_build', is_flag=True, help='trigger pre build event')
@click.option('--post_build', is_flag=True, help='trigger post build event')
@click.option('--module', help='The module to trigger pre/post build event')
def main(configuration, platform, std, workspace, only_generate, pre_build, post_build, module):
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
            glog.check_eq(std[0:3],'c++')
            v_config.std=int(std[3:])
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