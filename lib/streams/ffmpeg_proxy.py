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

import errno
import subprocess
import time

from lib.clients.web_handler import WebHTTPHandler
from lib.streams.video import Video
from lib.db.db_config_defn import DBConfigDefn
from .stream import Stream
from .stream_queue import StreamQueue
from .pts_validation import PTSValidation

MAX_IDLE_TIMER = 59


class FFMpegProxy(Stream):

    def __init__(self, _plugins, _hdhr_queue):
        self.ffmpeg_proc = None
        self.last_refresh = None
        self.block_prev_time = None
        self.buffer_prev_time = None
        self.small_pkt_streaming = False
        self.block_max_pts = 0
        self.block_prev_pts = 0
        self.prev_last_pts = 0
        self.default_duration = 0
        self.block_moving_avg = 0
        self.channel_dict = None
        self.write_buffer = None
        self.stream_queue = None
        self.pts_validation = None
        self.tuner_no = -1
        super().__init__(_plugins, _hdhr_queue)
        self.db_configdefn = DBConfigDefn(self.config)
        self.video = Video(self.config)

    def update_tuner_status(self, _status):
        ch_num = self.channel_dict['display_number']
        namespace = self.channel_dict['namespace']
        scan_list = WebHTTPHandler.rmg_station_scans[namespace]
        tuner = scan_list[self.tuner_no]
        if type(tuner) == dict and tuner['ch'] == ch_num:
            WebHTTPHandler.rmg_station_scans[namespace][self.tuner_no]['status'] = _status

    def stream(self, _channel_dict, _write_buffer, _tuner_no):
        global MAX_IDLE_TIMER
        self.logger.info('Using ffmpeg_proxy for channel {}'.format(_channel_dict['uid']))
        self.tuner_no = _tuner_no
        self.channel_dict = _channel_dict
        self.write_buffer = _write_buffer
        self.config = self.db_configdefn.get_config()
        MAX_IDLE_TIMER = self.config[self.namespace.lower()]['stream-g_stream_timeout']

        self.pts_validation = PTSValidation(self.config, self.channel_dict)
        channel_uri = self.get_stream_uri(self.channel_dict)
        if not channel_uri:
            self.logger.warning('Unknown Channel {}'.format(_channel_dict['uid']))
            return
        self.ffmpeg_proc = self.open_ffmpeg_proc(channel_uri)
        time.sleep(0.01)
        self.last_refresh = time.time()
        self.block_prev_time = self.last_refresh
        self.buffer_prev_time = self.last_refresh
        self.read_buffer()
        while True:
            if not self.video.data:
                self.logger.info(
                    'No Video Data, refreshing stream {} {}'
                    .format(_channel_dict['uid'], self.ffmpeg_proc.pid))
                self.ffmpeg_proc = self.refresh_stream()
            else:
                try:
                    self.validate_stream()
                    self.update_tuner_status('Streaming')
                    start_ttw = time.time()
                    self.write_buffer.write(self.video.data)
                    delta_ttw = time.time() - start_ttw
                    self.logger.info(
                        'Serving {} {} ({}B) ttw:{:.2f}s'
                        .format(self.ffmpeg_proc.pid, _channel_dict['uid'],
                                len(self.video.data), delta_ttw))
                except IOError as e:
                    if e.errno in [errno.EPIPE, errno.ECONNABORTED, errno.ECONNRESET, errno.ECONNREFUSED]:
                        self.logger.info('1. Connection dropped by end device {}'.format(self.ffmpeg_proc.pid))
                        break
                    else:
                        self.logger.error('{}{}'.format(
                            '1 UNEXPECTED EXCEPTION=', e))
                        raise
            try:
                self.read_buffer()
            except exceptions.CabernetException as ex:
                self.logger.info('{} {}'.format(ex, self.ffmpeg_proc.pid))
                break
            except Exception as e:
                self.logger.error('{}{}'.format(
                    '2 UNEXPECTED EXCEPTION=', e))
                break
        self.terminate_stream()

    def validate_stream(self):
        if not self.config[self.config_section]['player-enable_pts_filter']:
            return

        has_changed = True
        while has_changed:
            has_changed = False
            results = self.pts_validation.check_pts(self.video.data)
            if results['byteoffset'] != 0:
                if results['byteoffset'] < 0:
                    self.write_buffer.write(self.video.data[-results['byteoffset']:len(self.video.data) - 1])
                else:
                    self.write_buffer.write(self.video.data[0:results['byteoffset']])
                has_changed = True
            if results['refresh_stream']:
                self.ffmpeg_proc = self.refresh_stream()
                self.read_buffer()
                has_changed = True
            if results['reread_buffer']:
                self.read_buffer()
                has_changed = True
        return

    def read_buffer(self):
        global MAX_IDLE_TIMER
        data_found = False
        self.video.data = None
        idle_timer = MAX_IDLE_TIMER  # time slice segments are less than 10 seconds
        while not data_found:
            self.video.data = self.stream_queue.read()
            if self.video.data:
                data_found = True
            else:
                time.sleep(1)
                idle_timer -= 1
                if idle_timer < 1:
                    idle_timer = MAX_IDLE_TIMER  # time slice segments are less than 10 seconds
                    self.logger.info(
                        'No Video Data, refreshing stream {}'
                        .format(self.ffmpeg_proc.pid))
                    self.ffmpeg_proc = self.refresh_stream()
                elif int(MAX_IDLE_TIMER / 2) == idle_timer:
                    self.update_tuner_status('No Reply')
        return

    def terminate_stream(self):
        self.logger.debug('Terminating ffmpeg stream {}'.format(self.ffmpeg_proc.pid))
        while True:
            try:
                self.ffmpeg_proc.terminate()
                self.ffmpeg_proc.wait(timeout=1.5)
                break
            except ValueError:
                pass
            except subprocess.TimeoutExpired:
                time.sleep(0.01)

    def refresh_stream(self):
        self.last_refresh = time.time()
        channel_uri = self.get_stream_uri(self.channel_dict)
        self.terminate_stream()

        self.logger.debug('{}{}'.format(
            'Refresh Stream channelUri=', channel_uri))
        ffmpeg_process = self.open_ffmpeg_proc(channel_uri)
        # make sure the previous ffmpeg is terminated before exiting        
        self.buffer_prev_time = time.time()
        return ffmpeg_process

    def open_ffmpeg_proc_locast(self, _channel_uri):
        """
        ffmpeg drops the first 9 frame/video packets when the program starts.
        this means everytime a refresh occurs, 9 frames will be dropped.  This is
        visible by looking at the video packets for a 6 second window being 171
        instead of 180.  Following the first read, the packets increase to 180.
        """
        ffmpeg_command = [
            self.config['paths']['ffmpeg_path'],
            '-i', str(_channel_uri),
            '-f', 'mpegts',
            '-nostats',
            '-hide_banner',
            '-loglevel', 'warning',
            '-copyts',
            'pipe:1']
        ffmpeg_process = subprocess.Popen(
            ffmpeg_command,
            stdout=subprocess.PIPE,
            bufsize=-1)
        self.stream_queue = StreamQueue(188, ffmpeg_process, self.channel_dict['uid'])
        time.sleep(0.1)
        return ffmpeg_process

    def open_ffmpeg_proc(self, _channel_uri):
        """
        ffmpeg drops the first 9 frame/video packets when the program starts.
        this means everytime a refresh occurs, 9 frames will be dropped.  This is
        visible by looking at the video packets for a 6 second window being 171
        instead of 180.  Following the first read, the packets increase to 180.
        """
        header = self.channel_dict['json'].get('Header')
        str_array = []
        if header:
            str_array.append('-headers')
            header_value = ''
            for key, value in header.items():
                header_value += key+': '+value+'\r\n'
                if key == 'Referer':
                    self.logger.debug('Using HTTP Referer: {}  Channel: {}'.format(value, self.channel_dict['uid']))
            str_array.append(header_value)

        ffmpeg_options = [
            '-i', str(_channel_uri),
            '-nostats',
            '-hide_banner',
            '-fflags', '+genpts',
            '-threads', '2',
            '-loglevel', 'quiet',
            '-c', 'copy',
            '-f', 'mpegts',
            '-c', 'copy',
            'pipe:1']

        ffmpeg_command = [
            self.config['paths']['ffmpeg_path']
            ]
        # Header option must come first in the options list
        if str_array:
            ffmpeg_command.extend(str_array)
        ffmpeg_command.extend(ffmpeg_options)
        ffmpeg_process = subprocess.Popen(
            ffmpeg_command,
            stdout=subprocess.PIPE,
            bufsize=-1)
        self.stream_queue = StreamQueue(188, ffmpeg_process, self.channel_dict['uid'])
        time.sleep(0.1)
        return ffmpeg_process
