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

import datetime
import logging

from lib.db.db_channels import DBChannels


class PluginChannels:
    logger = None

    def __init__(self, _instance_obj):
        if PluginChannels.logger is None:
            PluginChannels.logger = logging.getLogger(__name__)
        self.instance_obj = _instance_obj
        self.plugin_obj = _instance_obj.plugin_obj
        self.instance_key = _instance_obj.instance_key
        self.db = DBChannels(self.instance_obj.config_obj.data)
        self.config_section = self.instance_obj.config_section


    def refresh_channels(self, force=False):
        last_update = self.db.get_status(self.plugin_obj.name, self.instance_key)
        update_needed = False
        if not last_update:
            update_needed = True
        else:
            delta = datetime.datetime.now() - last_update
            if delta.total_seconds() / 3600 >= self.instance_obj.config_obj.data[
                    self.plugin_obj.name.lower()]['channel-update_timeout']:
                update_needed = True
        if update_needed or force:
            ch_dict = self.get_channels()
            if 'channel-import_groups' in self.instance_obj.config_obj.data[self.plugin_obj.name.lower()]:
                self.db.save_channel_list(self.plugin_obj.name, self.instance_key, ch_dict, \
                    self.instance_obj.config_obj.data[self.plugin_obj.name.lower()]['channel-import_groups'])
            else:
                self.db.save_channel_list(self.plugin_obj.name, self.instance_key, ch_dict)
        else:
            self.logger.debug('Channel data still new for {} {}, not refreshing' \
                .format(self.plugin_obj.name, self.instance_key))

