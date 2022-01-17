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

from .channels import Channels
from .epg import EPG
from lib.plugins.plugin_instance_obj import PluginInstanceObj


class USTVGOInstance(PluginInstanceObj):

    def __init__(self, _ustvgo, _instance):
        super().__init__(_ustvgo, _instance)
        self.config_obj = _ustvgo.config_obj
        if not self.config_obj.data[_ustvgo.name.lower()]['enabled']:
            return
        if not self.config_obj.data[self.config_section]['enabled']:
            return
        self.channels = Channels(self)
        self.epg = EPG(self)
        
