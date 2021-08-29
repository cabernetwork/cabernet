"""
MIT License

Copyright (C) 2021 ROCKY4546
https://github.com/rocky4546

This file is part of Cabernet

Permission is hereby granted, free of charge, to any person obtaining a copy of this software
and associated documentation files (the “Software”), to deal in the Software without restriction,
including without limitation the rights to use, copy, modify, merge, publish, distribute,
sublicense, and/or sell copies of the Software, and to permit persons to whom the Software
is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or
substantial portions of the Software.
"""

import json
import logging
import subprocess


class PTSValidation:
    logger = None

    def __init__(self, _config, _channel_dict):
        self.ffmpeg_proc = None
        self.last_refresh = None
        self.buffer_prev_time = None
        self.small_pkt_streaming = False
        self.block_max_pts = 0
        self.block_prev_pts = 0
        self.prev_last_pts = 0
        self.default_duration = 0
        self.block_moving_avg = 0
        self.channel_dict = _channel_dict
        self.write_buffer = None
        self.stream_queue = None
        self.config = _config
        self.pts_json = None
        if PTSValidation.logger is None:
            PTSValidation.logger = logging.getLogger(__name__)

    def check_pts(self, _video_data):
        """
        Checks the PTS in the video stream.  If a bad PTS packet is found, 
        it will update the video stream until the stream is valid.
        returns a dict containing 3 values
        byteoffset (if >0, then write the offset before continuing)
        refresh_stream (if True, then refresh the stream)
        reread_buffer (if True, then drop current video_data and re-read buffer)
        The items should be processed in the order listed above
        """
        self.pts_json = self.get_probe_results(_video_data)
        if self.pts_json is None:
            return {'refresh_stream': False, 'byteoffset': 0, 'reread_buffer': False}
        pkt_len = self.check_for_video_pkts()
        if pkt_len < 1:
            return {'refresh_stream': False, 'byteoffset': 0, 'reread_buffer': False}
        pts_data = self.get_pts_values(self.pts_json)
        if pts_data is None:
            return {'refresh_stream': False, 'byteoffset': 0, 'reread_buffer': False}

        pts_minimum = int(self.config[self.channel_dict['namespace'].lower()]['player-pts_minimum'])
        if pts_data['first_pts'] < pts_minimum:
            if pts_data['last_pts'] < pts_minimum:
                self.logger.debug('Small PTS for entire stream, drop and refresh buffer')
                return {'refresh_stream': False, 'byteoffset': 0, 'reread_buffer': True}
            elif pts_data['last_pts'] <= self.prev_last_pts:
                self.logger.debug('Small PTS to Large PTS with entire PTS in the past. last_pts={} vs prev={}'
                    .format(pts_data['last_pts'], self.prev_last_pts))
                return {'refresh_stream': False, 'byteoffset': 0, 'reread_buffer': True}
            else:
                byte_offset = self.find_bad_pkt_offset(from_front=False)
                if byte_offset > 0:
                    self.logger.debug('{} {}{}'.format(
                        'Small bad PTS on front with good large PTS on end.',
                        'Writing good bytes=', byte_offset))
                    return {'refresh_stream': False, 'byteoffset': -byte_offset, 'reread_buffer': True}
                else:
                    self.logger.debug('RARE CASE: Large delta but no bad PTS ... unknown case, ignore')
                    self.prev_last_pts = pts_data['last_pts']
                    return {'refresh_stream': False, 'byteoffset': 0, 'reread_buffer': False}
        elif pts_data['last_pts'] < pts_minimum:
            self.logger.debug('RARE CASE: Large PTS on front with small PTS on end.')
            return {'refresh_stream': True, 'byteoffset': 0, 'reread_buffer': False}

        elif pts_data['delta_from_prev'] > \
                int(self.config[self.channel_dict['namespace'].lower()]['player-pts_max_delta']):
            self.logger.debug('{} {}{}'.format(
                'Large delta PTS between reads. Refreshing Stream',
                'DELTA=', pts_data['delta_from_prev']))
            return {'refresh_stream': True, 'byteoffset': 0, 'reread_buffer': False}

        elif pts_data['pts_size'] > \
                int(self.config[self.channel_dict['namespace'].lower()]['player-pts_max_delta']):
            byte_offset = self.find_bad_pkt_offset(from_front=True)
            if byte_offset > 0:
                self.logger.debug('{} {}{}'.format(
                    'Large delta PTS with good front.',
                    'Writing good bytes=', byte_offset))
                return {'refresh_stream': True, 'byteoffset': byte_offset, 'reread_buffer': False}
            else:
                self.logger.debug('RARE CASE: Large delta but no bad PTS ... unknown case, ignore')
                self.prev_last_pts = pts_data['last_pts']
                return {'refresh_stream': False, 'byteoffset': 0, 'reread_buffer': False}

        elif pts_data['first_pts'] < self.prev_last_pts:
            if pts_data['last_pts'] <= self.prev_last_pts:
                self.logger.debug('Entire PTS buffer in the past last_pts={} vs prev={}'.format(pts_data['last_pts'],
                    self.prev_last_pts))
                return {'refresh_stream': False, 'byteoffset': 0, 'reread_buffer': True}
            else:
                byte_offset = self.find_past_pkt_offset(self.prev_last_pts)
                self.logger.debug('{} {}{} {}'.format(
                    'PTS buffer in the past.',
                    ' Writing end bytes from offset=', byte_offset,
                    'out to client'))
                if byte_offset < 0:
                    return {'refresh_stream': False, 'byteoffset': 0, 'reread_buffer': True}
                else:
                    self.prev_last_pts = pts_data['last_pts']
                    return {'refresh_stream': False, 'byteoffset': -byte_offset, 'reread_buffer': True}
        else:
            self.prev_last_pts = pts_data['last_pts']
            return {'refresh_stream': False, 'byteoffset': 0, 'reread_buffer': False}

    def get_probe_results(self, _video_data):
        ffprobe_command = [self.config['paths']['ffprobe_path'],
            '-print_format', 'json',
            '-v', 'quiet', '-show_packets',
            '-select_streams', 'v:0',
            '-show_entries', 'side_data=:packet=pts,pos,duration,size',
            '-']
        cmdpts = subprocess.Popen(ffprobe_command,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        ptsout = cmdpts.communicate(_video_data)[0]
        exit_code = cmdpts.wait()
        if exit_code != 0:
            self.logger.warning('FFPROBE failed to execute with error code: {}'
                .format(exit_code))
            return None
        return json.loads(ptsout)

    def check_for_video_pkts(self):
        try:
            pkt_len = len(self.pts_json['packets'])
        except KeyError:
            pkt_len = 0
            self.logger.debug('Packet received with no video packet included')
        return pkt_len

    def get_pts_values(self, _pts_json):
        try:
            first_pts = _pts_json['packets'][0]['pts']
            if self.prev_last_pts == 0:
                delta_from_prev = 0
            else:
                delta_from_prev = first_pts - self.prev_last_pts
            end_of_json = len(self.pts_json['packets']) - 1
            if 'duration' in self.pts_json['packets'][end_of_json]:
                dur = self.pts_json['packets'][end_of_json]['duration']
                self.default_duration = dur
            else:
                dur = self.default_duration
            last_pts = self.pts_json['packets'][end_of_json]['pts'] + dur
        except KeyError:
            self.logger.info('KeyError exception: no pts in first or last packet, ignore')
            return None
        pts_size = abs(last_pts - first_pts)
        self.logger.debug('{}{} {}{} {}{} {}{} {}{}'.format(
            'First PTS=', first_pts,
            'Last PTS=', last_pts,
            'PTS SIZE=', pts_size,
            'DELTA PTS=', delta_from_prev,
            'Pkts Rcvd=', len(_pts_json['packets'])))
        return {'first_pts': first_pts, 'last_pts': last_pts,
            'pts_size': pts_size, 'delta_from_prev': delta_from_prev}

    def find_bad_pkt_offset(self, from_front):
        """
        Determine where in the stream the pts diverges
        """
        num_of_pkts = len(self.pts_json['packets']) - 1  # index from 0 to len - 1
        i = 1
        prev_pkt_pts = self.pts_json['packets'][0]['pts']
        byte_offset = -1
        size = 0
        while i < num_of_pkts:
            next_pkt_pts = self.pts_json['packets'][i]['pts']

            if size == 0 and 'size' in self.pts_json['packets'][i]:
                size = int(self.pts_json['packets'][i]['size'])
            if abs(next_pkt_pts - prev_pkt_pts) \
                    > int(self.config[self.channel_dict['namespace'].lower()]['player-pts_max_delta']):
                # found place where bad packets start
                # only video codecs have byte position info
                if from_front:
                    pts = prev_pkt_pts
                    byte_offset = int((int(self.pts_json['packets'][i - 1]['pos']) + size) / 188) * 188
                    self.prev_last_pts = pts
                else:
                    pts = next_pkt_pts
                    byte_offset = int((int(self.pts_json['packets'][i]['pos']) - 1) / 188) * 188
                    self.prev_last_pts = self.pts_json['packets'][num_of_pkts]['pts']
                self.logger.debug('Middle PTS {}  byte_offset={}'.format(pts, byte_offset))
                break

            i += 1
            prev_pkt_pts = next_pkt_pts
        return byte_offset

    def find_past_pkt_offset(self, prev_last_pts):
        num_of_pkts = len(self.pts_json['packets']) - 1  # index from 0 to len - 1
        next_pkt_pts = 0
        i = 0
        byte_offset = -1
        while i < num_of_pkts:
            prev_pkt_dts = next_pkt_pts
            next_pkt_pts = self.pts_json['packets'][i]['pts']
            if next_pkt_pts >= prev_last_pts - 2:
                # found place where future packets start
                # only video codecs have byte position info
                byte_offset = int(int(self.pts_json['packets'][i]['pos']) / 188) * 188
                self.logger.debug(
                    '{}{} {}{} {}{}'.format('Future PTS at byte_offset=', byte_offset, 'pkt_pts=', next_pkt_pts,
                        'prev_pkt=', prev_pkt_dts))
                break
            i += 1
        return byte_offset
