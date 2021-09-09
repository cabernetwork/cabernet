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
from lib.db.db_epg import DBepg
from lib.db.db_channels import DBChannels
from lib.plugins.plugin_epg import PluginEPG

from . import constants
from .translations import xumo_tv_genres


class EPG(PluginEPG):

    def __init__(self, _instance_obj):
        super().__init__(_instance_obj)

    def dates_to_pull(self):
        """
        Since epg is less than one day, return a forced day item with no
        aging items        
        """
        return [1], []

    @handle_json_except
    @handle_url_except
    def get_url_listing(self):
        """
        {"id": "SH038289620000", "contentType": "SERIES", "title": "Latest News", "descriptions": {"small": "stuff"},
        "start": 1630696080000, "end": 1630697400000, "channelId": 9999148, "type": "Asset"}
        """
        url = 'https://valencia-app-mds.xumo.com/v2/channels/list/{}/onnowandnext.json?f=asset.title&f=asset.descriptions' \
            .format(self.plugin_obj.geo.channelListId)
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as resp:
            listing = json.load(resp)

        ch_db = DBChannels(self.instance_obj.config_obj.data)
        ch_list = ch_db.get_channels(self.plugin_obj.name, self.instance_key)
        return ch_list, listing

    def refresh_programs(self, _epg_day, use_cache=True):
        todaydate = datetime.datetime.utcnow().date()
        program_list = self.db.get_epg_one(self.plugin_obj.name, self.instance_key, todaydate)
        if len(program_list) == 0:
            program_list = []
            timeslot_list = {}
        else:
            program_list = json.loads(program_list[0]['json'])
            timeslot_list = {}
            for program in program_list:
                ts = (program['channel'], program['start'])
                if ts not in timeslot_list.keys():
                    timeslot_list[ts] = None

        # Determine if GMT time is between 00:00 and 02:00.  If so, then process the entire day.
        # else, process only the next 2 programs.
        if utils.is_time_between(datetime.time(0,1), datetime.time(2,0)):
            self.logger.debug('Time is between midnight and 2am UTC, so will generate a full days guide')
            program_list = self.get_fullday_programs(program_list, timeslot_list)
        #else:
        #    self.logger.debug('Time is not between midnight and 2am UTC, so will generate a quick small update')
        #    program_list = self.get_nownext_programs(program_list, timeslot_list)

        # push the update to the database
        self.db.save_program_list(self.plugin_obj.name, self.instance_key, todaydate, program_list)
        self.logger.debug('Refreshed EPG data for {}:{} day {}'
            .format(self.plugin_obj.name, self.instance_key, todaydate))

    def get_nownext_programs(self, _program_list, _prog_id_list):
        """
        Returns a quick list of what is currently playing and what is on next
        """
        ch_list, listing = self.get_url_listing()
        for listing_data in listing['results']:
            try:
                ch_data = ch_list[str(listing_data['channelId'])][0]
                if not ch_data['enabled']:
                    continue
                if str(listing_data['channelId']) in _prog_id_list:
                    program_json = self.get_program(ch_data,
                        listing_data, _prog_id_list[str(listing_data['channelId'])])
                else:
                    program_json = self.get_program(ch_data,
                        listing_data, None)
            except KeyError:
                self.logger.debug('Missing Channel: {}'.format(str(listing_data['channelId'])))
                continue
            if program_json is not None:
                _program_list.append(program_json)
        return _program_list

    @handle_json_except
    @handle_url_except
    def get_fullday_programs(self, _program_list, _timeslot_list):
        """
        Returns a days (from midnight to midnight UTC) of programs
        # List of channels
        #https://valencia-app-mds.xumo.com/v2/channels/list/10006.json?geoId=924baa2b
        # Current thing playing, needed to get the stream uri by prog id
        #https://valencia-app-mds.xumo.com/v2/channels/channel/99991331/onnow.json?f=title&f=descriptions#descriptions
        # Current and next thing playing, so a very fast way to get current programs
        #https://valencia-app-mds.xumo.com/v2/channels/list/10006/onnowandnext.json?f=asset.title&f=asset.descriptions&f=logo
        # Provides programs (id and time slot) by channel over 24 hours GMT time, one hours at a time
        # THIS IS WHERE THE progid is for m3u8 streaming...
        #https://valencia-app-mds.xumo.com/v2/channels/channel/99991331/broadcast.json?hour=23
        # Data for a single program. Note the channel number listed does not seem to match...  It also has the m3u8 url as well
        #https://valencia-app-mds.xumo.com/v2/assets/asset/XM002J24LQYDS0.json?f=title&f=providers&f=descriptions&f=runtime&f=availableSince&f=cuePoints&f=ratings
        ?f=asset.title&f=asset.episodeTitle&f=asset.providers&f=asset.runtime&f=asset.availableSince&f=asset.ratings
        \u002Fv2\u002Fcategories\u002Fcategory\u002F1507.json
        https://live-content.xumo.com/137/content/XM0QYR4ADYAUOA/23022737/master.m3u8
        /client/index-c1d4ed7cf6fe454fd43f.js
        https:\u002F\u002Flive-content.xumo.com\u002F1870\u002Fcaptions\u002FXM0MQ06IH0PXSG\u002Fxumo45d8043f52f84869ae3c2c1f7a067d983757172727560471838.vtt_xumo.dfxp
        "apiConfig": {
            "server": "https:\u002F\u002Fvalencia-app-mds.xumo.com",
            "key": "BJ8e86EyuW8GUsXJ",
            "channelListId": "10006",
            "cacheBuster": "2",
            "videoQS": "?f=title&f=providers&f=descriptions&f=runtime&f=availableSince&f=cuePoints&f=ratings",
            "playlistQS": "?f=asset.title&f=asset.episodeTitle&f=asset.providers&f=asset.runtime&f=asset.availableSince&f=asset.ratings",
            "defaultPlaylist": "\u002Fv2\u002Fcategories\u002Fcategory\u002F1507.json",
            "epgQS": "?f=asset.title&f=asset.descriptions",
            "defaultChannel": 9999110,
            "geoId": "924baa2b",
            "adTagUrl": "https:\u002F\u002Fvalencia-app.xumo.com\u002Fconfig",
            "beaconServer": "https:\u002F\u002Fvalencia-beacons.xumo.com",
            "enableBeacons": true,
            "omniServer": "https:\u002F\u002Fsaa.cbsi.com\u002Fb\u002Fss\u002Fcbsicbsnewssite\u002F0",
            "playlistLimit": "50"
        },
        "apiConfig.server") + "/v2/channels/list/" + e.store.channelListId + "/genres.json"
        "apiConfig.server") + "/v2/assets/asset/" + f + ".json" + (0, P.default)("apiConfig.videoQS"), e.next = 23, v.default.get(p)

        SH0... m3u8
        XM0DMBUSIXH9T1
        https:\u002F\u002Fdai2.xumo.com\u002Famagi_hls_data_xumo1212A-abcnews\u002FCDN\u002Fmaster.m3u8

        """

        ch_db = DBChannels(self.instance_obj.config_obj.data)
        ch_list = ch_db.get_channels(self.plugin_obj.name, self.instance_key)
        prog_list = {}
        for ch in ch_list.keys():
            if not ch_list[ch][0]['enabled']:
                    continue
            self.logger.debug('{}:{} Processing Channel {} {}' \
                .format(self.plugin_obj.name, self.instance_key, ch, ch_list[ch][0]['display_name']))
            for hr in range(0,24):
                url = 'https://valencia-app-mds.xumo.com/v2/channels/channel/{}/broadcast.json?hour={}' \
                    .format(ch, hr)
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req) as resp:
                    listing = json.load(resp)
                for prog in listing['assets']:
                    start_time = utils.tm_local_parse(prog['timestamps']['start'])
                    
                    if prog['id'] not in prog_list.keys():
                        prog_list[prog['id']] = {
                            'id': prog['id'],
                            'channelId': ch,
                            'start': prog['timestamps']['start'], 
                            'end': prog['timestamps']['end']}

        self.logger.debug('{}:{} Processing {} Programs' \
                .format(self.plugin_obj.name, self.instance_key, len(prog_list.keys())))
        for prog in prog_list.keys():
            self.logger.debug('{}:{} Processing Program {}' \
                .format(self.plugin_obj.name, self.instance_key, prog))
            url = 'https://valencia-app-mds.xumo.com/v2/assets/asset/{}.json?f=title&f=providers&f=descriptions&f=runtime&f=availableSince' \
                .format(prog)
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req) as resp:
                listing = json.load(resp)
            prog_list[prog]['title'] = listing['title']
            if 'descriptions' in listing:
                key = list(listing['descriptions'].keys())[0]
                prog_list[prog]['descriptions'] = {}
                prog_list[prog]['descriptions'][key] = listing['descriptions'][key]
            
        self.logger.debug('{}:{} Finalizing EPG updates' \
            .format(self.plugin_obj.name, self.instance_key))
        for progid, listing_data in prog_list.items():
            try:
                ch_data = ch_list[str(listing_data['channelId'])][0]
                if str(listing_data['channelId']) in _timeslot_list:
                    program_json = self.get_program(ch_data,
                        listing_data, _timeslot_list[str(listing_data['channelId'])])
                else:
                    program_json = self.get_program(ch_data,
                        listing_data, None)
            except KeyError:
                self.logger.info('Missing Channel: {}'.format(str(listing_data['channelId'])))
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
        if _timeslot_list is not None and prog_id in _timeslot_list:
            return None
        
        start_time = utils.tm_local_parse(_program_data['start'])
        end_time = utils.tm_local_parse(_program_data['end'])
        dur_min = int((_program_data['end'] - _program_data['start']) / 60 / 1000)
        sid = str(_program_data['channelId'])
        title = _program_data['title']
        entity_type = None

        if 'descriptions' not in _program_data.keys():
            description = 'Unavailable'
        else:
            key = list(_program_data['descriptions'].keys())[0]
            description = _program_data['descriptions'][key]
            
        short_desc = description
        video_quality = None
        cc = False
        live = False
        is_new = False
        finale = False
        premiere = False
        air_date = None
        formatted_date = None
        rating = None

        icon = "https://image.xumo.com/v1/channels/channel/{}/512x512.png?type=color_onBlack" \
            .format(sid)

        if _ch_data['json']['groups_other'] in xumo_tv_genres:
            genres = xumo_tv_genres[_ch_data['json']['groups_other']]
        else:
            self.logger.info('Missing xumo genre translation for: {}' \
                    .format(_ch_data['json']['groups_other']))
            genres = _ch_data['json']['groups_other']

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
