
quick cmake, auto-generating CMake configuration.

----------------

# Get Started
quick cmake assumes that projects are managed in a modular way.The output of some modules is lib, some are executable.

First a project using quick_cmake to generating CMake file needs to be satisfied the following directory structure:
```
# xxx means the wildcards for names, not fixed.
xxxx[project_name]  #  which is also the workspace dir
  |
  | -- sources  # general directories of code.
         | -- xxx[module name] # module name for code.
               | -- [other code files, support sub-direcoties]
               | -- build.py   # config for modular source code.
         | -- xxx[module name] # other modules.
  | -- third_parties # general directories for third parties.
         | -- xxx[libary_name]
               | -- build.py   # config for third party source code.
```

`./example` is an example project that shows how to use.

as shown above, there are two type build file under the each sub-directories of the modular-code and the third-party.

They are a python file, named `build.py`.

## For modular-code build file

Here is an example(example/example_module_config.py):
```

# module name must be the same as the directory name in the build file
class module_name:
    def __init__(self, config):

        '''
        reference to sources\quick_cmake\config.py for config instance.
        config contains following values:
        output: output for the module, config.Output.BINARY, STATIC_LIB, DYNAMIC_LIB
        configuration: build configuration. config.Configuration.DEBUG, RELEASE
        platform: config.Platform.WIN32, X64, ARM, ARM64
        system: config.System.WINDOWS, LINUX
        '''

        # required, output can be the BINARY, STATIC_LIB, DYNAMIC_LIB
        self.output = config.Output.BINARY

        # optional, dependencies contains the dependency of this module
        self.dependencies = ['other_module']

        # optional, define the third parties, must located at the folder third_parties/
        self.third_parties = ['third_party']

        # optional, define the system libs here, contains the system lib.
        self.system_libs = ['socket']

        # optional, only set it if the output value is BINARY and enable the unit test generation.
        self.main_file = 'main.cpp'

    # define the pre build event
    def pre_build(self):
        pass

    # define the post build event
    def post_build(self):
        pass

```

For the code file, the source file whose file name is in the form of `*_test.cc/.cpp/.cxx/or others` will be recognized as an Unit test file, and an UT project will be automatically generated.

The target name of a unit test will be :
```
test_[module_name]_[relative_path_to_the_unit_test_file]
```

In addition, an additional project will be generated to execute all UT files under this module, named `test_[module_name]`.

If use `make` to compile the project, run `make test_[module_name]` will auto compile all the UT files under this module, and run them one by one.

## For third-party build file:
Here is an example(example/example_third_party_config.py):
```
# third party name must be the same as the directory name in the build file
class third_party_name:
    def __init__(self, config):
        '''
        reference to sources\quick_cmake\config.py for config instance.
        config contains following values:
        output: output for the module, config.Output.BINARY, STATIC_LIB, DYNAMIC_LIB
        configuration: build configuration. config.Configuration.DEBUG, RELEASE
        platform: config.Platform.WIN32, X64, ARM, ARM64
        system: config.System.WINDOWS, LINUX
        '''

        # include directories for the third party
        self.include_dirs = []

        # binary directories for the third party
        self.bin_dirs = []

        # binary files for the third party
        self.bins = []

        # libary directories for the third party
        self.lib_dirs = []
        
        # library directories for the third party
        self.libs = []

        # system libs for the third party
        self.system_libs = []

```

Cross-platform definition can be done by configuring the value. Only support Windows && Linux currently.


# Run quick_cmake

Under your project workspace, run
```
python3 [path to quick_cmake project]/sources/quick_cmake/main.py
```

The output files will generating under the dir `project_files`.

# Requirements
1. The version of python must be >= 3.7
2. install pip3 packages:
```
click
glog
```

# Options

There are some other options for quick_cmake:
```
@click.option('--configuration', default='DEBUG,RELEASE', help='values can be:DEBUG,RELEASE')
@click.option('--platform', default='X64', help='values can one of:WIN32,X64,ARM,ARM64')
@click.option('--std', default='c++11', help='set std version')
@click.option('--disable_unittest', is_flag=True, help='Disable Unittest for project')
@click.option('--workspace', default='.', help='Workspace dir')
@click.option('--only_generate', is_flag=True, help='Only generate CMakeListst.txt, but not execute cmake to update')
@click.option('--compile_options', default='', help='Add compile options, use `add_compile_options` in cmake.')

# todo: support custom flags in the quick cmake
@click.option('--custom_flags', help='custom_flags, access by config.custom_flags_str and config.custom_flags (dict)')
```
