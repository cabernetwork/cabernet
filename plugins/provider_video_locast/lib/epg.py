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
import logging
import urllib.request

import lib.common.exceptions as exceptions
import lib.common.utils as utils
from lib.common.decorators import handle_url_except
from lib.common.decorators import handle_json_except
from lib.db.db_epg import DBepg

from . import constants


class EPG:
    logger = None

    def __init__(self, _locast_instance):
        self.locast_instance = _locast_instance
        self.instance = _locast_instance.instance
        self.db = DBepg(self.locast_instance.config_obj.data)
        self.config_section = _locast_instance.config_section
        self.episode_adj = int(self.locast_instance.config_obj.data \
            [self.locast_instance.config_section]['epg-episode_adjustment'])
        if self.locast_instance.location.has_dma_changed:
            self.db.del_instance(
                self.locast_instance.locast.name, self.instance)

    def refresh_epg(self):
        if not self.is_refresh_expired():
            self.logger.debug('EPG still new for {} {}, not refreshing'.format(self.locast_instance.locast.name, self.instance))
            return
        if not self.locast_instance.config_obj.data[self.locast_instance.config_section]['epg-enabled']:
            self.logger.debug('EPG collection not enabled for {} {}'
                .format(self.locast_instance.locast.name, self.instance))
            return
        forced_dates, aging_dates = self.dates_to_pull()
        self.db.del_old_programs(self.locast_instance.locast.name, self.instance)
        for epg_day in forced_dates:
            self.refresh_programs(epg_day, False)
        for epg_day in aging_dates:
            self.refresh_programs(epg_day, True)

    def is_refresh_expired(self):
        """
        Makes it so the minimum epg update rate
        can only occur based on epg_min_refresh_rate
        """
        checking_date = datetime.date.today()
        last_update = self.db.get_last_update(self.locast_instance.locast.name, self.instance, checking_date)
        if not last_update:
            return True
        expired_date = datetime.datetime.now() - datetime.timedelta(
            seconds=self.locast_instance.config_obj.data[
                self.locast_instance.locast.name.lower()]['epg-min_refresh_rate'])
        if last_update < expired_date:
            return True
        return False

    def dates_to_pull(self):
        todaydate = datetime.date.today()
        forced_days = []
        aging_days = []
        for x in range(0, self.locast_instance.config_obj.data[self.locast_instance.locast.name.lower()]['epg-days']):
            if x < self.locast_instance.config_obj.data[self.locast_instance.locast.name.lower()]['epg-days_start_refresh']:
                forced_days.append(todaydate + datetime.timedelta(days=x))
            else:
                aging_days.append(todaydate + datetime.timedelta(days=x))
        return forced_days, aging_days

    @handle_json_except
    @handle_url_except
    def get_url_data(self, _day):
        url = ('https://api.locastnet.org/api/watch/epg/{}?startTime={}'
               .format(self.locast_instance.location.dma, _day.isoformat()))
        # pull if successful may not contain any listing data (len=0)
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as resp:
            results = json.load(resp)
        if len(results[0]['listings']) == 0:
            self.logger.warning('EPG Days to collect is too high.  {} has no data'.format(_day.isoformat()))
            return None
        else:
            return results

    def refresh_programs(self, _day, use_cache):
        if use_cache:
            last_update = self.db.get_last_update(self.locast_instance.locast.name, self.instance, _day)
            if last_update:
                todaydate = datetime.datetime.now()
                use_cache_after = todaydate - datetime.timedelta(
                    days=self.locast_instance.config_obj.data[
                        self.locast_instance.locast.name.lower()]['epg-days_aging_refresh'])
                if last_update > use_cache_after:
                    return

        program_list = []
        json_data = self.get_url_data(_day)
        if json_data is not None:
            for ch_data in json_data:
                for listing_data in ch_data['listings']:
                    program_json = self.get_program(listing_data)
                    program_list.append(program_json)

            # push the update to the database
            self.db.save_program_list(self.locast_instance.locast.name, self.instance, _day, program_list)
            self.logger.debug('Refreshing EPG data for {}:{} day:{}'
                .format(self.locast_instance.locast.name, self.instance, _day))

    def get_program(self, _program_data):
        # https://github.com/XMLTV/xmltv/blob/master/xmltv.dtd

        sid = str(_program_data['stationId'])
        start_time = utils.tm_local_parse(_program_data['startTime'])
        dur_min = int(_program_data['duration'] / 60)
        end_time = utils.tm_local_parse(_program_data['startTime'] + _program_data['duration'] * 1000)
        title = _program_data['title']
        entity_type = _program_data['entityType']
        prog_id = _program_data['programId']

        if 'description' not in _program_data.keys():
            description = 'Unavailable'
        elif not _program_data['description']:
            description = 'Unavailable None'
        else:
            description = _program_data['description']

        if 'shortDescription' not in _program_data.keys():
            short_desc = description
        else:
            short_desc = _program_data['shortDescription']

        video_quality = None
        if 'videoProperties' in _program_data.keys():
            if 'HD' in _program_data['videoProperties']:
                video_quality = 'HDTV'

        cc = False
        if 'audioProperties' in _program_data.keys():
            if 'CC' in _program_data['audioProperties']:
                cc = True

        live = False
        if 'videoProperties' in _program_data.keys():
            if 'Live' in _program_data['videoProperties']:
                live = True

        finale = False
        if 'videoProperties' in _program_data.keys():
            if 'Finale' in _program_data['videoProperties']:
                finale = True

        premiere = False
        if 'videoProperties' in _program_data.keys():
            if 'Premiere' in _program_data['videoProperties']:
                premiere = True

        if _program_data['entityType'] == 'Movie' and 'releaseYear' in _program_data.keys():
            air_date = str(_program_data['releaseYear'])
            formatted_date = air_date
        elif 'airdate' in _program_data.keys():
            air_date = utils.date_parse(_program_data['airdate'], '%Y%m%d')
            formatted_date = utils.date_parse(_program_data['airdate'], '%Y/%m/%d')
        elif 'gameDate' in _program_data.keys():
            date_obj = datetime.datetime.strptime(_program_data['gameDate'], '%Y-%m-%d')
            air_date = utils.date_obj_parse(date_obj, '%Y%m%d')
            formatted_date = utils.date_obj_parse(date_obj, '%Y/%m/%d')
        elif 'releaseDate' in _program_data.keys():
            air_date = utils.date_parse(_program_data['releaseDate'], '%Y%m%d')
            formatted_date = utils.date_parse(_program_data['releaseDate'], '%Y/%m/%d')
        else:
            air_date = None
            formatted_date = None

        icon = _program_data['preferredImage']

        if 'rating' in _program_data.keys():
            rating = _program_data['rating']
        else:
            rating = None

        if 'isNew' in _program_data.keys() and _program_data['isNew']:
            is_new = True
        else:
            is_new = False

        if 'genres' in _program_data.keys():
            genres = [x.strip() for x in _program_data['genres'].split(',')]
        else:
            genres = None

        if 'directors' in _program_data.keys():
            directors = _program_data['directors'].split(",")
        else:
            directors = None

        if 'topCast' in _program_data.keys():
            actors = _program_data['topCast'].split(",")
        else:
            actors = None

        if 'seasonNumber' in _program_data.keys():
            season = _program_data['seasonNumber']
        else:
            season = None
            
        if 'episodeNumber' in _program_data.keys():
            episode = _program_data['episodeNumber'] + self.episode_adj
        else:
            progid_episode = int(prog_id[-4:]) + self.episode_adj
            if progid_episode > self.episode_adj:
                episode = progid_episode
            else:
                episode = None


        if (season is None) and (episode is None):
            se_common = None
            se_xmltv_ns = None
            se_prog_id = None
        elif (season is not None) and (episode is not None):
            se_common = 'S%02dE%02d' % (season, episode)
            se_xmltv_ns = ''.join([str(season - 1), '.', str(episode - 1), '.0/1'])
            se_prog_id = '{}.{}'.format(_program_data['programId'][:10], int(_program_data['programId'][10:])+self.episode_adj)
                
        elif (season is None) and (episode is not None):
            se_common = None
            se_xmltv_ns = None
            se_prog_id = '{}.{}'.format(_program_data['programId'][:10], int(_program_data['programId'][10:])+self.episode_adj)
        else:  # (season is not None) and (episode is None):
            se_common = 'S%02dE%02d' % (season, 0)
            se_xmltv_ns = ''.join([str(season - 1), '.', '0', '.0/1'])
            se_prog_id = ''

        if season is not None:
            subtitle = 'S%02dE%02d ' % (season, episode)
        elif episode is not None:
            subtitle = 'E%02d ' % (episode)
        else:
            subtitle = ''
        if 'episodeTitle' in _program_data.keys():
            subtitle += _program_data['episodeTitle']
        elif 'eventTitle' in _program_data.keys():
            subtitle += _program_data['eventTitle']
        elif _program_data['entityType'] == 'Movie' and 'releaseYear' in _program_data.keys():
            subtitle = 'Movie: {}'.format(_program_data['releaseYear'])
        else:
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


EPG.logger = logging.getLogger(__name__)
