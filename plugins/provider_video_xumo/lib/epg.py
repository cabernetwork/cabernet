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
        
        days_to_pull = int(self.config_obj.data[self.instance_obj.config_section]['epg-days'])            
        forced_days = []
        aging_days = []
        for x in range(0, days_to_pull):
            if x < 2:
                forced_days.append(x)
            else:
                aging_days.append(x)
        return forced_days, aging_days

    def refresh_programs(self, _epg_day, use_cache=True):
        timeslot_list = {}
        program_list = []
        todaydate = datetime.datetime.utcnow().date()
        date_to_process = todaydate + datetime.timedelta(days=_epg_day)
        
        if use_cache:
            program_list = self.db.get_epg_one(self.plugin_obj.name, self.instance_key, date_to_process)
            if len(program_list) != 0:
                self.logger.debug('{}:{} Reusing EPG database data for date {}'.format(
                    self.plugin_obj.name, self.instance_key, date_to_process))
                return


        program_list = self.get_fullday_programs(date_to_process)
        self.db.save_program_list(self.plugin_obj.name, self.instance_key, date_to_process, program_list)
        self.logger.debug('Refreshed EPG data for {}:{} day {}'
                          .format(self.plugin_obj.name, self.instance_key, date_to_process))

    
    def get_fullday_programs(self, _date_to_process):
        """
        Returns a days (from midnight to midnight UTC) of programs
        """
        ch_db = DBChannels(self.config_obj.data)
        ch_list = ch_db.get_channels(self.plugin_obj.name, self.instance_key)
        prog_list = {}
        prog_ids = {}
        program_list = []

        day_part_url = ''.join([
            self.plugin_obj.unc_xumo_base,
            self.plugin_obj.unc_xumo_epg
            ])
        
        for offset in range(0, 301, 50):
            for i in range(0,4):
                url = day_part_url.format(
                    self.plugin_obj.geo.channelListId,
                    datetime.datetime.strftime(_date_to_process, '%Y%m%d'),
                    i, offset
                    )
                listing = self.get_uri_data(url)
                for ch in listing['channels']:
                    chid = ch['channelId']
                    if str(chid) not in ch_list.keys():
                        self.logger.info('New Channel {} not in current list during EPG generation {}, ignoring'.format(chid, ch_list.keys()))
                        continue
                    if not ch_list[str(chid)][0]['enabled']:
                        continue

                    if chid in prog_list.keys():
                        ch_data = prog_list[chid]
                    else:
                        ch_data = []
                    chno = ch['number']
                    ch_prog_list = []
                    for prog in ch['schedule']:
                        start = prog['start']
                        end = prog['end']
                        dt = datetime.datetime.strptime(start, '%Y-%m-%dT%H:%M:%S%z')
                        start_sec = int(dt.timestamp())
                        dt = datetime.datetime.strptime(end, '%Y-%m-%dT%H:%M:%S%z')
                        end_sec = int(dt.timestamp())
                        prog_id = prog['assetId']
                        prog_ids[prog_id] = None
                        ch_prog_list.append({
                            'prog_id': prog_id,
                            'start': start,
                            'end': end,
                            'start_sec': start_sec,
                            'end_sec': end_sec
                            })
                    if chid in prog_list.keys():
                        prog_list[chid].extend(ch_prog_list)
                    else:
                        prog_list[chid] = ch_prog_list


        self.logger.info(
            '{}:{} Processing {} EPG Channels for day {}'
            .format(self.plugin_obj.name, self.instance_key, len(ch_list.keys()), _date_to_process))
        for ch in ch_list.keys():
            if not ch_list[ch][0]['enabled']:
                continue

        program_count = self.sublist_len(prog_list)
        self.logger.info(
            '{}:{} Processing {} Programs {}'
            .format(self.plugin_obj.name, self.instance_key, program_count, _date_to_process))

        for prog in prog_ids.keys():
            program = self.db_programs.get_program(self.plugin_obj.name, prog)
            if len(program) == 0:
                self.update_program_info(prog)

        program = None  # helps with garbage collection


        self.logger.debug(
            '{}:{} Finalizing EPG updates {}'
            .format(self.plugin_obj.name, self.instance_key, _date_to_process))


        for chid, listing_data in prog_list.items():
            ch_data = ch_list[str(chid)][0]
            for prog in listing_data:
                program_json = self.get_program(
                    ch_data,
                    prog)
                if program_json is not None:
                    program_list.append(program_json)
        return program_list
        
    def get_program_uri(self, _listing):
        uri = None
        if 'providers' in _listing:
            for provider in _listing['providers']:
                for source in provider['sources']:
                    uri = source['uri']
        return uri

    def get_program(self, _ch_data, _program_data):
        if not _ch_data['enabled']:
            return None
        prog_id = _program_data['prog_id']

        prog_details = self.db_programs.get_program(self.plugin_obj.name, prog_id)
        if len(prog_details) == 0:
            self.logger.warning(
                'EPG program details missing {} {}'
                .format(self.plugin_obj.name, prog_id))
            return None

        prog_details = json.loads(prog_details[0]['json'])

        start_time = utils.tm_local_parse(
            (_program_data['start_sec']
             + self.config_obj.data[self.config_section]['epg-start_adjustment'])
            * 1000)
        end_time = utils.tm_local_parse(
            (_program_data['end_sec']
             + self.config_obj.data[self.config_section]['epg-start_adjustment'])
            * 1000)
        dur_min = int((_program_data['end_sec'] - _program_data['start_sec']) / 60)
        sid = str(_ch_data['uid'])
        title = prog_details['title']
        entity_type = None

        if 'description' not in prog_details.keys():
            description = 'Unavailable'
        else:
            description = prog_details['description']
        short_desc = description
        video_quality = None
        cc = False
        live = None
        is_new = None
        finale = False
        premiere = False
        air_date = None
        formatted_date = None
        rating = None

        icon = self.plugin_obj.unc_xumo_icons \
            .format(sid)
        if prog_details.get('genres'):
            if prog_details['genres'][0] in xumo_tv_genres:
                genres = xumo_tv_genres[prog_details['genres'][0]]
            else:
                self.logger.info(
                    '1 Missing XUMO genre translation for: {}'
                    .format(prog_details['genres'][0]))
                genres = prog_details['genres']                
        else:
            if _ch_data['json']['groups_other'] is None:
                genres = None
            elif _ch_data['json']['groups_other'] in xumo_tv_genres:
                genres = xumo_tv_genres[_ch_data['json']['groups_other']]
            else:
                self.logger.info(
                    '2 Missing XUMO genre translation for: {}'
                    .format(_ch_data['json']['groups_other']))
                genres = [_ch_data['json']['groups_other']]

        season = prog_details.get('season')
        episode = prog_details.get('episode')
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

        if season is not None and episode is not None:
            subtitle = 'S%02dE%02d ' % (season, episode)
        elif episode is not None:
            subtitle = 'E%02d ' % episode
        else:
            subtitle = ''
        if prog_details.get('subtitle'):
            subtitle += prog_details['subtitle']
        else:
            subtitle = None

        directors = None
        actors = None

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
            '{}:{} Processing New Program {} from XUMO'
            .format(self.plugin_obj.name, self.instance_key, _prog))
        program = {}

        url = ''.join([self.plugin_obj.unc_xumo_base,
                       self.plugin_obj.unc_xumo_program
                      .format(_prog)])
        listing = self.get_uri_data(url)
        if listing is None:
            return program
        program['title'] = listing['title']
        if 'episodeTitle' in listing:
            program['subtitle'] = listing['episodeTitle']
        else:
            program['subtitle'] = None

        if 'episode' in listing:
            program['episode'] = listing['episode']
        else:
            program['episode'] = None
        if 'season' in listing:
            program['season'] = listing['season']
        else:
            program['season'] = None

        if 'genres' in listing and listing['genres']:
            program['genres'] = [ listing['genres'][0]['value'] ]
        else:
            program['genres'] = None


        # TBD NEED SHORT DESCR
        
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

            if 'small' in listing['descriptions'].keys():
                key = 'small'
            elif 'medium' in listing['descriptions'].keys():
                key = 'medium'
            elif 'large' in listing['descriptions'].keys():
                key = 'large'
            else:
                key = list(listing['descriptions'].keys())[0]
            program['short_desc'] = listing['descriptions'][key]

        program['stream_url'] = None
        if 'providers' in listing:
            for source in listing['providers'][0]['sources']:
                if 'drm' not in source:
                    if source['produces'] == 'application/x-mpegURL':
                        program['stream_url'] = source['uri']
                        break
                    elif source['produces'] == 'application/x-mpegURL;type=tv':
                        program['stream_url'] = source['uri']
        self.db_programs.save_program(self.plugin_obj.name, _prog, program)
        return program

    def sublist_len(self, _list):
        length = 0
        for pid, progs in _list.items():
            l = len(progs)
            length += l
        return length
