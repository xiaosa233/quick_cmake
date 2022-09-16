
import glob
import glog
import os
from os import path
import shutil

def set_to_sorted_list(value):
    result = list(value)
    result.sort()
    return result

def write_text(content, file_path):
    ''' Write text content to file. If file is exists, it will be overwrite! '''
    # Ensure dir of file path is exsits
    file_dir = path.dirname(file_path)
    if not path.exists(file_dir):
        os.makedirs(file_dir)

    with open(file_path, 'w') as f:
        f.write(content)
  
def match_files(workspace, dirs, files, relative_dir = ''):
    ''' mathc files that give by files under the dirs 
    Args:
        workspace: workspace about the dirs. will combine the value in the dirs if it is not a 
            absolute path
        relative_dir: return the result relative path to the relative dir
    Return:
        set : return path with files relative to the relative dir
    '''
    result = set()
    for dir in dirs:
        check_dir = dir
        if not path.isabs(check_dir):
            check_dir = path.join(workspace, dir)
        
        for file in files:
            file_list = glob.glob(path.join(check_dir, file))
            if not path.isabs(dir) and relative_dir:
                file_list = [ path.relpath(f, relative_dir) for f in file_list ]
            result.update(set(file_list))
    return result

def split_path(path_value):
    result = []
    p = path_value
    while p :
        base_name = path.basename(p)
        if not base_name:
            result.append(p)
            break
        result.append(base_name)
        p = path.dirname(p)
    result.reverse()
    return result

def copy_files(files, dist_dir, is_overwrite=False):
    # make dir
    if not path.exists(dist_dir):
        os.makedirs(dist_dir)
    for file in files:
        new_dist = path.join(dist_dir, path.basename(file))
        if is_overwrite or not path.exists(new_dist):
            glog.info('Copy file {} --> {}'.format(file, new_dist))
            shutil.copyfile(file, new_dist)

def containers_format(containers, format_str):
    format_result = ''
    for it in containers:
        format_result += format_str.format(it)
    return format_result
