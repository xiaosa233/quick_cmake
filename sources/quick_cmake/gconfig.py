
# Global config for project, unvisible for user
class GConfig:

    # std version, value can be 11 14 17
    STD = 11

    # if enable unit test in project
    ENABLE_UNITTEST = True

    # only link dependency lib if it is exists
    ONLY_DEPENDENCY_LIB_EXISTS = False

    # sources files extension
    SOURCES_FILTER = ['*.h', '*.hpp', '*.inl', '.hh', 
                      '*.cc', '*.cpp', '*.c', 
                      '*.cxx', '*.cp', '*.c++']

    # unit test sources files extension
    UNITTEST_SOURCES_FILTTER = ['*_test.cc', '*_test.cpp', '*_test.c', 
                                '*_test.cxx', '*_test.cp', '*_test.c++']

    LIB_EXTENSION = '.lib'
    