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
import threading
import urllib.request

import lib.common.utils as utils
from lib.db.db_epg import DBepg
from lib.common.decorators import handle_url_except
from lib.common.decorators import handle_json_except



class PluginPrograms:

    def __init__(self, _instance_obj):
        self.logger = logging.getLogger(__name__)
        self.instance_obj = _instance_obj
        self.config_obj = self.instance_obj.config_obj
        self.instance_key = _instance_obj.instance_key
        self.plugin_obj = _instance_obj.plugin_obj
        self.config_section = self.instance_obj.config_section

    def get_program_info(self, _prog_id):
        """
        Interface method to override
        """
        pass

    @handle_url_except(timeout=10.0)
    @handle_json_except
    def get_uri_data(self, _uri, _header=None):
        if _header is None:
            header = {'User-agent': utils.DEFAULT_USER_AGENT}
        else:
            header = _header
        req = urllib.request.Request(_uri, headers=header)
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            x = json.load(resp)
        return x





    def check_logger_refresh(self):
        if not self.logger.isEnabledFor(40):
            self.logger = logging.getLogger(__name__+str(threading.get_ident()))
            self.logger.notice('######## CHECKING AND UPDATING LOGGER3')
