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

from .channels import Channels
from .epg import EPG
from lib.plugins.plugin_instance_obj import PluginInstanceObj


class M3UGenericInstance(PluginInstanceObj):

    def __init__(self, _plugin, _instance):
        super().__init__(_plugin, _instance)
        self.config_obj = _plugin.config_obj
        if not self.config_obj.data[_plugin.name.lower()]['enabled']:
            return
        if not self.config_obj.data[self.config_section]['enabled']:
            return

        self.channels = Channels(self)
        self.epg = EPG(self)

    def scheduler_tasks(self):
        sched_ch_hours = random.randint(4, 6)
        sched_ch_mins = random.randint(1, 55)
        sched_ch = '{:0>2d}:{:0>2d}'.format(sched_ch_hours, sched_ch_mins)
        label = self.config_obj.data[self.config_section]['label']
        if self.scheduler_db.save_task(
                'Channels',
                'Refresh {} Channels'.format(label),
                self.plugin_obj.name,
                self.instance_key,
                'refresh_channels',
                20,
                'inline',
                'Pulls channel lineup from M3U'
        ):
            self.scheduler_db.save_trigger(
                'Channels',
                'Refresh {} Channels'.format(label),
                'startup')
            self.scheduler_db.save_trigger(
                'Channels',
                'Refresh {} Channels'.format(label),
                'daily',
                timeofday=sched_ch
            )
        if self.scheduler_db.save_task(
                'EPG',
                'Refresh {} EPG'.format(label),
                self.plugin_obj.name,
                self.instance_key,
                'refresh_epg',
                10,
                'thread',
                'Add triggers to the EPG Refresh based on when the m3u is updated online.'
        ):
            self.scheduler_db.save_trigger(
                'EPG',
                'Refresh {} EPG'.format(label),
                'startup')
