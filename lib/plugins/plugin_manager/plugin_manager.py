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
import pathlib
import plugins
import shutil
import sys
import time

import lib.common.utils as utils
from lib.db.db_plugins import DBPlugins
from lib.db.db_scheduler import DBScheduler
from lib.common.decorators import handle_url_except


class PluginManager:
    logger = None

    def __init__(self, _config, _plugins):
        if PluginManager.logger is None:
            PluginManager.logger = logging.getLogger(__name__)
        self.plugin_handler = _plugins
        self.config = _config
        self.plugin_db = DBPlugins(self.config)
        self.db_scheduler = DBScheduler(self.config)

    def delete_plugin(self, _repo_id, _plugin_id, _sched_queue):
        plugin_rec = self.plugin_db.get_plugins(None, _repo_id, _plugin_id)
        self.logger.warning('calling delete_plugin() xxx {} '.format(plugin_rec))
        if not plugin_rec:
            self.logger.warning('No plugin found, aborting')
            return 'No plugin found, aborting delete request'
        elif not plugin_rec[0]['version']['installed']:
            self.logger.warning('Plugin not installed, aborting')
            return 'Plugin not installed, aborting delete request'
        

        plugin_rec = plugin_rec[0]
        namespace = plugin_rec['name']

        results = 'Deleting all {} scheduled tasks'.format(namespace)
        tasks = self.db_scheduler.get_tasks_by_name(plugin_rec['name'], None)
        for task in tasks:
            _sched_queue.put({'cmd': 'delinstance', 'name': plugin_rec['name'], 'instance': None})

        results += '<br>Deleting plugin objects'
        self.plugin_handler.terminate(namespace)

        plugin_path = pathlib.Path(
            self.config['paths']['main_dir'],
            self.config['paths']['internal_plugins_pkg'],
            _plugin_id
            )
        if plugin_path.exists():
            results += '<br>Deleting plugin folder {}'.format(plugin_path)
            self.logger.warning('found package {}'.format(plugin_path))
            shutil.rmtree(plugin_path)
        else:
            results += '<br>ERROR: Plugin missing {}'.format(plugin_path)
            self.logger.warning('missing package {}'.format(plugin_path))

        plugin_rec['version']['installed'] = False
        plugin_rec['version']['current'] = None
        plugin_rec = self.plugin_db.save_plugin(plugin_rec)

        results += '<br>A restart is suggested to finish cleaning up plugin'
        return results
        
    def install_plugin(self, _repo_id, _plugin_id, _sched_queue):
        plugin_rec = self.plugin_db.get_plugins(None, _repo_id, _plugin_id)
        self.logger.warning("calling install_plugin()")
        if not plugin_rec:
            self.logger.warning('No plugin found, aborting')
            return 'No plugin found, aborting delete request'
        elif plugin_rec[0]['version']['installed']:
            self.logger.warning('Plugin not installed, aborting')
            return 'Plugin already installed, aborting install request'

        repo_rec = self.plugin_db.get_repos(_repo_id)
        if not repo_rec:
            self.logger.warning('No repo {} associated with plugin {}, aborting install'
                .format(_repo_id, _plugin_id))
            return 'No repo found {}, associated with plugin {}, aborting install request' \
                .format(_repo_id, _plugin_id)

        plugin_rec = plugin_rec[0]
        # check Cabernet required version
        req = plugin_rec.get('requires')
        if req:
            cabernet = req[0].get(utils.CABERNET_ID)
            if cabernet:
                ver = cabernet.get('version')
                if ver:
                    self.logger.warning('cabernet version requirement found for plugin {} {}'.format(_plugin_id, ver))
                    v_req = utils.get_version_index(ver)
                    v_cur = utils.get_version_index(utils.VERSION)
                    self.logger.warning('{} {}'.format(v_req, v_cur))
                    if v_req > v_cur:
                        self.logger.warning('Cabernet version too low, aborting install')
                        return 'Cabernet version {} too low for plugin. Requires {}, aborting install' \
                            .format(utils.VERSION, ver)

        # if so start install process
        tmp_zip_path = self.download_zip(pathlib.Path(
            repo_rec['datadir'], plugin_rec['id'], plugin_rec['id']+'-'+ver+'.zip'
            ))
        self.logger.warning('tmp_zip_path: {}'.format(tmp_zip_path))
        
        
        # unzip folder
        # Tell plugin handler to create the plugin
        # update the database to say plugin is installed and what version
        # Enable plugin?
        
        
        
    @handle_url_except
    def download_zip(self, _zip_url, _zip_filename):
        """
        Returns the location of the zip file
        """

        buf_size = 2 * 16 * 16 * 1024
        save_path = pathlib.Path(self.config['paths']['tmp_dir']).joinpath(_zip_filename)
        h = {'Content-Type': 'application/zip', 'User-agent': utils.DEFAULT_USER_AGENT}
        req = urllib.request.Request(_zip_url, headers=h)
        with urllib.request.urlopen(req) as resp:
            with open(save_path, 'wb') as out_file:
                while True:
                    chunk = resp.read(buf_size)
                    if not chunk:
                        break
                    out_file.write(chunk)
        return save_path
