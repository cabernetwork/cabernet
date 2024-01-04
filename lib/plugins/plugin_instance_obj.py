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
        self.programs = None
        self.epg = None
        if not self.config_obj.data[self.config_section]['enabled']:
            self.enabled = False
        else:
            self.enabled = True

    def terminate(self):
        """
        Removes all has a object from the object and calls any subclasses to also terminate
        Not calling inherited class at this time
        """
        self.enabled = False
        if self.channels:
            self.channels.terminate()
        if self.epg:
            self.epg.terminate()
        if self.programs:
            self.programs.terminate()
        self.logger = None
        self.config_obj = None
        self.plugin_obj = None
        self.instance_key = None
        self.scheduler_db = None
        self.enabled = None
        self.channels = None
        self.programs = None
        self.epg = None


    ##############################
    # ## EXTERNAL STREAM METHODS
    ##############################

    def is_time_to_refresh(self, _last_refresh):
        """
        External request to determine if the m3u8 stream uri needs to 
        be refreshed.
        Called from stream object.
        """
        return False

    def get_channel_uri(self, sid):
        """
        External request to return the uri for a m3u8 stream.
        Called from stream object.
        """
        if self.enabled and self.config_obj.data[self.config_section]['enabled']:
            return self.channels.get_channel_uri(sid)
        else:
            self.logger.debug(
                '{}:{} Plugin instance disabled, not getting Channel uri'
                .format(self.plugin_obj.name, self.instance_key))
            return None

    ##############################
    # ## EXTERNAL EPG METHODS
    ##############################

    def get_channel_day(self, _zone, _uid, _day):
        """
        External request to return the program list for a channel
        based on the day requested day=0 means today
        """
        if self.enabled and self.config_obj.data[self.config_section]['enabled']:
            return self.epg.get_channel_day(_zone, _uid, _day)
        else:
            self.logger.debug(
                '{}:{} Plugin instance disabled, not getting EPG channel data'
                .format(self.plugin_obj.name, self.instance_key))
            return None

    def get_program_info(self, _prog_id):
        """
        External request to return the program details
        either from provider or from database
        includes updating database if needed.
        """
        if self.enabled and self.config_obj.data[self.config_section]['enabled']:
            return self.programs.get_program_info(_prog_id)
        else:
            self.logger.debug(
                '{}:{} Plugin instance disabled, not getting EPG program data'
                .format(self.plugin_obj.name, self.instance_key))
            return None

    def get_channel_list(self, _zone_id, _ch_ids=None):
        """
        External request to return the channel list for a zone.
        if ch_ids is None, then all channels are returned
        """
        if self.enabled and self.config_obj.data[self.config_section]['enabled']:
            return self.channels.get_channel_list(_zone_id, _ch_ids)
        else:
            self.logger.debug(
                '{}:{} Plugin instance disabled, not getting EPG zone data'
                .format(self.plugin_obj.name, self.instance_key))
            return None

    ##############################

    def scheduler_tasks(self):
        """
        dummy routine that will be overridden by subclass,
        if scheduler tasks are needed at the instance level
        """
        pass

    def refresh_channels(self):
        """
        Called from the scheduler
        """
        self.config_obj.refresh_config_data()
        if self.channels is not None and \
                self.config_obj.data[self.config_section]['enabled']:
            return self.channels.refresh_channels()
        else:
            self.logger.notice(
                '{}:{} Plugin instance disabled, not refreshing Channels'
                .format(self.plugin_obj.name, self.instance_key))
            return False

    def refresh_epg(self):
        """
        Called from the scheduler
        """
        self.config_obj.refresh_config_data()
        if self.epg is not None and \
                self.config_obj.data[self.config_section]['enabled']:
            return self.epg.refresh_epg()
        else:
            self.logger.info(
                '{}:{} Plugin instance disabled, not refreshing EPG'
                .format(self.plugin_obj.name, self.instance_key))
            return False

    def check_logger_refresh(self):
        if not self.logger.isEnabledFor(40):
            self.logger = logging.getLogger(__name__ + str(threading.get_ident()))
            if self.channels is not None:
                self.channels.check_logger_refresh()
            if self.epg is not None:
                self.epg.check_logger_refresh()
            if self.programs is not None:
                self.programs.check_logger_refresh()

    @property
    def config_section(self):
        return utils.instance_config_section(self.plugin_obj.name, self.instance_key)
