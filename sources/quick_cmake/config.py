import platform
import glog

class Configuration:
    def __init__(self):
        self.DEBUG = 1
        self.RELEASE =2 

class System:
    def __init__(self):
        self.LINUX = 1
        self.WINDOWS =2 

class Platform:
    # if system is not windows, Platform config is invalid.
    def __init__(self):
        self.WIN32 = 1
        self.X64 = 2
        self.ARM = 3
        self.ARM64 = 4

class Output:
    def __init__(self):
        self.BINARY = 1
        self.STATIC_LIB = 2
        self.DYNAMIC_LIB = 3

class Config:
    def __init__(self):
        self._predeine_values()
        self.configuration = self.Configuration.RELEASE
        self.system = self._get_system()
        # TODO(xiaojianli):Change default value of platform relative to the sytem
        self.platform = self.Platform.X64

    def _predeine_values(self):
        self.Configuration = Configuration()
        self.System = System()
        self.Platform = Platform()
        self.Output = Output()

    def _get_system(self):
        if platform.system() == 'Windows':
            return self.System.WINDOWS
        elif platform.system() == 'Linux':
            return self.System.LINUX
        else:
            glog.warn('Can not identify the system :' + platform.system())
