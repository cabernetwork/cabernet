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

import os
import json
import logging
import os
import pathlib
import signal
import threading
import time
import urllib
from threading import Thread
from logging import config
from http.server import HTTPServer
from urllib.parse import urlparse

from lib.common import utils
from lib.common.decorators import gettunerrequest
from lib.web.pages.templates import web_templates
from lib.db.db_config_defn import DBConfigDefn
from lib.streams.m3u8_redirect import M3U8Redirect
from lib.streams.internal_proxy import InternalProxy
from lib.streams.ffmpeg_proxy import FFMpegProxy
from lib.streams.streamlink_proxy import StreamlinkProxy
from lib.streams.thread_queue import ThreadQueue
from .web_handler import WebHTTPHandler


@gettunerrequest.route('/tunerstatus')
def tunerstatus(_webserver):
    _webserver.do_mime_response(200, 'application/json', json.dumps(WebHTTPHandler.rmg_station_scans, cls=ObjectJsonEncoder))


@gettunerrequest.route('RE:/watch/.+')
def watch(_webserver):
    sid = _webserver.content_path.replace('/watch/', '')
    _webserver.do_tuning(sid, _webserver.query_data['name'], _webserver.query_data['instance'])


@gettunerrequest.route('/logreset')
def logreset(_webserver):
    logging.config.fileConfig(fname=_webserver.config['paths']['config_file'],
                              disable_existing_loggers=False)
    _webserver.do_mime_response(200, 'text/html')


@gettunerrequest.route('RE:/auto/v.+')
def autov(_webserver):
    channel = _webserver.content_path.replace('/auto/v', '')
    station_list = TunerHttpHandler.channels_db.get_channels(
        _webserver.query_data['name'], _webserver.query_data['instance'])

    # check channel number with adjustments
    for station in station_list.keys():
        updated_chnum = utils.wrap_chnum(
            str(station_list[station][0]['display_number']), station_list[station][0]['namespace'],
            station_list[station][0]['instance'], _webserver.config)
        if updated_chnum == channel:
            _webserver.do_tuning(station, _webserver.query_data['name'],
                                 _webserver.query_data['instance'])
            return

    _webserver.do_mime_response(503, 'text/html', web_templates['htmlError'].format('503 - Unknown channel'))


class ObjectJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ThreadQueue):
            return str(obj)
        else:
            return json.JSONEncoder.default(self.obj)


class TunerHttpHandler(WebHTTPHandler):

    def __init__(self, *args):
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        self.script_dir = pathlib.Path(os.path.dirname(os.path.abspath(__file__)))
        self.ffmpeg_proc = None  # process for running ffmpeg
        self.block_moving_avg = 0
        self.last_refresh = None
        self.block_prev_pts = 0
        self.block_prev_time = None
        self.buffer_prev_time = None
        self.block_max_pts = 0
        self.small_pkt_streaming = False
        self.real_namespace = None
        self.real_instance = None
        self.content_path = None
        self.query_data = None
        self.m3u8_redirect = M3U8Redirect(TunerHttpHandler.plugins, TunerHttpHandler.hdhr_queue)
        self.internal_proxy = InternalProxy(TunerHttpHandler.plugins, TunerHttpHandler.hdhr_queue)
        self.ffmpeg_proxy = FFMpegProxy(TunerHttpHandler.plugins, TunerHttpHandler.hdhr_queue)
        self.streamlink_proxy = StreamlinkProxy(TunerHttpHandler.plugins, TunerHttpHandler.hdhr_queue)
        self.db_configdefn = DBConfigDefn(self.config)
        try:
            super().__init__(*args)
        except ConnectionResetError as ex:
            self.logger.warning(
                'ConnectionResetError occurred, will try again {}'
                .format(ex))
            time.sleep(1)
            super().__init__(*args)
        except ValueError as ex:
            self.logger.warning(
                'ValueError occurred, Bad stream recieved.  {}'
                .format(ex))
            raise

    def do_GET(self):
        try:
            self.content_path, self.query_data = self.get_query_data()
            if gettunerrequest.call_url(self, self.content_path):
                pass
            else:
                self.logger.warning('Unknown request to {}'.format(self.content_path))
                self.do_mime_response(501, 'text/html', web_templates['htmlError'].format('501 - Not Implemented'))
        except Exception as ex:
            self.logger.exception('{}{}'.format(
                'UNEXPECTED EXCEPTION on GET=', ex))

    def do_POST(self):
        try:
            self.content_path = self.path
            self.query_data = {}
            # get POST data
            if self.headers.get('Content-Length') != '0':
                post_data = self.rfile.read(int(self.headers.get('Content-Length'))).decode('utf-8')
                # if an input is empty, then it will remove it from the list when the dict is gen
                self.query_data = urllib.parse.parse_qs(post_data)

            # get QUERYSTRING
            if self.path.find('?') != -1:
                get_data = self.path[(self.path.find('?') + 1):]
                get_data_elements = get_data.split('&')
                for get_data_item in get_data_elements:
                    get_data_item_split = get_data_item.split('=')
                    if len(get_data_item_split) > 1:
                        self.query_data[get_data_item_split[0]] = get_data_item_split[1]

            self.do_mime_response(501, 'text/html', web_templates['htmlError'].format('501 - Badly Formatted Message'))
        except Exception as ex:
            self.logger.exception('{}{}'.format(
                'UNEXPECTED EXCEPTION on POST=', ex))

    def do_tuning(self, sid, _namespace, _instance):
        # refresh the config data in case it changed in the web_admin process
        self.plugins.config_obj.refresh_config_data()
        self.config = self.db_configdefn.get_config()
        self.plugins.config_obj.data = self.config
        # try:
        station_list = TunerHttpHandler.channels_db.get_channels(_namespace, _instance)
        try:
            self.real_namespace, self.real_instance, station_data = self.get_ns_inst_station(station_list[sid])
            if not self.config[self.real_namespace.lower()]['enabled']:
                self.logger.warning(
                    'Plugin is not enabled, ignoring request: {} sid:{}'
                    .format(self.real_namespace, sid))
                self.do_mime_response(503, 'text/html', web_templates['htmlError'].format('503 - Plugin Disabled'))
                return
            if not self.plugins.plugins[self.real_namespace].plugin_obj:
                self.logger.warning(
                    'Plugin not initialized, ignoring request: {}:{} sid:{}'
                    .format(self.real_namespace, self.real_instance, sid))
                self.do_mime_response(503, 'text/html',
                                      web_templates['htmlError'].format('503 - Plugin Not Initialized'))
                return
            section = self.plugins.plugins[self.real_namespace].plugin_obj.instances[self.real_instance].config_section
            if not self.config[section]['enabled']:
                self.logger.warning(
                    'Plugin Instance is not enabled, ignoring request: {}:{} sid:{}'
                    .format(self.real_namespace, self.real_instance, sid))
                self.do_mime_response(503, 'text/html',
                                      web_templates['htmlError'].format('503 - Plugin Instance Disabled'))
                return
        except (KeyError, TypeError):
            self.logger.warning(
                'Unknown Channel ID, not found in database {} {} {}'
                .format(_namespace, _instance, sid))
            self.do_mime_response(503, 'text/html', web_templates['htmlError'].format('503 - Unknown channel'))
            return
        self.logger.notice('{}:{} Tuning to channel {}'.format(self.real_namespace, self.real_instance, sid))
        if self.config[section]['player-stream_type'] == 'm3u8redirect':
            self.do_dict_response(self.m3u8_redirect.gen_m3u8_response(station_data))
            return
        elif self.config[section]['player-stream_type'] == 'internalproxy':
            resp = self.internal_proxy.gen_response(
                self.real_namespace, self.real_instance, 
                station_data['display_number'], station_data['json'].get('VOD'))
            self.do_dict_response(resp)
            if resp['tuner'] < 0:
                return
            else:
                self.internal_proxy.stream(station_data, self.wfile, self.terminate_queue)
        elif self.config[section]['player-stream_type'] == 'ffmpegproxy':
            resp = self.ffmpeg_proxy.gen_response(
                self.real_namespace, self.real_instance, 
                station_data['display_number'], station_data['json'].get('VOD'))
            self.do_dict_response(resp)
            if resp['tuner'] < 0:
                return
            else:
                self.ffmpeg_proxy.stream(station_data, self.wfile)
        elif self.config[section]['player-stream_type'] == 'streamlinkproxy':
            resp = self.streamlink_proxy.gen_response(
                self.real_namespace, self.real_instance, 
                station_data['display_number'], station_data['json'].get('VOD'))
            self.do_dict_response(resp)
            if resp['tuner'] < 0:
                return
            else:
                self.streamlink_proxy.stream(station_data, self.wfile)
        else:
            self.do_mime_response(501, 'text/html', web_templates['htmlError'].format('501 - Unknown streamtype'))
            self.logger.error('Unknown [player-stream_type] {}'
                              .format(self.config[section]['player-stream_type']))
            return
        station_scans = WebHTTPHandler.rmg_station_scans[self.real_namespace][resp['tuner']]
        if station_scans != 'Idle':
            if station_scans['mux'] is None or not station_scans['mux'].is_alive():
                self.logger.notice('Provider Connection Closed, ch_id={} {}'.format(sid, threading.get_ident()))
                WebHTTPHandler.rmg_station_scans[self.real_namespace][resp['tuner']] = 'Idle'
            else:
                self.logger.info('1 Client Connection Closed, provider continuing ch_id={} {}'.format(sid, threading.get_ident()))
        else:
            self.logger.info('2 Client Connection Closed, provider continuing ch_id={} {}'.format(sid, threading.get_ident()))
        time.sleep(0.01)

    def get_ns_inst_station(self, _station_data):
        lowest_namespace = _station_data[0]['namespace']
        lowest_instance = _station_data[0]['instance']
        station = _station_data[0]

        # do simple checks first.
        # is there only one channel?
        if len(_station_data) == 1:
            return lowest_namespace, \
                lowest_instance, \
                station

        # Is there only one channel instance enabled?
        i = 0
        for one_station in _station_data:
            if one_station['enabled']:
                station = one_station
                i += 1
        if i == 1:
            return station['namespace'], \
                station['instance'], \
                station

        # round robin capability when instances are tied to a single provider
        # must make sure the channel is enabled for both instances
        ns = []
        inst = []
        counter = {}
        for one_station in _station_data:
            ns.append(one_station['namespace'])
            inst.append(one_station['instance'])
            counter[one_station['instance']] = 0
        for namespace, status_list in WebHTTPHandler.rmg_station_scans.items():
            for status in status_list:
                if type(status) is dict:
                    if status['instance'] not in counter:
                        counter[status['instance']] = 1
                    else:
                        counter[status['instance']] += 1

        # pick the instance with the lowest counter
        lowest_value = 100
        for instance, value in counter.items():
            if value < lowest_value:
                lowest_value = value
                lowest_instance = instance
        for i in range(len(inst)):
            if inst[i] == lowest_instance:
                lowest_namespace = ns[i]
                break

        # find the station data associated with the pick
        for one_station in _station_data:
            if one_station['namespace'] == lowest_namespace and \
                    one_station['instance'] == lowest_instance:
                station = one_station
                break
        return lowest_namespace, lowest_instance, station

    @classmethod
    def init_class_var_sub(cls, _plugins, _hdhr_queue, _terminate_queue, _sched_queue):
        WebHTTPHandler.logger = logging.getLogger(__name__)
        tuner_count = 0
        for plugin_name in _plugins.plugins.keys():
            if plugin_name:
                if _plugins.config_obj.data.get(plugin_name.lower()):
                    if 'player-tuner_count' in _plugins.config_obj.data[plugin_name.lower()]:
                        WebHTTPHandler.logger.debug('{} Implementing {} tuners for {}'
                                                    .format(cls.__name__,
                                                            _plugins.config_obj.data[plugin_name.lower()][
                                                                'player-tuner_count'],
                                                            plugin_name))
                        tuner_count += _plugins.config_obj.data[plugin_name.lower()]['player-tuner_count']
        WebHTTPHandler.total_instances = tuner_count
        super(TunerHttpHandler, cls).init_class_var(_plugins, _hdhr_queue, _terminate_queue)


class TunerHttpServer(Thread):

    def __init__(self, server_socket, _plugins):
        Thread.__init__(self)
        self.bind_ip = _plugins.config_obj.data['web']['bind_ip']
        self.bind_port = _plugins.config_obj.data['web']['plex_accessible_port']
        self.socket = server_socket
        self.server_close = None
        self.start()

    def run(self):
        HttpHandlerClass = FactoryTunerHttpHandler()
        httpd = HTTPServer((self.bind_ip, int(self.bind_port)), HttpHandlerClass, bind_and_activate=False)
        httpd.socket = self.socket
        httpd.server_bind = self.server_close = lambda self: None
        httpd.serve_forever()


def FactoryTunerHttpHandler():
    class CustomHttpHandler(TunerHttpHandler):
        def __init__(self, *args, **kwargs):
            super(CustomHttpHandler, self).__init__(*args, **kwargs)

    return CustomHttpHandler

def child_exited(sig, frame):
    logger = logging.getLogger(__name__)
    try:
        pid, exitcode = os.wait()
        logger.warning('Child process {} exited with code {}'.format(pid, exitcode))
    except ChildProcessError as ex:
        logger.warning('Child exit error {}'.format(str(ex)))

def start(_plugins, _hdhr_queue, _terminate_queue):
    # uncomment this to find out about m3u8 subprocess exits
    #signal.signal(signal.SIGCHLD, child_exited)
    TunerHttpHandler.start_httpserver(
        _plugins, _hdhr_queue, _terminate_queue,
        _plugins.config_obj.data['web']['plex_accessible_port'],
        TunerHttpServer)
