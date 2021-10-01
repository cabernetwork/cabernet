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

import importlib
import logging
import os
import shutil
import sqlite3
import threading
import time

import lib.common.utils as utils
from lib.db.db_channels import DBChannels
from lib.db.db_scheduler import DBScheduler

REQUIRED_VERSION = '0.9.4'
LOGGER = None

def patch_upgrade(_config_obj, _new_version):
    """
    This method is called when a cabernet upgrade is requested.  Versions are
    major.minor.patch
    The system is setup to stop at each major or minor increment and
    perform an upgrade. This does imply that patch upgrades do not require changes to the data.
    To make sure this only executes associated with a specific version, the version 
    it is associated is tested with this new version.
    """
    global LOGGER
    LOGGER = logging.getLogger(__name__)
    results = ''
    if _new_version.startswith(REQUIRED_VERSION):
        LOGGER.info('Applying the patch to version: {}'.format(REQUIRED_VERSION))
        results = 'Patch updates migrating config settings...'

        key = move_key(_config_obj, 'channel-import_groups')
        key = move_key(_config_obj, 'channel-update_timeout')
        key = move_key(_config_obj, 'player-stream_type')
        key = move_key(_config_obj, 'player-enable_url_filter')
        key = move_key(_config_obj, 'player-url_filter')
        key = move_key(_config_obj, 'player-enable_pts_filter')
        key = move_key(_config_obj, 'player-pts_minimum')
        key = move_key(_config_obj, 'player-pts_max_delta')
        key = move_key(_config_obj, 'player-enable_pts_resync')
        key = move_key(_config_obj, 'player-pts_resync_type')
        key = move_key(_config_obj, 'epg-min_refresh_rate')

    return results


def move_key(_config_obj, _key):
    find_key_by_section(_config_obj, _key, 'plutotv')
    find_key_by_section(_config_obj, _key, 'xumo')


def find_key_by_section(_config_obj, _key, _section):
    global LOGGER
    if _section in _config_obj.data:
        if _key in _config_obj.data[_section]:
            LOGGER.info('Moving setting {}:{} to instance'.format(_section, _key))
            value = _config_obj.data[_section][_key]
            sections = find_instance(_config_obj.data, _section)
            for section in sections:
                _config_obj.write(section, _key, value)
            _config_obj.write(_section, _key, None)
    

def find_instance(_config, _plugin_name):
    sections = []
    for section in _config.keys():
        if section.startswith(_plugin_name+'_'):
            sections.append(section)
    return sections
