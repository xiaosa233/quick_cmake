
import os
from os import path
import subprocess
import sys

def main():
    # Collect all unit test files
    # Unit test file will end with [other_part]_test.py.
    unit_test_files = []
    for subdir, dirs, files in os.walk(path.dirname(__file__)):
        for f in files:
            if f.endswith('_test.py'):
                unit_test_files.append(path.relpath(path.join(subdir,f)))

    # Running unit tests
    run_results = []
    success_count = 0
    for ut in unit_test_files:
        python_exe = sys.executable
        print('\n', python_exe, ' ', ut, ' -v\n')
        run_results.append(subprocess.run([python_exe, ut, '-v']).returncode)
        if run_results[-1] == 0:
            success_count += 1

    # report result
    if success_count == len(run_results):
        print('Running all unit successful:', success_count)
    else:
        print('Running successful unit-tests:', success_count, ', error:', len(run_results) - success_count)
        for i in range(len(unit_test_files)):
            print(unit_test_files[i], '    ', 'OK' if run_results[i] == 0 else 'Error')

if __name__ == '__main__':
    main()