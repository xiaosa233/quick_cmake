class A:
    def __init__(self, config):
        self.output = config.Output.BINARY
        self.dependencies = ['B', 'C']
        self.third_parties = []
        self.system_libs = ['test']

        if config.configuration == config.Configuration.RELEASE and \
            config.platform == config.Platform.X64:
            self.dependencies.append('only_Release_X64')
        if config.configuration == config.Configuration.DEBUG and \
            config.system == config.System.LINUX:
            self.dependencies.append('only_Linux_Debug')

    def pre_build(self):
        pass