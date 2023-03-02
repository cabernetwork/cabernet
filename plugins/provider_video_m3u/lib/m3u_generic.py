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

from lib.plugins.plugin_obj import PluginObj

from .m3u_generic_instance import M3UGenericInstance
from ..lib import translations


class M3UGeneric(PluginObj):

    def __init__(self, _plugin):
        super().__init__(_plugin)
        if not self.config_obj.data[_plugin.name.lower()]['enabled']:
            return
        for inst in _plugin.instances:
            self.instances[inst] = M3UGenericInstance(self, inst)
        self.unc_pluto_base = self.uncompress(translations.pluto_base)
