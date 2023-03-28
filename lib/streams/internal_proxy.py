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
import errno
import os
import re
import socket
import threading
import time
import urllib.parse
from multiprocessing import Queue, Process
from queue import Empty

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

MAX_OUT_QUEUE_SIZE = 60
IDLE_COUNTER_MAX = 60   # time in seconds beyond any filtered or serving packet to terminate the stream
STARTUP_IDLE_COUNTER = 40 # time to wait for an initial stream
# code assumes a timeout response in TVH of 15 or higher.

class InternalProxy(Stream):
    is_m3u8_starting = 0

    def __init__(self, _plugins, _hdhr_queue):
        global MAX_OUT_QUEUE_SIZE
        self.last_refresh = None
        self.channel_dict = None
        self.wfile = None
        self.file_filter = None
        self.t_m3u8 = None
        self.duration = 6
        self.last_ts_filename = ''
        super().__init__(_plugins, _hdhr_queue)
        self.db_configdefn = DBConfigDefn(self.config)
        self.db_channels = DBChannels(self.config)
        self.video = Video(self.config)
        self.atsc = ATSCMsg()
        self.initialized_psi = False
        self.in_queue = Queue()
        self.out_queue = Queue(maxsize=MAX_OUT_QUEUE_SIZE)
        self.terminate_queue = None
        self.tc_match = re.compile(r'^.+\D+(\d*)\.ts')
        self.idle_counter = 0
        # last time the idle counter was reset
        self.last_reset_time = datetime.datetime.now()
        self.last_atsc_msg = 0
        self.filter_counter = 0
        self.is_starting = True
        self.cue = False

    def terminate(self, *args):
        try:
            while not self.in_queue.empty():
                self.in_queue.get()
        except (Empty, EOFError):
            pass
        self.in_queue.put({'uri': 'terminate'})
        time.sleep(0.2)
        # since t_m3u8 has been told to terminate, clear the
        # out queue and then wait for t_m3u8, so it can clean up ffmpeg
        self.t_m3u8.join(timeout=15)
        if self.t_m3u8.is_alive():
            # this is not likely but if t_m3u8 does not self terminate then force it to terminate
            self.logger.debug(
                't_m3u8 failed to self terminate. Forcing it to terminate {}'
                .format(self.t_m3u8.pid))
            self.t_m3u8.terminate()
        time.sleep(0.5)
        self.t_m3u8 = None
        self.clear_queues()

    @handle_url_except()
    @handle_json_except
    def get_m3u8_data(self, _uri):
        # it sticks here.  Need to find a workaround for the socket.timeout per process
        return m3u8.load(_uri,
                         headers={'User-agent': utils.DEFAULT_USER_AGENT})

    def stream(self, _channel_dict, _wfile, _terminate_queue):
        """
        Processes m3u8 interface without using ffmpeg
        """
        self.config = self.db_configdefn.get_config()
        self.channel_dict = _channel_dict
        if not self.start_m3u8_queue_process():
            self.terminate()
            return
        self.wfile = _wfile
        self.terminate_queue = _terminate_queue
        while True:
            try:
                self.check_termination()
                self.play_queue()
                if not self.t_m3u8.is_alive():
                    break
            except IOError as ex:
                # Check we hit a broken pipe when trying to write back to the client
                if ex.errno in [errno.EPIPE, errno.ECONNABORTED, errno.ECONNRESET, errno.ECONNREFUSED]:
                    # Normal process.  Client request end of stream
                    self.logger.info(
                        'Connection dropped by end device {} {}'
                        .format(ex, self.t_m3u8.pid))
                    break
                else:
                    self.logger.error('{}{} {} {}'.format(
                        'UNEXPECTED EXCEPTION=', ex, self.t_m3u8.pid, socket.getdefaulttimeout()))
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

    def play_queue(self):
        global MAX_OUT_QUEUE_SIZE
        global IDLE_COUNTER_MAX

        if not self.cue:
            self.update_idle_counter()
        if self.is_starting and self.idle_counter > STARTUP_IDLE_COUNTER:
            # we need to terminate this feed.  Some providers require a 
            # retry in order to make it work.
            self.idle_counter = 0
            self.last_reset_time = datetime.datetime.now()
            self.last_atsc_msg = 0
            self.logger.info(
                '1 Provider has not started playing the stream. Terminating the connection {}'
                .format(self.t_m3u8.pid))
            raise exceptions.CabernetException(
                '2 Provider has not started playing the stream. Terminating the connection {}'
                .format(self.t_m3u8.pid))
        elif self.idle_counter > self.filter_counter + IDLE_COUNTER_MAX:
            self.idle_counter = 0
            self.last_atsc_msg = 0
            self.last_reset_time = datetime.datetime.now()
            self.filter_counter = 0
            self.logger.info(
                '1 Provider has stop playing the stream. Terminating the connection {}'
                .format(self.t_m3u8.pid))
            raise exceptions.CabernetException(
                '2 Provider has stop playing the stream. Terminating the connection {}'
                .format(self.t_m3u8.pid))
        elif self.idle_counter > self.last_atsc_msg+6 \
            and self.is_starting:
                self.last_atsc_msg = self.idle_counter
                self.write_atsc_msg()
        elif self.idle_counter > self.last_atsc_msg+14:
            self.last_atsc_msg = self.idle_counter
            self.logger.debug('1 Requesting status from m3u8_queue {}'.format(self.t_m3u8.pid))
            self.in_queue.put({'uri': 'status'})
            if not self.is_starting \
                    and self.config[self.channel_dict['namespace'].lower()] \
                    ['player-send_atsc_keepalive']:
                self.write_atsc_msg()
        while True:
            try:
                out_queue_item = self.out_queue.get(timeout=1)
            except Empty:
                break
            if out_queue_item['atsc'] is not None:
                self.channel_dict['atsc'] = out_queue_item['atsc']
                self.db_channels.update_channel_atsc(
                    self.channel_dict)
            uri = out_queue_item['uri']
            if uri == 'terminate':
                raise exceptions.CabernetException(
                    'm3u8 queue termination requested, aborting stream {}'
                    .format(self.t_m3u8.pid))
            elif uri == 'running':
                self.logger.debug('1 Status of Running returned from m3u8_queue {}'.format(self.t_m3u8.pid))
                continue
            data = out_queue_item['data']
            if data['cue'] == 'in':
                self.cue = False
                self.logger.debug('Turning M3U8 cue to False')
            elif data['cue'] == 'out':
                self.cue = True
                self.logger.debug('Turning M3U8 cue to True')
            if data['filtered']:
                self.filter_counter = self.idle_counter
                self.logger.info('Filtered Msg {} {}'.format(self.t_m3u8.pid, urllib.parse.unquote(uri)))
                self.update_tuner_status('Filtered')
                # self.write_buffer(out_queue_item['stream'])
                if self.is_starting:
                    self.is_starting = False
                    self.write_atsc_msg()
                    self.logger.debug('2 Requesting status from m3u8_queue {}'.format(self.t_m3u8.pid))
                    self.in_queue.put({'uri': 'status'})
                time.sleep(0.5)
            else:
                self.video.data = out_queue_item['stream']
                if self.video.data is not None:
                    self.idle_counter = 0
                    self.last_atsc_msg = 0
                    self.last_reset_time = datetime.datetime.now()
                    self.filter_counter = 0
                    if self.config['stream']['update_sdt']:
                        self.atsc.update_sdt_names(self.video,
                                                   self.channel_dict['namespace'].encode(),
                                                   self.set_service_name(self.channel_dict).encode())
                    self.duration = data['duration']
                    uri_decoded = urllib.parse.unquote(uri)
                    if self.check_ts_counter(uri_decoded):
                        start_ttw = time.time()
                        self.write_buffer(self.video.data)
                        delta_ttw = time.time() - start_ttw
                        self.logger.info(
                            'Serving {} {} ({})s ({}B) ttw:{:.2f}s'
                            .format(self.t_m3u8.pid, uri_decoded, self.duration,
                                    len(self.video.data), delta_ttw))
                        self.is_starting = False
                        self.update_tuner_status('Streaming')
                        time.sleep(0.1)
                else:
                    if not self.is_starting:
                        self.update_tuner_status('No Reply')
                    uri_decoded = urllib.parse.unquote(uri)
                    self.logger.debug(
                        'No Video Stream from Provider {} {}'
                        .format(self.t_m3u8.pid, uri_decoded))
            self.check_termination()
            time.sleep(0.01)
        self.video.terminate()

    def write_buffer(self, _data):
        try:
            self.wfile.flush()
            # Do not use chunk writes! Just send data.
            # x = self.wfile.write('{}\r\n'.format(len(_data)).encode())
            x = self.wfile.write(_data)
            # x = self.wfile.write('\r\n'.encode())
            self.wfile.flush()
        except socket.timeout:
            raise
        except IOError:
            raise
        return x

    def write_atsc_msg(self):
        if not self.channel_dict['atsc']:
            self.logger.debug(
                'No video data, Sending Empty ATSC Msg {}'
                .format(self.t_m3u8.pid))
            self.write_buffer(
                self.atsc.format_video_packets())
        else:
            self.logger.debug(
                'No video data, Sending Default ATSC Msg for channel {}'
                .format(self.t_m3u8.pid))
            self.write_buffer(
                self.atsc.format_video_packets(
                    self.channel_dict['atsc']))

    def get_ts_counter(self, _uri):
        m = self.tc_match.findall(_uri)
        if len(m) == 0:
            return '', 0
        else:
            self.logger.debug('ts_counter {} {}'.format(m, _uri))
            x_tuple = m[len(m) - 1]
            if len(x_tuple) == 0:
                x_tuple = (_uri, '0')
            else:
                x_tuple = (_uri, x_tuple)
            return x_tuple

    def update_tuner_status(self, _status):
        ch_num = self.channel_dict['display_number']
        namespace = self.channel_dict['namespace']
        scan_list = WebHTTPHandler.rmg_station_scans[namespace]
        for i, tuner in enumerate(scan_list):
            if type(tuner) == dict and tuner['ch'] == ch_num:
                WebHTTPHandler.rmg_station_scans[namespace][i]['status'] = _status

    def update_idle_counter(self):
        """
        Updates the idle_counter to the nearest int in seconds
        based on when it was last reset
        """
        current_time = datetime.datetime.now()
        delta_time = current_time - self.last_reset_time
        self.idle_counter = int(delta_time.total_seconds())


    def check_ts_counter(self, _uri):
        """
        Providers sometime add the same stream section back into the list.
        This methods catches this and informs the caller that it should be ignored.
        """
        # counter = self.tc_match.findall(uri_decoded)
        # if len(counter) != 0:
        # counter = counter[0]
        # else:
        # counter = -1
        # self.logger.debug('ts counter={}'.format(counter))
        if _uri == self.last_ts_filename:
            self.logger.notice(
                'TC Counter Same section being transmitted, ignoring uri: {} m3u8pid:{} proxypid:{}'
                .format(_uri, self.t_m3u8.pid, os.getpid()))
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
        max_tries = 40
        restarts = 5
        while True:
            while InternalProxy.is_m3u8_starting != 0:
                time.sleep(0.1)
            InternalProxy.is_m3u8_starting = threading.get_ident()
            time.sleep(0.01)
            if InternalProxy.is_m3u8_starting == threading.get_ident():
                break
        while not is_running and restarts > 0:
            restarts -= 1
            # Process is not thread safe.  Must do the same target, one at a time.
            self.t_m3u8 = Process(target=m3u8_queue.start, args=(
                self.config, self.plugins, self.in_queue, self.out_queue, self.channel_dict,))
            self.t_m3u8.start()
            self.logger.debug('3 Requesting status from m3u8_queue {}'.format(self.t_m3u8.pid))
            self.in_queue.put({'uri': 'status'})
            time.sleep(0.1)
            tries = 0
            while self.out_queue.empty() and tries < max_tries:
                tries += 1
                time.sleep(0.2)
            if tries >= max_tries:
                self.m3u8_terminate()
            else:
                try:
                    # queue is not empty, but it sticks here anyway...
                    status = self.out_queue.get(False, 3)
                except Empty:
                    self.m3u8_terminate()
                    continue

                if status['uri'] == 'terminate':
                    self.logger.debug('Receive request to terminate from m3u8_queue {}'.format(self.t_m3u8.pid))
                    InternalProxy.is_m3u8_starting = False
                    return False
                elif status['uri'] == 'running':
                    self.logger.debug('2 Status of Running returned from m3u8_queue {}'.format(self.t_m3u8.pid))
                    is_running = True
                else:
                    self.logger.warning(
                        'Unknown response from m3u8queue: {}'
                        .format(status['uri']))
        InternalProxy.is_m3u8_starting = False
        return restarts > 0

    def m3u8_terminate(self):
        while not self.in_queue.empty():
            try:
                self.in_queue.get()
                time.sleep(0.1)
            except (Empty, EOFError):
                pass
        self.t_m3u8.terminate()
        self.t_m3u8.join()
        self.logger.debug(
            'm3u8_queue did not start correctly, restarting {}'
            .format(self.channel_dict['uid']))
        try:
            while not self.out_queue.empty():
                self.out_queue.get()
        except (Empty, EOFError):
            pass
        self.clear_queues()
        time.sleep(0.3)
        self.in_queue = Queue()
        self.out_queue = Queue(maxsize=MAX_OUT_QUEUE_SIZE)
