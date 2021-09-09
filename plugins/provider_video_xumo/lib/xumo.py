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
import random
import time
import urllib.request

from lib.plugins.plugin_obj import PluginObj

from .geo import Geo
from .xumo_instance import XUMOInstance


class XUMO(PluginObj):

    def __init__(self, _plugin):
        super().__init__(_plugin)
        self.geo = Geo(_plugin.config_obj, self.namespace.lower())
        
        for inst in _plugin.instances:
            self.instances[inst] = XUMOInstance(self, inst)

    def refresh_channels_ext(self, _instance=None):
        """
        External request to refresh channels. Called from the plugin manager.
        All tasks are namespace based so instance is ignored. 
        This calls the scheduler to run the task.
        """
        self.refresh_obj('Channels', 'Refresh XUMO Channels')

    def refresh_epg_ext(self, _instance=None):
        """
        External request to refresh epg. Called from the plugin manager.
        All tasks are namespace based so instance is ignored.
        This calls the scheduler to run the task.
        """
        self.refresh_obj('EPG', 'Refresh XUMO EPG')

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

    def scheduler_tasks(self):
        sched_epg_hours = self.utc_to_local_time(0)
        sched_epg_mins = random.randint(1,55)
        sched_epg = '{:0>2d}:{:0>2d}'.format(sched_epg_hours, sched_epg_mins)
        sched_ch_hours = self.utc_to_local_time(23)
        sched_ch_mins = random.randint(1,55)
        sched_ch = '{:0>2d}:{:0>2d}'.format(sched_ch_hours, sched_ch_mins)
        # if self.scheduler_db.save_task(
                # 'Channels',
                # 'Refresh XUMO Channels',
                # self.name,
                # None,
                # 'refresh_channels',
                # 20,
                # 'inline',
                # 'Pulls channel lineup from XUMO'
                # ):
            # self.scheduler_db.save_trigger(
                # 'Channels',
                # 'Refresh XUMO Channels',
                # 'startup')
            # self.scheduler_db.save_trigger(
                # 'Channels',
                # 'Refresh XUMO Channels',
                # 'daily',
                # timeofday=sched_ch
                # )
        # if self.scheduler_db.save_task(
                # 'EPG',
                # 'Refresh XUMO EPG',
                # self.name,
                # None,
                # 'refresh_epg',
                # 10,
                # 'thread',
                # 'Pulls channel program data from XUMO'
                # ):
            # self.scheduler_db.save_trigger(
                # 'EPG',
                # 'Refresh XUMO EPG',
                # 'startup')
            # self.scheduler_db.save_trigger(
                # 'EPG',
                # 'Refresh XUMO EPG',
                # 'daily',
                # timeofday=sched_epg
                # )
