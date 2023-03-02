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
import json
import time

import lib.common.utils as utils
from lib.db.db_epg_programs import DBEpgPrograms
from lib.db.db_channels import DBChannels
from lib.plugins.plugin_epg import PluginEPG

from .translations import xumo_tv_genres


class EPG(PluginEPG):

    def __init__(self, _instance_obj):
        super().__init__(_instance_obj)
        self.db_programs = DBEpgPrograms(self.config_obj.data)

    def dates_to_pull(self):
        """
        Since epg is less than one day, return a forced day item with no
        aging items        
        """
        return [1], []

    def refresh_programs(self, _epg_day, use_cache=True):
        timeslot_list = {}
        program_list = []
        todaydate = datetime.datetime.utcnow().date()
        if use_cache:
            program_list = self.db.get_epg_one(self.plugin_obj.name, self.instance_key, todaydate)
            if len(program_list) != 0:
                program_list = json.loads(program_list[0]['json'])
                for program in program_list:
                    ts = (program['channel'], program['start'])
                    if ts not in timeslot_list.keys():
                        timeslot_list[ts] = program
        program_list = self.get_fullday_programs(program_list, timeslot_list)
        self.db.save_program_list(self.plugin_obj.name, self.instance_key, todaydate, program_list)
        self.logger.debug('Refreshed EPG data for {}:{} day {}'
                          .format(self.plugin_obj.name, self.instance_key, todaydate))

    def get_fullday_programs(self, _program_list, _timeslot_list):
        """
        Returns a days (from midnight to midnight UTC) of programs
        """
        ch_db = DBChannels(self.config_obj.data)
        ch_list = ch_db.get_channels(self.plugin_obj.name, self.instance_key)
        prog_list = {}
        prog_ids = {}
        time_sec_now = time.time()
        start_hour = datetime.datetime.utcnow().hour - 2
        if start_hour < 0:
            start_hour = 0
        self.logger.info(
            '{}:{} Processing {} EPG Channels from hour {}:00 to hour 23:00 UTC'
            .format(self.plugin_obj.name, self.instance_key, len(ch_list.keys()), start_hour))
        for ch in ch_list.keys():
            if not ch_list[ch][0]['enabled']:
                continue
            self.logger.debug(
                '{}:{} Processing EPG Channel {} '
                .format(self.plugin_obj.name, self.instance_key, ch, ch_list[ch][0]['display_name']))
            for hr in range(start_hour, 24):
                url = ''.join([self.plugin_obj.unc_xumo_base,
                               self.plugin_obj.unc_xumo_channel
                              .format(ch, hr)])
                listing = self.get_uri_data(url)
                if listing is None:
                    continue
                for prog in listing['assets']:
                    start_time = utils.tm_local_parse(prog['timestamps']['start'] * 1000)
                    key = (ch, start_time)
                    if 'live' not in prog:
                        prog['live'] = False
                    if key not in prog_list.keys():
                        prog_list[key] = {
                            'id': prog['id'],
                            'channelId': ch,
                            'start': prog['timestamps']['start'],
                            'end': prog['timestamps']['end'],
                            'is_live': prog['live']}
                        prog_ids[prog['id']] = None

        self.logger.info(
            '{}:{} Processing {} Programs'
            .format(self.plugin_obj.name, self.instance_key, len(prog_list.keys())))
        for prog in prog_ids.keys():
            program = self.db_programs.get_program(self.plugin_obj.name, prog)
            if len(program) == 0:
                self.update_program_info(prog)
            # else:
            #    self.logger.debug('{}:{} Processing Program {} from cache' \
            #        .format(self.plugin_obj.name, self.instance_key, prog))
        program = None  # helps with garbage collection

        self.logger.debug(
            '{}:{} Finalizing EPG updates'
            .format(self.plugin_obj.name, self.instance_key))
        for key, listing_data in prog_list.items():
            if time_sec_now - listing_data['start'] > 86400:
                for hr in range(start_hour, 24):
                    dt_start_day = datetime.datetime.utcnow()
                    dt_start_time = dt_start_day.replace(tzinfo=datetime.timezone.utc, hour=hr, minute=0, second=0,
                                                         microsecond=0)
                    listing_data['start'] = round(dt_start_time.timestamp())
                    listing_data['end'] = round(dt_start_time.timestamp() + 3600)
                    try:
                        ch_data = ch_list[str(listing_data['channelId'])][0]
                        key_ts = (listing_data['channelId'], utils.tm_local_parse(listing_data['start'] * 1000))
                        if key_ts in _timeslot_list:
                            program_json = self.get_program(ch_data,
                                                            listing_data, _timeslot_list[key_ts])
                        else:
                            program_json = self.get_program(ch_data,
                                                            listing_data, None)
                        if program_json is not None:
                            _program_list.append(program_json)
                    except KeyError as e:
                        self.logger.info('1 Missing Channel: {} {}'.format(str(listing_data['channelId']), e))
                        continue
                self.logger.debug(
                    'Channel has no programs, adding default programming for {}'
                    .format(listing_data['channelId']))
                continue
            try:
                ch_data = ch_list[str(listing_data['channelId'])][0]
                key_ts = (listing_data['channelId'], utils.tm_local_parse(listing_data['start'] * 1000))
                if key_ts in _timeslot_list:
                    program_json = self.get_program(ch_data,
                                                    listing_data, _timeslot_list[key_ts])
                else:
                    program_json = self.get_program(ch_data,
                                                    listing_data, None)
            except KeyError as e:
                self.logger.info('2 Missing Channel: {} {}'.format(str(listing_data['channelId']), e))
                continue
            if program_json is not None:
                _program_list.append(program_json)
        return _program_list

    def get_program_uri(self, _listing):
        uri = None
        if 'providers' in _listing:
            for provider in _listing['providers']:
                for source in provider['sources']:
                    uri = source['uri']
        return uri

    def get_program(self, _ch_data, _program_data, _timeslot_list):
        if not _ch_data['enabled']:
            return None
        prog_id = _program_data['id']
        key = (_ch_data['uid'], _program_data['start'])

        if _timeslot_list is not None and key in _timeslot_list:
            return None

        prog_details = self.db_programs.get_program(self.plugin_obj.name, prog_id)
        if len(prog_details) == 0:
            self.logger.warning(
                'Program error: EPG program details missing {} {}'
                .format(self.plugin_obj.name, prog_id))
            return None

        prog_details = json.loads(prog_details[0]['json'])

        start_time = utils.tm_local_parse(
            (_program_data['start']
             + self.config_obj.data[self.config_section]['epg-start_adjustment'])
            * 1000)
        end_time = utils.tm_local_parse(
            (_program_data['end']
             + self.config_obj.data[self.config_section]['epg-start_adjustment'])
            * 1000)
        dur_min = int((_program_data['end'] - _program_data['start']) / 60)
        sid = str(_program_data['channelId'])
        title = prog_details['title']
        entity_type = None

        if 'description' not in prog_details.keys():
            description = 'Unavailable'
        else:
            description = prog_details['description']
        short_desc = description
        video_quality = None
        cc = False
        live = _program_data['is_live']
        is_new = _program_data['is_live']
        finale = False
        premiere = False
        air_date = None
        formatted_date = None
        rating = None

        icon = self.plugin_obj.unc_xumo_icons \
            .format(sid)

        if _ch_data['json']['groups_other'] is None:
            genres = None
        elif _ch_data['json']['groups_other'] in xumo_tv_genres:
            genres = xumo_tv_genres[_ch_data['json']['groups_other']]
        else:
            self.logger.info(
                'Missing XUMO genre translation for: {}'
                .format(_ch_data['json']['groups_other']))
            genres = [_ch_data['json']['groups_other']]

        directors = None
        actors = None
        season = None
        episode = None
        se_common = None
        se_xmltv_ns = None
        se_prog_id = None
        subtitle = None

        json_result = {'channel': sid, 'progid': prog_id, 'start': start_time, 'stop': end_time,
                       'length': dur_min, 'title': title, 'subtitle': subtitle, 'entity_type': entity_type,
                       'desc': description, 'short_desc': short_desc,
                       'video_quality': video_quality, 'cc': cc, 'live': live, 'finale': finale,
                       'premiere': premiere,
                       'air_date': air_date, 'formatted_date': formatted_date, 'icon': icon,
                       'rating': rating, 'is_new': is_new, 'genres': genres, 'directors': directors, 'actors': actors,
                       'season': season, 'episode': episode, 'se_common': se_common, 'se_xmltv_ns': se_xmltv_ns,
                       'se_progid': se_prog_id}
        return json_result

    def update_program_info(self, _prog):
        self.logger.debug(
            '{}:{} Processing Program {} from XUMO'
            .format(self.plugin_obj.name, self.instance_key, _prog))
        program = {}
        url = ''.join([self.plugin_obj.unc_xumo_base,
                       self.plugin_obj.unc_xumo_program
                      .format(_prog)])
        listing = self.get_uri_data(url)
        if listing is None:
            return program
        program['title'] = listing['title']
        if 'descriptions' in listing:
            if 'large' in listing['descriptions'].keys():
                key = 'large'
            elif 'medium' in listing['descriptions'].keys():
                key = 'medium'
            elif 'small' in listing['descriptions'].keys():
                key = 'small'
            else:
                key = list(listing['descriptions'].keys())[0]
            program['description'] = listing['descriptions'][key]
        program['stream_url'] = None
        for source in listing['providers'][0]['sources']:
            if 'drm' not in source:
                if source['produces'] == 'application/x-mpegURL':
                    program['stream_url'] = source['uri']
                    break
                elif source['produces'] == 'application/x-mpegURL;type=tv':
                    program['stream_url'] = source['uri']
        if program['stream_url'] is None:
            self.logger.info('No stream available for program {}'.format(_prog))
        self.db_programs.save_program(self.plugin_obj.name, _prog, program)
        return program
