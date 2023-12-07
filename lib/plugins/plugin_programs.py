"""
MIT License

Copyright (C) 2023 ROCKY4546
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
import logging
import threading

import lib.common.utils as utils
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

    def terminate(self):
        """
        Removes all has a object from the object and calls any subclasses to also terminate
        Not calling inherited class at this time
        """
        self.logger = None
        self.instance_obj = None
        self.config_obj = None
        self.instance_key = None
        self.plugin_obj = None
        self.config_section = None

    @handle_url_except()
    @handle_json_except
    def get_uri_data(self, _uri, _retries, _header=None):
        if _header is None:
            header = {'User-agent': utils.DEFAULT_USER_AGENT}
        else:
            header = _header
        resp = self.plugin_obj.http_session.get(_uri, headers=header, timeout=8)
        x = resp.json()
        resp.raise_for_status()
        return x

    def check_logger_refresh(self):
        if not self.logger.isEnabledFor(40):
            self.logger = logging.getLogger(__name__ + str(threading.get_ident()))
