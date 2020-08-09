
import click
import glog

from build_importer import BuildImporter
import config
from path_manager import PathManager

def _parse_member(value, str):
    result = getattr(value, str, None)
    object_attributes = [s for s in dir(value) if not (len(s) > 2 and s[0:2] == '__') ]
    glog.check(result != None, 'Parameter \'{}\' should be one of {}'.format(str, object_attributes))
    return result

@click.command()
@click.option('--configuration', default='DEBUG,RELEASE', help='values can be:DEBUG,RELEASE')
@click.option('--platform', default='X86,X64', help='values can be:X86,X64,ARM,ARM64')
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

if __name__ == '__main__':
    main()