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
import json
import importlib
import importlib.resources

import lib.common.exceptions as exceptions
import lib.common.utils as utils

from .plugin import Plugin
from lib.db.db_plugins import DBPlugins

PLUGIN_DEFN_FILE = 'plugin_defn.json'


class PluginHandler:

    logger = None
    cls_plugins = None

    def __init__(self, _config_obj):
        self.plugins = {}
        self.config_obj = _config_obj
        if PluginHandler.logger is None:
            PluginHandler.logger = logging.getLogger(__name__)
        self.plugin_defn = self.load_plugin_defn()
        self.collect_plugins(self.config_obj.data['paths']['internal_plugins_pkg'])
        self.collect_plugins(self.config_obj.data['paths']['external_plugins_pkg'])
        if PluginHandler.cls_plugins is not None:
            del PluginHandler.cls_plugins
        PluginHandler.cls_plugins = self.plugins

    def collect_plugins(self, _plugins_pkg):
        plugin_db = DBPlugins(self.config_obj.data)
        #plugin_db.reinitialize_tables()
        for folder in importlib.resources.contents(_plugins_pkg):
            if folder.startswith('__'):
                continue
            try:
                importlib.resources.read_text(_plugins_pkg, folder)
            except (IsADirectoryError, PermissionError) as e:
                try:
                    plugin = Plugin(self.config_obj, self.plugin_defn, '.'.join([_plugins_pkg, folder]))
                    self.plugins[plugin.name] = plugin
                except (exceptions.CabernetException, AttributeError):
                    pass
        self.del_missing_plugins()

    def del_missing_plugins(self):
        """
        deletes the plugins from the db that are no longer present
        """
        plugin_db = DBPlugins(self.config_obj.data)
        plugin_dblist = plugin_db.get_plugins()
        for p_dict in plugin_dblist:
            if (p_dict['name'] not in self.plugins) and (p_dict['name'] != utils.CABERNET_NAMESPACE):
                plugin_db.del_plugin(p_dict['name'])

    def load_plugin_defn(self):
        try:
            defn_file = importlib.resources.read_text(self.config_obj.data['paths']['resources_pkg'], PLUGIN_DEFN_FILE)
            self.logger.debug('Plugin Defn file loaded')
            defn = json.loads(defn_file)
        except FileNotFoundError:
            self.logger.warning('PLUGIN DEFN FILE NOT FOUND AT {} {}'.format(
                self.config_obj.data['paths']['resources_dir'], PLUGIN_DEFN_FILE))
            defn = {}
        return defn

    def initialize_plugins(self):
        for name, plugin in self.plugins.items():
            if not self.config_obj.data[plugin.name.lower()]['enabled']:
                self.logger.info('Plugin {} is disabled in config.ini'.format(plugin.name))
                plugin.enabled = False
            else:
                try:
                    plugin.plugin_obj = plugin.init_func(plugin, self.plugins)
                except exceptions.CabernetException:
                    self.logger.debug('Setting plugin {} to disabled'.format(plugin.name))
                    self.config_obj.data[plugin.name.lower()]['enabled'] = False
                    plugin.enabled = False
