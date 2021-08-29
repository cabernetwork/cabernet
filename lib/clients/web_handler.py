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

import importlib
import importlib.resources
import logging
import mimetypes
import pathlib
import platform
import socket
import time
import urllib

from http.server import BaseHTTPRequestHandler

import lib.common.utils as utils
from lib.web.pages.templates import web_templates
from lib.config.config_defn import ConfigDefn
from lib.db.db_plugins import DBPlugins
from lib.db.db_channels import DBChannels
from lib.common.pickling import Pickling
from lib.plugins.plugin_handler import PluginHandler


class WebHTTPHandler(BaseHTTPRequestHandler):

    plugins = None
    hdhr_queue = None
    sched_queue = None
    config = None
    logger = None
    channels_db = None
    rmg_station_scans = {}
    namespace_list = None
    total_instances = 0

    def log_message(self, _format, *args):
        if int(args[1]) > 399:
            self.logger.warning('[%s] %s' % (self.address_string(), _format % args))
        else:
            self.logger.info('[%s] %s' % (self.address_string(), _format % args))

    def get_query_data(self):
        content_path = self.path
        query_data = {}
        if self.headers.get('Content-Length') is not None \
                and self.headers.get('Content-Length') != '0':
            post_data = self.rfile.read(int(self.headers.get('Content-Length'))).decode('utf-8')
            # if an input is empty, then it will remove it from the list when the dict is gen
            query_data = urllib.parse.parse_qs(post_data, keep_blank_values=True)
            for key, value in query_data.items():
                if value[0] == '':
                    query_data[key] = [None]
        if self.path.find('?') != -1:
            content_path = self.path[0:self.path.find('?')]
            get_data = self.path[(self.path.find('?') + 1):]
            get_data_elements = get_data.split('&')
            for get_data_item in get_data_elements:
                get_data_item_split = get_data_item.split('=')
                if len(get_data_item_split) > 1:
                    query_data[get_data_item_split[0]] = get_data_item_split[1]
        if 'name' not in query_data:
            query_data['name'] = None
        if 'instance' not in query_data:
            query_data['instance'] = None
        if query_data['instance'] or query_data['name']:
            return content_path, query_data
        path_list = content_path.split('/')
        if len(path_list) > 2:
            instance = None
            for ns in WebHTTPHandler.namespace_list:
                if path_list[1].lower() == ns.lower():
                    namespace = ns
                    del path_list[1]
                    instance_list = WebHTTPHandler.namespace_list[namespace]
                    if len(path_list) > 2:
                        for inst in instance_list:
                            if inst.lower() == path_list[1].lower():
                                instance = inst
                                del path_list[1]
                    query_data['name'] = namespace
                    query_data['instance'] = instance
                    content_path = '/'.join(path_list)
                    break
        return content_path, query_data

    def do_file_response(self, _code, _package, _reply_file):
        if _reply_file:
            try:
                if _package:
                    x = importlib.resources.read_binary(_package, _reply_file)
                else:
                    x_path = pathlib.Path(str(_reply_file))
                    with open(x_path, 'br') as reader:
                        x = reader.read()
                mime_lookup = mimetypes.guess_type(_reply_file)
                self.send_response(_code)
                self.send_header('Content-type', mime_lookup[0])
                self.end_headers()
                try:
                    self.wfile.write(x)
                except BrokenPipeError as ex:
                    self.logger.debug('Client dropped connection while writing out, ignoring. {}'.format(ex))

            except IsADirectoryError as e:
                self.logger.info('1:{}'.format(e))
                self.do_mime_response(401, 'text/html', web_templates['htmlError'].format('401 - Unauthorized'))
            except FileNotFoundError as e:
                self.logger.info('2:{}'.format(e))
                self.do_mime_response(404, 'text/html', web_templates['htmlError'].format('404 - File Not Found'))
            except NotADirectoryError as e:
                self.logger.info('3:{}'.format(e))
                self.do_mime_response(404, 'text/html', web_templates['htmlError'].format('404 - Folder Not Found'))
            except ConnectionAbortedError as e:
                self.logger.info('4:{}'.format(e))
            except ModuleNotFoundError as e:
                self.logger.info('5:{}'.format(e))
                self.do_mime_response(404, 'text/html', web_templates['htmlError'].format('404 - Area Not Found'))

    def do_response(self, _code, _mime, _reply_str=None):
        self.send_response(_code)
        self.send_header('Content-type', _mime)
        self.end_headers()
        if _reply_str:
            try:
                self.wfile.write(_reply_str.encode('utf-8'))
            except BrokenPipeError as ex:
                self.logger.debug('Client dropped connection before results were sent, ignoring. {}'.format(ex))

    def do_mime_response(self, _code, _mime, _reply_str=None):
        self.do_dict_response({ 
            'code': _code, 'headers': {'Content-type': _mime},
            'text': _reply_str
            })

    def do_dict_response(self, rsp_dict):
        """
        { 'code': '[code]', 'headers': { '[name]': '[value]', ... }, 'text': b'...' }
        """
        self.send_response(rsp_dict['code'])
        for header, value in rsp_dict['headers'].items():
            self.send_header(header, value)
        self.end_headers()
        if rsp_dict['text']:
            try:
                self.wfile.write(rsp_dict['text'].encode('utf-8'))
            except BrokenPipeError as ex:
                self.logger.debug('Client dropped connection while writing, ignoring. {}'.format(ex))

    @classmethod
    def init_class_var(cls, _plugins, _hdhr_queue):
        WebHTTPHandler.logger = logging.getLogger(__name__)
        WebHTTPHandler.config = _plugins.config_obj.data
        
        if platform.system() in ['Windows']:
            unpickle_it = Pickling(WebHTTPHandler.config)
            _plugins = unpickle_it.from_pickle(_plugins.__class__.__name__)
            PluginHandler.cls_plugins = _plugins.plugins

        WebHTTPHandler.plugins = _plugins
        WebHTTPHandler.hdhr_queue = _hdhr_queue
        if not cls.plugins.config_obj.defn_json:
            cls.plugins.config_obj.defn_json = ConfigDefn(_config=_plugins.config_obj.data)
        plugins_db = DBPlugins(_plugins.config_obj.data)
        WebHTTPHandler.namespace_list = plugins_db.get_instances()
        WebHTTPHandler.channels_db = DBChannels(_plugins.config_obj.data)
        tmp_rmg_scans = {}
        for plugin_name in _plugins.plugins.keys():
            if 'player-tuner_count' in _plugins.config_obj.data[plugin_name.lower()]:
                tmp_rmg_scans[plugin_name] = []
                for x in range(int(_plugins.config_obj.data[plugin_name.lower()]['player-tuner_count'])):
                    tmp_rmg_scans[plugin_name].append('Idle')
        WebHTTPHandler.rmg_station_scans = tmp_rmg_scans
        if WebHTTPHandler.total_instances == 0:
            WebHTTPHandler.total_instances = _plugins.config_obj.data['web']['concurrent_listeners']

        
    @classmethod
    def start_httpserver(cls, _plugins, _hdhr_queue, _port, _http_server_class, _sched_queue=None):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((_plugins.config_obj.data['web']['bind_ip'], _port))
        server_socket.listen(int(_plugins.config_obj.data['web']['concurrent_listeners']))
        utils.logging_setup(_plugins.config_obj.data)
        logger = logging.getLogger(__name__)
        cls.init_class_var(_plugins, _hdhr_queue, _sched_queue)
        if cls.total_instances == 0:
            _plugins.config_obj.data['web']['concurrent_listeners']
        logger.debug(
            'Now listening for requests. Number of listeners={}'
                .format(cls.total_instances))
        for i in range(cls.total_instances):
            _http_server_class(server_socket, _plugins)
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            pass
