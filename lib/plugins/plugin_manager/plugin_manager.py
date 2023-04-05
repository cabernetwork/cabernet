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
import os
import pathlib
import plugins
import shutil
import sys
import time
import urllib
import zipfile

import lib.common.utils as utils
from lib.db.db_plugins import DBPlugins
from lib.db.db_scheduler import DBScheduler
from lib.common.decorators import handle_url_except


class PluginManager:
    logger = None

    def __init__(self, _plugins, _config_obj=None):
        """
        If called during a patch update, the plugins is unknown,
        so it should be set to None and the config object passed in instead
        Otherwise, pass in the plugins and set the config object to None
        """
        if PluginManager.logger is None:
            PluginManager.logger = logging.getLogger(__name__)
        self.plugin_handler = _plugins
        if self.plugin_handler:
            self.config = _plugins.config_obj.data
            self.config_obj = _plugins.config_obj
        else:
            self.config = _config_obj.data
            self.config_obj = _config_obj
        
        self.plugin_db = DBPlugins(self.config)
        self.db_scheduler = DBScheduler(self.config)
        self.plugin_rec = None
        self.repo_rec = None

    def check_plugin_status(self, _repo_id, _plugin_id):
        """
        Returns None if successful, otherwise, returns
        string of the error
        """
        self.plugin_rec = self.plugin_db.get_plugins(None, _repo_id, _plugin_id)
        if not self.plugin_rec:
            self.logger.notice('No plugin found, aborting')
            return 'Error: No plugin found, aborting request'

        self.repo_rec = self.plugin_db.get_repos(_repo_id)
        if not self.repo_rec:
            self.logger.notice('No repo {} associated with plugin {}, aborting install'
                .format(_repo_id, _plugin_id))
            return 'Error: No repo found {}, associated with plugin {}, aborting install' \
                .format(_repo_id, _plugin_id)
        self.plugin_rec = self.plugin_rec[0]
        self.repo_rec = self.repo_rec[0]

        # if plugin exists, make sure we can delete it
        if self.plugin_rec['external']:
            plugin_path = self.config['paths']['external_plugins_pkg']
        else:
            plugin_path = self.config['paths']['internal_plugins_pkg']
        plugin_path = pathlib.Path(
            self.config['paths']['main_dir'],
            plugin_path,
            _plugin_id
            )
        if plugin_path.exists() and not os.access(plugin_path, os.W_OK):
            self.logger.warning('Unable to update folder: OS Permission issue on plugin {}, aborting'.format(plugin_path))
            return 'Error: Unable to update folder: OS Permission issue on plugin {}, aborting'.format(plugin_path)

        return None

    def check_version_requirements(self):
        # check Cabernet required version
        req = self.plugin_rec.get('requires')
        if req:
            cabernet = req[0].get(utils.CABERNET_ID)
            if cabernet:
                ver = cabernet.get('version')
                if ver:
                    v_req = utils.get_version_index(ver)
                    v_cur = utils.get_version_index(utils.VERSION)
                    if v_req > v_cur:
                        self.logger.notice('Cabernet version too low, aborting install')
                        return 'Error: Cabernet version {} too low for plugin. Requires {}, aborting install' \
                            .format(utils.VERSION, ver)
        return None
        
    def get_plugin_zipfile(self):
        # starting install process
        zip_file = ''.join([
            self.plugin_rec['id'], '-', 
            self.plugin_rec['version']['latest'],
            '.zip'
            ])
        zippath = '/'.join([
            self.repo_rec['dir']['datadir']['url'], 
            self.plugin_rec['id'], zip_file
            ])
        tmp_zip_path = self.download_zip(zippath, zip_file)
        if not tmp_zip_path:
            self.logger.notice('Unable to obtain zip file from repo, aborting')
            results = 'Error: Unable to obtain zip file {} from repo, aborting' \
                .format(zip_file)
            return (False, results)
        results = 'Downloaded plugin {} from repo'.format(zip_file)
        try:
            with zipfile.ZipFile(tmp_zip_path, 'r') as z:
                file_list = z.namelist()
                res = [i for i in file_list if i.endswith(self.plugin_rec['id']+'/')]
                if not res:
                    results += '<br>Error: Zip file does not contain plugin folder {}, aborting' \
                        .format(self.plugin_rec['id'])
                    return (False, results)
                if len(res) != 1:
                    results += '<br>Error: Zip file contains multiple plugin folders {}, aborting' \
                        .format(self.plugin_rec['id'])
                    return (False, results)

                z.extractall(os.path.dirname(tmp_zip_path))
                
        except FileNotFoundError as ex:
            self.logger.notice('File {} missing from tmp area, aborting'
                .format(zip_file))
            results += '<br>Error: File {} missing from tmp area, aborting' \
                .format(zip_file)
            return (False, results)

        tmp_plugin_path = pathlib.Path(os.path.dirname(tmp_zip_path), res[0])
        plugin_folder = pathlib.Path(
            self.config['paths']['main_dir'], 
            self.config['paths']['external_plugins_pkg'])

        plugin_id_folder = plugin_folder.joinpath(self.plugin_rec['id'])

        if plugin_id_folder.exists():
            shutil.rmtree(plugin_id_folder)
            
        shutil.move(str(tmp_plugin_path), str(plugin_folder))
        results += '<br>Installed plugin {} from repo, version {}' \
            .format(self.plugin_rec['id'], self.plugin_rec['version']['latest'])
        
        # remove the leftovers in the tmp folder
        try:
            p = pathlib.Path(tmp_plugin_path)
            shutil.rmtree(p.parents[0])
            os.remove(tmp_zip_path)
        except OSError as ex:
            self.logger.notice('Unable to delete plugin from tmp area: {}'.format(str(ex)))
            results += '<br>Error: Unable to delete plugin folder from tmp area {}'.format(str(ex))
            return (False, results)
        return (True, results)

    def upgrade_plugin(self, _repo_id, _plugin_id, _sched_queue):
        results = self.check_plugin_status(_repo_id, _plugin_id)
        if results:
            return results
        
        results = self.check_version_requirements()
        if results:
            return results

        is_successful, results = self.get_plugin_zipfile()
        if not is_successful:
            return results

        # update the plugin database entry with the new version...
        self.plugin_rec['version']['current'] = self.plugin_rec['version']['latest']
        self.plugin_db.save_plugin(self.plugin_rec)

        results += '<br>A restart is required to finish cleaning up plugin'
        return results

    def install_plugin(self, _repo_id, _plugin_id, _sched_queue=None):
        results = self.check_plugin_status(_repo_id, _plugin_id)
        if results:
            return results
        
        if self.plugin_rec['version']['installed']:
            self.logger.notice('Error: Plugin already installed, aborting')
            return 'Error: Plugin already installed, aborting install'

        results = self.check_version_requirements()
        if results:
            return results

        is_successful, results = self.get_plugin_zipfile()
        if not is_successful:
            return results

        # next inform cabernet that there is a new plugin
        if self.plugin_handler:
            try:
                self.plugin_handler.collect_plugin(self.config['paths']['external_plugins_pkg'], True, self.plugin_rec['id'])
            except FileNotFoundError:
                self.logger.notice('Plugin folder not in external plugin folder: {}'.format(str(ex)))
                results += '<br>Error: Plugin folder not in external plugin folder {}'.format(str(ex))
                return results

        # update the database to say plugin is installed and what version
        # Enable plugin?
        self.config_obj.write(
            self.plugin_rec['name'].lower(), 'enabled', True)

        results += '<br>A restart is suggested to finish cleaning up plugin'
        return results

    def delete_plugin(self, _repo_id, _plugin_id, _sched_queue=None):
        plugin_rec = self.plugin_db.get_plugins(None, _repo_id, _plugin_id)
        if not plugin_rec:
            self.logger.notice('No plugin found, aborting')
            return 'Error: No plugin found, aborting delete request'
        elif not plugin_rec[0]['version']['installed']:
            self.logger.notice('Plugin not installed, aborting')
            return 'Error: Plugin not installed, aborting delete request'
        
        plugin_rec = plugin_rec[0]
        namespace = plugin_rec['name']
        if plugin_rec['external']:
            plugin_path = self.config['paths']['external_plugins_pkg']
        else:
            plugin_path = self.config['paths']['internal_plugins_pkg']

        plugin_path = pathlib.Path(
            self.config['paths']['main_dir'],
            plugin_path,
            _plugin_id
            )
        if not plugin_path.exists():
            self.logger.notice('Missing plugin {}, aborting'.format(plugin_path))
            return 'Error: Missing plugin {}, aborting'.format(plugin_path)
        elif not os.access(plugin_path, os.W_OK):
            self.logger.warning('Unable to delete folder: OS Permission issue on plugin {}, aborting'.format(plugin_path))
            return 'Error: Unable to delete folder: OS Permission issue on plugin {}, aborting'.format(plugin_path)

        results = 'Deleting all {} scheduled tasks'.format(namespace)
        tasks = self.db_scheduler.get_tasks_by_name(plugin_rec['name'], None)
        if _sched_queue:
            for task in tasks:
                _sched_queue.put({'cmd': 'delinstance', 'name': plugin_rec['name'], 'instance': None})

        results += '<br>Deleting plugin objects'
        if self.plugin_handler:
            self.plugin_handler.terminate(namespace)

        results += '<br>Deleting plugin folder {}'.format(plugin_path)
        try:
            shutil.rmtree(plugin_path)
        except OSError as ex:
            self.logger.notice('Unable to delete plugin: {}'.format(str(ex)))
            results += '<br>Error: Unable to delete plugin folder {}'.format(str(ex))
            return results

        plugin_rec['version']['installed'] = False
        plugin_rec['version']['current'] = None
        plugin_rec = self.plugin_db.save_plugin(plugin_rec)

        results += '<br>A restart is suggested to finish cleaning up plugin'
        return results
        
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
