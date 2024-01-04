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

from lib.db.db_plugins import DBPlugins
from lib.plugins.plugin_manager.plugin_manager import PluginManager


class PluginsUpgrade:

    def __init__(self, _plugins):
        self.logger = logging.getLogger(__name__)
        self.config_obj = _plugins.config_obj
        self.config = _plugins.config_obj.data
        self.plugin_db = DBPlugins(self.config)
        self.pm = PluginManager(None, self.config_obj)


    def upgrade_plugins(self, _web_status):
        _web_status.data += '#### Checking Plugins ####<br>\r\n'
        plugin_defns = self.plugin_db.get_plugins(True)
        if not plugin_defns:
            return True

        for p_defn in plugin_defns:
            if not p_defn.get('external'):
                continue
            if p_defn['version']['current'] == p_defn['version']['latest']:
                continue
            # upgrade available
            _web_status.data += self.pm.delete_plugin(p_defn['repoid'], p_defn['id'])
            _web_status.data += self.pm.install_plugin(p_defn['repoid'], p_defn['id'])
        _web_status.data += '<br>\r\n#### Plugin Upgrades Finished ####<br>\r\n'

        return True

