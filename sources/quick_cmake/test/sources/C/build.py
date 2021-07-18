class C:
    def __init__(self, config):
        self.output = config.Output.STATIC_LIB
        self.dependencies = ['D']
        self.third_parties = ['default_party_only_include']