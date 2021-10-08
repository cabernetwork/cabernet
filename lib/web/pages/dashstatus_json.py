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
import json
import logging
import urllib

from lib.common.decorators import getrequest
from lib.common.decorators import handle_url_except
from lib.db.db_scheduler import DBScheduler


@getrequest.route('/api/dashstatus.json')
def pages_dashstatus_json(_webserver):
    dashstatus_js = DashStatusJS(_webserver.config)
    expire_time = datetime.datetime.utcnow()
    expire_str = expire_time.strftime("%a, %d %b %Y %H:%M:%S GMT")
    _webserver.do_dict_response({ 
            'code': 200, 'headers': {'Content-type': 'application/json',
            'Expires': expire_str
            },
            'text': dashstatus_js.get()
            })
    return True


class DashStatusJS:

    def __init__(self, _config):
        self.logger = logging.getLogger(__name__)
        self.config = _config

    def get(self):
        js = ''.join([
            '{ "tunerstatus": ', self.get_tuner_status(),
            ', "schedstatus": ', self.get_scheduler_status(),
            '}'
        ])
        return js

    def get_tuner_status(self):
        web_tuner_url = 'http://localhost:' + \
            str(self.config['web']['plex_accessible_port'])
        url = ( web_tuner_url + '/tunerstatus')
        return self.get_url(url)

    @handle_url_except()
    def get_url(self, _url):
        req = urllib.request.Request(_url)
        with urllib.request.urlopen(req) as resp:
            result = resp.read()
        return result.decode('utf-8')

    def get_scheduler_status(self):
        scheduler_db = DBScheduler(self.config)
        active_tasks = scheduler_db.get_tasks_by_active()
        return json.dumps(active_tasks, default=str)
