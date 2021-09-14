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
import sys
import time
import urllib.request

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from threading import Thread

from lib.db.db_channels import DBChannels
from lib.streams.atsc import ATSCMsg
from lib.streams.video import Video
from .pts_validation import PTSValidation
from .pts_resync import PTSResync


class M3U8Queue:
    """
    URIs can hang causing delays.  This queue get the data from the uri request
    as fast as possible and places the data on a queue.
    """

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


    def process_queue(self):
        try:
            while True:
                queue_item = self.m3u8_queue.get()
                if queue_item['uri'] == 'terminate':
                    self.pts_resync.terminate()
                    self.clear_queues()
                    break
                self.logger.debug('Processing next stream {}'.format(queue_item['uri']))
                self.process_m3u8_item(queue_item)
                self.logger.debug('Finished processing stream {}'.format(queue_item['uri']))
        except KeyboardInterrupt:
            self.pts_resync.terminate()
            self.clear_queues()
            sys.exit()

    def process_m3u8_item(self, _queue_item):
        uri = _queue_item['uri']
        data = _queue_item['data']
        if data['filtered']:
            self.data_queue.put({'uri': uri,
                'data': self.get_stream_from_atsc()})
        else:
            self.video.data = None
            count = 5
            while count > 0:
                count -= 1
                try:
                    req = urllib.request.Request(uri)
                    with urllib.request.urlopen(req) as resp:
                        self.video.data = resp.read()
                        break
                except http.client.IncompleteRead as e:
                    self.logger.info('Provider gave partial stream, trying again. {}'
                        .format(e, len(e.partial)))
                    self.video.data = e.partial
                    time.sleep(0.5)
                except urllib.error.URLError as e:
                    self.logger.info('HTTP Error, trying again. {}'.format(e))
                except ConnectionResetError as e:
                    self.logger.info('Connection Error, trying again. {}'.format(e))
            if not self.video.data:
                self.logger.warning(f'Segment {uri} not available. Skipping..')
                return


            if data['key']:
                i = 3
                while i > 0:
                    try:
                        if data['key']['uri']:
                            key_data = None
                            req = urllib.request.Request(data['key']['uri'])
                            with urllib.request.urlopen(req) as resp:
                                key_data = resp.read()
                                    
                            if data['key']['iv'].startswith('0x'):
                                iv = bytearray.fromhex(data['key']['iv'][2:])
                            else:
                                iv = bytearray.fromhex(data['key']['iv'])
                            cipher = Cipher(algorithms.AES(key_data), modes.CBC(iv), default_backend())
                            decryptor = cipher.decryptor()
                            self.video.data = decryptor.update(self.video.data)
                        break
                    except urllib.error.URLError as e:
                        self.logger.info('Key Exception caught, retrying: {}'.format(e))
                        i -= 1

            if not self.is_pts_valid():
                return
            self.pts_resync.resequence_pts(self.video)
            if self.video.data is None:
                self.data_queue.put({'uri': uri,
                    'data': self.video.data})
                return

            if self.atsc is None:
                self.initialized_psi = True
                p_list = self.atsc_msg.extract_psip(self.video.data)
                if len(p_list) != 0:
                    self.atsc = p_list
            elif not self.initialized_psi:
                self.initialized_psi = True
                p_list = self.atsc_msg.extract_psip(self.video.data)
                for i in range(len(p_list)):
                    if p_list[i][4:] != self.atsc[i][4:]:
                        self.atsc = p_list
                        self.channel_dict['atsc'] = p_list
                        self.db_channels.update_channel_atsc(
                            self.channel_dict)
                        break

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


def start(_config, _m3u8_queue, _data_queue, _channel_dict):
    q = M3U8Queue(_config, _m3u8_queue, _data_queue, _channel_dict)
    q.process_queue()
