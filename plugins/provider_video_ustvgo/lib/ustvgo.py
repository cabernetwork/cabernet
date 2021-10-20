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

from .ustvgo_instance import USTVGOInstance
from ..lib import translations

class USTVGO(PluginObj):

    def __init__(self, _plugin):
        super().__init__(_plugin)
        if not self.config_obj.data[_plugin.name.lower()]['enabled']:
            return
        for inst in _plugin.instances:
            self.instances[inst] = USTVGOInstance(self, inst)
        self.unc_ustvgo_channels = self.uncompress(translations.ustvgo_channels)
        self.unc_ustvgo_png = self.uncompress(translations.ustvgo_png)
        self.unc_ustvgo_stream = self.uncompress(translations.ustvgo_stream)
        self.unc_ustvgo_epg = self.uncompress(translations.ustvgo_epg)
        self.unc_ustvgo_program = self.uncompress(translations.ustvgo_program)


    def scheduler_tasks(self):
        sched_ch_hours = random.randint(3,5)
        sched_epg_hours = sched_ch_hours + 1
        sched_ch_mins = random.randint(1,55)
        sched_epg_mins = random.randint(1,55)
        sched_ch = '{:0>2d}:{:0>2d}'.format(sched_ch_hours, sched_ch_mins)
        sched_epg = '{:0>2d}:{:0>2d}'.format(sched_epg_hours, sched_epg_mins)
        if self.scheduler_db.save_task(
                'Channels',
                'Refresh {} Channels'.format(self.namespace),
                self.name,
                None,
                'refresh_channels',
                20,
                'inline',
                'Pulls channel lineup from {}'.format(self.namespace)
                ):
            self.scheduler_db.save_trigger(
                'Channels',
                'Refresh {} Channels'.format(self.namespace),
                'startup')
            self.scheduler_db.save_trigger(
                'Channels',
                'Refresh {} Channels'.format(self.namespace),
                'daily',
                timeofday=sched_ch
                )
        if self.scheduler_db.save_task(
                'EPG',
                'Refresh {} EPG'.format(self.namespace),
                self.name,
                None,
                'refresh_epg',
                10,
                'thread',
                'Pulls channel program data from {}'.format(self.namespace)
                ):
            self.scheduler_db.save_trigger(
                'EPG',
                'Refresh {} EPG'.format(self.namespace),
                'startup')
            self.scheduler_db.save_trigger(
                'EPG',
                'Refresh {} EPG'.format(self.namespace),
                'interval',
                interval=160,
                randdur=40
                )
