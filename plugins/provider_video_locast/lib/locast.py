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
import time
import urllib.request

from lib.db.db_scheduler import DBScheduler
from lib.plugins.plugin_obj import PluginObj

from .authenticate import Authenticate
from .locast_instance import LocastInstance


class Locast(PluginObj):

    def __init__(self, _plugin):
        super().__init__(_plugin)
        self.auth = Authenticate(_plugin.config_obj, self.namespace.lower())
        self.scheduler_db = DBScheduler(self.config_obj.data)
        for inst in _plugin.instances:
            self.instances[inst] = LocastInstance(self, inst)
        self.scheduler_tasks()

    def refresh_channels_ext(self, _instance=None):
        """
        External request to refresh channels. Called from the plugin manager.
        All tasks are namespace based so instance is ignored. 
        This calls the scheduler to run the task.
        """
        self.web_admin_url = 'http://localhost:' + \
            str(self.config_obj.data['web']['web_admin_port'])
        task = self.scheduler_db.get_tasks('Channels', 'Refresh Locast Channels')[0]
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

    def refresh_epg_ext(self, _instance=None):
        """
        External request to refresh epg. Called from the plugin manager.
        All tasks are namespace based so instance is ignored.
        This calls the scheduler to run the task.
        """
        self.web_admin_url = 'http://localhost:' + \
            str(self.config_obj.data['web']['web_admin_port'])
        task = self.scheduler_db.get_tasks('EPG', 'Refresh Locast EPG')[0]
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

    def get_channel_uri_ext(self, sid, _instance=None):
        """
        External request to return the uri for a m3u8 stream.
        Called from stream object.
        """
        return self.instances[_instance].get_channel_uri(sid)

    def is_time_to_refresh_ext(self, _last_refresh, _instance):
        """
        External request to determine if the m3u8 stream uri needs to 
        be refreshed.
        Called from stream object.
        """
        return self.instances[_instance].is_time_to_refresh(_last_refresh)

    def refresh_channels(self, _instance=None):
        """
        Called from the scheduler
        """
        if _instance is None:
            for key, instance in self.instances.items():
                instance.refresh_channels()
        else:
            self.instances[_instance].refresh_channels()

    def refresh_epg(self, _instance=None):
        """
        Called from the scheduler
        """
        if _instance is None:
            for key, instance in self.instances.items():
                instance.refresh_epg()
        else:
            self.instances[_instance].refresh_epg()

    def scheduler_tasks(self):
        if self.scheduler_db.save_task(
                'Channels',
                'Refresh Locast Channels',
                self.name,
                None,
                'refresh_channels',
                20,
                'inline',
                'Pulls channel lineup from Locast'
                ):
            self.scheduler_db.save_trigger(
                'Channels',
                'Refresh Locast Channels',
                'startup')
            self.scheduler_db.save_trigger(
                'Channels',
                'Refresh Locast Channels',
                'daily',
                timeofday='22:00'
                )
        if self.scheduler_db.save_task(
                'EPG',
                'Refresh Locast EPG',
                self.name,
                None,
                'refresh_epg',
                10,
                'thread',
                'Pulls channel program data from Locast'
                ):
            self.scheduler_db.save_trigger(
                'EPG',
                'Refresh Locast EPG',
                'startup')
            self.scheduler_db.save_trigger(
                'EPG',
                'Refresh Locast EPG',
                'interval',
                interval=700
                )

    @property
    def name(self):
        return self.namespace

