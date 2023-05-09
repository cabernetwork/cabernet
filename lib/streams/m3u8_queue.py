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

import logging
import os
import re
import requests
import socket
import sys
import threading
import time
import urllib.parse
from collections import OrderedDict
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from multiprocessing import Queue
from queue import Empty
from threading import Thread

import lib.common.utils as utils
import lib.m3u8 as m3u8
from lib.common.decorators import handle_url_except
from lib.common.decorators import handle_json_except
from lib.streams.atsc import ATSCMsg
from lib.streams.video import Video
from .pts_validation import PTSValidation
from .pts_resync import PTSResync


PLAY_LIST = OrderedDict()
IN_QUEUE = Queue()
OUT_QUEUE = Queue()
TERMINATE_REQUESTED = False
MAX_STREAM_QUEUE_SIZE = 40
STREAM_QUEUE = Queue()
OUT_QUEUE_LIST = []
IS_VOD = False

class M3U8Queue(Thread):
    """
    This runs as an independent process (one per stream) to get and process the 
    data stream as fast as possible and return it to the tuner web server for 
    output to the client.
    """
    is_stuck = None
    http_session = requests.session()

    def __init__(self, _config, _channel_dict):
        Thread.__init__(self)
        self.logger = logging.getLogger(__name__ + str(threading.get_ident()))
        self.config = _config
        self.namespace = _channel_dict['namespace'].lower()
        self.pts_validation = None
        self.initialized_psi = False
        self.first_segment = True
        self.config_section = utils.instance_config_section(_channel_dict['namespace'], _channel_dict['instance'])
        self.atsc_msg = ATSCMsg()
        self.channel_dict = _channel_dict
        if self.config[self.config_section]['player-enable_pts_filter']:
            self.pts_validation = PTSValidation(_config, _channel_dict)
        self.video = Video(self.config)
        self.atsc = _channel_dict['atsc']
        if _channel_dict['json'].get('Header') is None:
            self.header = {'User-agent': utils.DEFAULT_USER_AGENT}
        else:
            self.header = _channel_dict['json']['Header']
        if _channel_dict['json'].get('use_date_on_m3u8_key') is None:
            self.use_date_on_key = True
        else:
            self.use_date_on_key = _channel_dict['json']['use_date_on_m3u8_key']

        self.pts_resync = PTSResync(_config, self.config_section, _channel_dict['uid'])
        self.key_list = {}
        self.start()

    @handle_url_except()
    def get_uri_data(self, _uri):
        resp = self.http_session.get(_uri, headers=self.header, timeout=(8, 8))
        x = resp.content
        resp.raise_for_status()
        return x

    def run(self):
        global OUT_QUEUE
        global STREAM_QUEUE
        global TERMINATE_REQUESTED
        try:
            while not TERMINATE_REQUESTED:
                queue_item = STREAM_QUEUE.get()
                if queue_item['uri_dt'] == 'terminate':
                    self.logger.debug('Received terminate from internalproxy {}'.format(os.getpid()))
                    TERMINATE_REQUESTED = True
                    break
                elif queue_item['uri_dt'] == 'status':
                    out_queue_put({'uri': 'running',
                                   'data': None,
                                   'stream': None,
                                   'atsc': None})
                    continue
                time.sleep(0.01)
                self.process_m3u8_item(queue_item)
        except (KeyboardInterrupt, EOFError) as ex:
            TERMINATE_REQUESTED = True
            clear_queues()
            if self.pts_resync is not None:
                self.pts_resync.terminate()
                self.pts_resync = None
            time.sleep(0.01)
            sys.exit()
        except Exception as ex:
            TERMINATE_REQUESTED = True
            STREAM_QUEUE.put({'uri_dt': 'terminate'})
            IN_QUEUE.put({'uri': 'terminate'})
            if self.pts_resync is not None:
                self.pts_resync.terminate()
                self.pts_resync = None
            clear_queues()
            time.sleep(0.01)
            self.logger.exception('{}'.format(
                'UNEXPECTED EXCEPTION M3U8Queue='))
            sys.exit()
        # we are terminating so cleanup ffmpeg
        if self.pts_resync is not None:
            self.pts_resync.terminate()
            self.pts_resync = None
        time.sleep(0.01)
        out_queue_put({'uri': 'terminate',
                       'data': None,
                       'stream': None,
                       'atsc': None})
        time.sleep(0.01)
        TERMINATE_REQUESTED = True
        self.logger.debug('M3U8Queue terminated {}'.format(os.getpid()))

    def decrypt_stream(self, _data):
        if _data['key'] and _data['key']['uri']:
            if _data['key']['uri'] in self.key_list.keys():
                key_data = self.key_list[_data['key']['uri']]
                self.logger.debug('Reusing key {} {}'.format(os.getpid(), _data['key']['uri']))
            elif not _data['key']['uri'].startswith('http'):
                self.logger.warning('Unknown protocol, aborting {} {}'.format(os.getpid(), _data['key']['uri']))
                return False
            else:
                key_data = self.get_uri_data(_data['key']['uri'])

            if key_data is not None:
                self.key_list[_data['key']['uri']] = key_data
                if _data['key']['iv'] is None:
                    # if iv is none, use a random value
                    iv = bytearray.fromhex('000000000000000000000000000000F6')
                elif _data['key']['iv'].startswith('0x'):
                    iv = bytearray.fromhex(_data['key']['iv'][2:])
                else:
                    iv = bytearray.fromhex(_data['key']['iv'])
                cipher = Cipher(algorithms.AES(key_data), modes.CBC(iv), default_backend())
                decryptor = cipher.decryptor()
                self.video.data = decryptor.update(self.video.data)
        if len(self.key_list.keys()) > 20:
            del self.key_list[list(self.key_list)[0]]
        return True

    def atsc_processing(self):
        if not self.atsc:
            p_list = self.atsc_msg.extract_psip(self.video.data)
            if len(p_list) != 0:
                self.atsc = p_list
                self.channel_dict['atsc'] = p_list
                self.initialized_psi = True
                return p_list

        elif not self.initialized_psi:
            p_list = self.atsc_msg.extract_psip(self.video.data)
            if len(self.atsc) < len(p_list):
                self.atsc = p_list
                self.channel_dict['atsc'] = p_list
                self.initialized_psi = True
                return p_list
            if len(self.atsc) == len(p_list):
                for i in range(len(p_list)):
                    if p_list[i][4:] != self.atsc[i][4:]:
                        self.atsc = p_list
                        self.channel_dict['atsc'] = p_list
                        self.initialized_psi = True
                        is_changed = True
                        return p_list
        return None

    def process_m3u8_item(self, _queue_item):
        global IS_VOD
        global TERMINATE_REQUESTED
        global PLAY_LIST
        global OUT_QUEUE
        uri_dt = _queue_item['uri_dt']
        data = _queue_item['data']
        if data['filtered']:
            out_queue_put({'uri': uri_dt[0],
                           'data': data,
                           'stream': self.get_stream_from_atsc(),
                           'atsc': None})
            PLAY_LIST[uri_dt]['played'] = True
            time.sleep(0.01)
        else:
            if IS_VOD:
                count = self.config['stream']['vod_retries']
            else:
                count = 1
            while count > 0:
                self.video.data = self.get_uri_data(uri_dt[0])
                if self.video.data:
                    break
                out_queue_put({'uri': 'extend',
                               'data': data,
                               'stream': None,
                               'atsc': None})
                count -= 1
            if uri_dt not in PLAY_LIST.keys():
                return
            if self.video.data is None:
                PLAY_LIST[uri_dt]['played'] = True
                out_queue_put({'uri': uri_dt[0],
                               'data': data,
                               'stream': None,
                               'atsc': None
                               })
                return
            if not self.decrypt_stream(data):
                # terminate if stream is not decryptable
                out_queue_put({'uri': 'terminate',
                               'data': data,
                               'stream': None,
                               'atsc': None})
                TERMINATE_REQUESTED = True
                self.pts_resync.terminate()
                self.pts_resync = None
                clear_queues()
                PLAY_LIST[uri_dt]['played'] = True
                time.sleep(0.01)
                return
            if not self.is_pts_valid():
                PLAY_LIST[uri_dt]['played'] = True
                out_queue_put({'uri': uri_dt[0],
                               'data': data,
                               'stream': None,
                               'atsc': None
                               })
                return

            if self.first_segment:
                self.first_segment = False
            self.pts_resync.resequence_pts(self.video)
            if self.video.data is None:
                out_queue_put({'uri': uri_dt[0],
                               'data': data,
                               'stream': self.video.data,
                               'atsc': None})
                PLAY_LIST[uri_dt]['played'] = True
                time.sleep(0.01)
                return
            atsc_default_msg = self.atsc_processing()
            out_queue_put({'uri': uri_dt[0],
                           'data': data,
                           'stream': self.video.data,
                           'atsc': atsc_default_msg
                           })
            PLAY_LIST[uri_dt]['played'] = True
            time.sleep(0.1)

    def is_pts_valid(self):
        if self.pts_validation is None:
            return True
        results = self.pts_validation.check_pts(self.video)
        if results['byteoffset'] != 0:
            return False
        if results['refresh_stream']:
            return False
        if results['reread_buffer']:
            return False
        return True

    def get_stream_from_atsc(self):
        if self.atsc is not None:
            return self.atsc_msg.format_video_packets(self.atsc)
        else:
            self.logger.info(''.join([
                'No ATSC msg available during filtered content, ',
                'recommend running this channel again to catch the ATSC msg.']))
            return self.atsc_msg.format_video_packets()


class M3U8Process(Thread):
    """
    process for managing the list of m3u8 data sections.
    Includes managing the processing queue and providing
    the M3U8Queue with what to process.
    """

    def __init__(self, _config, _plugins, _channel_dict):
        Thread.__init__(self)
        self.logger = logging.getLogger(__name__ + str(threading.get_ident()))
        self.config = _config
        self.channel_dict = _channel_dict
        if _channel_dict['json'].get('Header') is None:
            self.header = {'User-agent': utils.DEFAULT_USER_AGENT}
        else:
            self.header = _channel_dict['json']['Header']
        if _channel_dict['json'].get('use_date_on_m3u8_key') is None:
            self.use_date_on_key = True
        else:
            self.use_date_on_key = _channel_dict['json']['use_date_on_m3u8_key']

        self.ch_uid = _channel_dict['uid']
        self.is_starting = True
        self.last_refresh = time.time()
        self.plugins = _plugins
        self.config_section = utils.instance_config_section(_channel_dict['namespace'], _channel_dict['instance'])

        self.is_running = True
        self.duration = 6
        self.m3u8_q = M3U8Queue(_config, _channel_dict)
        self.file_filter = None
        self.start()

    def run(self):
        global IS_VOD
        global IN_QUEUE
        global OUT_QUEUE
        global TERMINATE_REQUESTED

        self.stream_uri = self.get_stream_uri()
        if not self.stream_uri:
            self.logger.warning('Unknown Channel {}'.format(self.ch_uid))
            out_queue_put({'uri': 'terminate',
                           'data': None,
                           'stream': None,
                           'atsc': None})
            time.sleep(0.01)
            self.terminate()
            self.m3u8_q.join()
            TERMINATE_REQUESTED = True
            self.logger.debug('1 M3U8Process terminated {}'.format(os.getpid()))
            return
        else:
            out_queue_put({'uri': 'running',
                           'data': None,
                           'stream': None,
                           'atsc': None})
            time.sleep(0.01)

        try:
            self.logger.debug('M3U8: {} {}'.format(self.stream_uri, os.getpid()))
            if self.config[self.config_section]['player-enable_url_filter']:
                stream_filter = self.config[self.config_section]['player-url_filter']
                if stream_filter is not None:
                    self.file_filter = re.compile(stream_filter)
                else:
                    self.logger.warning('[{}]][player-enable_url_filter]'
                                        ' enabled but [player-url_filter] not set'
                                        .format(self.config_section))
            while not TERMINATE_REQUESTED:
                added = 0
                removed = 0
                self.logger.debug('Reloading m3u8 stream queue {}'.format(os.getpid()))
                playlist = self.get_m3u8_data(self.stream_uri)
                if playlist is None:
                    self.logger.debug('M3U Playlist is None, retrying')
                    self.sleep(self.duration+0.5)
                    continue
                if playlist.playlist_type == 'vod' or self.config[self.config_section]['player-play_all_segments']:
                    if not IS_VOD:
                        self.logger.debug('Setting stream type to VOD {}'.format(os.getpid()))
                        IS_VOD = True
                elif IS_VOD:
                    self.logger.debug('Setting stream type to non-VOD {}'.format(os.getpid()))
                    IS_VOD = False
                removed += self.remove_from_stream_queue(playlist)
                added += self.add_to_stream_queue(playlist)
                if self.plugins.plugins[self.channel_dict['namespace']].plugin_obj \
                        .is_time_to_refresh_ext(self.last_refresh, self.channel_dict['instance']):
                    self.stream_uri = self.get_stream_uri()
                    self.logger.debug('M3U8: {} {}'
                                      .format(self.stream_uri, os.getpid()))
                    self.last_refresh = time.time()
                    time.sleep(0.3)
                elif self.duration > 0.5:
                    self.sleep(self.duration+0.5)
        except Exception as ex:
            self.logger.exception('{}'.format(
                'UNEXPECTED EXCEPTION M3U8Process='))
        self.terminate()
        # wait for m3u8_q to finish so it can cleanup ffmpeg
        self.m3u8_q.join()
        TERMINATE_REQUESTED = True
        self.logger.debug('M3U8Process terminated {}'.format(os.getpid()))

    def sleep(self, _time):
        global TERMINATE_REQUESTED
        start_ttw = time.time()
        for i in range(round(_time * 5)):
            if not TERMINATE_REQUESTED:
                time.sleep(self.duration * 0.2)
            delta_ttw = time.time() - start_ttw
            if delta_ttw > _time:
                break

    def terminate(self):
        global STREAM_QUEUE
        try:
            STREAM_QUEUE.put({'uri_dt': 'terminate'})
            time.sleep(0.01)
        except ValueError as ex:
            pass

    def get_stream_uri(self):
        return self.plugins.plugins[self.channel_dict['namespace']] \
            .plugin_obj.get_channel_uri_ext(self.channel_dict['uid'], self.channel_dict['instance'])

    @handle_url_except()
    def get_m3u8_data(self, _uri):
        # it sticks here.  Need to find a work around for the socket.timeout per process
        return m3u8.load(_uri, headers=self.header, http_session=M3U8Queue.http_session)

    def segment_date_time(self, _segment):
        if _segment:
            return None
        if _segment.current_program_date_time:
            return None
        return _segment.current_program_date_time.replace(microsecond=0)

    def add_to_stream_queue(self, _playlist):
        global PLAY_LIST
        global STREAM_QUEUE
        global TERMINATE_REQUESTED
        total_added = 0
        if _playlist.keys != [None]:
            keys = [{"uri": key.absolute_uri, "method": key.method, "iv": key.iv}
                    for key in _playlist.keys if key]
            if len(keys) != len(_playlist.segments):
                keys = [{"uri": keys[0]['uri'], "method": keys[0]['method'], "iv": keys[0]['iv']}
                        for i in range(0, len(_playlist.segments))]
        else:
            keys = [None for i in range(0, len(_playlist.segments))]
        num_segments = len(_playlist.segments)
        if self.is_starting and not self.config[self.config_section]['player-play_all_segments']:
            seg_to_play = self.config[self.config_section]['player-segments_to_play']
            if _playlist.playlist_type == 'vod':
                seg_to_play = num_segments
            elif seg_to_play > num_segments:
                seg_to_play = num_segments

            skipped_seg = num_segments - seg_to_play
            # total_added += self.add_segment(_playlist.segments[0], keys[0])

            for m3u8_segment, key in zip(_playlist.segments[0:skipped_seg], keys[0:skipped_seg]):
                total_added += self.add_segment(m3u8_segment, key, _default_played=True)
            for i in range(skipped_seg, num_segments):
                total_added += self.add_segment(
                    _playlist.segments[i], keys[i])
            self.is_starting = False
        else:
            key_list = list(PLAY_LIST.keys())
            if len(key_list) == 0:
                i = 0
            else:
                last_key = list(PLAY_LIST.keys())[-1]
                i = 0
                for index, segment in enumerate(reversed(_playlist.segments)):
                    uri = segment.absolute_uri
                    dt = self.segment_date_time(segment)
                    if self.use_date_on_key:
                        uri_dt = (uri, dt)
                    else:
                        uri_dt = (uri, 0)
                    if last_key == uri_dt:
                        i = num_segments - index
            for m3u8_segment, key in zip(
                    _playlist.segments[i:num_segments], keys[i:num_segments]):
                added = self.add_segment(m3u8_segment, key)
                total_added += added
                if added == 0 or TERMINATE_REQUESTED:
                    break
            time.sleep(0.1)
        return total_added

    def add_segment(self, _segment, _key, _default_played=False):
        global TERMINATE_REQUESTED
        self.set_cue_status(_segment)
        uri = _segment.absolute_uri
        dt = self.segment_date_time(_segment)
        if self.use_date_on_key:
            uri_dt = (uri, dt)
        else:
            uri_dt = (uri, 0)
        if uri_dt not in PLAY_LIST.keys():
            played = _default_played
            filtered = False
            cue_status = self.set_cue_status(_segment)
            if self.file_filter is not None:
                m = self.file_filter.match(urllib.parse.unquote(uri))
                if m:
                    filtered = True
            PLAY_LIST[uri_dt] = {
                'uid': self.channel_dict['uid'],
                'played': played,
                'filtered': filtered,
                'duration': _segment.duration,
                'cue': cue_status,
                'key': _key
            }
            if _segment.duration > 0:
                # use geometric averaging of 4 items
                self.duration = (self.duration*3 + _segment.duration)/4
            try:
                if not played and not TERMINATE_REQUESTED:
                    self.logger.debug('Added {} to play queue {}'
                                      .format(uri, os.getpid()))
                    STREAM_QUEUE.put({'uri_dt': uri_dt,
                                      'data': PLAY_LIST[uri_dt]})
                    return 1
                if _default_played:
                    self.logger.debug('Skipping {} {} {}'
                                      .format(uri, os.getpid(), _segment.program_date_time))
            except ValueError as ex:
                # queue is closed, terminating
                pass

        return 0

    def remove_from_stream_queue(self, _playlist):
        global PLAY_LIST
        total_removed = 0
        if _playlist.discontinuity_sequence is not None:
            disc_index = 0
            total_index = len(_playlist.segments)
            url_list = [key[0] for key in PLAY_LIST]
            for i, segment in enumerate(reversed(_playlist.segments)):
                if segment.discontinuity:
                    disc_index = total_index - i
                    break
            for segment in _playlist.segments[disc_index:total_index]:
                s_uri = segment.absolute_uri
                s_dt = self.segment_date_time(segment)
                if self.use_date_on_key:
                    s_key = (s_uri, s_dt)
                else:
                    s_key = (s_uri, 0)

                if s_key in PLAY_LIST.keys():
                    continue
                else:
                    try:
                        i = url_list.index(s_uri)
                        PLAY_LIST = utils.rename_dict_key(list(PLAY_LIST.keys())[i], s_key, PLAY_LIST)
                    except ValueError as ex:
                        # not in list
                        pass

        for segment_key in list(PLAY_LIST.keys()):
            is_found = False
            for segment_m3u8 in _playlist.segments:
                s_uri = segment_m3u8.absolute_uri
                s_dt = self.segment_date_time(segment_m3u8)
                if self.use_date_on_key:
                    s_key = (s_uri, s_dt)
                else:
                    s_key = (s_uri, 0)
                if segment_key == s_key:
                    is_found = True
                    break
            if not is_found:
                if PLAY_LIST[segment_key]['played']:
                    del PLAY_LIST[segment_key]
                    total_removed += 1
                    self.logger.debug('Removed {} from play queue {}'
                                      .format(segment_key[0], os.getpid()))
                continue
            else:
                break
        return total_removed

    def set_cue_status(self, _segment):
        if _segment.cue_out_start:
            return 'out'
        elif _segment.cue_in:
            return 'in'
        else:
            return None


def clear_q(q):
    try:
        while True:
            q.get_nowait()
    except (Empty, ValueError, EOFError) as ex:
        pass


def clear_queues():
    # closing a multiprocessing queue with 'close' without emptying
    # it will prevent a process dependant on that queue
    # from terminating and fulfilling a 'join' if there was an entry in the queue
    # so we need to proactivley clear all queue entries instead of closing the queues
    global STREAM_QUEUE
    global OUT_QUEUE
    global IN_QUEUE
    clear_q(OUT_QUEUE)
    clear_q(STREAM_QUEUE)
    clear_q(IN_QUEUE)

def out_queue_put(data_dict):
    global OUT_QUEUE
    logger = logging.getLogger(__name__)
    for t in OUT_QUEUE_LIST:
        data_dict['thread_id'] = t
        OUT_QUEUE.put(data_dict)
        time.sleep(0.01)


def start(_config, _plugins, _m3u8_queue, _data_queue, _channel_dict, extra=None):
    """
    All items in this process must handle a socket timeout of 5.0
    """
    global IN_QUEUE
    global STREAM_QUEUE
    global OUT_QUEUE
    global TERMINATE_REQUESTED
    logger = None
    try:
        utils.logging_setup(_plugins.config_obj.data)
        logger = logging.getLogger(__name__)
        socket.setdefaulttimeout(5.0)
        IN_QUEUE = _m3u8_queue
        STREAM_QUEUE = Queue(maxsize=MAX_STREAM_QUEUE_SIZE)
        OUT_QUEUE = _data_queue
        p_m3u8 = M3U8Process(_config, _plugins, _channel_dict)
        while not TERMINATE_REQUESTED:
            try:
                q_item = IN_QUEUE.get()
                if q_item['uri'] == 'terminate':
                    OUT_QUEUE_LIST.remove(q_item['thread_id'])
                    if not len(OUT_QUEUE_LIST):
                        TERMINATE_REQUESTED = True
                        clear_queues()
                    else:
                        clear_q(OUT_QUEUE)
                    time.sleep(0.01)

                    # clear queues in case queues are full (eg VOD) with queue.put stmts blocked 
                    # p_m3u8 & m3u8_q then see TERMINATE_REQUESTED and exit including stopping ffmpeg
                    OUT_QUEUE.put({
                        'thread_id': q_item['thread_id'],
                        'uri': 'terminate',
                        'data': None,
                        'stream': None,
                        'atsc': None})
                    time.sleep(0.01)
                    if not len(OUT_QUEUE_LIST):
                        p_m3u8.join()
                elif q_item['uri'] == 'status':
                    if q_item['thread_id'] not in OUT_QUEUE_LIST:
                        OUT_QUEUE_LIST.append(q_item['thread_id'])
                        logger.debug('Adding client thread {} to m3u8 queue list'.format(q_item['thread_id']))
                    STREAM_QUEUE.put({'uri_dt': 'status'})
                    logger.debug('Sending Status request to stream queue {}'.format(os.getpid()))
                    time.sleep(0.01)
                else:
                    logger.debug('UNKNOWN m3u8 queue request {}'.format(q_item['uri']))
            except (KeyboardInterrupt, EOFError, TypeError, ValueError) as ex:
                TERMINATE_REQUESTED = True
                try:
                    clear_queues()
                    out_queue_put({
                        'uri': 'terminate',
                        'data': None,
                        'stream': None,
                        'atsc': None})
                    time.sleep(0.01)
                    STREAM_QUEUE.put({'uri_dt': 'terminate'})
                    time.sleep(0.1)
                except (EOFError, TypeError, ValueError) as ex:
                    pass
                logger.debug('4 m3u8_queue process terminated {}'.format(os.getpid()))
                sys.exit()
        clear_queues()
        logger.debug('1 m3u8_queue process terminated {}'.format(os.getpid()))
        sys.exit()
    except Exception as ex:
        logger.exception('{}'.format(
            'UNEXPECTED EXCEPTION startup'))
        TERMINATE_REQUESTED = True
        logger.debug('3 m3u8_queue process terminated {}'.format(os.getpid()))
        sys.exit()
    except KeyboardInterrupt as ex:
        TERMINATE_REQUESTED = True
        logger.debug('2 m3u8_queue process terminated {}'.format(os.getpid()))
        sys.exit()
