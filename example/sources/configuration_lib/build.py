
class configuration_lib:
    def __init__(self, config):
        self.output = config.Output.STATIC_LIB
        self.dependencies = []

        if config.configuration == config.Configuration.DEBUG:
            self.dependencies.append('only_debug')
        elif config.configuration == config.Configuration.RELEASE:
            self.dependencies.append('only_release')
