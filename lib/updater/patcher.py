"""
MIT License

Copyright (C) 2021 ROCKY4546
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

import logging
import os
import sqlite3
import threading
import time

import lib.common.utils as utils
from lib.db.db_channels import DBChannels

REQUIRED_VERSION = '0.9.3'

def patch_upgrade(_config_obj, _new_version):
    """
    This method is called when a cabernet upgrade is requested.  Versions are
    major.minor.patch
    The system is setup to stop at each major or minor increment and
    perform an upgrade. This does imply that patch upgrades do not require changes to the data.
    To make sure this only executes associated with a specific version, the version 
    it is associated is tested with this new version.
    """
    LOGGER = logging.getLogger(__name__)
    results = ''
    if _new_version.startswith(REQUIRED_VERSION):
        LOGGER.info('Applying the patch to version: {}'.format(REQUIRED_VERSION))
        results = 'Patch updates File logging settings...'
        _config_obj.write('handler_filehandler', 'args', \
            "(os.getenv('LOGS_DIR','data/logs')+'/cabernet.log', 'a', 10000000, 10)"
            )
        _config_obj.write('handler_filehandler', 'class', \
            "lib.common.log_handlers.MPRotatingFileHandler"
            )
        _config_obj.write('locast', 'enabled', \
            False
            )
        
    return results
        



