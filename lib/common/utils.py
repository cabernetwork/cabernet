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
import glob
import linecache
import logging
import logging.config
import mimetypes
import ntpath
import os
import pathlib
import platform
import re
import shutil
import socket
import struct
import sys
import time
import tracemalloc

import lib.common.exceptions as exceptions

VERSION = '0.9.15.00-RC01'
CABERNET_URL = 'https://github.com/cabernetwork/cabernet'
CABERNET_ID = 'cabernet'
CABERNET_REPO = 'manifest.json'
DEFAULT_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0'
PLUGIN_DATA = 'Wawc9dxf2ivj5lmunpq4hrbsktgyXz01e3Y6o7Z8+/'


def get_version_str():
    return VERSION

logger = None
LOG_LVL_NOTICE = 25
LOG_LVL_TRACE = 5
SEARCH_VERSION = re.compile('^([\d]+)\.([\d]+)\.([\d]+)(?:\.([\d]+))*(?:[\D]+(\d)+)*')

def get_version_index(_ver):
    """
    Based on the version string will calculate a number representing the version,
    which can be used to compare versions. Ignores any text after the fourth number
    format a.b.c.d or a.b.c
    """
    m = re.findall(SEARCH_VERSION, _ver)
    d1, d2, d3, d4, d5 = m[0]
    v_int = ((((int(d1)*100)+int(d2 or 0))*100)+int(d3 or 0))*100+int(d4 or 0)+int(d5 or 0)/100 
    return v_int


def logging_setup(_config):
    global logger
    if os.environ.get('LOGS_DIR') is None:
        if _config['paths']['logs_dir'] is not None:
            os.environ['LOGS_DIR'] = _config['paths']['logs_dir']
            try:
                logging.config.fileConfig(fname=_config['paths']['config_file'])
            except PermissionError as e:
                logging.critical(e)
                raise e
    if str(logging.getLevelName('NOTICE')).startswith('Level'):
        logging.addLevelName(LOG_LVL_NOTICE, 'NOTICE')
        def notice(self, message, *args, **kws):
            if self.isEnabledFor(LOG_LVL_NOTICE):
                self._log(LOG_LVL_NOTICE, message, args, **kws) 
        logging.Logger.notice = notice
    if str(logging.getLevelName('TRACE')).startswith('Level'):
        logging.addLevelName(LOG_LVL_TRACE, 'TRACE')
        def trace(self, message, *args, **kws):
            if self.isEnabledFor(LOG_LVL_TRACE):
                self._log(LOG_LVL_TRACE, message, args, **kws) 
        logging.Logger.trace = trace
    if str(logging.getLevelName('NOTUSED')).startswith('Level'):
        try:
            logging.config.fileConfig(fname=_config['paths']['config_file'])
        except FileNotFoundError:
            if _config['handler_filehandler']['enabled']:
                logging.warning('Unable to create cabernet.log in the data/logs area with File Logging enabled.')
        except PermissionError as e:
            logging.critical(e)
            raise e
        logging.addLevelName(100, 'NOTUSED')

    logger = logging.getLogger(__name__)

def clean_exit(exit_code=0):
    try:
        sys.stderr.flush()
        sys.stdout.flush()
    except BrokenPipeError:
        pass
    sys.exit(exit_code)


def block_print():
    sys.stdout = open(os.devnull, 'w')


def enable_print():
    sys.stdout = sys.__stdout__


def str2bool(s):
    return str(s).lower() in ['true', '1', 'yes', 'on']


def tm_parse(tm):
    tm_date = datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=tm / 1000)
    tm = str(tm_date.strftime('%Y%m%d%H%M%S +0000'))
    return tm


def convert_to_utc(tm):
    """
    Given a datetime obj with a timezone, convert it to UTC.
    """
    tm_blank = tm.replace(tzinfo=datetime.timezone.utc)
    tm_utc = tm + (tm_blank - tm)
    return tm_utc.replace(tzinfo=datetime.timezone.utc)
    
    

def tm_local_parse(tm):
    tm_date = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc) + datetime.timedelta(seconds=tm / 1000)
    tm = str(tm_date.astimezone().strftime('%Y%m%d%H%M%S %z'))
    return tm


def date_parse(date_secs, format_str):
    if not date_secs:
        return date_secs
    dt_date = datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=date_secs / 1000)
    dt_str = str(dt_date.strftime(format_str))
    return dt_str

def date_obj_parse(date_obj, format_str):
    if not date_obj:
        return date_obj
    dt_str = str(date_obj.strftime(format_str))
    return dt_str

def is_time_between(begin_time, end_time, check_time=None):
    """
    Check if current GMT time is between 10:30a and 4:30p
    EX: is_time_between(time(10,30), time(16,30))
    """
    check_time = check_time or datetime.datetime.utcnow().time()
    if begin_time < end_time:
        return check_time >= begin_time and check_time <= end_time
    else: # crosses midnight
        return check_time >= begin_time or check_time <= end_time


def is_file_expired(filepath, days=0, hours=0):
    if not os.path.exists(filepath):
        return True
    current_time = datetime.datetime.utcnow()
    file_time = datetime.datetime.utcfromtimestamp(os.path.getmtime(filepath))
    if days == 0:
        if int((current_time - file_time).total_seconds() / 3600) > hours:
            return True
    elif (current_time - file_time).days > days:
        return True
    return False


def merge_dict(d1, d2, override=False, ignore_conflicts=False):
    for key in d2:
        if key in d1:
            if isinstance(d1[key], dict) and isinstance(d2[key], dict):
                merge_dict(d1[key], d2[key], override, ignore_conflicts)
            elif d1[key] == d2[key]:
                pass
            elif override:
                d1[key] = d2[key]
            elif not ignore_conflicts:
                raise exceptions.CabernetException('Conflict when merging dictionaries {}'.format(str(key)))
        else:
            d1[key] = d2[key]
            
    return d1

def rename_dict_key(_old_key, _new_key, _dict):
    """
    renames a key in a dict without losing the order
    """
    return { key if key != _old_key else _new_key: value for key, value in _dict.items()}


def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


def wrap_chnum(_chnum, _namespace, _instance, _config):
    """
    Adds prefix and suffix to chnum.  If prefix is a integer, then
    will add the prefix to the chnum instead of using it like a string.
    """
    inst_config_sect = instance_config_section(_namespace, _instance)
    prefix = _config[inst_config_sect]['epg-prefix']
    suffix = _config[inst_config_sect]['epg-suffix']
    if prefix is None:
        prefix = ""
    if suffix is None:
        suffix = ""
    try:
        ch_int = int(prefix)
        ch_split = _chnum.split('.', 1)
        ch_int += int(ch_split[0])
        if len(ch_split) == 2:
            ch_str = str(ch_int) + '.' + ch_split[1]
        else:
            ch_str = str(ch_int)
    except ValueError:
        ch_str = prefix + _chnum
    ch_str += suffix
    return ch_str


def instance_config_section(_namespace, _instance):
    return _namespace.lower() + '_' + _instance


def process_image_url(_config, _thumbnail_url):
    global logger
    if _thumbnail_url is not None and _thumbnail_url.startswith('file://'):
        filename = ntpath.basename(_thumbnail_url)
        mime_lookup = mimetypes.guess_type(filename)
        new_filename = filename.replace(' ','')
        if mime_lookup[0] is not None and \
                mime_lookup[0].startswith('image'):
            old_path = _thumbnail_url.replace('file://', '')
            new_path = pathlib.Path(_config['paths']['data_dir'],
                'web', 'temp')
            if not new_path.exists():
                os.makedirs(new_path)
            new_path = new_path.joinpath(new_filename)
            if not new_path.exists():
                try:
                    shutil.copyfile(old_path, new_path)
                except FileNotFoundError:
                    logging.warning('FileNotFoundError: Image not found: {}'.format(old_path))
                    return '/temp/FILENOTFOUND'
                except OSError as e:
                    try:
                        if platform.system() in ['Windows']:
                            # standard windows path exception.  remove '/'
                            shutil.copyfile(old_path[1:], new_path)                
                        else:
                            logging.warning('OSError:{}'.format(e))
                            return '/temp/FILENOTFOUND'
                    except FileNotFoundError:
                        logging.warning('FileNotFoundError: Image file not found: {}'.format(old_path[1:]))
                        return '/temp/FILENOTFOUND'
            return '/temp/'+new_filename
        else:
            return '/temp/NOTANIMAGE'
    else:
        return _thumbnail_url

def cleanup_web_temp(_config):
    dir = _config['paths']['data_dir']
    filelist = glob.glob(os.path.join(dir, 'web', 'temp', '*'))
    for f in filelist:
        if os.path.isfile(f):
            os.remove(f)

# MEMORY USAGE

def start_mem_trace(_config):
    if _config['main']['memory_usage']:
        logger.warning('starting tracemalloc {}'.format(tracemalloc.is_tracing()))
        tracemalloc.start()

def end_mem_trace(_config):
    if _config['main']['memory_usage'] and tracemalloc.is_tracing():
        snapshot = tracemalloc.take_snapshot()
        tracemalloc.stop()
        return snapshot
    else:
        return None

def display_top(_config, snapshot, key_type='lineno', limit=3):
    if _config['main']['memory_usage'] and snapshot is not None:
        snapshot = snapshot.filter_traces((
            tracemalloc.Filter(False, "<frozen importlib._bootstrap>"),
            tracemalloc.Filter(False, "<unknown>"),
        ))
        top_stats = snapshot.statistics(key_type)

        logging.debug('pid:{} Top {} lines'.format(os.getpid(), limit))
        for index, stat in enumerate(top_stats[:limit], 1):
            frame = stat.traceback[0]
            # replace "/path/to/module/file.py" with "module/file.py"
            filename = os.sep.join(frame.filename.split(os.sep)[-2:])
            logging.debug("#%s: %s:%s: %.1f KiB"
                  % (index, filename, frame.lineno, stat.size / 1024))
            line = linecache.getline(frame.filename, frame.lineno).strip()
            if line:
                logging.debug('    %s' % line)

        other = top_stats[limit:]
        if other:
            size = sum(stat.size for stat in other)
            logging.debug("%s other: %.1f KiB" % (len(other), size / 1024))
        total = sum(stat.size for stat in top_stats)
        logging.debug("Total allocated size: %.1f KiB" % (total / 1024))


# BYTE METHODS

def set_u8(integer):
    return struct.pack('B', integer)


def set_u16(integer):
    return struct.pack('>H', integer)


def set_u32(integer):
    return struct.pack('>I', integer)


def set_u64(integer):
    return struct.pack('>Q', integer)


# HDHR requires a null byte at the end most of the time
def set_str(string, add_null):
    # places the length in a single byte, the string and then a null byte if add_null is true
    if add_null:
        return struct.pack('B%dsB' % (len(string)), len(string) + 1, string, 0)
    else:
        return struct.pack('B%ds' % (len(string)), len(string), string)

