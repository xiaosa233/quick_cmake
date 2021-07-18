
# module name must be the same as the directory name in the build file
class module_name:
    def __init__(self, config):

        '''
        reference to sources\quick_cmake\config.py for config instance.
        config contains following values:
        output: output for the module, config.Output.BINARY, STATIC_LIB, DYNAMIC_LIB
        configuration: build configuration. config.Configuration.DEBUG, RELEASE
        platform: config.Platform.WIN32, X64, ARM, ARM64
        system: config.System.WINDOWS, LINUX
        '''

        # required, output can be the BINARY, STATIC_LIB, DYNAMIC_LIB
        self.output = config.Output.BINARY

        # optional, dependencies contains the dependency of this module
        self.dependencies = ['other_module']

        # optional, define the third parties, must located at the folder third_parties/
        self.third_parties = ['third_party']

        # optional, define the system libs here, contains the system lib.
        self.system_libs = ['socket']

        # optional, only set it if the output value is BINARY and enable the unit test generation.
        self.main_file = 'main.cpp'

    # define the pre build event
    def pre_build(self):
        pass

    # define the post build event
    def post_build(self):
        pass
