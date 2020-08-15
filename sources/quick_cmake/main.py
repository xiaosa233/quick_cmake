
import click
import glog

from build_model import BuildModel
import config
from path_manager import PathManager

def _parse_member(value, str):
    result = getattr(value, str, None)
    object_attributes = [s for s in dir(value) if not (len(s) > 2 and s[0:2] == '__') ]
    glog.check(result != None, 'Parameter \'{}\' should be one of {}'.format(str, object_attributes))
    return result

@click.command()
@click.option('--configuration', default='DEBUG,RELEASE', help='values can be:DEBUG,RELEASE')
@click.option('--platform', default='WIN32', help='values can one of:WIN32,X64,ARM,ARM64')
@click.option('--workspace', default='.', help='Workspace dir')
def main(configuration, platform, workspace):
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

if __name__ == '__main__':
    main()