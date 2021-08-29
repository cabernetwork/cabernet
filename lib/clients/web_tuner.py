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
import urllib
import pathlib
import logging
from threading import Thread
from logging import config
from http.server import HTTPServer
from urllib.parse import urlparse

from lib.web.pages.templates import web_templates
from lib.db.db_config_defn import DBConfigDefn
from lib.streams.m3u8_redirect import M3U8Redirect
from lib.streams.internal_proxy import InternalProxy
from lib.streams.ffmpeg_proxy import FFMpegProxy
from .web_handler import WebHTTPHandler


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
        self.m3u8_redirect = M3U8Redirect(TunerHttpHandler.plugins, TunerHttpHandler.hdhr_queue)
        self.internal_proxy = InternalProxy(TunerHttpHandler.plugins, TunerHttpHandler.hdhr_queue)
        self.ffmpeg_proxy = FFMpegProxy(TunerHttpHandler.plugins, TunerHttpHandler.hdhr_queue)
        self.db_configdefn = DBConfigDefn(self.config)
        try:
            super().__init__(*args)
        except ConnectionResetError:
            self.logger.warning('########## ConnectionResetError occurred, will try again')
            time.sleep(1)
            super().__init__(*args)
        except ValueError:
            self.logger.warning('ValueError occurred, Bad stream recieved.  Could be HTTPS or the stream was disconnected early')




    def do_GET(self):
        content_path, query_data = self.get_query_data()
        if content_path.startswith('/auto/v'):
            channel = content_path.replace('/auto/v', '')
            station_list = TunerHttpHandler.channels_db.get_channels(query_data['name'], query_data['instance'])
            if channel not in station_list.keys():
                # check channel number
                for station in station_list.keys():
                    if station_list[station]['number'] == channel:
                        self.do_tuning(station, query_data['name'], query_data['instance'])
                        return
            else:
                self.do_tuning(channel, query_data['name'], query_data['instance'])
                return
            self.do_mime_response(501, 'text/html', web_templates['htmlError'].format('501 - Unknown channel'))

        elif content_path.startswith('/logreset'):
            logging.config.fileConfig(fname=self.config['paths']['config_file'], disable_existing_loggers=False)
            self.do_mime_response(200, 'text/html')

        elif content_path.startswith('/watch'):
            sid = content_path.replace('/watch/', '')
            self.do_tuning(sid, query_data['name'], query_data['instance'])
        else:
            self.logger.warning("Unknown request to " + content_path)
            self.do_mime_response(501, 'text/html', web_templates['htmlError'].format('501 - Not Implemented'))
        return

    def do_POST(self):
        content_path = self.path
        query_data = {}
        self.logger.debug('Receiving a post form {}'.format(content_path))
        # get POST data
        if self.headers.get('Content-Length') != '0':
            post_data = self.rfile.read(int(self.headers.get('Content-Length'))).decode('utf-8')
            # if an input is empty, then it will remove it from the list when the dict is gen
            query_data = urllib.parse.parse_qs(post_data)

        # get QUERYSTRING
        if self.path.find('?') != -1:
            get_data = self.path[(self.path.find('?') + 1):]
            get_data_elements = get_data.split('&')
            for get_data_item in get_data_elements:
                get_data_item_split = get_data_item.split('=')
                if len(get_data_item_split) > 1:
                    query_data[get_data_item_split[0]] = get_data_item_split[1]

        self.do_mime_response(501, 'text/html', web_templates['htmlError'].format('501 - Badly Formatted Message'))
        return

    def do_tuning(self, sid, _namespace, _instance):

        # refresh the config data in case it changed in the web_admin process
        self.plugins.config_obj.refresh_config_data()
        self.config = self.plugins.config_obj.data
        self.config = self.db_configdefn.get_config()
        self.plugins.config_obj.data = self.config
        #try:
        station_list = TunerHttpHandler.channels_db.get_channels(_namespace, _instance)
        try:
            self.real_namespace, self.real_instance, station_data = self.get_ns_inst_station(station_list[sid])
        except KeyError:
            self.logger.warning('Unknown channel ID, not found in database {} {} {}'.format(_namespace, _instance, sid))
            self.do_mime_response(501, 'text/html', web_templates['htmlError'].format('501 - Unknown channel'))
            return
        if self.config[self.real_namespace.lower()]['player-stream_type'] == 'm3u8redirect':
            self.do_dict_response(self.m3u8_redirect.gen_m3u8_response(station_data))
            return
        elif self.config[self.real_namespace.lower()]['player-stream_type'] == 'internalproxy':
            resp = self.internal_proxy.gen_response(self.real_namespace, self.real_instance, station_data['number'], TunerHttpHandler)
            self.do_dict_response(resp)
            if resp['tuner'] < 0:
                return
            else:
                self.internal_proxy.stream_direct(station_data, self.wfile)
        elif self.config[self.real_namespace.lower()]['player-stream_type'] == 'ffmpegproxy':
            resp = self.ffmpeg_proxy.gen_response(self.real_namespace, self.real_instance, station_data['number'], TunerHttpHandler)
            self.do_dict_response(resp)
            if resp['tuner'] < 0:
                return
            else:
                self.ffmpeg_proxy.stream_ffmpeg(station_data, self.wfile)
        else:
            self.do_mime_response(501, 'text/html', web_templates['htmlError'].format('501 - Unknown streamtype'))
            self.logger.error('Unknown [player-stream_type] {}'
                .format(self.config[self.real_namespace.lower()]['player-stream_type']))
            return
        self.logger.info('1 Provider Connection Closed')
        WebHTTPHandler.rmg_station_scans[self.real_namespace][resp['tuner']] = 'Idle'


    def get_ns_inst_station(self, _station_data):
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
        lowest_instance = None
        for instance, value in counter.items():
            if value < lowest_value:
                lowest_value = value
                lowest_instance = instance
        
        lowest_namespace = None
        for i in range(len(inst)):
            if inst[i] == lowest_instance:
                lowest_namespace = ns[i]
        
        # find the station data associated with the pick
        station = None
        for one_station in _station_data:
            if one_station['namespace'] == lowest_namespace and \
                    one_station['instance'] == lowest_instance:
                station = one_station
                break
        return lowest_namespace, lowest_instance, station


    @classmethod
    def init_class_var(cls, _plugins, _hdhr_queue, _sched_queue):
        WebHTTPHandler.logger = logging.getLogger(__name__)
        tuner_count = 0
        for plugin_name in _plugins.plugins.keys():
            if 'player-tuner_count' in _plugins.config_obj.data[plugin_name.lower()]:
                WebHTTPHandler.logger.debug('{} Implementing {} tuners for {}'
                    .format(cls.__name__,
                    _plugins.config_obj.data[plugin_name.lower()]['player-tuner_count'],
                    plugin_name))
                tuner_count += _plugins.config_obj.data[plugin_name.lower()]['player-tuner_count']
        WebHTTPHandler.total_instances = tuner_count
        super(TunerHttpHandler, cls).init_class_var(_plugins, _hdhr_queue)


class TunerHttpServer(Thread):

    def __init__(self, server_socket, _plugins):
        Thread.__init__(self)
        self.bind_ip = _plugins.config_obj.data['web']['bind_ip']
        self.bind_port = _plugins.config_obj.data['web']['plex_accessible_port']
        self.socket = server_socket
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


def start(_plugins, _hdhr_queue):
    TunerHttpHandler.start_httpserver(
        _plugins, _hdhr_queue,
        _plugins.config_obj.data['web']['plex_accessible_port'],
        TunerHttpServer)
