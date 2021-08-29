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

import gc

import argparse
import logging
import os
import platform
import sys
import time
from multiprocessing import Queue, Process

import lib.clients.hdhr.hdhr_server as hdhr_server
import lib.clients.web_tuner as web_tuner
import lib.clients.web_admin as web_admin
import lib.common.utils as utils
import lib.plugins.plugin_handler as plugin_handler
import lib.clients.ssdp.ssdp_server as ssdp_server
import lib.db.datamgmt.backups as backups
import lib.updater.updater as updater
from lib.db.db_scheduler import DBScheduler
from lib.common.utils import clean_exit
from lib.common.pickling import Pickling
from lib.schedule.scheduler import Scheduler
from lib.common.decorators import getrequest
from lib.web.pages.templates import web_templates


try:
    import pip
except ModuleNotFoundError:
    print('Unable to load pip module to install modules')

try:
    import cryptography
except ImportError:
    # pip.main(['install', 'cryptography'])
    print('Unable to load cryptography module, will not encrypt passwords')

import lib.config.user_config as user_config

RESTART_REQUESTED = None
LOGGER = None
    
if sys.version_info.major == 2 or sys.version_info < (3, 7):
    print('Error: Cabernet requires python 3.7+.')
    sys.exit(1)


def get_args():
    parser = argparse.ArgumentParser(description='Fetch online streams', epilog='')
    parser.add_argument('-c', '--config_file', dest='cfg', type=str, default=None, help='config.ini location')
    parser.add_argument('-r', '--restart', help='Restart process')
    return parser.parse_args()


def restart_cabernet(_plugins):
    global RESTART_REQUESTED
    RESTART_REQUESTED = True
    while RESTART_REQUESTED:
        time.sleep(0.10)


@getrequest.route('/api/restart')
def restart_api(_webserver):
    scheduler_db = DBScheduler(_webserver.config)
    tasks = scheduler_db.get_tasks('Applications', 'Restart')
    if len(tasks) == 1:
        _webserver.sched_queue.put({'cmd': 'runtask', 'taskid': tasks[0]['taskid'] })
        _webserver.do_mime_response(200, 'text/html', 'Restarting Cabernet')
    else:
        _webserver.do_mime_response(404, 'text/html', web_templates['htmlError'].format('404 - Request Not Found'))


def main(script_dir):
    """ main startup method for app """
    global RESTART_REQUESTED
    global LOGGER
    hdhr_serverx = None
    ssdp_serverx = None
    webadmin = None
    tuner = None

    # Gather args
    args = get_args()
    if args.restart:
        time.sleep(0.01)

    # Get Operating system
    opersystem = platform.system()
    config_obj = None
    try:
        RESTART_REQUESTED = False

        config_obj = user_config.get_config(script_dir, opersystem, args)
        config = config_obj.data
        LOGGER = logging.getLogger(__name__)

        LOGGER.warning('#########################################')
        LOGGER.warning('MIT License, Copyright (C) 2021 ROCKY4546')
        LOGGER.info('Initiating Cabernet v{}'.format(utils.get_version_str()))

        utils.cleanup_web_temp(config)
        plugins = init_plugins(config_obj)
        config_obj.defn_json = None
        init_versions(plugins)

        scheduler_tasks(config)

        if opersystem in ['Windows']:
            pickle_it = Pickling(config)
            pickle_it.to_pickle(plugins)

        backups.scheduler_tasks(config)
        hdhr_queue = Queue()
        sched_queue = Queue()
        webadmin = init_webadmin(config, plugins, hdhr_queue, sched_queue)
        tuner = init_tuner(config, plugins, hdhr_queue)
        scheduler = Scheduler(plugins, sched_queue)
        time.sleep(0.1)
        ssdp_serverx = init_ssdp(config)
        hdhr_serverx = init_hdhr(config, hdhr_queue)

        if opersystem in ['Windows']:
            time.sleep(2)
            pickle_it.delete_pickle(plugins.__class__.__name__)
        LOGGER.info('Cabernet is now online.')

        RESTART_REQUESTED = False
        while not RESTART_REQUESTED:            
            time.sleep(5)
        RESTART_REQUESTED = False
        LOGGER.info('Shutting Down...')
        time.sleep(1)
        terminate_processes(config, hdhr_serverx, ssdp_serverx, webadmin, tuner, scheduler, config_obj)

    except KeyboardInterrupt:
        LOGGER.info('^C received, shutting down the server')
        shutdown(config, hdhr_serverx, ssdp_serverx, webadmin, tuner, scheduler, config_obj)


def scheduler_tasks(_config):
    scheduler_db = DBScheduler(_config)
    scheduler_db.save_task(
        'Applications',
        'Restart',
        'internal',
        None,
        'lib.main.restart_cabernet',
        20,
        'inline',
        'Restarts Cabernet'
        )


def init_plugins(_config_obj):
    LOGGER.info('Getting Plugins...')
    plugins = plugin_handler.PluginHandler(_config_obj)
    plugins.initialize_plugins()
    return plugins


def init_versions(_plugins):
    updater_obj = updater.Updater(_plugins)
    updater_obj.scheduler_tasks()


def init_webadmin(_config, _plugins, _hdhr_queue, _sched_queue):
    LOGGER.info('Starting admin website on {}:{}'.format(
        _config['web']['plex_accessible_ip'],
        _config['web']['web_admin_port']))
    webadmin = Process(target=web_admin.start, args=(_plugins, _hdhr_queue, _sched_queue))
    webadmin.start()
    time.sleep(0.1)
    return webadmin


def init_tuner(_config, _plugins, _hdhr_queue):
    LOGGER.info('Starting streaming tuner website on {}:{}'.format(
        _config['web']['plex_accessible_ip'],
        _config['web']['plex_accessible_port']))
    tuner = Process(target=web_tuner.start, args=(_plugins, _hdhr_queue,))
    tuner.start()
    time.sleep(0.1)
    return tuner


def init_ssdp(_config):
    if not _config['ssdp']['disable_ssdp']:
        LOGGER.info('Starting SSDP service on port 1900')
        ssdp_serverx = Process(target=ssdp_server.ssdp_process, args=(_config,))
        ssdp_serverx.daemon = True
        ssdp_serverx.start()
        time.sleep(0.1)
        return ssdp_serverx
    return None


def init_hdhr(_config, _hdhr_queue):
    if not _config['hdhomerun']['disable_hdhr']:
        LOGGER.info('Starting HDHR service on port 65001')
        hdhr_serverx = Process(target=hdhr_server.hdhr_process, args=(_config, _hdhr_queue,))
        hdhr_serverx.start()
        time.sleep(0.1)
        return hdhr_serverx
    return None


def shutdown(_config, _hdhr_serverx, _ssdp_serverx, _webadmin, _tuner, _scheduler, _config_obj):
    terminate_processes(_config, _hdhr_serverx, _ssdp_serverx, _webadmin, _tuner, _scheduler, _config_obj)
    clean_exit()


def terminate_processes(_config, _hdhr_serverx, _ssdp_serverx, _webadmin, _tuner, _scheduler, _config_obj):
    if not _config['hdhomerun']['disable_hdhr'] and _hdhr_serverx:
        _hdhr_serverx.terminate()
        _hdhr_serverx.join()
        del _hdhr_serverx
    if not _config['ssdp']['disable_ssdp'] and _ssdp_serverx:
        _ssdp_serverx.terminate()
        _ssdp_serverx.join()
        del _ssdp_serverx
    if _scheduler:
        _scheduler.terminate()
        del _scheduler
    if _webadmin:
        _webadmin.terminate()
        _webadmin.join()
        del _webadmin
    if _tuner:
        _tuner.terminate()
        _tuner.join()
        del _tuner
    if _config_obj and _config_obj.defn_json:
        _config_obj.defn_json.terminate()
        del _config_obj
