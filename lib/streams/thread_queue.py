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

import logging
import threading
import time
from queue import Empty

from multiprocessing import Queue, Process
from threading import Thread


class ThreadQueue(Thread):
    """
    Takes a queue containing thread ids and pushes them 
    into other queues associated with those threads
    Assumes queue item is a dict containing a name/value of "thread_id"
    'terminate' can be sent via name 'uri' to terminate a specific thread id
    """
    # list of [threadid, queue] items

    def __init__(self, _queue, _config):
        Thread.__init__(self)
        self.logger = logging.getLogger(__name__ + str(threading.get_ident()))
        # incoming queue containing the thread id of which outgoing queue to send it to.
        self.queue = _queue
        # outgoing queues
        self.queue_list = {}
        self.config = _config
        self.terminate_requested = False
        # The process using the incoming queue to send data
        self._remote_proc = None
        # incoming queue to the process, stored locally
        self._status_queue = None
        self.start()

    def __str__(self):
        """
        Used to display the number of queues in the outgoing queue list
        """
        return str(len(self.queue_list))

    def run(self):
        thread_id = None
        try:
            while not self.terminate_requested:
                queue_item = self.queue.get()
                thread_id = queue_item.get('thread_id')
                if not thread_id:
                    self.logger.warning('Badly formatted queue. thread_id required and missing thread_id:{}  uri:{}'
                        .format(queue_item.get('thread_id'), queue_item.get('uri')))
                    continue
                if not queue_item.get('uri'):
                    self.logger.warning('Badly formatted queue. uri required and missing thread_id:{}  uri:{}'
                        .format(queue_item.get('thread_id'), queue_item.get('uri')))
                    continue
                if queue_item.get('uri') == 'terminate':
                    time.sleep(self.config['stream']['switch_channel_timeout'])
                    self.del_thread(thread_id, True)
                out_queue = self.queue_list.get(thread_id)
                if out_queue:
                    # Define the length of sleep to keep the queues from becoming full
                    # or using all the memory.  Occurs with VOD streams.
                    # sleep timer auto-adjusts to keep the queue a little over 10 items
                    # in the outgoing queue
                    if out_queue.qsize() > 10:
                        s = out_queue.qsize()/2
                    else:
                        s = 0.0
                    out_queue.put(queue_item)
                    self.sleep(s)

        except (KeyboardInterrupt, EOFError) as ex:
            self.terminate_requested = True
            self.clear_queues()
            self.logger.exception('{}{}'.format(
                'UNEXPECTED EXCEPTION ThreadQueue=', ex))
        except Exception as ex:
            # tell everyone we are terminating badly
            self.logger.exception('{}'.format(
                'UNEXPECTED EXCEPTION ThreadQueue'))
            for qdict in self.queue_list.items():
                qdict[1].put({'thread_id': qdict[0], 'uri': 'terminate'})
            self.terminate_requested = True
            self.clear_queues()
            time.sleep(0.01)

        self.clear_queues()
        self.terminate_requested = True
        self.logger.debug('ThreadQueue terminated')

    def clear_queues(self):
        self.clear_q(self.queue)

    def clear_q(self, _q):
        try:
            while True:
                item = _q.get_nowait()
        except (Empty, ValueError, EOFError, OSError) as ex:
            pass

    def add_thread(self, _thread_id, _queue):
        """
        Adds the thread id to the list of queues this class is sending data
        """
        out_queue = self.queue_list.get(_thread_id)
        self.queue_list[_thread_id] = _queue
        if not out_queue:
            self.logger.debug('Adding thread id queue to thread queue: {}'.format(_thread_id))

    def del_thread(self, _thread_id, _is_inrun=False):
        """
        Removes the thread id from the list of queues this class is sending data to
        if queue list is empty, then will also set the terminate to True
        and return True
        _is_inrun is set to true when the call comes from the thread run method, 
        so wait for terminate is not required since it already is not waiting for get queue processing
        """
        out_queue = self.queue_list.get(_thread_id)
        if out_queue:
            del self.queue_list[_thread_id]
            self.logger.debug('Removing thread id queue from thread queue: {}'.format(_thread_id))
            if not len(self.queue_list):
                # sleep to deal with boomerang effects on termination
                # when the channel does a quick reset by the client
                time.sleep(1.0)
            if not len(self.queue_list):
                self.logger.debug('Terminating thread queue')
                self.terminate_requested = True
                time.sleep(0.01)
                self.clear_queues()
                if _is_inrun:
                    return True
                else:
                    self.queue.put({'thread_id': _thread_id, 'uri': 'terminate'})
                    time.sleep(0.01)
                    self.wait_for_termination()
                return True
            else:
                return False
        else:
            return True

    def wait_for_termination(self):
        count = 50
        while self.is_alive() and count > 0:
            time.sleep(0.1)
            count -= 1
        self.clear_queues()

    def sleep(self, _time):
        """
        Creates a sleep function that will exit quickly if the termination flag is set
        """
        start_ttw = time.time()
        for i in range(round(_time * 5)):
            if not self.terminate_requested:
                time.sleep(_time * 0.2)
            else:
                break
            delta_ttw = time.time() - start_ttw
            if delta_ttw > _time:
                break

    @property
    def remote_proc(self):
        """
        process using the status_queue and sending to the incoming queue
        """
        return self._remote_proc

    @remote_proc.setter
    def remote_proc(self, _proc):
        self._remote_proc = _proc

    @property
    def status_queue(self):
        """
        queue used by the remote process as its incoming queue
        """
        return self._status_queue

    @status_queue.setter
    def status_queue(self, _queue):
        self._status_queue = _queue
