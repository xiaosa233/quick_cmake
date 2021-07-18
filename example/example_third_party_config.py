
# third party name must be the same as the directory name in the build file
class third_party_name:
    def __init__(self, config):
        '''
        reference to sources\quick_cmake\config.py for config instance.
        config contains following values:
        output: output for the module, config.Output.BINARY, STATIC_LIB, DYNAMIC_LIB
        configuration: build configuration. config.Configuration.DEBUG, RELEASE
        platform: config.Platform.WIN32, X64, ARM, ARM64
        system: config.System.WINDOWS, LINUX
        '''

        # include directories for the third party
        self.include_dirs = []

        # binary directories for the third party
        self.bin_dirs = []

        # binary files for the third party
        self.bins = []

        # libary directories for the third party
        self.lib_dirs = []
        
        # library directories for the third party
        self.libs = []

        # system libs for the third party
        self.system_libs = []
