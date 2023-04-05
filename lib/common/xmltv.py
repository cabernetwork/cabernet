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
import re
from xml.etree import ElementTree


import lib.common.utils as utils
import lib.common.exceptions as exceptions
from lib.common.tmp_mgmt import TMPMgmt

TMP_FOLDER = 'xmltv'

class XMLTV:
    """
    Currently only handles program ingest and not the channel ingest.
    When a xmltv only plugin is created, then the channel ingest will be needed.
    The limitation is the xmltv plugin will not understand stream urls, so its
    just an epg.
    """

    def __init__(self, _config, _url, _file_type):
        global TMP_FOLDER
        self.logger = logging.getLogger(__name__)
        self.url = _url
        self.file_type = _file_type
        self.config = _config
        self.iter_is_programme = True
        self.interator = None
        self.tmp_mgmt = TMPMgmt(self.config)
        self.has_future_dates = False
        self.start_date = None
        self.file_compressed = self.tmp_mgmt.download_file(self.url, TMP_FOLDER, None, self.file_type)
        if self.file_compressed is None:
            self.file = None
            raise exceptions.CabernetException('Unable to obtain XMLTV File {}' \
                .format(self.url))
        else:
            self.file = self.extract_file(self.file_compressed, self.file_type) 
        self.context = None
        self.root_elem = None

    def __iter__(self):
        self.context = ElementTree.iterparse(self.file, events=('start', 'end',))
        self.has_future_dates = False
        self.iterator = iter(self.context)
        event, self.root_elem = next(self.iterator, (None, None))
        return self
        
    def __next__(self):
        prog = None
        while prog is None:
            elem = self.get_next_prog_elem()
            if elem is None:
                return prog
            else:
                prog = self.get_program(elem)
        return prog

    def cleanup_tmp_folder(self):
        global TMP_FOLDER
        self.tmp_mgmt.cleanup_tmp(TMP_FOLDER)

    def get_next_prog_elem(self):
        while True:
            event, elem = next(self.iterator, (None, None))
            if event is None:
                return None
            if event == 'start':
                if elem.tag == 'programme':
                    return elem
            

    def set_iter_type(self, _is_programme=True):
        """
        Is either programme (True) or channel (False)
        """
        self.iter_is_programme = _is_programme

    def set_date(self, _start_date):
        """
        When returning programs, the date filters the programme return
        where the start date is in the date range (UTC)
        this is a datetime.date object
        """
        self.start_date = _start_date

    def extract_file(self, _filename, _file_type):
        if _file_type == '.zip':
            return self.tmp_mgmt.extract_zip(_filename)
        elif _file_type == '.gz':
            return self.tmp_mgmt.extract_gzip(_filename)
        else:
            return _filename

    def get_program(self, elem):
        program = None
        dt = self.str_to_datetime(elem.attrib['start'])
        dt_utc = utils.convert_to_utc(dt)
        if self.start_date is None or self.start_date == dt_utc.date():
            program = {'channel': elem.attrib['channel'], 'progid': None,
                'start': elem.attrib['start'], 'stop': elem.attrib['stop'],
                'length': 0, 'title': None, 'subtitle': None,
                'entity_type': None, 'desc': 'Not Available',
                'short_desc': 'Not Available',
                'video_quality': None, 'cc': False, 'live': False, 
                'finale': False, 'premiere': False, 'air_date': None, 
                'formatted_date': None, 'icon': None, 'rating': None,
                'is_new': False, 'genres': None, 'directors': None,
                'actors': None, 'season': None, 'episode': None,
                'se_common': None, 'se_xmltv_ns': None,
                'se_progid': None}
            while True:
                not_done = self.get_next_elem(program)
                self.root_elem.clear()
                if not not_done:
                    return program
        elif dt_utc.date() > self.start_date:
            self.has_future_dates = True
        return program

    def get_next_elem(self, _program):
        while True:
            event, elem = next(self.iterator, (None, None))
            if event is None:
                return False
            if event == 'start':
                if elem.tag == 'title':
                    _program['title'] = self.get_p_title(elem)
                    return True
                elif elem.tag == 'sub-title':
                    _program['subtitle'] = self.get_p_sub_title(elem)
                    return True
                elif elem.tag == 'desc':
                    _program['desc'] = self.get_p_desc(elem)
                    _program['short_desc'] = _program['desc']
                    return True
                elif elem.tag == 'length':
                    _program['length'] = self.get_p_length(elem)
                    return True
                elif elem.tag == 'icon':
                    _program['icon'] = self.get_p_icon(elem)
                    return True
                elif elem.tag == 'previously-shown':
                    _program['is_new'] = self.get_p_previously_shown(elem)
                    return True
                elif elem.tag == 'new':
                    _program['is_new'] = self.get_p_new(elem)
                    return True
                elif elem.tag == 'premiere':
                    _program['premiere'] = self.get_p_premiere(elem)
                    return True
                elif elem.tag == 'subtitles':
                    _program['cc'] = self.get_p_subtitles(elem)
                    return True
                elif elem.tag == 'rating':
                    _program['rating'] = self.get_p_rating(elem)
                    return True
                elif elem.tag == 'video':
                    _program['video_quality'] = self.get_p_video_quality(elem)
                    return True
                elif elem.tag == 'live':
                    _program['live'] = self.get_p_live(elem)
                    return True
                elif elem.tag == 'finale':
                    _program['finale'] = self.get_p_finale(elem)
                    return True
                elif elem.tag == 'category':
                    if _program['genres'] is None:
                        _program['genres'] = self.get_p_category(elem)
                    return True
                elif elem.tag == 'credits':
                    credits = self.get_p_credits(elem)
                    if credits:
                        if len(credits['actors']) != 0:
                            _program['actors'] = credits['actors']
                        if len(credits['directors']) != 0:
                            _program['directors'] = credits['directors']
                    return True
                elif elem.tag == 'date':
                    p_date = self.get_p_date(elem)
                    if p_date:
                        _program['air_date'] = p_date
                        if len(p_date) == 4:
                            _program['formatted_date'] = p_date
                        else:
                            _program['formatted_date'] = datetime.datetime.strptime(
                                p_date, '%Y%m%d').strftime('%Y/%m/%d')
                    return True
                elif elem.tag == 'episode-num':
                    episode_num = self.get_p_episode_num(elem)
                    if episode_num:
                        if episode_num['system'] == 'common' or \
                                episode_num['system'] == 'SxxExx':
                            ep_num = episode_num['text']
                            _program['se_common'] = ep_num
                            nums = re.findall('\d+', ep_num)
                            if len(nums) < 2:
                                _program['episode'] = nums[0]
                            else:
                                _program['episode'] = nums[1]
                                _program['season'] = nums[0]
                        elif episode_num['system'] == 'dd_progid':
                            ep_num = episode_num['text']
                            _program['se_progid'] = ep_num
                            _program['progid'] = ep_num.replace('.', '')
                            if _program['episode'] is None:
                                nums = int(re.findall('\d+$', ep_num)[0])
                                if nums != 0:
                                    _program['episode'] = nums
                        elif episode_num['system'] == 'xmltv_ns':
                            _program['se_xmltv_ns'] = episode_num['text']
                    return True
            if event == 'end' and elem.tag == 'programme':
                return False

    def str_to_datetime(self, date_str):
        return datetime.datetime.strptime(date_str, '%Y%m%d%H%M%S %z')
        
    def get_ch_channel(self, elem):
        return elem.attrib['id']
        
    def get_ch_display_name(self, elem):
        event, elem = next(self.iterator, (None, None))
        return elem.text
 
    def get_ch_icon(self, elem):
        return elem.attrib['src']

    def get_p_title(self, elem):
        event, elem = next(self.iterator, (None, None))
        return elem.text
        
    def get_p_sub_title(self, elem):
        event, elem = next(self.iterator, (None, None))
        return elem.text
        
    def get_p_desc(self, elem):
        event, elem = next(self.iterator, (None, None))
        if elem.text is None:
            return 'Not Available'
        else:
            return elem.text

    def get_p_length(self, elem):
        event, elem = next(self.iterator, (None, None))
        if elem.attrib['units'] == 'minutes':
            return int(elem.text)
        elif elem.attrib['units'] == 'hours':
            return int(elem.text) * 60
        elif elem.attrib['units'] == 'seconds':
            return round(int(elem.text) / 60)
        else:
            self.logger.warning('Unknown XMLTV program length {}:{}'
                .format(elem.attrib['units'], elem.text))
            return None

    def get_p_category(self, elem):
        # multiple hits
        event, elem = next(self.iterator, (None, None))
        return [ elem.text ]

    def get_p_icon(self, elem):
        return elem.attrib['src']

    def get_p_previously_shown(self, elem):
        return False

    def get_p_new(self, elem):
        return True

    def get_p_premiere(self, elem):
        return True

    def get_p_subtitles(self, elem):
        return True

    def get_p_episode_num(self, elem):
        # multiple hits
        system = elem.attrib['system']
        event, elem = next(self.iterator, (None, None))
        return {'system':system, 'text':elem.text}

    def get_p_rating(self, elem):
        event, elem = next(self.iterator, (None, None))
        event, elem = next(self.iterator, (None, None))
        return elem.text

    def get_p_credits(self, elem):
        # director
        # actor
        # producer
        event, elem = next(self.iterator, (None, None))
        actors = []
        directors = []
        while True:
            if event == 'end':
                if elem.tag == 'credits':
                    break
                else:
                    if elem.tag == 'actor':
                        actors.append(elem.text)
                    elif elem.tag == 'director':
                        directors.append(elem.text)
            event, elem = next(self.iterator, (None, None))
        return {'actors': actors, 'directors': directors}

    def get_p_date(self, elem):
        # 2 formats: YYYY or YYYYMMDD
        event, elem = next(self.iterator, (None, None))
        return elem.text

    def get_p_video_quality(self, elem):
        event, elem = next(self.iterator, (None, None))
        event, elem = next(self.iterator, (None, None))
        return elem.text

    def get_p_live(self, elem):
        return True
        # missing from epg2xml

    def get_p_finale(self, elem):
        return True
        # missing from epg2xml

