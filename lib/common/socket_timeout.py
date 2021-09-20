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

import logging
import os
import socket


"""
Socket timeout is not thread safe, so this tries to overcome the
global static variables.  Socket timeouts are needed for HTTPS
connection since the normal timeout during openurl does not work.
"""

ACTIVE_TIMEOUTS = []
DEFAULT_SOCKET_TIMEOUT = 5.0

def reset_timeout():
    global ACTIVE_TIMEOUTS
    ACTIVE_TIMEOUTS = []
    

def add_timeout(_timeout):
    global ACTIVE_TIMEOUTS
    ACTIVE_TIMEOUTS.append(_timeout)
    #set_timeout()
    logger = logging.getLogger(__name__)
    logger.debug('socket timeouts: {} {}' \
        .format(ACTIVE_TIMEOUTS, os.getpid()))
    
def del_timeout(_timeout):
    global ACTIVE_TIMEOUTS
    try:
        ACTIVE_TIMEOUTS.remove(_timeout)
        #set_timeout()
    except ValueError:
        logger = logging.getLogger(__name__)
        logger.warning('Requested timeout be removed, but missing {} {} {}' \
            .format(os.getpid(), _timeout, ACTIVE_TIMEOUTS))
        raise

def set_timeout():
    global ACTIVE_TIMEOUTS
    try:
        socket.setdefaulttimeout(max(ACTIVE_TIMEOUTS))
    except ValueError:
        socket.setdefaulttimeout(DEFAULT_SOCKET_TIMEOUT)
        logger = logging.getLogger(__name__)
        logger.debug('Setting timeout to default: {} {}' \
            .format(DEFAULT_SOCKET_TIMEOUT, os.getpid()))

