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

import logging
from lib.db.db_plugins import DBPlugins
from lib.db.db_scheduler import DBScheduler


class PluginManager:
    logger = None

    def __init__(self, _config):
        if PluginManager.logger is None:
            PluginManager.logger = logging.getLogger(__name__)
        self.config = _config
        self.plugin_db = DBPlugins(self.config)
        self.db_scheduler = DBScheduler(self.config)

    def delete_plugin(self, _repo_id, _plugin_id, _sched_queue):
        plugin_rec = self.plugin_db.get_plugins(None, _repo_id, _plugin_id)
        self.logger.warning("calling delete_plugin()")
        self.logger.warning(plugin_rec)
        if not plugin_rec:
            # no plugin found, do nothing
            self.logger.warning('no plugin found, aborting')
            return 'no plugin found, aborting'

        plugin_rec = plugin_rec[0]
        # determine if it is external
        # if so, then check to see if folder exists
        # if it exists, then delete the folder and all files within
        
        # need to check to see if it is the same as github...
        
        #once deleted, will need to update the plugin handler to remove the plugin.


        # delete all the sacheduled tasks associated with this plugin
        tasks = self.db_scheduler.get_tasks_by_name(plugin_rec['name'], None)
        for task in tasks:
            _sched_queue.put({'cmd': 'delinstance', 'name': plugin_rec['name'], 'instance': None})


