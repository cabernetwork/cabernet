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

import errno
import os
import time
import pathlib
import re
from threading import Thread
from http.server import HTTPServer

from lib.common.decorators import getrequest
from lib.common.decorators import postrequest
from lib.common.decorators import filerequest
from lib.web.pages.templates import web_templates
from .web_handler import WebHTTPHandler


@filerequest.route('/html/', '/images/', '/modules/')
def lib_web_htdocs(_webserver):
    valid_check = re.match(r'^(/([A-Za-z0-9\._\-]+)/[A-Za-z0-9\._\-/]+)[?%&A-Za-z0-9\._\-/=]*$', _webserver.path)
    if not valid_check:
        return False
    file_path = valid_check.group(1)
    htdocs_path = _webserver.config['paths']['www_pkg']
    path_list = file_path.split('/')
    fullfile_path = htdocs_path + '.'.join(path_list[:-1])
    _webserver.do_file_response(200, fullfile_path, path_list[-1])
    return True


@filerequest.route('/temp/')
def data_web(_webserver):
    valid_check = re.match(r'^(/([A-Za-z0-9\._\-]+)/[A-Za-z0-9\._\-/]+)[?%&A-Za-z0-9\._\-/=]*$', _webserver.path)
    if not valid_check:
        return False
    url_path = valid_check.group(1)

    temp_path = pathlib.Path(_webserver.config['paths']['data_dir'],
        'web')
    if not temp_path.exists():
        return False
    path_list = url_path.split('/')
    file_path = temp_path.joinpath(*path_list[:])
    _webserver.do_file_response(200, None, file_path)


class WebAdminHttpHandler(WebHTTPHandler):
    # class variables
    hdhr_station_scan = -1

    def __init__(self, *args):
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        self.script_dir = pathlib.Path(os.path.dirname(os.path.abspath(__file__)))
        self.stream_url = self.config['web']['plex_accessible_ip'] + \
            ':' + str(self.config['web']['plex_accessible_port'])
        self.web_admin_url = self.config['web']['plex_accessible_ip'] + \
            ':' + str(self.config['web']['web_admin_port'])
        self.content_path = None
        self.query_data = None

        try:
            super().__init__(*args)
        except ConnectionResetError:
            self.logger.warning('########## ConnectionResetError occurred, will try again')
            time.sleep(1)
            super().__init__(*args)
        except ValueError:
            self.logger.warning('ValueError occurred, Bad stream recieved.  Could be HTTPS or the stream was disconnected early')
        

    def do_GET(self):
        try:
            valid_check = re.match(r'^(/([A-Za-z0-9\._\-]+)/[A-Za-z0-9\._\-/]+)[?%&A-Za-z0-9\._\-/=]*$', self.path)
            self.content_path, self.query_data = self.get_query_data()
            self.plugins.config_obj.refresh_config_data()
            self.config = self.plugins.config_obj.data
            if getrequest.call_url(self, self.content_path):
                pass
            elif filerequest.call_url(self, self.content_path):
                pass
            else:
                self.logger.info('UNKNOWN HTTP Request {}'.format(self.content_path))
                self.do_mime_response(501, 'text/html', 
                    web_templates['htmlError'].format('501 - Not Implemented'))
            return
        except MemoryError as e:
            self.logger.error('UNKNOWN MEMORY EXCEPTION: {}'.format(e))
            self.do_mime_response(501, 'text/html', 
                web_templates['htmlError'].format('501 - {}'.format(e)))
        except IOError as e:
            if e.errno in [errno.EPIPE, errno.ECONNABORTED, errno.ECONNRESET, errno.ECONNREFUSED]:
                self.logger.info('Connection dropped by end device {}'.format(e))
            else:
                self.logger.error('{}{}'.format(
                    'UNEXPECTED IOERROR EXCEPTION=', e))
                raise

    def do_POST(self):
        self.content_path = self.path
        self.logger.debug('Receiving POST form {} {}'.format(self.content_path, self.query_data))
        # get POST data
        self.content_path, self.query_data = self.get_query_data()
        self.plugins.config_obj.refresh_config_data()
        self.config = self.plugins.config_obj.data
        if postrequest.call_url(self, self.content_path):
            pass
        else:
            self.logger.info('UNKNOWN HTTP POST Request {}'.format(self.content_path))
            self.do_mime_response(501, 'text/html', web_templates['htmlError'].format('501 - Not Implemented'))
        return

    @classmethod
    def get_ns_inst_path(cls, _query_data):
        if _query_data['name']:
            path = '/'+_query_data['name']
        else:
            path = ''
        if _query_data['instance']:
            path += '/'+_query_data['instance']
        return path

    def put_hdhr_queue(self, _namespace, _index, _channel, _status):
        if not self.config['hdhomerun']['disable_hdhr']:
            WebAdminHttpHandler.hdhr_queue.put(
                {'namespace': _namespace, 'tuner': _index, 'channel': _channel, 'status': _status})

    def update_scan_status(self, _namespace, _new_status):
        if _new_status == 'Scan':
            old_status = 'Idle'
        else:
            old_status = 'Scan'
            
        if _namespace is None:
            for namespace, status_list in WebAdminHttpHandler.rmg_station_scans.items():
                for i, status in enumerate(status_list):
                    if status == old_status:
                        WebAdminHttpHandler.rmg_station_scans[namespace][i] = _new_status
                        self.put_hdhr_queue(namespace, i, None, _new_status)
        else:
            status_list = WebAdminHttpHandler.rmg_station_scans[_namespace]
            for i, status in enumerate(status_list):
                if status == old_status:
                    WebAdminHttpHandler.rmg_station_scans[_namespace][i] = _new_status
                    self.put_hdhr_queue(_namespace, i, None, _new_status)

    @property
    def scan_state(self):
        return WebAdminHttpHandler.hdhr_station_scan

    @scan_state.setter
    def scan_state(self, new_value):
        WebAdminHttpHandler.hdhr_station_scan = new_value

    @classmethod
    def init_class_var(cls, _plugins, _hdhr_queue, _sched_queue):
        super(WebAdminHttpHandler, cls).init_class_var(_plugins, _hdhr_queue)
        WebAdminHttpHandler.sched_queue = _sched_queue
        getrequest.log_urls()
        postrequest.log_urls()
        filerequest.log_urls()
        

class WebAdminHttpServer(Thread):

    def __init__(self, server_socket, _plugins):
        Thread.__init__(self)
        self.bind_ip = _plugins.config_obj.data['web']['bind_ip']
        self.bind_port = _plugins.config_obj.data['web']['web_admin_port']
        self.socket = server_socket
        self.start()

    def run(self):
        HttpHandlerClass = FactoryWebAdminHttpHandler()
        httpd = HTTPServer((self.bind_ip, self.bind_port), HttpHandlerClass, bind_and_activate=False)
        httpd.socket = self.socket
        httpd.server_bind = self.server_close = lambda self: None
        httpd.server_activate()
        httpd.serve_forever()


def FactoryWebAdminHttpHandler():
    class CustomWebAdminHttpHandler(WebAdminHttpHandler):
        def __init__(self, *args, **kwargs):
            super(CustomWebAdminHttpHandler, self).__init__(*args, **kwargs)
    return CustomWebAdminHttpHandler


def start(_plugins, _hdhr_queue, _sched_queue):
    WebAdminHttpHandler.start_httpserver(
        _plugins, _hdhr_queue,
        _plugins.config_obj.data['web']['web_admin_port'],
        WebAdminHttpServer, _sched_queue)
