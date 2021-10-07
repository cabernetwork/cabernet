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

import json
import urllib

from lib.common.decorators import getrequest
from lib.db.db_scheduler import DBScheduler


@getrequest.route('/api/dashstatus.js')
def pages_dashstatus_js(_webserver):
    dashstatus_js = DashStatusJS() 
    _webserver.do_mime_response(200, 'text/javascript', dashstatus_js.get(_webserver.config))
    return True


class DashStatusJS:

    @staticmethod
    def get(_config):
        js = ''.join([
            'var tunerstatus = ', DashStatusJS.get_tuner_status(_config),
            '; var schedstatus = ', DashStatusJS.get_scheduler_status(_config)
        ])
        return js

    @staticmethod
    def get_tuner_status(_config):
        web_tuner_url = 'http://localhost:' + \
            str(_config['web']['plex_accessible_port'])
        url = ( web_tuner_url + '/tunerstatus')
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as resp:
            result = resp.read()
        return result.decode('utf-8')

    @staticmethod
    def get_scheduler_status(_config):
        scheduler_db = DBScheduler(_config)
        active_tasks = scheduler_db.get_tasks_by_active()
        return json.dumps(active_tasks, default=str)
