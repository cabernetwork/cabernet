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

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from threading import Thread

import lib.common.utils as utils
from lib.common.decorators import handle_url_except
import lib.common.socket_timeout as socket_timeout
from lib.db.db_channels import DBChannels
from lib.streams.atsc import ATSCMsg
from lib.streams.video import Video
from .pts_validation import PTSValidation
from .pts_resync import PTSResync

class M3U8Queue:
    """
    This runs as an independent process (one per stream) to get and process the 
    data stream as fast as possible and return it to the tuner web server for 
    output to the client.
    """
    is_stuck = None

    def __init__(self, _config, _m3u8_queue, _data_queue, _channel_dict):
        self.logger = logging.getLogger(__name__)
        self.config = _config
        self.m3u8_queue = _m3u8_queue
        self.data_queue = _data_queue
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

    @handle_url_except(timeout=1.0)
    def get_uri_data(self, _uri):
        header = {'User-agent': utils.DEFAULT_USER_AGENT}
        req = urllib.request.Request(_uri, headers=header)
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            x = resp.read()
        return x
    
    def process_queue(self):
        try:
            while True:
                queue_item = self.m3u8_queue.get()
                if queue_item['uri'] == 'terminate':
                    self.request_terminate = True
                    self.pts_resync.terminate()
                    self.clear_queues()
                    break
                elif queue_item['uri'] == 'status':
                    self.data_queue.put({'uri': 'running',
                        'data': None})
                    continue
                self.process_m3u8_item(queue_item)
                
        except KeyboardInterrupt:
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
        if len(self.key_list.keys()) > 10:
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
        uri = _queue_item['uri']
        data = _queue_item['data']
        if data['filtered']:
            self.data_queue.put({'uri': uri,
                'data': self.get_stream_from_atsc()})
        else:
            self.video.data = self.get_uri_data(uri)
            if self.video.data is None:
                return
            if not self.decrypt_stream(data):
                # terminate if stream is not decryptable
                self.data_queue.put({'uri': 'terminate',
                    'data': None})
                return
            if not self.is_pts_valid():
                return
            self.pts_resync.resequence_pts(self.video)
            if self.video.data is None:
                self.data_queue.put({'uri': uri,
                    'data': self.video.data})
                return
            self.atsc_processing()
            self.data_queue.put({'uri': uri,
                'data': self.video.data})

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
        self.m3u8_queue.close()
        self.data_queue.close()


def start(_config, _m3u8_queue, _data_queue, _channel_dict, extra=None):
    socket_timeout.DEFAULT_SOCKET_TIMEOUT = 1.0
    socket_timeout.reset_timeout()
    q = M3U8Queue(_config, _m3u8_queue, _data_queue, _channel_dict)
    q.process_queue()
