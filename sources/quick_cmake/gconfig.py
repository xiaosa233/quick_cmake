
# Global config for project, unvisible for user
class GConfig:

    # std version, value can be 11 14 17
    STD = 11

    # if enable unit test in project
    ENABLE_UNITTEST = True

    # C++ head file sources
    HEAD_FILE_FILTER = ['*.h', '*.hpp', '*.inl', '*.hh']
    SOURCE_FILE_FILTER = ['*.cc', '*.cpp', '*.c',
                        '*.cxx', '*.cp', '*.c++']

    # sources files extension
    SOURCES_FILTER = []
    SOURCES_FILTER.extend(HEAD_FILE_FILTER)
    SOURCES_FILTER.extend(SOURCE_FILE_FILTER)

    # unit test sources files extension
    UNITTEST_SOURCES_FILTTER = ['*_test.cc', '*_test.cpp', '*_test.c', 
                                '*_test.cxx', '*_test.cp', '*_test.c++']

    LIB_EXTENSION = '.lib'
    
    COMPILE_OPTIONS = ''

    COMPILE_DEFINITIONS = ''

    CUSTOM_FLAGS = ''

    OUTPUT_DIR = ''
