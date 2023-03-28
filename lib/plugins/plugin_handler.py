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
import json
import importlib
import importlib.resources

import lib.common.exceptions as exceptions
import lib.common.utils as utils

from .plugin import Plugin
from .repo_handler import RepoHandler
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
        self.repos = RepoHandler(self.config_obj)
        self.repos.load_cabernet_repo()
        self.collect_plugins(self.config_obj.data['paths']['internal_plugins_pkg'], False)
        self.collect_plugins(self.config_obj.data['paths']['external_plugins_pkg'], True)
        if PluginHandler.cls_plugins is not None:
            del PluginHandler.cls_plugins
        PluginHandler.cls_plugins = self.plugins

    def terminate(self, _plugin_name):
        """
        calls terminate to the plugin requested
        """
        self.plugins[_plugin_name].terminate()
        del self.plugins[_plugin_name]

    def collect_plugins(self, _plugins_pkg, _is_external):
        pkg = importlib.util.find_spec(_plugins_pkg)
        if not pkg:
            # module folder does not exist, do nothing
            self.logger.notice(
                'plugin folder {} does not exist with a __init__.py empty file in it.'
                .format(_plugins_pkg))
            return
        
        for folder in importlib.resources.contents(_plugins_pkg):
            self.collect_plugin(_plugins_pkg, _is_external, folder)
        self.del_missing_plugins()

    def collect_plugin(self, _plugins_pkg, _is_external, _folder):
        if _folder.startswith('__'):
            return
        try:
            importlib.resources.read_text(_plugins_pkg, _folder)
        except (IsADirectoryError, PermissionError):
            try:
                plugin = Plugin(self.config_obj, self.plugin_defn, _plugins_pkg, _folder, _is_external)
                self.plugins[plugin.name] = plugin
            except (exceptions.CabernetException, AttributeError):
                pass
        except UnicodeDecodeError:
            pass
        except Exception:
            pass
        return

    def del_missing_plugins(self):
        """
        updates to uninstalled the plugins from the db that are no longer present
        """
        plugin_db = DBPlugins(self.config_obj.data)
        plugin_dblist = plugin_db.get_plugins(_installed=True)
        if plugin_dblist:
            for p_dict in plugin_dblist:
                if (p_dict['name'] not in self.plugins) and (p_dict['name'] != utils.CABERNET_ID):
                    p_dict['version']['installed'] = False
                    plugin_db.save_plugin(p_dict)

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
            if not plugin.enabled or not self.config_obj.data[plugin.name.lower()]['enabled']:
                self.logger.info('Plugin {} is disabled in config.ini'.format(plugin.name))
                plugin.enabled = False
            else:
                try:
                    plugin.plugin_obj = plugin.init_func(plugin, self.plugins)
                except exceptions.CabernetException:
                    self.logger.debug('Setting plugin {} to disabled'.format(plugin.name))
                    self.config_obj.data[plugin.name.lower()]['enabled'] = False
                    plugin.enabled = False
