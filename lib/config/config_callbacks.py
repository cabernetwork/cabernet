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

import getpass
import importlib
import importlib.resources
import logging
import logging.config
import os
import pathlib
import platform
import urllib.request
import uuid

import lib.common.utils as utils
import lib.common.encryption as encryption
import lib.config.config_defn as config_defn
import lib.clients.hdhr.hdhr_server as hdhr_server
from lib.db.db_config_defn import DBConfigDefn
from lib.db.db_scheduler import DBScheduler
from lib.db.db_channels import DBChannels
from lib.clients.web_handler import WebHTTPHandler

try:
    import cryptography
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.fernet import Fernet

    CRYPTO_LOADED = True
except ImportError:
    CRYPTO_LOADED = False

ENCRYPT_STRING = 'ENC::'


def noop(_config_obj, _section, _key):
    pass


def logging_refresh(_config_obj, _section, _key):
    logging.config.fileConfig(fname=_config_obj.data['paths']['config_file'], disable_existing_loggers=False)
    req = urllib.request.Request('http://{}:{}/logreset'.format(
        _config_obj.data['web']['plex_accessible_ip'], str(_config_obj.data['web']['plex_accessible_port'])))
    with urllib.request.urlopen(req) as resp:
        content = resp.read()


def logging_enable(_config_obj, _section, _key):
    # update the config_file to enable or disable the log
    # [logger_root]
    # handlers = loghandler, filehandler
    handler_list = []
    if _config_obj.data['handler_filehandler']['enabled']:
        handler_list.append('filehandler')
    if _config_obj.data['handler_loghandler']['enabled']:
        handler_list.append('loghandler')
    handlers = ','.join(handler_list)
    _config_obj.write('logger_root', 'handlers', handlers)
    logging_refresh(_config_obj, _section, _key)


def set_version(_config_obj, _section, _key):
    _config_obj.data[_section][_key] \
        = utils.get_version_str()


def set_system(_config_obj, _section, _key):
    _config_obj.data[_section][_key] \
        = platform.system()


def set_python_version(_config_obj, _section, _key):
    _config_obj.data[_section][_key] \
        = platform.python_version()


def set_user(_config_obj, _section, _key):
    _config_obj.data[_section][_key] \
        = getpass.getuser()


def set_os(_config_obj, _section, _key):
    _config_obj.data[_section][_key] \
        = platform.version()


def set_path(_config_obj, _section, _key, _base_dir, _folder):
    if not _config_obj.data[_section][_key]:
        _config_obj.data[_section][_key] = pathlib.Path(_base_dir).joinpath(_folder)
    else:
        _config_obj.data[_section][_key] = pathlib.Path(_config_obj.data[_section][_key])
    if not _config_obj.data[_section][_key].is_dir():
        _config_obj.data[_section][_key].mkdir()
    _config_obj.data[_section][_key] = str(os.path.abspath(_config_obj.data[_section][_key]))


def set_data_path(_config_obj, _section, _key):
    if _config_obj.data[_section][_key] is None:
        set_path(_config_obj, _section, _key,
                 _config_obj.data['paths']['main_dir'], 'data')


def set_logs_path(_config_obj, _section, _key):
    if _config_obj.data[_section][_key] is None:
        set_path(_config_obj, _section, _key,
                 _config_obj.data['paths']['data_dir'], 'logs')


def set_thumbnails_path(_config_obj, _section, _key):
    if _config_obj.data[_section][_key] is None:
        set_path(_config_obj, _section, _key,
                 _config_obj.data['paths']['data_dir'], 'thumbnails')


def set_temp_path(_config_obj, _section, _key):
    if _config_obj.data[_section][_key] is None:
        set_path(_config_obj, _section, _key,
                 _config_obj.data['paths']['data_dir'], 'tmp')


def set_database_path(_config_obj, _section, _key):
    if _config_obj.data[_section][_key] is None:
        set_path(_config_obj, _section, _key,
                 _config_obj.data['paths']['data_dir'], 'db')


def set_backup_path(_config_obj, _section, _key):
    if _config_obj.data[_section][_key] is None:
        set_path(_config_obj, _section, _key,
                 _config_obj.data['paths']['data_dir'], 'backups')


def set_configdefn_path(_config_obj, _section, _key):
    if _config_obj.data[_section][_key] is None:
        _config_obj.data[_section][_key] = _config_obj.defn_json.defn_path


def set_main_path(_config_obj, _section, _key):
    if _config_obj.data[_section][_key] is None:
        _config_obj.data['paths']['main_dir'] = _config_obj.script_dir


def set_ffmpeg_path(_config_obj, _section, _key):
    if not _config_obj.data[_section][_key]:
        if platform.system() in ['Windows']:
            base_ffmpeg_dir \
                = pathlib.Path(_config_obj.script_dir).joinpath('ffmpeg/bin')
            if base_ffmpeg_dir.is_dir():
                _config_obj.data[_section][_key] \
                    = str(pathlib.Path(base_ffmpeg_dir).joinpath('ffmpeg.exe'))
            else:
                _config_obj.data[_section][_key] = 'ffmpeg.exe'
                _config_obj.logger.notice(
                    'ffmpeg_path does not exist in [cabernet]/ffmpeg/bin, will use PATH env to find ffmpeg.exe')
        else:
            _config_obj.data[_section][_key] = 'ffmpeg'


def set_ffprobe_path(_config_obj, _section, _key):
    if not _config_obj.data[_section][_key]:
        if platform.system() in ['Windows']:
            base_ffmpeg_dir \
                = pathlib.Path(_config_obj.script_dir).joinpath('ffmpeg/bin')
            if base_ffmpeg_dir.is_dir():
                _config_obj.data[_section][_key] \
                    = str(pathlib.Path(base_ffmpeg_dir).joinpath('ffprobe.exe'))
            else:
                _config_obj.data[_section][_key] = 'ffprobe.exe'
                _config_obj.logger.notice(
                    'ffprobe_path does not exist in [cabernet]/ffmpeg/bin, will use PATH env to find ffprobe.exe')
        else:
            _config_obj.data[_section][_key] = 'ffprobe'


def set_streamlink_path(_config_obj, _section, _key):
    if not _config_obj.data[_section][_key]:
        if platform.system() in ['Windows']:
            _config_obj.data[_section][_key] \
                = 'streamlink.exe'
            _config_obj.logger.notice(
                'streamlink_path does not exist in PATH to find streamlink.exe')
        else:
            streamlink_file = os.path.expanduser('~/.local/bin/streamlink')
            if os.path.isfile(streamlink_file):
                _config_obj.data[_section][_key] = streamlink_file
            else:
                _config_obj.data[_section][_key] = 'streamlink'


def set_pdata(_config_obj, _section, _key):
    if not _config_obj.data[_section][_key]:
        _config_obj.data[_section][_key] = \
            utils.PLUGIN_DATA + config_defn.PLUGIN_DATA


def check_encryption(_config_obj, _section, _key):
    if not CRYPTO_LOADED:
        return 'python cryptography module not installed, unable to encrypt'


def load_encrypted_setting(_config_obj, _section, _key):
    if CRYPTO_LOADED and _config_obj.data['main']['use_encryption']:
        if _config_obj.data['main']['encrypt_key'] is None:
            _config_obj.data['main']['encrypt_key'] = encryption.set_fernet_key().decode('utf-8')

        if _config_obj.data[_section][_key] is not None:
            if _config_obj.data[_section][_key].startswith(ENCRYPT_STRING):
                # encrypted
                _config_obj.data[_section][_key] \
                    = encryption.decrypt(
                    _config_obj.data[_section][_key],
                    _config_obj.data['main']['encrypt_key'])
                if _config_obj.data[_section][_key] is None:
                    _config_obj.logger.error(
                        'Unable to decrypt password. ' +
                        'Try updating password in config file in clear text')
            else:
                # not encrypted
                clear_pwd = _config_obj.data[_section][_key]
                encrypted_pwd = encryption.encrypt(
                    _config_obj.data[_section][_key],
                    _config_obj.data['main']['encrypt_key'])
                _config_obj.write(_section, _key, encrypted_pwd)
                _config_obj.data[_section][_key] = clear_pwd


def set_ip(_config_obj, _section, _key):
    if _config_obj.data[_section][_key] == '0.0.0.0':
        _config_obj.data['web']['bind_ip'] = '0.0.0.0'
        if _config_obj.data['web']['plex_accessible_ip'] == '0.0.0.0':
            _config_obj.data['web']['plex_accessible_ip'] \
                = utils.get_ip()
    else:
        _config_obj.data['web']['bind_ip'] \
            = _config_obj.data[_section][_key]
        if _config_obj.data['web']['plex_accessible_ip'] == '0.0.0.0':
            _config_obj.data['web']['plex_accessible_ip'] \
                = _config_obj.data[_section][_key]


def set_netmask(_config_obj, _section, _key):
    if not _config_obj.data[_section][_key]:
        _config_obj.data[_section][_key] = \
            '{}/32'.format(_config_obj.data['web']['plex_accessible_ip'])


def enable_hdhr(_config_obj, _section, _key):
    if not _config_obj.data[_section][_key]:
        if _config_obj.data['hdhomerun']['udp_netmask'] is None:
            _config_obj.data[_section][_key] = True
            return 'ERROR:: [hdhomerun][udp_netmask] must be set when HDHomeRun is enabled, reverted save'


def enable_ssdp(_config_obj, _section, _key):
    if not _config_obj.data[_section][_key]:
        if _config_obj.data['ssdp']['udp_netmask'] is None:
            _config_obj.data[_section][_key] = True
            return 'ERROR:: [ssdp][udp_netmask] must be set when HDHomeRun is enabled, reverted save'


def set_hdhomerun_id(_config_obj, _section, _key):
    if _config_obj.data[_section][_key] is None:
        _config_obj.write(
            _section, _key, hdhr_server.hdhr_gen_device_id())
    elif not hdhr_server.hdhr_validate_device_id(
            _config_obj.data[_section][_key]):
        _config_obj.write(
            _section, _key, hdhr_server.hdhr_gen_device_id())


def set_uuid(_config_obj, _section, _key):
    if _config_obj.data["main"]["uuid"] is None:
        _config_obj.write('main', 'uuid', str(uuid.uuid1()).upper())


def update_instance_label(_config_obj, _section, _key):
    value = _config_obj.data[_section][_key]
    db_confdefn = DBConfigDefn(_config_obj.data)
    areas = db_confdefn.get_area_by_section(_section)
    if len(areas) > 1:
        results = 'WARNING: There is more than one section named {}'.format(_section)
    elif len(areas) == 0:
        return
    else:
        results = None
    section_data = db_confdefn.get_one_section_dict(areas[0], _section)
    section_data[_section]['label'] = value
    db_confdefn.add_section(areas[0], _section, section_data[_section])
    # when instance label is updated, all tasks for that instance are removed
    # a restart is needed. Note added to config label
    db_scheduler = DBScheduler(_config_obj.data)
    namespace, instance = _section.split('_', 1)
    tasks = db_scheduler.get_tasks_by_name(namespace, instance)
    for task in tasks:
        WebHTTPHandler.sched_queue.put({'cmd': 'deltask', 'taskid': task['taskid']})
    return results


def update_channel_num(_config_obj, _section, _key):
    starting_num = _config_obj.data[_section][_key]
    init_num = starting_num
    is_changed = False
    namespace_l, instance = _section.split('_', 1)
    db_channels = DBChannels(_config_obj.data)
    namespaces = db_channels.get_channel_names()
    namespace = {n['namespace']: n for n in namespaces if namespace_l == n['namespace'].lower()}.keys()
    if len(namespace) == 0:
        return 'ERROR: Bad namespace'
    namespace = list(namespace)[0]
    ch_list = db_channels.get_channels(namespace, instance)
    for ch in ch_list.values():
        if starting_num == -1:
            if ch[0]['display_number'] != ch[0]['json']['number']:
                ch[0]['display_number'] = ch[0]['json']['number']
                is_changed = True
        else:
            if ch[0]['display_number'] != starting_num:
                ch[0]['display_number'] = starting_num
                is_changed = True
            starting_num += 1
        if is_changed:
            db_channels.update_channel_number(ch[0])
            is_changed = False

    if init_num == -1:
        return 'Renumbered channels back to default'.format(_section, _key)
    else:
        return 'Renumbered channels starting at {}'.format(_section, _key, init_num)


def set_theme_folders(_defn, _config, _section, _key):
    """
    To make this work, the themes folder must be static and known
    since theme folder list is set before the paths are initialized
    """
    theme_list = []
    themes_path = 'lib.web.htdocs.modules.themes'
    for folder in sorted(importlib.resources.contents(themes_path)):
        if folder.startswith('__'):
            continue
        try:
            importlib.resources.read_text(themes_path, folder)
        except (IsADirectoryError, PermissionError):
            theme_list.append(folder)
        except UnicodeDecodeError:
            continue
    _defn['general']['sections']['display']['settings']['theme']['values'] = theme_list
    theme_default = _defn['general']['sections']['display']['settings']['theme']['default']
    if theme_default not in theme_list:
        _defn['general']['sections']['display']['settings']['theme']['default'] = theme_list[0]
