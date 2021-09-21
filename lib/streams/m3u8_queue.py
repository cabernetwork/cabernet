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

import http
import logging
import os
import socket
import sys
import time
import urllib.request
from collections import OrderedDict
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from multiprocessing import Queue
from threading import Thread

import lib.common.utils as utils
import lib.m3u8 as m3u8
from lib.common.decorators import handle_url_except
from lib.common.decorators import handle_json_except
from lib.db.db_channels import DBChannels
from lib.streams.atsc import ATSCMsg
from lib.streams.video import Video
from .pts_validation import PTSValidation
from .pts_resync import PTSResync


PLAY_LIST = OrderedDict()
IN_QUEUE = None
STREAM_QUEUE = None
OUT_QUEUE = None
TERMINATE_REQUESTED = False

class M3U8Queue(Thread):
    """
    This runs as an independent process (one per stream) to get and process the 
    data stream as fast as possible and return it to the tuner web server for 
    output to the client.
    """
    is_stuck = None

    def __init__(self, _config, _channel_dict):
        Thread.__init__(self)
        self.logger = logging.getLogger(__name__)
        self.config = _config
        self.namespace = _channel_dict['namespace'].lower()
        self.pts_validation = None
        self.initialized_psi = False
        self.atsc_msg = ATSCMsg()
        self.channel_dict = _channel_dict
        if self.config[self.namespace]['player-enable_pts_filter']:
            self.pts_validation = PTSValidation(_config, _channel_dict)
        self.video = Video(self.config)
        self.atsc = _channel_dict['atsc']
        self.db_channels = DBChannels(_config)
        self.pts_resync = PTSResync(_config, self.namespace, _channel_dict['uid'])
        self.key_list = {}
        self.start()

    @handle_url_except(timeout=1.0)
    def get_uri_data(self, _uri):
        header = {'User-agent': utils.DEFAULT_USER_AGENT}
        req = urllib.request.Request(_uri, headers=header)
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            x = resp.read()
        return x
    
    def run(self):
        global OUT_QUEUE
        global STREAM_QUEUE
        try:
            while not TERMINATE_REQUESTED:
                queue_item = STREAM_QUEUE.get()
                if queue_item['uri'] == 'terminate':
                    self.pts_resync.terminate()
                    self.clear_queues()
                    time.sleep(0.01)
                    break
                elif queue_item['uri'] == 'status':
                    OUT_QUEUE.put({'uri': 'running',
                        'data': None})
                    time.sleep(0.01)
                    continue
                self.process_m3u8_item(queue_item)
                
        except (KeyboardInterrupt, EOFError):
            self.pts_resync.terminate()
            self.clear_queues()
            sys.exit()

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
                if _data['key']['iv'].startswith('0x'):
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
        if self.atsc is None:
            p_list = self.atsc_msg.extract_psip(self.video.data)
            if len(p_list) != 0:
                self.atsc = p_list
                self.channel_dict['atsc'] = p_list
                self.db_channels.update_channel_atsc(
                    self.channel_dict)
                self.initialized_psi = True

        elif not self.initialized_psi:
            p_list = self.atsc_msg.extract_psip(self.video.data)
            for i in range(len(p_list)):
                if p_list[i][4:] != self.atsc[i][4:]:
                    self.atsc = p_list
                    self.channel_dict['atsc'] = p_list
                    self.db_channels.update_channel_atsc(
                        self.channel_dict)
                    self.initialized_psi = True
                    break

    def process_m3u8_item(self, _queue_item):
        global TERMINATE_REQUESTED
        global PLAY_LIST
        global OUT_QUEUE
        uri = _queue_item['uri']
        data = _queue_item['data']
        if data['filtered']:
            OUT_QUEUE.put({'uri': uri,
                'data': data,
                'stream': self.get_stream_from_atsc()})
            PLAY_LIST[uri]['played'] = True
            time.sleep(0.01)
        else:
            self.video.data = self.get_uri_data(uri)
            if self.video.data is None:
                PLAY_LIST[uri]['played'] = True
                return
            if not self.decrypt_stream(data):
                # terminate if stream is not decryptable
                OUT_QUEUE.put({'uri': 'terminate',
                    'data': data,
                    'stream': None})
                TERMINATE_REQUESTED = True
                self.pts_resync.terminate()
                self.clear_queues()
                PLAY_LIST[uri]['played'] = True
                time.sleep(0.01)
                return
            if not self.is_pts_valid():
                PLAY_LIST[uri]['played'] = True
                return
            self.pts_resync.resequence_pts(self.video)
            if self.video.data is None:
                OUT_QUEUE.put({'uri': uri,
                    'data': data,
                    'stream': self.video.data})
                PLAY_LIST[uri]['played'] = True
                time.sleep(0.01)
                return
            self.atsc_processing()
            OUT_QUEUE.put({'uri': uri,
                'data': data,
                'stream': self.video.data})
            PLAY_LIST[uri]['played'] = True
            time.sleep(0.01)

                

    def is_pts_valid(self):
        if self.pts_validation is None:
            return True
        before = len(self.video.data)
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

    def clear_queues(self):
        global STREAM_QUEUE
        global OUT_QUEUE
        global IN_QUEUE
        STREAM_QUEUE.close()
        OUT_QUEUE.close()
        IN_QUEUE.close()


class M3U8Process(Thread):
    """
    process for managing the list of m3u8 data sections.
    Includes managing the processing queue and providing
    the M3U8Queue with what to process.
    """
    def __init__(self, _config, _plugins, _channel_dict):
        Thread.__init__(self)
        self.logger = logging.getLogger(__name__)
        global IN_QUEUE
        global OUT_QUEUE

        self.config = _config
        self.channel_dict = _channel_dict
        self.last_refresh = time.time()
        self.plugins = _plugins
        queue_item = IN_QUEUE.get()
        self.stream_uri = self.get_stream_uri()
        if not self.stream_uri:
            self.logger.warning('Unknown Channel {}'.format(_channel_dict['uid']))
            OUT_QUEUE.put({'uri': 'terminate'})
            time.sleep(0.01)
        else:
            OUT_QUEUE.put({'uri': 'running'})
            time.sleep(0.01)
        self.is_running = True
        self.duration = 6
        self.m3u8_q = M3U8Queue(_config, _channel_dict)
        self.start()


    def run(self):
        global TERMINATE_REQUESTED
        self.logger.debug('M3U8: {} {}'.format(self.stream_uri, os.getpid()))
        self.file_filter = None
        if self.config[self.channel_dict['namespace'].lower()]['player-enable_url_filter']:
            stream_filter = self.config[self.channel_dict['namespace'].lower()]['player-url_filter']
            if stream_filter is not None:
                self.file_filter = re.compile(stream_filter)
            else:
                self.logger.warning('[{}]][player-enable_url_filter]'
                    ' enabled but [player-url_filter] not set'
                    .format(self.channel_dict['namespace'].lower()))
        while not TERMINATE_REQUESTED:
            added = 0
            removed = 0
            self.logger.debug('Reloading m3u8 stream queue {}'.format(os.getpid()))
            playlist = self.get_m3u8_data(self.stream_uri)
            if playlist is None:
                self.logger.debug('Playlist is none, terminating stream')
                break
            removed += self.remove_from_stream_queue(playlist)
            added += self.add_to_stream_queue(playlist)
            if added == 0 and self.duration > 0:
                self.sleep(7)
            elif self.plugins.plugins[self.channel_dict['namespace']].plugin_obj \
                    .is_time_to_refresh_ext(self.last_refresh, self.channel_dict['instance']):
                self.stream_uri = self.get_stream_uri()
                self.logger.debug('M3U8: {} {}' \
                    .format(self.stream_uri, os.getpid()))
                self.last_refresh = time.time()
                self.sleep(3)
            else:
                self.sleep(7)
        self.terminate()

    def sleep(self, _time):
        for i in range(_time):
            if not TERMINATE_REQUESTED:
                time.sleep(self.duration * 0.1)

    def terminate(self):
        global STREAM_QUEUE
        try:
            STREAM_QUEUE.put({'uri': 'terminate'})
            time.sleep(0.01)
        except ValueError:
            pass

    def get_stream_uri(self):
        return self.plugins.plugins[self.channel_dict['namespace']] \
            .plugin_obj.get_channel_uri_ext(self.channel_dict['uid'], self.channel_dict['instance'])

    @handle_url_except()
    @handle_json_except
    def get_m3u8_data(self, _uri):
        # it sticks here.  Need to find a work around for the socket.timeout per process
        return m3u8.load(_uri,
            headers={'User-agent': utils.DEFAULT_USER_AGENT})

    def add_to_stream_queue(self, _playlist):
        global PLAY_LIST
        global STREAM_QUEUE
        total_added = 0
        if _playlist.keys != [None]:
            keys = [{"uri": key.absolute_uri, "method": key.method, "iv": key.iv} \
                for key in _playlist.keys if key]
        else:
            keys = [None for i in range(0, len(_playlist.segments))]
        for m3u8_segment, key in zip(_playlist.segments, keys):
            uri = m3u8_segment.absolute_uri
            if uri not in PLAY_LIST.keys():
                played = False
                filtered = False
                if self.file_filter is not None:
                    m = self.file_filter.match(urllib.parse.unquote(uri))
                    if m:
                        filtered = True
                PLAY_LIST[uri] = {
                    'uid': self.channel_dict['uid'],
                    'played': played,
                    'filtered': filtered,
                    'duration': m3u8_segment.duration,
                    'key': key
                }
                if m3u8_segment.duration > 0:
                    self.duration = m3u8_segment.duration
                self.logger.debug('Added {} to play queue {}' \
                    .format(uri, os.getpid()))
                total_added += 1
                try:
                    STREAM_QUEUE.put({'uri': uri, 
                        'data': PLAY_LIST[uri]})
                except ValueError:
                    # queue is closed, terminating
                    break
                time.sleep(0.01)
                # provide some time for the queue to work
                if total_added > 1:
                    return total_added
        return total_added

    def remove_from_stream_queue(self, _playlist):
        global PLAY_LIST
        total_removed = 0
        for segment_key in list(PLAY_LIST.keys()):
            is_found = False
            for segment_m3u8 in _playlist.segments:
                uri = segment_m3u8.absolute_uri
                if segment_key == uri:
                    is_found = True
                    break
            if not is_found:
                if PLAY_LIST[segment_key]['played']:
                    del PLAY_LIST[segment_key]
                    total_removed += 1
                    self.logger.debug('Removed {} from play queue {}' \
                        .format(segment_key, os.getpid()))
                continue
            else:
                break
        return total_removed


def start(_config, _plugins, _m3u8_queue, _data_queue, _channel_dict, extra=None):
    """
    All items in this process must handle a socket timeout of 1.0
    """
    global IN_QUEUE
    global STREAM_QUEUE
    global OUT_QUEUE
    global TERMINATE_REQUESTED
    socket.setdefaulttimeout(1.0)
    IN_QUEUE = _m3u8_queue
    STREAM_QUEUE = Queue()
    OUT_QUEUE = _data_queue
    p_m3u8 = M3U8Process(_config, _plugins, _channel_dict)
    logger = logging.getLogger(__name__)
    while not TERMINATE_REQUESTED:
        try:
            q_item = IN_QUEUE.get()
            if q_item['uri'] == 'terminate':
                TERMINATE_REQUESTED = True
                time.sleep(1)
            else:
                logger.debug('UNKNOWN m3u8 queue request')
        except (KeyboardInterrupt, EOFError):
            TERMINATE_REQUESTED = True
            STREAM_QUEUE.put({'uri': 'terminate'})
            time.sleep(1.0)
            sys.exit()
