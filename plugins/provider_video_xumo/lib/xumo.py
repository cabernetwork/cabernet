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

import random

from lib.plugins.plugin_obj import PluginObj

from .geo import Geo
from .xumo_instance import XUMOInstance
from ..lib import translations


class XUMO(PluginObj):

    def __init__(self, _plugin):
        super().__init__(_plugin)
        self.geo = Geo(_plugin.config_obj, self.namespace.lower())
        for inst in _plugin.instances:
            self.instances[inst] = XUMOInstance(self, inst)
        self.unc_xumo_base = self.uncompress(translations.xumo_base)
        self.unc_xumo_icons = self.uncompress(translations.xumo_icons)
        self.unc_xumo_channel = self.uncompress(translations.xumo_channel)
        self.unc_xumo_channels = self.uncompress(translations.xumo_channels)
        self.unc_xumo_program = self.uncompress(translations.xumo_program)

    def scheduler_tasks(self):
        sched_epg_hours = self.utc_to_local_time(0)
        sched_epg_mins = random.randint(1, 55)
        sched_epg = '{:0>2d}:{:0>2d}'.format(sched_epg_hours, sched_epg_mins)
        sched_ch_hours = self.utc_to_local_time(23)
        sched_ch_mins = random.randint(1, 55)
        sched_ch = '{:0>2d}:{:0>2d}'.format(sched_ch_hours, sched_ch_mins)
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
                'daily',
                timeofday=sched_epg
            )
