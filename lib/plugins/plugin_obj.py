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

import base64
import binascii
import datetime
import logging
import requests
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
        self.plugins = None
        self.http_session = requests.session()
        # Disable the CERT unverified warnings
        requests.packages.urllib3.disable_warnings()
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

    def terminate(self):
        """
        Removes all has a object from the object and calls any subclasses to also terminate
        Not calling inherited class at this time
        """
        self.enabled = False
        for key, instance in self.instances.items():
            return instance.terminate()
        self.logger = None
        self.plugin = None
        self.plugins = None
        self.http_session = None
        self.config_obj = None
        self.namespace = None
        self.def_trans = None
        self.instances = None
        self.scheduler_db = None

    

    # INTERFACE METHODS
    # Plugin may have the following methods
    # used to interface to the app.

    ##############################
    # ## EXTERNAL STREAM METHODS
    ##############################

    def is_time_to_refresh_ext(self, _last_refresh, _instance):
        """
        External request to determine if the m3u8 stream uri needs to 
        be refreshed.
        Called from stream object.
        """
        self.check_logger_refresh()
        return False

    def get_channel_uri_ext(self, _sid, _instance=None):
        """
        External request to return the uri for a m3u8 stream.
        Called from stream object.
        """
        self.check_logger_refresh()
        return self.instances[_instance].get_channel_uri(_sid)

    ##############################
    # ## EXTERNAL EPG METHODS
    ##############################

    def get_channel_day_ext(self, _zone, _uid, _day, _instance='default'):
        """
        External request to return the programs for the day requested 
        as an offset int from current time
        """
        self.check_logger_refresh()
        return self.instances[_instance].get_channel_day(_zone, _uid, _day)

    def get_program_info_ext(self, _prog_id, _instance='default'):
        """
        External request to return the program details
        either from provider or from database
        includes updating database if needed.
        """
        self.check_logger_refresh()
        return self.instances[_instance].get_program_info(_prog_id)

    def get_channel_list_ext(self, _zone_id, _ch_ids=None, _instance='default'):
        """
        External request to return the channe list based on the zone 
        and the list of channels requested
        """
        self.check_logger_refresh()
        return self.instances[_instance].get_channel_list(_zone_id, _ch_ids)

    # END OF INTERFACE METHODS

    def scheduler_tasks(self):
        """
        dummy routine that will be overridden by subclass
        """
        pass

    def enable_instance(self, _namespace, _instance, _instance_name='Instance'):
        """
        When one plugin is tied to another and requires it to be enabled,
        this method will enable the other instance and set this plugin to disabled until 
        everything is up
        Also used to create a new instance if missing.  When _instance is None, 
        will look for any instance, if not will create a default one.
        """
        name_config = _namespace.lower()
        # if _instance is None and config has no instance for namespace, add one
        if _instance is None:
            x = [ k for k in self.config_obj.data.keys() if k.startswith(name_config+'_')]
            if len(x):
                return
            else:
                _instance = 'Default'
        instance_config = name_config + '_' + _instance.lower()
        
        if self.config_obj.data.get(name_config):
            if self.config_obj.data.get(instance_config):
                if not self.config_obj.data[instance_config]['enabled']:
                    self.logger.warning('1. Enabling {}:{} plugin instance. Required by {}. Restart Required'
                                       .format(_namespace, _instance, self.namespace))
                    self.config_obj.write(
                        instance_config, 'enabled', True)
                    raise exceptions.CabernetException('{} plugin requested by {}.  Restart Required'
                                                       .format(_namespace, self.namespace))
            else:
                if _namespace != self.namespace:
                    self.logger.warning('2. Enabling {}:{} plugin instance. Required by {}. Restart Required'
                                       .format(_namespace, _instance, self.namespace))
                else:
                    self.logger.warning('3. Enabling {}:{} plugin instance. Restart Required'
                                       .format(_namespace, _instance, self.namespace))
                
                self.config_obj.write(
                    instance_config, 'Label', _namespace + ' ' + _instance_name)
                self.config_obj.write(
                    instance_config, 'enabled', True)
                raise exceptions.CabernetException('{} plugin requested by {}.  Restart Required'
                                                   .format(_namespace, self.namespace))
        else:
            self.logger.error('Requested Plugin {} by {} Missing'
                              .format(_namespace, self.namespace))
            raise exceptions.CabernetException('Requested Plugin {} by {} Missing'
                                               .format(_namespace, self.namespace))
        if _namespace not in self.plugins.keys():
            self.logger.warning('{}:{} not installed and requested by {} settings. Restart Required'
                               .format(_namespace, _instance, self.namespace))
            raise exceptions.CabernetException('{}:{} not enabled and requested by {} settings. Restart Required'
                                               .format(_namespace, _instance, self.namespace))

        if not self.plugins[_namespace].enabled:
            self.logger.warning('{}:{} not enabled and requested by {} settings. Restart Required'
                               .format(_namespace, _instance, self.namespace))
            raise exceptions.CabernetException('{}:{} not enabled and requested by {} settings. Restart Required'
                                               .format(_namespace, _instance, self.namespace))

    def refresh_obj(self, _topic, _task_name):
        if not self.enabled:
            self.logger.debug(
                '{} Plugin disabled, not refreshing {}'
                .format(self.plugin.name, _topic))
            return
        web_admin_url = 'http://localhost:' + \
                        str(self.config_obj.data['web']['web_admin_port'])
        task = self.scheduler_db.get_tasks(_topic, _task_name)[0]
        url = (web_admin_url + '/api/scheduler?action=runtask&taskid={}'
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
        return self.refresh_it('Channels', _instance)

    def refresh_epg(self, _instance=None):
        """
        Called from the scheduler
        """
        return self.refresh_it('EPG', _instance)

    def refresh_it(self, _what_to_refresh, _instance=None):
        """
        _what_to_refresh is either 'EPG' or 'Channels' for now
        """
        try:
            if not self.enabled:
                self.logger.debug(
                    '{} Plugin disabled, not refreshing {}'
                    .format(self.plugin.name, _what_to_refresh))
                return False
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
            return True
        except exceptions.CabernetException:
            self.logger.debug('Setting plugin {} to disabled'.format(self.plugin.name))
            self.enabled = False
            self.plugin.enabled = False
            return False

    def utc_to_local_time(self, _hours):
        """
        Used for scheduler on events
        """
        tz_delta = datetime.datetime.now() - datetime.datetime.utcnow()
        tz_hours = round(tz_delta.total_seconds() / 3610)
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
        self.config_obj.data['main']['plugin_data'].encode()
        try:
            return base64.b64decode(_data.translate(_data.maketrans(
                self.config_obj.data['main']['plugin_data']
                .encode(), self.def_trans))) \
                .decode()
        except (binascii.Error, UnicodeDecodeError):
            self.logger.error('Uncompression Error, invalid string {}'.format(_data))
            return None

    def check_logger_refresh(self):
        if not self.logger.isEnabledFor(40):
            self.logger = logging.getLogger(__name__ + str(threading.get_ident()))
            for inst, inst_obj in self.instances.items():
                inst_obj.check_logger_refresh()

    @property
    def name(self):
        return self.namespace
