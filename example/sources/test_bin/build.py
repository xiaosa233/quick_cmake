
class test_bin:
    def __init__(self, config):
        self.output = config.Output.BINARY
        self.main_file = 'test_bin.cc'
        self.dependencies = [
            'configuration_lib',
            'head_only',
        ]
        self.third_parties = []

    def post_build(self):
        print('post_build')
        pass

    def pre_build(self):
        print('pre_build')
        pass