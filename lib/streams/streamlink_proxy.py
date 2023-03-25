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

import lib.common.exceptions as exceptions
from lib.clients.web_handler import WebHTTPHandler
from lib.streams.video import Video
from lib.db.db_config_defn import DBConfigDefn
from .stream import Stream
from .stream_queue import StreamQueue
from .pts_validation import PTSValidation

IDLE_TIMER = 20      # Duration for no video causing a refresh
MAX_IDLE_TIMER = 59  # duration for no video causing stream termination

class StreamlinkProxy(Stream):

    def __init__(self, _plugins, _hdhr_queue):
        self.streamlink_proc = None
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
        super().__init__(_plugins, _hdhr_queue)
        self.db_configdefn = DBConfigDefn(self.config)
        self.video = Video(self.config)

    def update_tuner_status(self, _status):
        ch_num = self.channel_dict['display_number']
        namespace = self.channel_dict['namespace']
        scan_list = WebHTTPHandler.rmg_station_scans[namespace]
        for i, tuner in enumerate(scan_list):
            if type(tuner) == dict and tuner['ch'] == ch_num:
                WebHTTPHandler.rmg_station_scans[namespace][i]['status'] = _status

    def stream(self, _channel_dict, _write_buffer):
        self.logger.info('Using streamlink_proxy for channel {}'.format(_channel_dict['uid']))
        self.channel_dict = _channel_dict
        self.write_buffer = _write_buffer
        self.config = self.db_configdefn.get_config()
        self.pts_validation = PTSValidation(self.config, self.channel_dict)
        channel_uri = self.get_stream_uri(self.channel_dict)
        if not channel_uri:
            self.logger.warning('Unknown Channel {}'.format(_channel_dict['uid']))
            return
        self.streamlink_proc = self.open_streamlink_proc(channel_uri)
        if not self.streamlink_proc:
            return
        time.sleep(0.01)
        self.last_refresh = time.time()
        self.block_prev_time = self.last_refresh
        self.buffer_prev_time = self.last_refresh
        try:
            self.read_buffer()
        except exceptions.CabernetException as ex:
            self.logger.info(str(ex))
            return
        while True:
            if not self.video.data:
                self.logger.info(
                    '1 No Video Data, refreshing stream {} {}'
                    .format(_channel_dict['uid'], self.streamlink_proc.pid))
                self.streamlink_proc = self.refresh_stream()
            else:
                try:
                    self.validate_stream()
                    self.update_tuner_status('Streaming')
                    start_ttw = time.time()
                    self.write_buffer.write(self.video.data)
                    delta_ttw = time.time() - start_ttw
                    self.logger.info(
                        'Serving {} {} ({}B) ttw:{:.2f}s'
                        .format(self.streamlink_proc.pid, _channel_dict['uid'],
                                len(self.video.data), delta_ttw))
                except IOError as e:
                    if e.errno in [errno.EPIPE, errno.ECONNABORTED, errno.ECONNRESET, errno.ECONNREFUSED]:
                        self.logger.info('1. Connection dropped by end device {}'.format(self.streamlink_proc.pid))
                        break
                    else:
                        self.logger.error('{}{}'.format(
                            '1 UNEXPECTED EXCEPTION=', e))
                        raise
            try:
                self.read_buffer()
            except Exception as e:
                self.logger.error('{}{}'.format(
                    '2 UNEXPECTED EXCEPTION=', e))
                raise
        self.terminate_stream()

    def validate_stream(self):
        if not self.config[self.config_section]['player-enable_pts_filter']:
            return

        has_changed = True
        while has_changed:
            has_changed = False
            results = self.pts_validation.check_pts(self.video)
            if results['byteoffset'] != 0:
                if results['byteoffset'] < 0:
                    self.write_buffer.write(self.video.data[-results['byteoffset']:len(self.video.data) - 1])
                else:
                    self.write_buffer.write(self.video.data[0:results['byteoffset']])
                has_changed = True
            if results['refresh_stream']:
                self.streamlink_proc = self.refresh_stream()
                self.read_buffer()
                has_changed = True
            if results['reread_buffer']:
                self.read_buffer()
                has_changed = True
        return

    def read_buffer(self):
        data_found = False
        self.video.data = None
        idle_timer = MAX_IDLE_TIMER  # time slice segments are less than 10 seconds
        while not data_found:
            self.video.data = self.stream_queue.read()
            if self.video.data:
                data_found = True
            else:
                if self.stream_queue.is_terminated:
                    raise exceptions.CabernetException('Streamlink Terminated, exiting stream {}'.format(self.streamlink_proc.pid))

                time.sleep(1)
                idle_timer -= 1
                if idle_timer % IDLE_TIMER == 0:
                    self.logger.info(
                        '2 No Video Data, refreshing stream {}'
                        .format(self.streamlink_proc.pid))
                    self.streamlink_proc = self.refresh_stream()
                    
                if idle_timer < 1:
                    idle_timer = MAX_IDLE_TIMER  # time slice segments are less than 10 seconds
                    self.logger.info(
                        'No Video Data, terminating stream {}'
                        .format(self.streamlink_proc.pid))
                    time.sleep(15)
                    self.streamlink_proc = self.terminate_stream()
                    raise exceptions.CabernetException('Unable to get video stream, terminating')
                elif int(MAX_IDLE_TIMER / 2) == idle_timer:
                    self.update_tuner_status('No Reply')
        return

    def terminate_stream(self):
        self.logger.debug('Terminating streamlink stream {}'.format(self.streamlink_proc.pid))
        while True:
            try:
                self.streamlink_proc.terminate()
                self.streamlink_proc.wait(timeout=1.5)
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
        streamlink_process = self.open_streamlink_proc(channel_uri)
        # make sure the previous streamlink is terminated before exiting        
        self.buffer_prev_time = time.time()
        return streamlink_process

    def open_streamlink_proc(self, _channel_uri):
        """
        streamlink drops the first 9 frame/video packets when the program starts.
        this means everytime a refresh occurs, 9 frames will be dropped.  This is
        visible by looking at the video packets for a 6 second window being 171
        instead of 180.  Following the first read, the packets increase to 180.
        """
        header = self.channel_dict['json'].get('Header')
        str_array = []
        llevel = self.config['handler_loghandler']['level']
        if llevel == 'DEBUG':
            sl_llevel = 'trace'
        elif llevel == 'INFO':
            sl_llevel = 'info'
        elif llevel == 'NOTICE':
            sl_llevel = 'warning'
        elif llevel == 'WARNING':
            sl_llevel = 'error'
        else:
            sl_llevel = 'none'
        
        if header:
            for key, value in header.items():
                str_array.append('--http-header')
                str_array.append(key + '=' + value)
                if key == 'Referer':
                    self.logger.debug('Using HTTP Referer: {}  Channel: {}'.format(value, self.channel_dict['uid']))
        uri = '{}'.format(_channel_uri)
        streamlink_command = [
            self.config['paths']['streamlink_path'],
            '--stdout',
            '--loglevel', sl_llevel,
            '--ffmpeg-fout', 'mpegts',
            '--hls-segment-attempts', '2',
            '--hls-segment-timeout', '5',
            uri,
            '720,best'
        ]
        streamlink_command.extend(str_array)
        try:
            streamlink_process = subprocess.Popen(
                streamlink_command,
                stdout=subprocess.PIPE,
                bufsize=-1)
        except:
            self.logger.error('Streamlink Binary Not Found: {}'.format(self.config['paths']['streamlink_path']))
            return
        self.stream_queue = StreamQueue(188, streamlink_process, self.channel_dict['uid'])
        time.sleep(0.1)
        return streamlink_process
