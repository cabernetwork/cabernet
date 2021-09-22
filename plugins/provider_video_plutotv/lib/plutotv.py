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

from .plutotv_instance import PlutoTVInstance
from ..lib import translations

class PlutoTV(PluginObj):

    def __init__(self, _plugin):
        super().__init__(_plugin)
        if not self.config_obj.data[_plugin.name.lower()]['enabled']:
            return
        for inst in _plugin.instances:
            self.instances[inst] = PlutoTVInstance(self, inst)
        self.unc_pluto_base = self.uncompress(translations.pluto_base)

    def refresh_channels_ext(self, _instance=None):
        """
        External request to refresh channels. Called from the plugin manager.
        All tasks are namespace based so instance is ignored. 
        This calls the scheduler to run the task.
        """
        self.refresh_obj('Channels', 'Refresh PlutoTV Channels')

    def refresh_epg_ext(self, _instance=None):
        """
        External request to refresh epg. Called from the plugin manager.
        All tasks are namespace based so instance is ignored.
        This calls the scheduler to run the task.
        """
        self.refresh_obj('EPG', 'Refresh PlutoTV EPG')
        
    def scheduler_tasks(self):
        sched_ch_hours = self.utc_to_local_time(23)
        sched_ch_mins = random.randint(1,55)
        sched_ch = '{:0>2d}:{:0>2d}'.format(sched_ch_hours, sched_ch_mins)
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
                timeofday=sched_ch
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
                interval=200,
                randdur=80
                )
