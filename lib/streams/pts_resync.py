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

import copy
import logging
import os
import subprocess
import time
from threading import Thread

from .stream_queue import StreamQueue


class PTSResync:

    def __init__(self, _config, _config_section, _id):
        self.logger = logging.getLogger(__name__)
        self.config = _config
        self.config_section = _config_section
        self.empty_packet_count = 0
        self.is_restart_requested = False
        self.is_looping = False
        self.id = _id
        self.ffmpeg_proc = None
        if self.config[self.config_section]['player-enable_pts_resync']:
            if self.config[self.config_section]['player-pts_resync_type'] == 'ffmpeg':
                self.ffmpeg_proc = self.open_ffmpeg_proc()
            self.stream_queue = StreamQueue(188, self.ffmpeg_proc, _id)
            if self.config[self.config_section]['player-pts_resync_type'] == 'ffmpeg':
                self.logger.debug('PTS Resync running ffmpeg')

    def video_to_stdin(self, _video):
        video_copy = copy.copy(_video.data)
        i = 3
        self.is_looping = False
        while i > 0:
            i -= 1
            try:
                if video_copy:
                    self.ffmpeg_proc.stdin.write(video_copy)
                break
            except (BrokenPipeError, TypeError) as ex:
                # This occurs when the process does not start correctly
                self.logger.debug('BROKENPIPE {} {}'.format(self.ffmpeg_proc.pid, str(ex)))
                if not self.is_restart_requested:
                    errcode = self.restart_ffmpeg()
                    self.is_looping = True
                else:
                    time.sleep(0.7)
                    
            except ValueError:
                # during termination, writing to a closed port, ignore
                break
        self.is_looping = False
        video_copy = None

    def restart_ffmpeg(self):
        self.logger.debug('Restarting PTSResync ffmpeg due to no ffmpeg processing {}'.format(self.ffmpeg_proc.pid))
        errcode = 0
        self.empty_packet_count = 0
        self.stream_queue.terminate()
        while True:
            try:
                self.ffmpeg_proc.terminate()
                #self.ffmpeg_proc.wait(timeout=1.5)
                break
            except ValueError:
                pass
            except subprocess.TimeoutExpired:
                time.sleep(0.01)
        try:
            sout, serr = self.ffmpeg_proc.communicate()
            errcode = self.ffmpeg_proc.returncode
            # an errcode of 1 means ffmpeg could not run
            if errcode == 1:
                self.logger.debug('FFMPEG ERRCODE: {}, unable for pts_resync to process segment in ffmpeg'.format(self.ffmpeg_proc.returncode))
        except ValueError:
            pass
        while self.ffmpeg_proc.poll() is None:
            time.sleep(0.1)
        self.ffmpeg_proc = self.open_ffmpeg_proc()
        self.stream_queue = StreamQueue(188, self.ffmpeg_proc, self.id)
        time.sleep(0.5)
        return errcode


    def resequence_pts(self, _video):
        if not self.config[self.config_section]['player-enable_pts_resync']:
            return
        if _video.data is None:
            return
        if self.config[self.config_section]['player-pts_resync_type'] == 'ffmpeg':
            while self.is_looping:
                time.sleep(0.5)
            t_in = Thread(target=self.video_to_stdin, args=(_video,))
            t_in.start()
            time.sleep(0.1)
            new_video = self.stream_queue.read()
            if not new_video:
                self.empty_packet_count += 1
                if self.empty_packet_count > 2:
                    if not self.is_restart_requested:
                        self.is_restart_requested = True
                        self.restart_ffmpeg()
                        self.is_restart_requested = False
            else:
                self.empty_packet_count = 0

            _video.data = new_video
        elif self.config[self.config_section]['player-pts_resync_type'] == 'internal':
            self.logger.warning('player-pts_resync_type internal NOT IMPLEMENTED')
        else:
            self.logger.error('player-pts_resync_type UNKNOWN TYPE {}'.format(
                self.config[self.config_section]['player-pts_resync_type']))

    def terminate(self):
        if self.ffmpeg_proc is not None:
            self.stream_queue.terminate()
            self.ffmpeg_proc.stdin.flush()
            self.ffmpeg_proc.stdout.flush()
            self.ffmpeg_proc.terminate()
            try:
                sout, serr = self.ffmpeg_proc.communicate()
                errcode = self.ffmpeg_proc.returncode
                if errcode == 1:
                    self.logger.debug('FFMPEG errcode on exit: {}, unable for pts_resync to process segment in ffmpeg'.format(self.ffmpeg_proc.returncode))
            except ValueError:
                pass

    def open_ffmpeg_proc(self):
        """
        ffmpeg drops the first 9 frame/video packets when the program starts.
        this means everytime a refresh occurs, 9 frames will be dropped.  This is
        visible by looking at the video packets for a 6 second window being 171
        instead of 180.  Following the first read, the packets increase to 180.
        """
        ffmpeg_command = [
            self.config['paths']['ffmpeg_path'],
            '-nostats',
            '-hide_banner',
            '-loglevel', 'fatal',
            '-i', 'pipe:0',
            '-fflags', '+flush_packets+genpts',
            '-avioflags', '+direct',
            '-f', 'mpegts',
            '-c', 'copy',
            'pipe:1']
        ffmpeg_process = subprocess.Popen(
            ffmpeg_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            bufsize=-1)
        return ffmpeg_process
