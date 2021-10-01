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

import logging
import time
from threading import Thread


class StreamQueue:
    """
    This works when we run a process that has an output of a continuous stream.
    Used with ffmpeg and streamlink
    """

    def __init__(self, _bytes_per_read, _proc, _stream_id):
        self.logger = logging.getLogger(__name__)
        self.bytes_per_read = _bytes_per_read
        self.sout = _proc.stdout
        self.serr = _proc.stderr
        self.queue = []
        self.proc = _proc
        self.stream_id = _stream_id
        self.not_terminated = True

        def _populate_queue():
            """
            Collect lines from 'stream' and put them in 'queue'.
            """
            while self.not_terminated:
                try:
                    self.sout.flush()
                    video_data = self.sout.read(self.bytes_per_read)
                    if video_data:
                        self.queue.append(video_data)
                    else:
                        self.logger.debug('Stream ended for this process, exiting queue thread')
                        break
                except ValueError:
                    # occurs on termination with buffer must not be NULL
                    break
        self._t = Thread(target=_populate_queue, args=())
        self._t.daemon = True
        self._t.start()  # start collecting blocks from the stream

    def read(self):
        is_queue_changing = True
        queue_size = len(self.queue)
        while is_queue_changing:
            time.sleep(0.1)
            if len(self.queue) != queue_size:
                queue_size = len(self.queue)
            else:
                is_queue_changing = False
        
        if len(self.queue) > 0:
            clone_queue = self.queue.copy()
            del self.queue[:len(clone_queue)]
            return b''.join(clone_queue)
        return None
        
    def terminate(self):
        self.not_terminated = False
