# Instructions:
# 1. Copy this file in this folder renaming it 'load_local.py'
# 2. In the created 'load_local_vois.py' change the 'absolute_path_to_geolayer' accordingly
# Changes in the 'load_local.py' will not be detected (thanks .gitignore) a.k.a. sensitive info in path are secured

import importlib.util
import sys
import warnings
import os
from argparse import ArgumentParser

absolute_path_to_geolayer = '/mnt/batch/tasks/shared/LS_root/mounts/clusters/compute-for-voila/code/geolayer/geolayer/__init__.py'


def main(warning_set: bool, path_geolayer: str):
    # Check if __init__ file exists
    if os.path.basename(path_geolayer) != '__init__.py':
        raise FileNotFoundError(f'You are not pointing to a __init__.py file {path_geolayer}')
    if not os.path.exists(path_geolayer):
        raise FileNotFoundError(f'Could not find {path_geolayer}')

    # Load local geolayer library as python package
    spec = importlib.util.spec_from_file_location("geolayer", path_geolayer)
    module = importlib.util.module_from_spec(spec)
    sys.modules['geolayer'] = module
    spec.loader.exec_module(module)
    
    # Disable warnings
    if warning_set:
        warnings.filterwarnings("ignore", category=DeprecationWarning)


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("-w", "--warning-off",
                        action='store_const',
                        dest="warning",
                        help="Disable warning messages",
                        required=False,
                        const=True,
                        default=False)
    parser.add_argument("-p", "--path-local-geolayer",
                        action='store',
                        dest='path_geolayer',
                        help="Absolute path to local geolayer library __init__.py file",
                        type=str,
                        required=False,
                        default=absolute_path_to_geolayer)

    args = parser.parse_args()
    main(warning_set=args.warning, path_geolayer=args.path_geolayer)
