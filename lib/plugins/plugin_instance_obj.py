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
import threading

import lib.common.utils as utils
from lib.db.db_scheduler import DBScheduler


class PluginInstanceObj:

    def __init__(self, _plugin_obj, _instance_key):
        self.logger = logging.getLogger(__name__)
        self.config_obj = _plugin_obj.config_obj
        self.plugin_obj = _plugin_obj
        self.instance_key = _instance_key
        self.scheduler_db = DBScheduler(self.config_obj.data)
        self.scheduler_tasks()
        self.enabled = True
        self.channels = None
        self.epg = None
        if not self.config_obj.data[self.config_section]['enabled']:
            self.enabled = False
        else:
            self.enabled = True

    def scheduler_tasks(self):
        """
        dummy routine that will be overridden by subclass,
        if scheduler tasks are needed at the instance level
        """
        pass

    def refresh_channels(self):
        self.config_obj.refresh_config_data()
        if self.channels is not None and \
                self.config_obj.data[self.config_section]['enabled']:
            self.channels.refresh_channels()
        else:
            self.logger.debug('{}:{} Plugin instance disabled, not refreshing Channels' \
                .format(self.plugin_obj.name, self.instance_key))

    def get_channel_uri(self, sid):
        if self.enabled and self.config_obj.data[self.config_section]['enabled']:
            return self.channels.get_channel_uri(sid)
        else:
            self.logger.debug('{}:{} Plugin instance disabled, not getting Channel uri' \
                .format(self.plugin_obj.name, self.instance_key))
            return None

    def refresh_epg(self):
        self.config_obj.refresh_config_data()
        if self.epg is not None and \
                self.config_obj.data[self.config_section]['enabled']:
            self.epg.refresh_epg()
        else:
            self.logger.debug('{}:{} Plugin instance disabled, not refreshing EPG' \
                .format(self.plugin_obj.name, self.instance_key))

    def is_time_to_refresh(self, _last_refresh):
        return False
                
    def check_logger_refresh(self):
        if not self.logger.isEnabledFor(40):
            self.logger = logging.getLogger(__name__+str(threading.get_ident()))
            self.logger.notice('######## CHECKING AND UPDATING LOGGER2')
            if self.channels is not None:
                self.channels.check_logger_refresh()
            if self.epg is not None:
                self.epg.check_logger_refresh()

    @property
    def config_section(self):
        return utils.instance_config_section(self.plugin_obj.name, self.instance_key)
