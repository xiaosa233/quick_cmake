
import os
from os import path

def set_to_sorted_list(value):
    result = list(value)
    result.sort()
    return result

def strings_combine(container, combiner):
    ''' Combine strings in the container with combiner.
        e.g. ['yes','no'], ';', will output 'yes;no'
    '''
    result = ''
    for value in container:
        if value != container[-1]:
            result += value + combiner
        else:
            result += value
    return result

def write_text(content, file_path):
    ''' Write text content to file. If file is exists, it will be overwrite! '''
    # Ensure dir of file path is exsits
    file_dir = path.dirname(file_path)
    if not path.exists(file_dir):
        os.makedirs(file_dir)

    with open(file_path, 'w') as f:
        f.write(content)
  