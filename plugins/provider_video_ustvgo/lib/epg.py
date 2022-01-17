# pylama:ignore=E722
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
import json
import time
import urllib.request

import lib.common.exceptions as exceptions
import lib.common.utils as utils
from lib.common.decorators import handle_url_except
from lib.common.decorators import handle_json_except
from lib.db.db_epg_programs import DBEpgPrograms
from lib.db.db_channels import DBChannels
from lib.plugins.plugin_epg import PluginEPG

from .translations import ustvgo_genres


class EPG(PluginEPG):

    def __init__(self, _instance_obj):
        super().__init__(_instance_obj)
        self.db_programs = DBEpgPrograms(self.config_obj.data)
        self.first_day = True

    def dates_to_pull(self):
        """
        Since epg is less than one day, return a forced day item with no
        aging items        
        """
        return [1], []

    def refresh_programs(self, _epg_day, use_cache=True):
        self.first_day = True
        ch_db = DBChannels(self.config_obj.data)
        ch_list = ch_db.get_channels(self.plugin_obj.name, self.instance_key)

        prog_json = self.get_uri_data_ustvgo(self.plugin_obj.unc_ustvgo_channels)
        
        epg_date = datetime.datetime.utcnow().date()
        date_list = []
        while True:
            program_list = self.get_day_programs(prog_json, epg_date, ch_list)
            if len(program_list) == 0:
                break
            date_list.append(epg_date)
            self.db.save_program_list(self.plugin_obj.name, self.instance_key, epg_date, program_list)
            self.logger.debug('Refreshed EPG data for {}:{} day {}'
                .format(self.plugin_obj.name, self.instance_key, epg_date))
            epg_date += datetime.timedelta(days=1)

        self.logger.debug('Starting Program Details Update {}:{}'
            .format(self.plugin_obj.name, self.instance_key))
        program_list = None
        prog_json = None
        ch_list = None
        for date in date_list:
            one_day_epg_json = self.db.get_epg_one(self.plugin_obj.name, self.instance_key, date)
            if len(one_day_epg_json) == 0:
                continue
            one_day_epg = json.loads(one_day_epg_json[0]['json'])
            for prog in one_day_epg:
                self.update_program_info(prog)
            self.db.save_program_list(self.plugin_obj.name, self.instance_key, one_day_epg_json[0]['day'], one_day_epg)

    def get_day_programs(self, _prog_json, _epg_date, _ch_list):
        epg_datetime = datetime.datetime.combine(_epg_date, datetime.time.min)
        prev_midnight = int(epg_datetime.timestamp() // 86400 * 86400)
        next_midnight = int((epg_datetime.timestamp() // 86400)+1) * 86400
        prog_list = []
        # process all the channels listed on the website with EPG data
        ch_ids_processed = []
        for ch_dict in _prog_json:
            ch_id = str(ch_dict['channel']['sourceId'])
            ch_ids_processed.append(ch_id)
            if ch_id not in _ch_list.keys():
                continue
            if not _ch_list[ch_id][0]['enabled']:
                continue
            for prog in ch_dict['programSchedules']:
                start_seconds = prog['startTime']
                if not prev_midnight <= start_seconds < next_midnight:
                    continue
                start_time = utils.tm_local_parse((prog['startTime']
                    + self.config_obj.data[self.config_section]['epg-start_adjustment']) 
                    * 1000)
                end_time = utils.tm_local_parse((prog['endTime']
                    + self.config_obj.data[self.config_section]['epg-end_adjustment']) 
                    * 1000)
                dur_min = dur_min = int((prog['startTime'] - prog['endTime']) / 60)
                prog_list.append(
                    {'channel': ch_id, 'progid': prog['programId'], 'start': start_time, 'stop': end_time,
                    'length': dur_min, 'title': prog['title'], 'subtitle': None, 'entity_type': None,
                    'desc': 'Unavailable', 'short_desc': 'Unavailable',
                    'video_quality': None, 'cc': None, 'live': None, 'finale': None,
                    'premiere': None, 'air_date': None, 'formatted_date': None, 'icon': None,
                    'rating': prog['rating'], 'is_new': None, 'genres': None, 
                    'directors': None, 'actors': None,
                    'season': None, 'episode': None, 'se_common': None, 'se_xmltv_ns': None,
                    'se_progid': None,
                    'details': prog['programDetails']
                    })

        # process the channels not listed with EPG data
        extra_prog = self.process_missing_channels(ch_ids_processed, _ch_list)
        prog_list = [ *prog_list, *extra_prog ]
        return prog_list


    def process_missing_channels(self, _ch_ids_processed, _ch_list):
        if not self.first_day:
            return []
        self.first_day = False
        prog_list = []
        for ch_id in _ch_list.keys():
            if ch_id in _ch_ids_processed:
                continue
            if not _ch_list[ch_id][0]['enabled']:
                continue

            prog_json = self.get_uri_data_ustvgo(self.plugin_obj.unc_ustvgo_epg % (ch_id, ''))
            if prog_json is None:
                continue
            prog_json = prog_json['items'][list(prog_json['items'].keys())[0]]
            self.logger.debug('USTVGO: Adding minimal EPG data for channel {}'.format(ch_id))
            for prog in prog_json:
                start_time = utils.tm_local_parse((prog['start_timestamp']
                    + self.config_obj.data[self.config_section]['epg-start_adjustment']) 
                    * 1000)
                end_time = utils.tm_local_parse((prog['end_timestamp']
                    + self.config_obj.data[self.config_section]['epg-end_adjustment']) 
                    * 1000)
                dur_min = dur_min = int((prog['start_timestamp'] - prog['end_timestamp']) / 60)
                prog_list.append(
                    {'channel': ch_id, 'progid': prog['id'], 'start': start_time, 'stop': end_time,
                    'length': dur_min, 'title': prog['name'], 'subtitle': None, 'entity_type': None,
                    'desc': 'Unavailable', 'short_desc': 'Unavailable',
                    'video_quality': None, 'cc': None, 'live': None, 'finale': None,
                    'premiere': None, 'air_date': None, 'formatted_date': None, 'icon': None,
                    'rating': None, 'is_new': None, 'genres': None, 
                    'directors': None, 'actors': None,
                    'season': None, 'episode': None, 'se_common': None, 'se_xmltv_ns': None,
                    'se_progid': None,
                    'details': self.plugin_obj.unc_ustvgo_program % (prog['id'])
                    })
            
        return prog_list



    def update_program_info(self, _prog):
        if 'details' not in _prog:
            return
        prog_details = self.get_program_details(_prog)
        if prog_details is None:
            return
        if prog_details['desc'] is not None:
            _prog['desc'] = prog_details['desc']
            _prog['short_desc'] = prog_details['desc']
        _prog['air_date'] = prog_details['date']
        episode = prog_details['episode']
        _prog['episode'] = episode
        season = prog_details['season']
        _prog['season'] = season

        genres = prog_details['genres']
        if genres is not None:
            if genres in ustvgo_genres:
                genres = ustvgo_genres[genres]
            else:
                self.logger.info('Missing USTVGO genre translation for: {}' \
                        .format(genres))
                genres = [x.strip() for x in genres.split(' & ')]
        _prog['genres'] = genres

        if (season is None) and (episode is None):
            se_common = None
            se_xmltv_ns = None
            se_prog_id = None
        elif (season is not None) and (episode is not None):
            se_common = 'S%02dE%02d' % (season, episode)
            se_xmltv_ns = ''.join([str(season - 1), '.', str(episode - 1), '.0/1'])
            se_prog_id = None
        elif (season is None) and (episode is not None):
            se_common = None
            se_xmltv_ns = None
            se_prog_id = None
        else:  # (season is not None) and (episode is None):
            se_common = 'S%02dE%02d' % (season, 0)
            se_xmltv_ns = ''.join([str(season - 1), '.', '0', '.0/1'])
            se_prog_id = None
        _prog['se_common'] = se_common
        _prog['se_xmltv_ns'] = se_xmltv_ns
        _prog['se_progid'] = se_prog_id

        if season is not None:
            subtitle = 'S%02dE%02d ' % (season, episode)
        elif episode is not None:
            subtitle = 'E%02d ' % (episode)
        else:
            subtitle = ''
        if prog_details['subtitle'] is not None:
            _prog['subtitle'] = subtitle + prog_details['subtitle']
        del _prog['details']

    def get_program_details(self, _prog):
    
        prog_details = self.db_programs.get_program(self.plugin_obj.name, _prog['progid'])
        if len(prog_details) != 0:
            return json.loads(prog_details[0]['json'])

        prog_details = self.get_uri_data_ustvgo(_prog['details'])
        if prog_details is None:
            return None

        self.logger.debug('{}:{} Processing Program {} from USTVGO' \
            .format(self.plugin_obj.name, self.instance_key, _prog['progid']))
        prog_details = prog_details['data']['item']

        if len(prog_details['genres']) != 0:
            genres = prog_details['genres'][0]['name']
        else:
            genres = None
        if prog_details['episodeNumber'] == 0:
            episode = None
        else:
            episode = prog_details['episodeNumber']

        program = { 'title': prog_details['title'], 
            'desc': prog_details['description'],
            'date': str(prog_details['releaseYear']),
            'episode': episode,
            'season': prog_details['seasonNumber'],
            'subtitle': prog_details['episodeTitle'],
            'genres': genres }

        self.db_programs.save_program(self.plugin_obj.name, _prog['progid'], program)
        return program

    def get_uri_data_ustvgo(self, _uri):
        header = {
            'User-agent': utils.DEFAULT_USER_AGENT,
            'Referer': 'https://ustvgo.tv/'
        }
        return self.get_uri_data(_uri, _header=header)
