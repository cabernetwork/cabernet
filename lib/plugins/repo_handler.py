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
import json
import importlib
import importlib.resources
import os
import pathlib
import requests
import urllib

import lib.common.exceptions as exceptions
import lib.common.utils as utils
from lib.db.db_plugins import DBPlugins
from lib.common.decorators import handle_url_except
from lib.common.decorators import handle_json_except


class RepoHandler:

    http_session = requests.session()
    logger = None

    def __init__(self, _config_obj):
        self.config_obj = _config_obj
        if RepoHandler.logger is None:
            RepoHandler.logger = logging.getLogger(__name__)
        self.plugin_db = DBPlugins(_config_obj.data)



    def load_cabernet_repo(self):
        """
        Loads the manifest which points to the plugin.json list of plugins
        Will update the database on the manifest and plugin list
        If there is a plugin that is no longer in the list, will tag for
        deletion. (don't know at this point if it is installed.)
        """
        repo_settings = self.import_cabernet_manifest()
        self.save_repo(repo_settings)
        self.update_plugins(repo_settings)

    def import_cabernet_manifest(self):
        """
        Loads the manifest for cabernet repo
        """
        json_settings = importlib.resources.read_text(self.config_obj.data['paths']['resources_pkg'], utils.CABERNET_REPO)
        settings = json.loads(json_settings)
        if settings:
            settings = settings['plugin']
            settings['repo_url'] = utils.CABERNET_REPO
            self.plugin_db.get_repos(utils.CABERNET_ID)
        return settings

    def save_repo(self, _repo):
        """
        Saves to DB the repo json settings
        """
        self.plugin_db.save_repo(_repo)


    def cache_thumbnails(self, _plugin_defn):
        """
        Determine if the cache area has the thumbnail, if not
        will download and store the thumbnail
        """
        # path = thumbnail cache path + plugin_id + icon or fanart path
        thumbnail_path = self.config_obj.data['paths']['thumbnails_dir']
        plugin_id = _plugin_defn['id']
        icon_path = _plugin_defn['icon']
        fanart_path = _plugin_defn['fanart']
        
        repoid = _plugin_defn['repoid']
        repo_defn = self.plugin_db.get_repos(repoid)
        if not repo_defn:
            self.logger.notice('Repo not defined for plugin {}, unable to cache thumbnails'
                .format(plugin_id))
            return
        datadir = repo_defn[0]['dir']['datadir']['url']
        self.cache_thumbnail(datadir, plugin_id, icon_path, thumbnail_path)
        self.cache_thumbnail(datadir, plugin_id, fanart_path, thumbnail_path)

    def cache_thumbnail(self, _datadir, _plugin_id, _image_relpath, _thumbnail_path):
        """
        _datadir: datadir url from the repo definition
        _plugin_id: plugin id which is also the folder name
        _image_repath: relative path found in the plugin definition
        _thumbnail_path: config setting to the thumbnail path area
        """
        full_repo = '/'.join([
            _datadir, _plugin_id, _image_relpath])
        full_cache = pathlib.Path(
            _thumbnail_path, _plugin_id, _image_relpath)
        if not full_cache.exists():
            image = self.get_uri_data(full_repo)
            self.save_file(image, full_cache)

    def update_plugins(self, _repo_settings):
        """
        Gets the list of plugins for this repo from [dir][info] and updates the db
        """
        uri = _repo_settings['dir']['info']
        plugin_json = self.get_uri_json_data(uri)
        if plugin_json:
            plugin_json = plugin_json['plugins']
            for plugin in plugin_json:
                plugin = plugin['plugin']
                if 'repository' in plugin['category']:
                    continue
                # pull the db item. merge them and then update the db with new data.
                plugin_data = self.plugin_db.get_plugins(_installed=None, _repo_id=_repo_settings['id'], _plugin_id=plugin['id'])
                if plugin_data:
                    plugin_data = plugin_data[0]
                    plugin['repoid'] = _repo_settings['id']
                    plugin['version']['installed'] = plugin_data['version']['installed']
                    plugin['version']['latest'] = plugin['version']['current']
                    plugin['version']['current'] = plugin_data['version']['current']
                    plugin['changelog'] = plugin.get('changelog')
                    if plugin_data.get('external'):
                        plugin['external'] = plugin_data['external']
                    else:
                        plugin['external'] = True
                else:
                    plugin['repoid'] = _repo_settings['id']
                    plugin['version']['installed'] = False
                    plugin['version']['latest'] = plugin['version']['current']
                    plugin['version']['current'] = None
                    plugin['external'] = True
                self.cache_thumbnails(plugin)
                self.plugin_db.save_plugin(plugin)

    @handle_url_except()
    def get_uri_data(self, _uri):
        header = {
            'User-agent': utils.DEFAULT_USER_AGENT}
        resp = RepoHandler.http_session.get(_uri, headers=header, timeout=(2, 4))
        x = resp.content
        resp.raise_for_status()
        return x

    @handle_url_except()
    @handle_json_except
    def get_uri_json_data(self, _uri):
        header = {
            'Content-Type': 'application/json',
            'User-agent': utils.DEFAULT_USER_AGENT}
        req = urllib.request.Request(_uri, headers=header)
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            return json.load(resp)


    def save_file(self, _data, _file):
        try:
            os.makedirs(os.path.dirname(_file), exist_ok=True)
            
            open(os.path.join(_file), 'wb').write(_data)
        except Exception as e:
            self.logger.warning("An error occurred saving %s file\n%s" % (_file, e))
            raise
