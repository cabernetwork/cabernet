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


import logging
import traceback

from lib.plugins.plugin_manager.plugin_manager import PluginManager
from lib.db.db_plugins import DBPlugins
from lib.db.db_scheduler import DBScheduler


REQUIRED_VERSION = '0.9.12'
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
            plugin_db = DBPlugins(_config_obj.data)
            pm = PluginManager(None, _config_obj)

            # All plugins should be in the ext folder
            plugin_list = plugin_db.get_plugins(True)
            if plugin_list:
                for plugin in plugin_list:
                    if plugin.get('external') is False:
                        results = pm.delete_plugin(plugin['repoid'], plugin['id'])
                        results = pm.install_plugin(plugin['repoid'], plugin['id'])
                        results = 'Patch: Moving {} to plugins_ext ...'.format(plugin['id'])
                        LOGGER.warning('Patch: Moving {} to plugins_ext ...'.format(plugin['id']))

            # Check for Updates schedule task needs to be inline with high priority
            schedule_db = DBScheduler(_config_obj.data)
            task = schedule_db.get_tasks('Applications', 'Check for Updates')
            if task and task[0]['threadtype'] != 'inline':
                schedule_db.del_task('Applications', 'Check for Updates')
                LOGGER.warning('Resetting Check For Update task')

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
