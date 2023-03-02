# pylama:ignore=E722
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
import pathlib
import re

import lib.common.exceptions as exceptions
import lib.common.utils as utils
from lib.common.xmltv import XMLTV
from lib.plugins.plugin_epg import PluginEPG
from lib.db.db_channels import DBChannels
from lib.db.db_scheduler import DBScheduler


class EPG(PluginEPG):

    def __init__(self, _instance_obj):
        super().__init__(_instance_obj)
        self.url_chars = re.compile(r'[^-._~0-9a-zA-z]')

    def dates_to_pull(self):
        """
        Since epg is a single file, will have to parce through the data and split it into days.
        """
        return [1], []

    def refresh_programs(self, _epg_day, use_cache=True):

        ch_db = DBChannels(self.config_obj.data)
        if self.config_obj.data[self.config_section]['epg-xmltv_file'] is None:
            raise exceptions.CabernetException(
                '{}:{} XMLTV File config not set, unable to get epg list'
                .format(self.plugin_obj.name, self.instance_key))
        url = self.config_obj.data[self.config_section]['epg-xmltv_file']
        file_type = self.detect_filetype(url)
        xmltv = XMLTV(self.config_obj.data, url, file_type)
        start_date = datetime.datetime.utcnow().date()
        while True:
            xmltv.set_date(start_date)
            iterator = iter(xmltv)
            program_list = []
            epg_ch_list = {}
            while True:
                prog_one = next(iterator)
                if prog_one is None:
                    break
                program_list.append(prog_one)
                ch_id = re.sub(self.url_chars, '_', prog_one['channel'])
                epg_ch_list[ch_id] = None
            ch_list = ch_db.get_channels(self.plugin_obj.name, self.instance_key)
            for ch in ch_list.keys():
                if not ch_list[ch][0]['enabled']:
                    continue
                if ch in epg_ch_list:
                    continue
                self.logger.debug(
                    '{}:{} Channel {} missing program data, adding default for day {}'
                    .format(self.plugin_obj.name, self.instance_key, ch, start_date))
                # fill in default program data
                start_hour = datetime.datetime.utcnow().hour - 2
                if start_hour < 0:
                    start_hour = 0
                dt_start_day = datetime.datetime.combine(start_date, datetime.time())
                for hr in range(start_hour, 24):
                    dt_start_time = dt_start_day.replace(
                        tzinfo=datetime.timezone.utc, hour=hr, minute=0, second=0, microsecond=0)
                    start = round(dt_start_time.timestamp())
                    end = round(dt_start_time.timestamp() + 3600)
                    ch_data = ch_list[str(ch)][0]
                    if ch_data['json']['groups_other'] is None:
                        genres = None
                    else:
                        genres = [ch_data['json']['groups_other']]
                    prog_one = self.get_blank_program(start, end,
                                                      ch_data['uid'], ch_data['display_name'], genres)
                    program_list.append(prog_one)
            if len(program_list) == 0:
                if xmltv.has_future_dates:
                    start_date += datetime.timedelta(days=1)
                    continue
                else:
                    break
            self.db.save_program_list(self.plugin_obj.name,
                                      self.instance_key, start_date, program_list)
            self.logger.debug('Refreshed EPG data for {}:{} day {}'
                              .format(self.plugin_obj.name, self.instance_key, start_date))
            if xmltv.has_future_dates:
                start_date += datetime.timedelta(days=1)
            else:
                break
        sched_db = DBScheduler(self.config_obj.data)
        active = sched_db.get_num_active()
        if active < 2:
            xmltv.cleanup_tmp_folder()
        self.logger.debug('Refreshed EPG Completed for {}:{}'
                          .format(self.plugin_obj.name, self.instance_key))

    def get_blank_program(self, _start, _end, _ch_id, _ch_title, _groups):
        start_time = utils.tm_local_parse(
            (_start
             + self.config_obj.data[self.config_section]['epg-start_adjustment'])
            * 1000)
        end_time = utils.tm_local_parse(
            (_end
             + self.config_obj.data[self.config_section]['epg-start_adjustment'])
            * 1000)
        dur_min = int((_end - _start) / 60)
        sid = str(_ch_id)
        title = _ch_title
        json_result = {'channel': sid, 'progid': None, 'start': start_time, 'stop': end_time,
                       'length': dur_min, 'title': title, 'subtitle': None, 'entity_type': None,
                       'desc': 'Not Available', 'short_desc': 'Not Available',
                       'video_quality': None, 'cc': None, 'live': None, 'finale': None,
                       'premiere': None,
                       'air_date': None, 'formatted_date': None, 'icon': None,
                       'rating': None, 'is_new': False, 'genres': _groups, 'directors': None, 'actors': None,
                       'season': None, 'episode': None, 'se_common': None, 'se_xmltv_ns': None,
                       'se_progid': None}
        return json_result

    def detect_filetype(self, _filename):
        file_type = self.config_obj.data[self.config_section]['epg-xmltv_file_type']
        if file_type == 'autodetect':
            extension = pathlib.Path(_filename).suffix
            if extension == '.gz':
                file_type = '.gz'
            elif extension == '.zip':
                file_type = '.zip'
            elif extension == '.xml':
                file_type = '.xml'
            else:
                raise exceptions.CabernetException(
                    '{}:{} XMLTV File unknown File Type.  Set the XMLTV File Type in config.'
                    .format(self.plugin_obj.name, self.instance_key))
        elif file_type == 'gzip':
            file_type = '.gz'
        elif file_type == 'zip':
            file_type = '.zip'
        elif file_type == 'xml':
            file_type = '.xml'
        else:
            raise exceptions.CabernetException(
                '{}:{} XMLTV File unknown File Type in config.'
                .format(self.plugin_obj.name, self.instance_key))
        return file_type
