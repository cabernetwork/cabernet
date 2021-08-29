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

import logging

class PluginObj:

    logger = None

    def __init__(self, _plugin):
        if PluginObj.logger is None:
            PluginObj.logger = logging.getLogger(__name__)
        self.config_obj = _plugin.config_obj
        self.namespace = _plugin.namespace
        self.instances = {}

    # Plugin may have the following methods
    # used to interface to the app.

    #def refresh_channels_ext(self, _instance=None):
    """
    External request to refresh channel list. Called from the 
    plugin manager and only if method is present in the plugin.
    """
    
    #def refresh_epg_ext(self, _instance=None):
    """
    External request to refresh epg list.  Called from the 
    plugin manager and only if method is present in the plugin.
    """

    #def get_channel_uri_ext(self, sid, _instance=None):
    """
    Required for streaming
    External request to get the uri for a channel.  Called from the 
    stream object.  
    """

    #def is_time_to_refresh_ext(self, _last_refresh, _instance):
    """
    May be required for streaming based on stream type
    External request to determine if get_channel_uri_ext
    should be called again.  Called from the 
    stream sub-classes object.  
    """
