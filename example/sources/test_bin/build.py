
class test_bin:
    def __init__(self, config):
        self.output = config.Output.BINARY
        self.dependencies = ['configuration_lib']
        self.third_parties = []

        if config.configuration == config.Configuration.RELEASE:
            self.third_parties.append('default_party')

    def post_build(self):
        print('post_build')
        pass

    def pre_build(self):
        print('pre_build')
        pass