#!/usr/bin/env python3
"""
MIT License

Copyright (C) 2023 ROCKY4546
https://github.com/rocky4546

This file is part of Cabernet

Permission is hereby granted, free of charge, to any person obtaining a copy of this software
and associated documentation files (the "Software"), to deal in the Software without restriction,
including without limitation the rights to use, copy, modify, merge, publish, distribute,
sublicense, and/or sell copies of the Software, and to permit persons to whom the Software
is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or
substantial portions of the Software.
"""

import os
import sys
from inspect import getsourcefile

if sys.version_info.major == 2 or sys.version_info < (3, 8):
    print('Error: cabernet requires python 3.8+.')
    sys.exit(1)

from lib import main

if __name__ == '__main__':

    init_path = os.getcwd()
    script_dir = os.path.abspath(os.path.dirname(getsourcefile(lambda:0)))
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    #script_dir = pathlib.Path(os.path.dirname(os.path.abspath(__file__)))
    #print('os.path.realpath', os.path.realpath(__file__))
    #print('os.path.abspath(os.path.dirname',os.path.abspath(os.path.dirname(__file__)))
    #print('os.path.dirname',os.path.dirname(sys.argv[0]))
    #print('os.getcwd()', os.getcwd())
    #print('getsourcefile', os.path.abspath(os.path.dirname(getsourcefile(lambda:0))))
    main.main(script_dir)
    
    sys.stderr.flush()
    sys.stdout.flush()
    os.chdir(init_path)
    if ('-r' in sys.argv) or ('--restart' in sys.argv):
        pass
    else:
        sys.argv.append('-r')
        sys.argv.append('1')
    os.execl(sys.executable, sys.executable, *sys.argv)
