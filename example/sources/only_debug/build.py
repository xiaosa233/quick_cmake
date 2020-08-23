
class only_debug:
    def __init__(self, config):
        self.output = config.Output.STATIC_LIB
        self.dependencies = []
        self.third_parties = []
