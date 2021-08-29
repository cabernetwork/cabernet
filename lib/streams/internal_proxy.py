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
import re
import urllib.request
import time

from collections import OrderedDict

import lib.m3u8 as m3u8
from lib.common.atsc import ATSCMsg
from .stream import Stream
from .pts_validation import PTSValidation
from lib.db.db_config_defn import DBConfigDefn


class InternalProxy(Stream):

    def __init__(self, _plugins, _hdhr_queue):
        self.last_refresh = None
        self.channel_dict = None
        self.write_buffer = None
        self.file_filter = None
        self.pts_validation = None
        self.duration = 6
        super().__init__(_plugins, _hdhr_queue)
        self.config = self.plugins.config_obj.data
        self.db_configdefn = DBConfigDefn(self.config)

    def stream_direct(self, _channel_dict, _write_buffer):
        """
        Processes m3u8 interface without using ffmpeg
        """
        self.config = self.db_configdefn.get_config()
        self.channel_dict = _channel_dict
        self.write_buffer = _write_buffer
        duration = 6
        play_queue = OrderedDict()
        self.last_refresh = time.time()
        stream_uri = self.get_stream_uri(_channel_dict)
        if not stream_uri:
            self.logger.warning('Unknown Channel')
            return
        self.logger.debug('M3U8: {}'.format(stream_uri))
        self.file_filter = None
        if self.config[_channel_dict['namespace'].lower()]['player-enable_url_filter']:
            stream_filter = self.config[_channel_dict['namespace'].lower()]['player-url_filter']
            if stream_filter is not None:
                self.file_filter = re.compile(stream_filter)
            else:
                self.logger.warning('[{}]][player-enable_url_filter]'
                    ' enabled but [player-url_filter] not set'
                    .format(_channel_dict['namespace'].lower()))
        if self.config[_channel_dict['namespace'].lower()]['player-enable_pts_filter']:
            self.pts_validation = PTSValidation(self.config, self.channel_dict)

        while True:
            try:
                added = 0
                removed = 0
                playlist = m3u8.load(stream_uri)
                removed += self.remove_from_stream_queue(playlist, play_queue)
                added += self.add_to_stream_queue(playlist, play_queue)
                if added == 0 and duration > 0:
                    time.sleep(duration * 0.3)
                elif self.plugins.plugins[_channel_dict['namespace']].plugin_obj \
                        .is_time_to_refresh_ext(self.last_refresh, _channel_dict['instance']):
                    stream_uri = self.get_stream_uri(_channel_dict)
                    self.logger.debug('M3U8: {}'.format(stream_uri))
                    self.last_refresh = time.time()
                self.play_queue(play_queue)
            except IOError as e:
                # Check we hit a broken pipe when trying to write back to the client
                if e.errno in [errno.EPIPE, errno.ECONNABORTED, errno.ECONNRESET, errno.ECONNREFUSED]:
                    # Normal process.  Client request end of stream
                    self.logger.info('2. Connection dropped by end device {}'.format(e))
                    break
                else:
                    self.logger.error('{}{}'.format(
                        '3 UNEXPECTED EXCEPTION=', e))
                    raise

    def add_to_stream_queue(self, _playlist, _play_queue):
        total_added = 0
        for m3u8_segment in _playlist.segments:
            uri = m3u8_segment.absolute_uri
            if uri not in _play_queue:
                played = False
                if self.file_filter is not None:
                    m = self.file_filter.match(uri)
                    if m:
                        played = True
                _play_queue[uri] = {
                    'played': played,
                    'duration': m3u8_segment.duration
                }
                self.logger.debug(f"Added {uri} to play queue")
                total_added += 1
        return total_added

    def remove_from_stream_queue(self, _playlist, _play_queue):
        total_removed = 0
        for segment_key in list(_play_queue.keys()):
            is_found = False
            for segment_m3u8 in _playlist.segments:
                uri = segment_m3u8.absolute_uri
                if segment_key == uri:
                    is_found = True
                    break
            if not is_found:
                del _play_queue[segment_key]
                total_removed += 1
                self.logger.debug(f"Removed {segment_key} from play queue")
                continue
            else:
                break
        return total_removed

    def play_queue(self, _play_queue):
        for uri, data in _play_queue.items():
            if not data["played"]:
                start_download = datetime.datetime.utcnow()
                chunk = None
                count = 5
                while count > 0:
                    count -= 1
                    try:
                        req = urllib.request.Request(uri)
                        with urllib.request.urlopen(req) as resp:
                            chunk = resp.read()
                            break
                    except http.client.IncompleteRead as e:
                        self.logger.info('Provider gave partial stream, trying again. {}'.format(e, len(e.partial)))
                        chunk = e.partial
                        time.sleep(1)
                data['played'] = True
                if not chunk:
                    self.logger.warning(f"Segment {uri} not available. Skipping..")
                    continue
                if not self.is_pts_valid(chunk):
                    continue
                
                atsc_msg = ATSCMsg()
                chunk_updated = atsc_msg.update_sdt_names(chunk[:80], self.channel_dict['namespace'].encode(),
                    self.set_service_name(self.channel_dict).encode())
                chunk = chunk_updated + chunk[80:]
                self.duration = data['duration']
                runtime = (datetime.datetime.utcnow() - start_download).total_seconds()
                target_diff = 0.3 * self.duration
                wait = target_diff - runtime
                self.logger.info(f"Serving {uri} ({self.duration}s) ({len(chunk)}B)")
                self.write_buffer.write(chunk)
                if wait > 0:
                    time.sleep(wait)

    def is_pts_valid(self, video_data):
        if not self.config[self.channel_dict['namespace'].lower()]['player-enable_pts_filter']:
            return True
        results = self.pts_validation.check_pts(video_data)
        if results['byteoffset'] != 0:
            return False
        if results['refresh_stream']:
            return False
        if results['reread_buffer']:
            return False
        return True
