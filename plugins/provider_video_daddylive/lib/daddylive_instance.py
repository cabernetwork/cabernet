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

import lib.common.utils as utils
import lib.common.exceptions as exceptions
from lib.plugins.plugin_instance_obj import PluginInstanceObj

from .channels import Channels
from .epg import EPG


class DaddyLiveInstance(PluginInstanceObj):

    def __init__(self, _daddylive, _instance):
        super().__init__(_daddylive, _instance)
        if not self.config_obj.data[_daddylive.name.lower()]['enabled']:
            return
        if not self.config_obj.data[self.config_section]['enabled']:
            return

        self.channels = Channels(self)
        self.epg = EPG(self)

    def scan_channels(self):
        """
        Scans the channels that are disabled or untested to see if they should be disabled
        """
        self.config_obj.refresh_config_data()
        if self.channels is not None and \
                self.config_obj.data[self.config_section]['enabled']:
            self.channels.scan_channels()
        else:
            self.logger.debug('{}:{} Plugin instance disabled, not scanning Channels' \
                .format(self.plugin_obj.name, self.instance_key))
