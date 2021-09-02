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

from .plutotv_instance import PlutoTVInstance


class PlutoTV(PluginObj):

    def __init__(self, _plugin):
        super().__init__(_plugin)
        self.scheduler_db = DBScheduler(self.config_obj.data)
        for inst in _plugin.instances:
            self.instances[inst] = PlutoTVInstance(self, inst)
        self.scheduler_tasks()

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
                'Refresh PlutoTV Channels',
                self.name,
                None,
                'refresh_channels',
                20,
                'inline',
                'Pulls channel lineup from PlutoTV'
                ):
            self.scheduler_db.save_trigger(
                'Channels',
                'Refresh PlutoTV Channels',
                'startup')
            self.scheduler_db.save_trigger(
                'Channels',
                'Refresh PlutoTV Channels',
                'daily',
                timeofday='22:00'
                )
        if self.scheduler_db.save_task(
                'EPG',
                'Refresh PlutoTV EPG',
                self.name,
                None,
                'refresh_epg',
                10,
                'thread',
                'Pulls channel program data from PlutoTV'
                ):
            self.scheduler_db.save_trigger(
                'EPG',
                'Refresh PlutoTV EPG',
                'startup')
            self.scheduler_db.save_trigger(
                'EPG',
                'Refresh PlutoTV EPG',
                'interval',
                interval=120
                )

    @property
    def name(self):
        return self.namespace

