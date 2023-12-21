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


import configparser
import logging
import time
import traceback

from lib.plugins.plugin_manager.plugin_manager import PluginManager
from lib.db.db_plugins import DBPlugins
from lib.db.db_scheduler import DBScheduler


REQUIRED_VERSION = '0.9.14'
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
    if not LOGGER:
        LOGGER = logging.getLogger(__name__)

    results = ''
    if _new_version.startswith(REQUIRED_VERSION):
        LOGGER.info('Applying patches to version: {}'.format(REQUIRED_VERSION))

        try:
            try:
                _config_obj.config_handler.remove_option('streams', 'stream_timeout')
            except configparser.NoSectionError:
                pass
            _config_obj.config_handler.remove_option('logger_root', 'level')
            _config_obj.config_handler.set('logger_root', 'level', 'TRACE')


        except Exception:
            # Make sure that the patcher exits normally so the maintenance flag is removed
            LOGGER.warning(traceback.format_exc())
    return results


def move_key(_config_obj, _key):
    find_key_by_section(_config_obj, _key, 'plutotv')
    find_key_by_section(_config_obj, _key, 'xumo')


def find_key_by_section(_config_obj, _key, _section):
    global LOGGER
    if not LOGGER:
        LOGGER = logging.getLogger(__name__)
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
        if section.startswith(_plugin_name + '_'):
            sections.append(section)
    return sections
