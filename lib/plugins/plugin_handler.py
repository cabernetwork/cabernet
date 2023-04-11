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
import json
import importlib
import importlib.resources
import os
import pathlib

import lib.common.exceptions as exceptions
import lib.common.utils as utils

from .plugin import Plugin
from .repo_handler import RepoHandler
from lib.db.db_plugins import DBPlugins
from lib.db.db_channels import DBChannels
from lib.db.db_config_defn import DBConfigDefn

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
        self.check_external_plugin_folder()
        self.repos = RepoHandler(self.config_obj)

        self.repos.load_cabernet_repo()
        self.collect_plugins(self.config_obj.data['paths']['internal_plugins_pkg'], False)
        self.collect_plugins(self.config_obj.data['paths']['external_plugins_pkg'], True)
        self.cleanup_config_missing_plugins()
        if PluginHandler.cls_plugins is not None:
            del PluginHandler.cls_plugins
        PluginHandler.cls_plugins = self.plugins

    def terminate(self, _plugin_name):
        """
        calls terminate to the plugin requested
        """
        self.plugins[_plugin_name].terminate()
        del self.plugins[_plugin_name]

    def check_external_plugin_folder(self):
        """
        If the folder does not exists, then create it and place the 
        __init__.py file in it.
        """
        ext_folder = pathlib.Path(self.config_obj.data['paths']['main_dir']) \
            .joinpath(self.config_obj.data['paths']['external_plugins_pkg'])
        init_file = ext_folder.joinpath('__init__.py')
        if not init_file.exists():
            self.logger.notice('Creating external plugin folder for use by Cabernet')
            try:
                if not ext_folder.exists():
                    os.makedirs(ext_folder)
                f = open(init_file, 'wb')
                f.close()
            except PermissionError as e:
                self.logger.warning('ERROR: {} unable to create {}'.format(str(e), init_file))

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

    def cleanup_config_missing_plugins(self):
        """
        Case where the plugin is deleted from folder, but database and config
        still have data.
        """
        ch_db = DBChannels(self.config_obj.data)
        ns_inst_list = ch_db.get_channel_instances()
        ns_list = ch_db.get_channel_names()
        for ns in ns_list:
            ns = ns['namespace']
            if not self.plugins.get(ns) and self.config_obj.data.get(ns.lower()):
                for nv in self.config_obj.data.get(ns.lower()).items():
                    new_value = self.set_value_type(nv[1])
                    self.config_obj.data[ns.lower()][nv[0]] = new_value
        for ns_inst in ns_inst_list:
            if not self.plugins.get(ns_inst['namespace']):
                inst_name = utils.instance_config_section(ns_inst['namespace'], ns_inst['instance'])
                if self.config_obj.data.get(inst_name):
                    for nv in self.config_obj.data.get(inst_name).items():
                        new_value = self.set_value_type(nv[1])
                        self.config_obj.data[inst_name][nv[0]] = new_value
        db_configdefn = DBConfigDefn(self.config_obj.data)
        db_configdefn.add_config(self.config_obj.data)

    def set_value_type(self, _value):
        if not isinstance(_value, str):
            return _value
        if _value == 'True':
            return True
        elif _value == 'False':
            return False
        elif _value.isdigit():
            return int(_value)
        else:
            return _value

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
