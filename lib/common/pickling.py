"""
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
"""

import logging
import pathlib
import pickle
import os

TRAILER = '.pkl'

class Pickling:
    """
    Do to MS Windows OS not forking processes, pickling must occur
    to have the variables passed to the process have data.
    Simple variables may be passed succesffully without pickling.
    """
    def __init__(self, _config):
        self.logger = logging.getLogger(__name__)
        self.config = _config
        self.temp_dir = _config['paths']['data_dir']
    
    def to_pickle(self, _object_to_pickle):
        class_name = _object_to_pickle.__class__.__name__
        self.logger.debug('Pickling {}'.format(class_name))
        file_path = self.get_file_path(class_name)
        with open(file_path, 'wb') as f:
            pickle.dump(_object_to_pickle, f, -1)
            f.close()

    def from_pickle(self, _class_name):
        self.logger.debug('Unpickling {}'.format(_class_name))
        file_path = self.get_file_path(_class_name)
        if os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                obj_copy = pickle.load(f)
                f.close()
            return obj_copy
        else:
            self.logger.warning('Pickling import file does not exist: {}'
                .format(file_path))
            return None

    def delete_pickle(self, _class_name):
        self.logger.debug('Deleting Pickle File {}'.format(_class_name))
        file_path = self.get_file_path(_class_name)
        if os.path.exists(file_path):
            os.remove(file_path)
        else:
            self.logger.warning('Deleting pickle file does not exist: {}'
                .format(file_path))
            


    def get_file_path(self, classname):
        file_path = pathlib.Path(self.temp_dir) \
            .joinpath(classname + TRAILER)
        return file_path
