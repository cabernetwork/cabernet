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

import lib.common.utils as utils
from lib.plugins.plugin_epg import PluginEPG

from .translations import plutotv_tv_genres


class EPG(PluginEPG):

    def __init__(self, _instance_obj):
        super().__init__(_instance_obj)

    def dates_to_pull(self):
        """
        Since epg is less than one day, return a forced day item with no
        aging items        
        """
        return [1], []

    def get_day_data(self):
        stime = datetime.datetime.utcnow() - datetime.timedelta(hours=2)
        # back up 2 hours
        start = str(stime.strftime('%Y-%m-%dT%H:00:00.000Z'))
        etime = stime + datetime.timedelta(
            hours=self.config_obj.data[self.plugin_obj.name.lower()]['epg-hours'])
        end = str(etime.strftime('%Y-%m-%dT%H:00:00.000Z'))
        results = {}
        epg_urls = ''.join([self.plugin_obj.unc_pluto_base, '?start={}&stop={}'])
        if stime.date() != etime.date():
            # crosses midnight
            mstime = str(stime.strftime('%Y-%m-%dT23:59:00.000Z'))
            metime = str(etime.strftime('%Y-%m-%dT00:00:00.000Z'))
            url = (epg_urls.format(start, mstime))
            results[stime.date()] = self.get_uri_data(url)
            url = (epg_urls.format(metime, end))
            results[etime.date()] = self.get_uri_data(url)
        else:
            url = (epg_urls.format(start, end))
            results[stime.date()] = self.get_uri_data(url)
        return results

    def refresh_programs(self, _epg_day, use_cache=True):
        try:
            json_data = self.get_day_data()
            for day, day_data in json_data.items():
                if day_data is None:
                    self.logger.info(
                        '{}:{} Unable to update EPG, no data for day {}'
                        .format(self.plugin_obj.name, self.instance_key, day))
                    continue
                program_list = []
                for ch_data in day_data:
                    if 'timelines' in ch_data:
                        for listing_data in ch_data['timelines']:
                            program_json = self.get_program(ch_data, listing_data)
                            if program_json is not None:
                                program_list.append(program_json)
                # push the update to the database
                if len(program_list) == 0:
                    self.logger.info(
                        '{}:{} Unable to update EPG, no timelines for day {}'
                        .format(self.plugin_obj.name, self.instance_key, day))
                    continue
                self.db.save_program_list(self.plugin_obj.name, self.instance_key, day, program_list)
                self.logger.debug('Refreshed EPG data for {}:{} day {}'
                                  .format(self.plugin_obj.name, self.instance_key, day))
        except KeyError as e:
            self.logger.info('Unable to update PlutoTV EPG, no timelines. Key Error: {}'.format(e))

    def get_program(self, _ch_data, _program_data):
        # https://github.com/XMLTV/xmltv/blob/master/xmltv.dtd

        # a duration of 0 means dummy program, so skip
        if _program_data['episode']['duration'] == 0:
            return None

        dur_min = int(_program_data['episode']['duration'] / 60 / 1000)

        sid = str(_ch_data['_id'])
        start_time = datetime.datetime.fromisoformat(
            _program_data['start'].replace('Z', '+00:00')).timestamp() \
            + self.config_obj.data[self.config_section]['epg-start_adjustment']
        start_time = utils.tm_local_parse(start_time * 1000)
        end_time = datetime.datetime.fromisoformat(
            _program_data['stop'].replace('Z', '+00:00')).timestamp() \
            + self.config_obj.data[self.config_section]['epg-end_adjustment']
        end_time = utils.tm_local_parse(end_time * 1000)
        title = _program_data['title']
        entity_type = None
        prog_id = None

        if 'description' not in _program_data['episode'].keys():
            description = 'Unavailable'
        elif not _program_data['episode']['description']:
            description = 'Unavailable None'
        else:
            description = _program_data['episode']['description']

        short_desc = description
        video_quality = None
        cc = False

        live = False
        is_new = False
        if 'liveBroadcast' in _program_data['episode'].keys():
            if _program_data['episode']['liveBroadcast']:
                live = True
                is_new = True

        finale = False
        premiere = False

        if 'clip' in _program_data['episode'].keys():
            air_date_msec = datetime.datetime.fromisoformat(
                _program_data['episode']['clip']['originalReleaseDate']
                .replace('Z', '+00:00')).timestamp() * 1000
            air_date = utils.date_parse(air_date_msec, '%Y%m%d')
            formatted_date = utils.date_parse(air_date_msec, '%Y/%m/%d')
        else:
            air_date = None
            formatted_date = None

        icon = None
        icon_type = self.config_obj.data[self.plugin_obj.name.lower()]['program_thumbnail']
        if icon_type == 'featuredImage' and \
                icon_type in _program_data['episode']['series'].keys():
            icon = _program_data['episode']['series'][icon_type]['path']
        elif icon_type in _program_data['episode'].keys():
            icon = _program_data['episode'][icon_type]['path']
        elif 'featuredImage' in _program_data['episode']['series'].keys():
            icon = _program_data['episode']['series']['featuredImage']['path']
        elif 'poster' in _program_data['episode'].keys():
            icon = _program_data['episode']['poster']['path']

        if 'rating' in _program_data['episode'].keys():
            rating = _program_data['episode']['rating']
        else:
            rating = None

        if 'genre' in _program_data['episode'].keys():
            if _program_data['episode']['genre'] in plutotv_tv_genres:
                genres = plutotv_tv_genres[_program_data['episode']['genre']]
            else:
                self.logger.info(
                    'Missing PlutoTV genre translation for: {}'
                    .format(_program_data['episode']['genre']))
                genres = [x.strip() for x in _program_data['episode']['genre'].split(' and ')]
        else:
            genres = None

        directors = None
        actors = None
        season = None
        episode = None

        if 'season' in _program_data['episode'].keys():
            if 'number' in _program_data['episode'].keys():
                if _program_data['episode']['season'] == 1 and \
                        _program_data['episode']['number'] == 1:
                    season = None
                    episode = None
                else:
                    season = _program_data['episode']['season']
                    episode = _program_data['episode']['number'] + self.episode_adj
            else:
                season = None
                episode = None
        elif 'number' in _program_data['episode'].keys():
            season = None
            episode = None

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

        if season is not None:
            subtitle = 'S%02dE%02d ' % (season, episode)
        elif episode is not None:
            subtitle = 'E%02d ' % episode
        else:
            subtitle = ''
        if 'name' in _program_data['episode'].keys():
            subtitle += _program_data['episode']['name']
        else:
            subtitle = None

        json_result = {
            'channel': sid, 'progid': prog_id, 'start': start_time, 'stop': end_time,
            'length': dur_min, 'title': title, 'subtitle': subtitle, 'entity_type': entity_type,
            'desc': description, 'short_desc': short_desc,
            'video_quality': video_quality, 'cc': cc, 'live': live, 'finale': finale,
            'premiere': premiere,
            'air_date': air_date, 'formatted_date': formatted_date, 'icon': icon,
            'rating': rating, 'is_new': is_new, 'genres': genres, 'directors': directors, 'actors': actors,
            'season': season, 'episode': episode, 'se_common': se_common, 'se_xmltv_ns': se_xmltv_ns,
            'se_progid': se_prog_id}
        return json_result
