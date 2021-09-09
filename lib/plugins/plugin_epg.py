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
import logging

from lib.db.db_epg import DBepg


class PluginEPG:
    logger = None

    def __init__(self, _instance_obj):
        if PluginEPG.logger is None:
            PluginEPG.logger = logging.getLogger(__name__)
        self.instance_obj = _instance_obj
        self.instance_key = _instance_obj.instance_key
        self.plugin_obj = _instance_obj.plugin_obj
        self.db = DBepg(self.instance_obj.config_obj.data)
        self.config_section = self.instance_obj.config_section
        self.episode_adj = int(self.instance_obj.config_obj.data \
            [self.instance_obj.config_section]['epg-episode_adjustment'])


    def refresh_epg(self):
        if not self.is_refresh_expired():
            self.logger.debug('EPG still new for {} {}, not refreshing'.format(self.plugin_obj.name, self.instance_key))
            return
        if not self.instance_obj.config_obj.data[self.instance_obj.config_section]['epg-enabled']:
            self.logger.debug('EPG collection not enabled for {} {}'
                .format(self.plugin_obj.name, self.instance_key))
            return
        forced_dates, aging_dates = self.dates_to_pull()
        self.db.del_old_programs(self.plugin_obj.name, self.instance_key)
        for epg_day in forced_dates:
            self.refresh_programs(epg_day, False)
        for epg_day in aging_dates:
            self.refresh_programs(epg_day, True)

    def refresh_programs(self, _epg_day, use_cache=True):
        """
        dummy method to be overridden
        """
        pass

    def dates_to_pull(self):
        """
        Returns the days to pull, if EPG is less than a day, then
        override and return a simgle array value in force_days and an empty array in aging_days
        """
        todaydate = datetime.date.today()
        forced_days = []
        aging_days = []
        for x in range(0, self.instance_obj.config_obj.data[self.plugin_obj.name.lower()]['epg-days']):
            if x < self.config_obj.data[self.plugin_obj.name.lower()]['epg-days_start_refresh']:
                forced_days.append(todaydate + datetime.timedelta(days=x))
            else:
                aging_days.append(todaydate + datetime.timedelta(days=x))
        return forced_days, aging_days

    def is_refresh_expired(self):
        """
        Makes it so the minimum epg update rate
        can only occur based on epg_min_refresh_rate
        """
        todaydate = datetime.datetime.utcnow().date()
        last_update = self.db.get_last_update(self.plugin_obj.name, self.instance_key, todaydate)
        if not last_update:
            return True
        expired_date = datetime.datetime.now() - datetime.timedelta(
            seconds=self.instance_obj.config_obj.data[
                self.plugin_obj.name.lower()]['epg-min_refresh_rate'])
        if last_update < expired_date:
            return True
        return False
