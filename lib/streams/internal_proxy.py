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
import errno
import http
import os
import re
import signal
import socket
import threading
import time
import urllib.request
from collections import OrderedDict
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from multiprocessing import Queue, Process
from queue import Empty
from threading import Thread

import lib.common.socket_timeout as socket_timeout
import lib.common.exceptions as exceptions
import lib.common.utils as utils
import lib.m3u8 as m3u8
import lib.streams.m3u8_queue as m3u8_queue
from lib.common.decorators import handle_url_except
from lib.common.decorators import handle_json_except
from lib.streams.video import Video
from lib.streams.atsc import ATSCMsg
from lib.db.db_config_defn import DBConfigDefn
from lib.db.db_channels import DBChannels
from lib.clients.web_handler import WebHTTPHandler
from .stream import Stream


class InternalProxy(Stream):

    is_m3u8_starting = 0

    def __init__(self, _plugins, _hdhr_queue):
        self.last_refresh = None
        self.channel_dict = None
        self.wfile = None
        self.file_filter = None
        self.duration = 6
        self.last_ts_filename = ''
        super().__init__(_plugins, _hdhr_queue)
        self.config = self.plugins.config_obj.data
        self.db_configdefn = DBConfigDefn(self.config)
        self.db_channels = DBChannels(self.config)
        self.video = Video(self.config)
        self.atsc = ATSCMsg()
        self.initialized_psi = False
        self.in_queue = Queue()
        self.out_queue = Queue(maxsize=2)
        self.terminate_queue = None
        self.tc_match = re.compile( r'^.+[^\d]+(\d*)\.ts' )
        
    def terminate(self, *args):
        try:
            while True:
                self.in_queue.get_nowait()
        except (Empty, EOFError):
            pass
        self.in_queue.put({'uri': 'terminate'})
        time.sleep(0.2)
        self.t_m3u8.terminate()
        self.t_m3u8.join()
        time.sleep(0.5)
        self.t_m3u8 = None
        self.clear_queues()

    @handle_url_except(timeout=14.0)
    @handle_json_except
    def get_m3u8_data(self, _uri):
        return m3u8.load(_uri,
            headers={'User-agent': utils.DEFAULT_USER_AGENT})

    def stream(self, _channel_dict, _wfile, _terminate_queue):
        """
        Processes m3u8 interface without using ffmpeg
        """
        self.config = self.db_configdefn.get_config()
        self.channel_dict = _channel_dict
        self.wfile = _wfile
        self.terminate_queue = _terminate_queue
        self.start_m3u8_queue_process()
        play_queue_dict = OrderedDict()
        self.last_refresh = time.time()
        stream_uri = self.get_stream_uri(_channel_dict)
        if not stream_uri:
            self.logger.warning('Unknown Channel {}'.format(_channel_dict['uid']))
            self.terminate()
            return
        self.logger.debug('{} M3U8: {}'.format(self.t_m3u8.pid, stream_uri))
        self.file_filter = None
        if self.config[_channel_dict['namespace'].lower()]['player-enable_url_filter']:
            stream_filter = self.config[_channel_dict['namespace'].lower()]['player-url_filter']
            if stream_filter is not None:
                self.file_filter = re.compile(stream_filter)
            else:
                self.logger.warning('[{}]][player-enable_url_filter]'
                    ' enabled but [player-url_filter] not set'
                    .format(_channel_dict['namespace'].lower()))
        while True:
            try:
                self.check_termination()
                added = 0
                removed = 0
                self.logger.debug('Reloading m3u8 stream {}'.format(self.t_m3u8.pid))
                playlist = self.get_m3u8_data(stream_uri)
                if playlist is None:
                    break
                removed += self.remove_from_stream_queue(playlist, play_queue_dict)
                added += self.add_to_stream_queue(playlist, play_queue_dict)
                if added == 0 and self.duration > 0:
                    time.sleep(self.duration * 0.7)
                elif self.plugins.plugins[_channel_dict['namespace']].plugin_obj \
                        .is_time_to_refresh_ext(self.last_refresh, _channel_dict['instance']):
                    stream_uri = self.get_stream_uri(_channel_dict)
                    self.logger.debug('{} M3U8: {}'.format(self.t_m3u8.pid, stream_uri))
                    self.last_refresh = time.time()
                self.play_queue(play_queue_dict)
            except IOError as ex:
                # Check we hit a broken pipe when trying to write back to the client
                if ex.errno in [errno.EPIPE, errno.ECONNABORTED, errno.ECONNRESET, errno.ECONNREFUSED]:
                    # Normal process.  Client request end of stream
                    self.logger.info('Connection dropped by end device {} {}'.format(ex, self.t_m3u8.pid))
                    break
                else:
                    self.logger.error('{}{} {}'.format(
                        'UNEXPECTED EXCEPTION=', ex, self.t_m3u8.pid))
                    raise
            except exceptions.CabernetException as ex:
                self.logger.info('{} {}'.format(ex, self.t_m3u8.pid))
                break
        self.terminate()

    def check_termination(self):
        if not self.terminate_queue.empty():
            raise exceptions.CabernetException("Termination Requested")

    def clear_queues(self):
        self.in_queue.close()
        self.out_queue.close()        
    
    def add_to_stream_queue(self, _playlist, _play_queue_dict):
        total_added = 0
        if _playlist.keys != [None]:
            keys = [{"uri": key.absolute_uri, "method": key.method, "iv": key.iv} \
                for key in _playlist.keys if key]
        else:
            keys = [None for i in range(0, len(_playlist.segments))]
        for m3u8_segment, key in zip(_playlist.segments, keys):
            uri = m3u8_segment.absolute_uri
            if uri not in _play_queue_dict.keys():
                played = False
                filtered = False
                if self.file_filter is not None:
                    m = self.file_filter.match(urllib.parse.unquote(uri))
                    if m:
                        filtered = True
                _play_queue_dict[uri] = {
                    'uid': self.channel_dict['uid'],
                    'played': played,
                    'filtered': filtered,
                    'duration': m3u8_segment.duration,
                    'key': key
                }
                self.logger.debug(f"Added {uri} to play queue {self.t_m3u8.pid}")
                total_added += 1
                self.in_queue.put({'uri': uri, 
                    'data': _play_queue_dict[uri]})
                # provide some time for the queue to work
                self.check_termination()
                if total_added > 1:
                    return total_added
                time.sleep(0.5)
        return total_added

    def remove_from_stream_queue(self, _playlist, _play_queue_dict):
        total_removed = 0
        for segment_key in list(_play_queue_dict.keys()):
            is_found = False
            for segment_m3u8 in _playlist.segments:
                uri = segment_m3u8.absolute_uri
                if segment_key == uri:
                    is_found = True
                    break
            if not is_found:
                if _play_queue_dict[segment_key]['played']:
                    del _play_queue_dict[segment_key]
                    total_removed += 1
                    self.logger.debug(f"Removed {segment_key} from play queue {self.t_m3u8.pid}")
                continue
            else:
                break
        return total_removed

    def play_queue(self, _play_queue_dict):
        num_served = 0
        while not self.out_queue.empty() and num_served < 2:
            out_queue_item = self.out_queue.get()
            uri = out_queue_item['uri']
            if uri == 'terminate':
                raise exceptions.CabernetException('m3u8 queue termination requested, aborting stream {}' \
                    .format(self.t_m3u8.pid))
            data = _play_queue_dict[uri]
            if data['filtered']:
                self.logger.debug(f"Filtered, Sending ATSC Msg {self.t_m3u8.pid}")
                self.write_buffer(out_queue_item['data'])
            else:
                self.video.data = out_queue_item['data']
                if self.video.data is not None:
                    if self.config['stream']['update_sdt']:
                        self.atsc.update_sdt_names(self.video,
                            self.channel_dict['namespace'].encode(),
                            self.set_service_name(self.channel_dict).encode())
                    self.duration = data['duration']
                    uri_decoded = urllib.parse.unquote(uri)
                    if self.check_ts_counter(uri_decoded):
                        self.logger.info(f"Serving {self.t_m3u8.pid} {uri_decoded}  ({self.duration}s) ({len(self.video.data)}B)")
                        self.write_buffer(self.video.data)
                    else:
                        self.write_atsc_msg()
                else:
                    self.write_atsc_msg()
                num_served += 1
            data['played'] = True
            self.check_termination()
            time.sleep(0.5 * self.duration)
        self.video.terminate()

    def write_buffer(self, _data):
        socket_timeout.add_timeout(20.0)
        try:
            x = self.wfile.write(_data)
        except socket.timeout as ex:
            socket_timeout.del_timeout(20.0)
            raise
        except IOError as e:
            socket_timeout.del_timeout(20.0)
            raise
        socket_timeout.del_timeout(20.0)
        return x

    def write_atsc_msg(self):
        if self.channel_dict['atsc'] is None:
            self.logger.debug(f"No video data, Sending Empty ATSC Msg {self.t_m3u8.pid}")
            self.write_buffer(
                self.atsc.format_video_packets())
        else:
            self.logger.debug(f"No video data, Sending default ATSC Msg for channel {self.t_m3u8.pid}")
            self.write_buffer(
                self.atsc.format_video_packets(
                self.channel_dict['atsc']))

    def get_ts_counter(self, _uri):
        m = self.tc_match.findall(_uri)
        if len(m) == 0:
            return '', 0
        else:
            self.logger.debug('ts_counter {} {}'.format(m, _uri))
            x_tuple = m[len(m)-1]
            if len(x_tuple) == 0:
                x_tuple = (_uri, '0')
            else:
                x_tuple = (_uri, x_tuple)
            return x_tuple

    def check_ts_counter(self, _uri):
        """
        Providers sometime add the same stream section back into the list.
        This methods catches this and informs the caller that it should be ignored.
        """
        if _uri == self.last_ts_filename:
            self.logger.warning('TC Counter Same section being transmitted, ignoring uri: {} {}' \
                .format(_uri, self.t_m3u8.pid))
            return False
        self.last_ts_filename = _uri
        return True

    def start_m3u8_queue_process(self):
        """
        Python sometimes starts a process where it is not connected to the parent,
        so the queues do not interact.  The process is killed and restarted
        until python can do this correctly.
        """
        is_running = False
        tries = 0
        while True:
            while InternalProxy.is_m3u8_starting != 0:
                time.sleep(0.1)
            InternalProxy.is_m3u8_starting = threading.get_ident()
            time.sleep(0.01)
            if InternalProxy.is_m3u8_starting == threading.get_ident():
                break
        while not is_running:
            # Process is not thread safe.  Must do the same target, one at a time.
            self.t_m3u8 = Process(target=m3u8_queue.start, args=(
                self.config, self.in_queue, self.out_queue, self.channel_dict,))
            self.t_m3u8.start()
            self.in_queue.put({'uri': 'status'})
            while self.out_queue.empty() and tries < 5:
                tries += 1
                time.sleep(0.1)
            if tries > 4:
                while not self.in_queue.empty():
                    try:
                        time.sleep(0.1)
                        self.in_queue.get_nowait()
                    except (Empty, EOFError):
                        pass
                self.t_m3u8.terminate()
                self.t_m3u8.join()
                tries = 0
                time.sleep(0.3)
            else:
                status = self.out_queue.get()
                is_running = True
        InternalProxy.is_m3u8_starting = False
