class B:
    def __init__(self, config):
        self.output = config.Output.STATIC_LIB
        self.dependencies = ['D']
        self.third_parties = ['third_party1']