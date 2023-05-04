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

import datetime
import json
import logging
import threading

import lib.common.utils as utils
from lib.db.db_epg import DBepg
from lib.common.decorators import handle_url_except
from lib.common.decorators import handle_json_except


class PluginEPG:

    def __init__(self, _instance_obj):
        self.logger = logging.getLogger(__name__)
        self.instance_obj = _instance_obj
        self.config_obj = self.instance_obj.config_obj
        self.instance_key = _instance_obj.instance_key
        self.plugin_obj = _instance_obj.plugin_obj
        self.db = DBepg(self.config_obj.data)
        self.config_section = self.instance_obj.config_section
        self.episode_adj = self.config_obj.data[self.instance_obj.config_section]\
            .get('epg-episode_adjustment')
        if self.episode_adj is None:
            self.episode_adj = 0
        else:
            self.episode_adj = int(self.episode_adj)

    def terminate(self):
        """
        Removes all has a object from the object and calls any subclasses to also terminate
        Not calling inherited class at this time
        """
        self.logger = None
        self.instance_obj = None
        self.config_obj = None
        self.instance_key = None
        self.plugin_obj = None
        self.db = None
        self.config_section = None
        self.episode_adj = None

    @handle_url_except(timeout=10.0)
    @handle_json_except
    def get_uri_data(self, _uri, _header=None):
        if _header is None:
            header = {'User-agent': utils.DEFAULT_USER_AGENT}
        else:
            header = _header
        resp = self.plugin_obj.http_session.get(_uri, headers=header, timeout=(4, 8))
        x = resp.json()
        resp.raise_for_status()
        return x

    def refresh_epg(self):
        if not self.is_refresh_expired():
            self.logger.debug('EPG still new for {} {}, not refreshing'.format(self.plugin_obj.name, self.instance_key))
            return False
        if not self.config_obj.data[self.instance_obj.config_section]['epg-enabled']:
            self.logger.info('EPG Collection not enabled for {} {}'
                             .format(self.plugin_obj.name, self.instance_key))
            return False
        forced_dates, aging_dates = self.dates_to_pull()
        self.db.del_old_programs(self.plugin_obj.name, self.instance_key)

        for epg_day in forced_dates:
            self.refresh_programs(epg_day, False)
        for epg_day in aging_dates:
            self.refresh_programs(epg_day, True)
        self.logger.info('{}:{} EPG update completed'.format(self.plugin_obj.name, self.instance_key))
        return True

    def refresh_programs(self, _epg_day, use_cache=True):
        """
        dummy method to be overridden
        """
        pass

    def get_channel_days(self, _zone, _uid, _days):
        """
        For a channel (uid) in a zone (like a zipcode), return
        a dict listed by day with all programs listed for that day within it.
        This interface is for the epg plugins
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
        for x in range(0, self.config_obj.data[self.plugin_obj.name.lower()]['epg-days']):
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
            seconds=self.config_obj.data[
                self.instance_obj.config_section]['epg-min_refresh_rate'])
        if last_update < expired_date:
            return True
        return False

    def check_logger_refresh(self):
        if not self.logger.isEnabledFor(40):
            self.logger = logging.getLogger(__name__ + str(threading.get_ident()))
