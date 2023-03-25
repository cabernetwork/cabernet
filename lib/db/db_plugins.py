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

from lib.db.db import DB
from lib.common.decorators import Backup
from lib.common.decorators import Restore

DB_REPOS_TABLE = 'repos'
DB_PLUGINS_TABLE = 'plugins'
DB_INSTANCE_TABLE = 'instance'
DB_CONFIG_NAME = 'db_files-plugins_db'

sqlcmds = {
    'ct': [
        """
        CREATE TABLE IF NOT EXISTS repos (
            id        VARCHAR(255) NOT NULL,
            name      VARCHAR(255) NOT NULL,
            url       VARCHAR(255) NOT NULL,
            json TEXT NOT NULL,
            UNIQUE(id)
            )
        """,
        """
        CREATE TABLE IF NOT EXISTS plugins (
            id        VARCHAR(255) NOT NULL,
            repo      VARCHAR(255) NOT NULL,
            namespace VARCHAR(255) NOT NULL,
            installed BOOLEAN NOT NULL,
            json TEXT NOT NULL,
            UNIQUE(repo, namespace, id)
            )
        """,
        """
        CREATE TABLE IF NOT EXISTS instance (
            repo      VARCHAR(255) NOT NULL,
            namespace VARCHAR(255) NOT NULL,
            instance  VARCHAR(255) NOT NULL,
            description TEXT,
            UNIQUE(repo, namespace, instance)
            )
        """
    ],
    'dt': [
        """
        DROP TABLE IF EXISTS instance
        """,
        """
        DROP TABLE IF EXISTS plugins
        """,
        """
        DROP TABLE IF EXISTS repos
        """
    ],
    'repos_add':
        """
        INSERT OR REPLACE INTO repos (
            id, name, url, json
            ) VALUES ( ?, ?, ?, ? )
        """,
    'repos_get':
        """
        SELECT * FROM repos WHERE id LIKE ?
        """,
    'repos_del':
        """
        DELETE FROM repos WHERE id=?
        """,

    'plugins_add':
        """
        INSERT OR REPLACE INTO plugins (
            id, repo, namespace, installed, json
            ) VALUES ( ?, ?, ?, ?, ? )
        """,
    'plugins_get':
        """
        SELECT * FROM plugins WHERE repo LIKE ? AND id LIKE ?
        AND installed=?
        """,
    'plugins_name_get':
        """
        SELECT * FROM plugins WHERE repo LIKE ? AND namespace LIKE ?
        AND installed=?
        """,
    'plugins_all_get':
        """
        SELECT * FROM plugins WHERE repo LIKE ? AND id LIKE ?
        """,
    'plugins_all_name_get':
        """
        SELECT * FROM plugins WHERE repo LIKE ? AND namespace LIKE ?
        """,
    'plugins_del':
        """
        DELETE FROM plugins WHERE repo=? AND id=?
        """,

    'instance_add':
        """
        INSERT OR REPLACE INTO instance (
            repo, namespace, instance, description
            ) VALUES ( ?, ?, ?, ? )
        """,
    'instance_get':
        """
        SELECT * FROM instance WHERE repo LIKE ?
        AND namespace LIKE ? ORDER BY namespace, instance
        """,
    'instance_del':
        """
        DELETE FROM instance WHERE repo LIKE ? AND 
        namespace LIKE ? AND instance LIKE ?
        """
}


class DBPlugins(DB):

    def __init__(self, _config):
        super().__init__(_config, _config['datamgmt'][DB_CONFIG_NAME], sqlcmds)

    def save_repo(self, _repo_dict):
        self.add(DB_REPOS_TABLE, (
            _repo_dict['id'],
            _repo_dict['name'],
            _repo_dict['repo_url'],
            json.dumps(_repo_dict)))

    def save_plugin(self, _plugin_dict):
        self.add(DB_PLUGINS_TABLE, (
            _plugin_dict['id'],
            _plugin_dict['repoid'],
            _plugin_dict['name'],
            _plugin_dict['version']['installed'],
            json.dumps(_plugin_dict)))

    def save_instance(self, _repo_id, _namespace, _instance, _descr):
        self.add(DB_INSTANCE_TABLE, (
            _repo_id,
            _namespace,
            _instance,
            _descr))

    def get_repos(self, _id):
        if not _id:
            _id = '%'
        rows = self.get_dict(DB_REPOS_TABLE, (_id,))
        plugin_list = []
        for row in rows:
            plugin_list.append(json.loads(row['json']))
        if len(plugin_list) == 0:
            plugin_list = None
        return plugin_list

    def del_repo(self, _id):
        """
        If a plugin is installed, it must be removed before the 
        repo can be deleted.  Once all plugins are not installed,
        then will remove the repo, plugin and all instances
        """
        plugins_installed = self.get_plugins(True, _id)
        self.logger.warning('################## TBD, aborting delete {}'.format(len(plugins_installed)))
        

        #self.delete(DB_INSTANCE_TABLE, (_id, '%', '%',))
        #self.delete(DB_PLUGINS_TABLE, (_id, '%',))
        #self.delete(DB_REPOS_TABLE, (_id,))

    def get_plugins(self, _installed, _repo_id=None, _plugin_id=None):
        if not _repo_id:
            _repo_id = '%'
        if not _plugin_id:
            _plugin_id = '%'
        if _installed is None:
            rows = self.get_dict(DB_PLUGINS_TABLE+'_all', (_repo_id, _plugin_id,))
        else:
            rows = self.get_dict(DB_PLUGINS_TABLE, (_repo_id, _plugin_id, _installed,))
        plugin_list = []
        for row in rows:
            plugin_list.append(json.loads(row['json']))
        if len(plugin_list) == 0:
            plugin_list = None
        return plugin_list

    def get_plugins_by_name(self, _installed, _repo_id=None, _plugin_name=None):
        if not _repo_id:
            _repo_id = '%'
        if not _plugin_name:
            _plugin_name = '%'
        if _installed is None:
            rows = self.get_dict(DB_PLUGINS_TABLE+'_all_name', (_repo_id, _plugin_name,))
        else:
            rows = self.get_dict(DB_PLUGINS_TABLE+'_name', (_repo_id, _plugin_name, _installed,))
        plugin_list = []
        for row in rows:
            plugin_list.append(json.loads(row['json']))
        if len(plugin_list) == 0:
            plugin_list = None
        return plugin_list

    def del_plugin(self, _repo_id, _plugin_id):
        """
        Deletes the instance rows first due to constaints, then
        deletes the plugin
        """
        self.delete(DB_INSTANCE_TABLE, (_repo_id, _plugin_id, '%',))
        self.delete(DB_PLUGINS_TABLE, (_repo_id, _plugin_id,))

    def del_instance(self, _repo, _namespace, _instance):
        return self.delete(DB_INSTANCE_TABLE, (_repo, _namespace, _instance,))

    def get_instances(self, _repo=None, _namespace=None):
        """
        createa a dict of namespaces that contain an array of instances
        """
        if not _repo:
            _repo = '%'
        if not _namespace:
            _namespace = '%'
        rows_dict = {}
        rows = self.get_dict(DB_INSTANCE_TABLE, (_repo, _namespace,))
        for row in rows:
            if row['namespace'] not in rows_dict:
                rows_dict[row['namespace']] = []
            instances = rows_dict[row['namespace']]
            instances.append(row['instance'])
            # rows_dict[row['namespace']] = row['instance']

        return rows_dict

    def get_instances_full(self, _repo=None, _namespace=None):
        if not _repo:
            _repo = '%'
        if not _namespace:
            _namespace = '%'
        rows_dict = {}
        rows = self.get_dict(DB_INSTANCE_TABLE, (_repo, _namespace,))
        for row in rows:
            rows_dict[row['namespace']] = row
        return rows_dict

    @Backup(DB_CONFIG_NAME)
    def backup(self, backup_folder):
        self.export_sql(backup_folder)

    @Restore(DB_CONFIG_NAME)
    def restore(self, backup_folder):
        msg = self.import_sql(backup_folder)
        if msg is None:
            return 'Plugin Manifest Database Restored'
        else:
            return msg
