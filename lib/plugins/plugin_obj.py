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

import base64
import binascii
import datetime
import logging
import string
import threading
import time
import urllib.request

import lib.common.exceptions as exceptions
from lib.db.db_scheduler import DBScheduler


class PluginObj:

    def __init__(self, _plugin):
        self.logger = logging.getLogger(__name__)
        self.plugin = _plugin
        self.config_obj = _plugin.config_obj
        self.namespace = _plugin.namespace
        self.def_trans = ''.join([
            string.ascii_uppercase,
            string.ascii_lowercase,
            string.digits,
            '+/'
            ]).encode()
        self.instances = {}
        self.scheduler_db = DBScheduler(self.config_obj.data)
        self.scheduler_tasks()
        self.enabled = True
        self.logger.debug('Initializing plugin {}'.format(self.namespace))

    # INTERFACE METHODS
    # Plugin may have the following methods
    # used to interface to the app.
    
    def is_time_to_refresh_ext(self, _last_refresh, _instance):
        """
        External request to determine if the m3u8 stream uri needs to 
        be refreshed.
        Called from stream object.
        """
        self.check_logger_refresh()
        return False

    def get_channel_uri_ext(self, sid, _instance=None):
        """
        External request to return the uri for a m3u8 stream.
        Called from stream object.
        """
        self.check_logger_refresh()
        return self.instances[_instance].get_channel_uri(sid)

    # END OF INTERFACE METHODS


    def scheduler_tasks(self):
        """
        dummy routine that will be overridden by subclass
        """
        pass

    def refresh_obj(self, _topic, _task_name):
        if not self.enabled:
            self.logger.debug('{} Plugin disabled, not refreshing {}' \
                .format(self.plugin.name, _topic))
            return
        self.web_admin_url = 'http://localhost:' + \
            str(self.config_obj.data['web']['web_admin_port'])
        task = self.scheduler_db.get_tasks(_topic, _task_name)[0]
        url = ( self.web_admin_url + '/api/scheduler?action=runtask&taskid={}'
               .format(task['taskid']))
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as resp:
            result = resp.read()

        # wait for the last run to update indicating the task has completed.
        while True:
            task_status = self.scheduler_db.get_task(task['taskid'])
            x = datetime.datetime.utcnow() - task_status['lastran']
            # If updated in the last 20 minutes, then ignore
            # Many media servers will request this multiple times.
            if x.total_seconds() < 1200:
                break
            time.sleep(0.5)

    def refresh_channels(self, _instance=None):
        """
        Called from the scheduler
        """
        self.refresh_it('Channels', _instance)

    def refresh_epg(self, _instance=None):
        """
        Called from the scheduler
        """
        self.refresh_it('EPG', _instance)

    def refresh_it(self, _what_to_refresh, _instance=None):
        """
        _what_to_refresh is either 'EPG' or 'Channels' for now
        """
        try:
            if not self.enabled:
                self.logger.debug('{} Plugin disabled, not refreshing {}' \
                    .format(self.plugin.name, _what_to_refresh))
                return
            if _instance is None:
                for key, instance in self.instances.items():
                    if _what_to_refresh == 'EPG':
                        instance.refresh_epg()
                    elif _what_to_refresh == 'Channels':
                        instance.refresh_channels()
            else:
                if _what_to_refresh == 'EPG':
                    self.instances[_instance].refresh_epg()
                elif _what_to_refresh == 'Channels':
                    self.instances[_instance].refresh_channels()
        except exceptions.CabernetException:
            self.logger.debug('Setting plugin {} to disabled'.format(self.plugin.name))
            self.enabled = False
            self.plugin.enabled = False

    def utc_to_local_time(self, _hours):
        """
        Used for scheduler on daily events
        """
        tz_delta = datetime.datetime.now() - datetime.datetime.utcnow()
        tz_hours = round(tz_delta.total_seconds()/3610)
        local_hours = tz_hours + _hours
        if local_hours < 0:
            local_hours += 24
        elif local_hours > 23:
            local_hours -= 24
        return local_hours

    def compress(self, _data):
        if type(_data) is str:
            _data = _data.encode()
        return base64.b64encode(_data).translate(
            _data.maketrans(self.def_trans,
            self.config_obj.data['main']['plugin_data'].encode()))

    def uncompress(self, _data):
        if type(_data) is str:
            _data = _data.encode()
        a = self.config_obj.data['main']['plugin_data'].encode()
        try:
            return base64.b64decode(_data.translate(_data.maketrans(
                self.config_obj.data['main']['plugin_data']
                .encode(), self.def_trans))) \
                .decode()
        except (binascii.Error, UnicodeDecodeError) as ex:
            self.logger.error('Uncompression Error, invalid string {}' \
                .format(_data))
            return None

    def check_logger_refresh(self):
        if not self.logger.isEnabledFor(40):
            self.logger = logging.getLogger(__name__+str(threading.get_ident()))
            for inst, inst_obj in self.instances.items():
                self.logger.notice('######## CHECKING AND UPDATING LOGGER')
                inst_obj.check_logger_refresh()

    @property
    def name(self):
        return self.namespace

