#!/usr/bin/env python
'''
MIT License

Copyright (C) 2021 ROCKY4546
https://github.com/rocky4546

This file is part of Cabernet

Permission is hereby granted, free of charge, to any person obtaining a copy of this software
and associated documentation files (the “Software”), to deal in the Software without restriction,
including without limitation the rights to use, copy, modify, merge, publish, distribute,
sublicense, and/or sell copies of the Software, and to permit persons to whom the Software
is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or
substantial portions of the Software.
'''

import os
import sys
import time
import argparse
import platform
import pathlib
import base64
import binascii
import logging

# install required libraries
try:
    from pip._internal import main as pip
    try:
        import cryptography
    except ImportError:
        pip(['install', 'cryptography'])
    except ModuleNotFoundError:
        print('Unable to install required cryptography module')
    try:
        import requests
    except ImportError:
        pip(['install', 'requests'])
    except ModuleNotFoundError:
        print('Unable to install required requests module')
except (ImportError, ModuleNotFoundError):
    print('Unable to load pip module to install required modules')

from lib.config.user_config import get_config


def get_args():
    parser = argparse.ArgumentParser(description='Fetch provider', epilog='')
    parser.add_argument('-i', '--installdir', dest='instdir', type=str, default=None, help='', required=True)
    parser.add_argument('-c', '--configfile', dest='cfg', type=str, default=None, help='')
    parser.add_argument('-d', '--datadir', dest='datadir', type=str, default=None, help='')
    return parser.parse_args()


# Startup Logic
if __name__ == '__main__':
    # os.chdir(os.path.dirname(os.path.abspath(__file__)))
    script_dir = pathlib.Path(os.path.dirname(os.path.abspath(__file__)))
    opersystem = platform.system()

    args = get_args()

    # determine if a config.ini file exists at the top folder of the install
    # if not found, use the example config file
    # otherwise, update currect config.ini with the new user/pwd info
    install_dir = pathlib.Path(os.path.abspath(str(args.instdir)))
    if not os.path.exists(install_dir):
        print('ERROR: install directory not found at ', install_dir)
        sys.exit(1)

    data_dir = pathlib.Path(os.path.abspath(str(args.datadir)))
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print('INFO: Creating data directory: ', data_dir)
        
    config_file = pathlib.Path(data_dir).joinpath('config.ini')
    if os.path.exists(config_file):
        print('config file found at ', config_file)
        args.cfg = config_file
        # update current config.ini file
    else:
        print('Creating new config file at ', config_file)
        # find the examples config file
        config_ex_file = pathlib.Path(install_dir).joinpath('lib/tvheadend/config_example.ini')
        if os.path.exists(config_ex_file):
            print('config example file found at ', config_ex_file)
            args.cfg = config_ex_file
        else:
            print('ERROR: config example file not found at ', config_ex_file)
            sys.exit(1)


    configObj = get_config(install_dir, opersystem, args)

    # update config object
    if not configObj.config_handler.has_section('paths'):
        configObj.config_handler.add_section('paths')
    configObj.data['paths']['data_dir'] = str(data_dir)
    configObj.config_handler.set('paths', 'data_dir', str(data_dir))

    with open(config_file, 'w') as config_fileptr:
        configObj.config_handler.write(config_fileptr)
