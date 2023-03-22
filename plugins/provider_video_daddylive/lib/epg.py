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
import re

import lib.common.utils as utils
from lib.db.db_epg_programs import DBEpgPrograms
from lib.db.db_channels import DBChannels
from lib.plugins.plugin_epg import PluginEPG


class EPG(PluginEPG):

    def __init__(self, _instance_obj):
        super().__init__(_instance_obj)
        self.db_programs = DBEpgPrograms(self.config_obj.data)
        self.db_channels = DBChannels(self.config_obj.data)
        self.provider_channel_epg_dict = {}
        self.current_time = datetime.datetime.now(datetime.timezone.utc)
        self.midnight = self.current_time.replace(hour=0, minute=0, second=0, microsecond=0)
        self.last_day_to_refresh = self.config_obj.data[self.config_section]['epg-days'] - 1

    def dates_to_pull(self):
        """
        daddylive provides upto 3 days of EPG.  Each channel is different.
        return (forced date, aging dates)
        For now request all days to be forced
        """
        return list(range(0, self.config_obj.data[self.config_section]['epg-days'])), []

    def refresh_programs(self, _epg_day, use_cache=True):
        """
        if use_cache is true, then use cached data in the database for those days
        EPG plugin should detrmine how to use cache...
        """
        self.current_time = datetime.datetime.now(datetime.timezone.utc)
        self.midnight = self.current_time.replace(hour=0, minute=0, second=0, microsecond=0)
        start_time = self.midnight + datetime.timedelta(days=_epg_day)
        start_date = start_time.date()

        program_list = self.get_fullday_programs(_epg_day)
        if program_list:
            self.db.save_program_list(self.plugin_obj.name, self.instance_key, start_date, program_list)
            self.logger.debug('Refreshed EPG data for {}:{} day {}'
                              .format(self.plugin_obj.name, self.instance_key, start_date))
        program_list = None   # help with garbage collection

    def get_fullday_programs(self, _epg_day):
        """
        Returns a days (from midnight to midnight UTC) of programs for all channels
        enabled.  Also adds epg data for any channel with no epg data.
        """
        missing_ch_list = []
        program_list = []

        start_time = self.midnight + datetime.timedelta(days=_epg_day)
        start_seconds = int(start_time.timestamp())

        channel_list = self.db_channels.get_channels(self.plugin_obj.name, self.instance_key)

        for ch in channel_list.values():
            ch = ch[0]
            ch_id = ch['uid']
            epg_id = ch['json'].get('epg_id')
            if self.config_obj.data[self.plugin_obj.name.lower()]['epg-plugin'] == 'None':
                # make sure if the epg plugin is not set, then skip it
                epg_id = None
            if not ch['enabled']:
                # skip if channel is disabled
                continue
            if epg_id is None:
                # daddylive has no epg, so if epg_id is not listed, then 
                # add to missing list
                missing_ch_list.append(ch_id)
                continue

            # at this point, the epg points to a plugin to obtain the data
            ch_sched = self.plugin_obj.plugins[ch['json']['plugin']].plugin_obj \
                .get_channel_day_ext(epg_id[0], epg_id[1], start_seconds)
            if ch_sched is None:
                # Either no data for the days requested or an error from the provider
                missing_ch_list.append(ch_id)
                continue

            for prog in ch_sched:
                program_json = self.gen_program(ch, prog)
                if program_json is not None:
                    program_list.append(program_json)

        # if program_list for the day has data, also fill in for missing channels
        if program_list:
            for ch_id in missing_ch_list:
                ch_data = channel_list[ch_id][0]
                program_json = self.get_missing_program(ch_data,
                                                        ch_id, start_seconds)
                if program_json is not None:
                    program_list.extend(program_json)
        return program_list

    def get_missing_program(self, _ch_data, _ch_id, _start_seconds):
        """
        For a channel, will create a set of program events 1 hour apart
        for 24 hours based on the _start_seconds starting point. Most of the 
        event data are defaults.
        """
        if not _ch_data['enabled']:
            return None
        self.logger.debug('{}:{} Adding minimal EPG data for channel {}'
                          .format(self.plugin_obj.name, self.instance_key, _ch_id))
        event_list = []
        start_date = datetime.datetime.fromtimestamp(_start_seconds, datetime.timezone.utc)
        for incr_hr in range(0, 24):
            start_time = start_date + datetime.timedelta(hours=incr_hr)
            start_fmt = utils.tm_local_parse(start_time.timestamp() * 1000)
            end_time = start_time + datetime.timedelta(hours=1)
            end_fmt = utils.tm_local_parse(end_time.timestamp() * 1000)
            dur_min = 60
            event = {'channel': _ch_id, 'progid': None, 'start': start_fmt, 'stop': end_fmt,
                     'length': dur_min, 'title': _ch_data['display_name'], 'subtitle': None, 'entity_type': None,
                     'desc': 'Unavailable', 'short_desc': 'Unavailable',
                     'video_quality': None, 'cc': None, 'live': None, 'finale': None,
                     'premiere': None, 'air_date': None, 'formatted_date': None, 'icon': None,
                     'rating': None, 'is_new': None, 'genres': None,
                     'directors': None, 'actors': None,
                     'season': None, 'episode': None, 'se_common': None, 'se_xmltv_ns': None,
                     'se_progid': None
                     }
            event_list.append(event)
        return event_list

    def gen_program(self, _ch_data, _event_data):
        """
        Takes a single channel data with the program event and 
        returns a json program event object
        """
        if not _ch_data['enabled']:
            return None
        prog_id = _event_data['id']

        prog_details = self.plugin_obj.plugins[_ch_data['json']['plugin']].plugin_obj \
            .get_program_info_ext(prog_id)
        if len(prog_details) == 0:
            self.logger.notice('Program error: EPG program details missing {} {}'
                                .format(self.plugin_obj.name, prog_id))
            return None

        prog_details = json.loads(prog_details[0]['json'])

        start_time = utils.tm_local_parse(
            (_event_data['start']
             + self.config_obj.data[self.config_section]['epg-start_adjustment'])
            * 1000)
        end_time = utils.tm_local_parse(
            (_event_data['end']
             + self.config_obj.data[self.config_section]['epg-end_adjustment'])
            * 1000)
        dur_min = int((_event_data['end'] - _event_data['start']) / 60)

        if not prog_details['date']:
            if prog_details['year']:
                air_date = str(prog_details['year'])
                formatted_date = str(air_date)
            else:
                air_date = None
                formatted_date = None
        else:
            air_date_msec = int(prog_details['date'])
            air_date = utils.date_parse(air_date_msec, '%Y%m%d')
            formatted_date = utils.date_parse(air_date_msec, '%Y/%m/%d')

        title = prog_details['title']
        entity_type = prog_details['type']

        if prog_details['desc']:
            description = prog_details['desc']
        else:
            description = 'Unavailable'
        if prog_details['short_desc']:
            short_desc = prog_details['short_desc']
        else:
            short_desc = description

        if prog_details['episode']:
            episode = prog_details['episode'] + self.episode_adj
        else:
            episode = None
        season = prog_details['season']

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

        if prog_details['subtitle']:
            if season and episode:
                subtitle = 'S%02dE%02d ' % (season, episode)
            elif episode:
                subtitle = 'E%02d ' % episode
            else:
                subtitle = ''
            subtitle += prog_details['subtitle']
        else:
            subtitle = None

        rating = prog_details['rating']

        video_quality = None
        cc = False
        live = None
        is_new = None
        finale = None
        premiere = None

        icon = prog_details['image']

        if prog_details['genres'] is None:
            genres = None
        else:
            genres = prog_details['genres']

        directors = None
        actors = None

        json_result = {'channel': _ch_data['uid'], 'progid': prog_id, 'start': start_time, 'stop': end_time,
                       'length': dur_min, 'title': title, 'subtitle': subtitle, 'entity_type': entity_type,
                       'desc': description, 'short_desc': short_desc,
                       'video_quality': video_quality, 'cc': cc, 'live': live, 'finale': finale,
                       'premiere': premiere,
                       'air_date': air_date, 'formatted_date': formatted_date, 'icon': icon,
                       'rating': rating, 'is_new': is_new, 'genres': genres, 'directors': directors, 'actors': actors,
                       'season': season, 'episode': episode, 'se_common': se_common, 'se_xmltv_ns': se_xmltv_ns,
                       'se_progid': se_prog_id}
        return json_result

    def update_program_info(self, _prog_id):
        """
        Assumes the prog_id is not in the database, obtains the 
        data from online provider and place info into the epg programs database
        """
        uri = self.plugin_obj.unc_daddylive_prog_details.format(_prog_id)
        prog_details = self.get_uri_data(uri)

        prog_details = prog_details['data']['item']
        if prog_details['title'] is None:
            prog_details['title'] = prog_details['name']

        self.logger.debug('{}:{} Adding Program {} {} to db'
                          .format(self.plugin_obj.name, self.instance_key, _prog_id, prog_details['title']))

        if len(prog_details['images']) != 0:
            image_bucket = prog_details['images'][0]['bucketPath']
            image_url = self.plugin_obj.unc_daddylive_image + image_bucket
        else:
            image_url = None

        if len(prog_details['genres']) != 0:
            genres = prog_details['genres'][0]['name']
        else:
            genres = None
        if prog_details['episodeNumber'] == 0:
            episode = None
        else:
            episode = prog_details['episodeNumber']

        if prog_details['episodeAirDate'] is None:
            pass
        elif prog_details['episodeAirDate'].startswith('/Date'):
            m = re.search(r'Date\((\d*)\)', prog_details['episodeAirDate'])
            if m is None:
                prog_details['episodeAirDate'] = None
            else:
                prog_details['episodeAirDate'] = m.group(1)
        else:
            self.logger.warning('{}:{} Unknown format for episodeAirDate. Program:{}  Date:{}'
                                .format(self.plugin_obj.name, self.instance_key, _prog_id,
                                        prog_details['episodeAirDate']))

        program = {
            'title': prog_details['title'],
            'desc': prog_details['description'],
            'short_desc': prog_details['description'],
            'rating': prog_details['tvRating'],
            'year': prog_details['releaseYear'],
            'date': prog_details['episodeAirDate'],
            'type': prog_details['type'],
            'episode': episode,
            'season': prog_details['seasonNumber'],
            'subtitle': prog_details['episodeTitle'],
            'genres': genres,
            'image': image_url}

        self.db_programs.save_program(self.plugin_obj.name, _prog_id, program)
        return program
