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

import ast
import json
import datetime
import sqlite3

from lib.db.db import DB
from lib.common.decorators import Backup
from lib.common.decorators import Restore

DB_CHANNELS_TABLE = 'channels'
DB_STATUS_TABLE = 'status'
DB_ZONE_TABLE = 'zones'
DB_CATEGORIES_TABLE = 'categories'
DB_CONFIG_NAME = 'db_files-channels_db'

sqlcmds = {
    'ct': [
        """
        CREATE TABLE IF NOT EXISTS channels (
            namespace VARCHAR(255) NOT NULL,
            instance  VARCHAR(255) NOT NULL,
            enabled   BOOLEAN NOT NULL,
            uid       VARCHAR(255) NOT NULL,
            number    VARCHAR(255) NOT NULL,
            display_number VARCHAR(255) NOT NULL,
            display_name VARCHAR(255) NOT NULL,
            group_tag     VARCHAR(255),
            updated   BOOLEAN NOT NULL,
            thumbnail VARCHAR(255),
            thumbnail_size VARCHAR(255),
            atsc      VARCHAR(1500),
            json TEXT NOT NULL,
            UNIQUE(namespace, instance, uid)
            )
        """,
        """
        CREATE TABLE IF NOT EXISTS status (
            namespace VARCHAR(255) NOT NULL,
            instance  VARCHAR(255),
            last_update TIMESTAMP,
            UNIQUE(namespace, instance)
            )
        """,
        """
        CREATE TABLE IF NOT EXISTS categories (
            namespace VARCHAR(255) NOT NULL,
            instance  VARCHAR(255),
            uid       VARCHAR(255) NOT NULL,
            category  VARCHAR(255) NOT NULL
            )
        """,
        """
        CREATE TABLE IF NOT EXISTS zones (
            namespace VARCHAR(255) NOT NULL,
            instance  VARCHAR(255),
            uid       VARCHAR(255) NOT NULL,
            name      VARCHAR(255) NOT NULL,
            UNIQUE(namespace, instance, uid)
            )
        """

    ],
    'dt': [
        """
        DROP TABLE IF EXISTS channels
        """,
        """
        DROP TABLE IF EXISTS status
        """,
        """
        DROP TABLE IF EXISTS categories
        """
        """
        DROP TABLE IF EXISTS zones
        """
    ],

    'channels_add':
        """
        INSERT INTO channels (
            namespace, instance, enabled, uid, number, display_number, display_name,
            group_tag, thumbnail, thumbnail_size, updated, json
            ) VALUES ( ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ? )
        """,
    'channels_update':
        """
        UPDATE channels SET 
            number=?, updated=?, json=?
            WHERE namespace=? AND instance=? AND uid=?
        """,
    'channels_editable_update':
        """
        UPDATE channels SET 
            enabled=?, display_number=?, display_name=?, group_tag=?, thumbnail=?, thumbnail_size=?
            WHERE namespace=? AND instance=? AND uid=?
        """,
    'channels_updated_update':
        """
        UPDATE channels SET updated = False WHERE namespace=? AND instance=?
        """,
    'channels_atsc_update':
        """
        UPDATE channels SET 
            atsc=?
            WHERE namespace=? AND instance=? AND uid=?
        """,
    'channels_json_update':
        """
        UPDATE channels SET 
            json=?
            WHERE namespace=? AND instance=? AND uid=?
        """,
    'channels_chnum_update':
        """
        UPDATE channels SET 
            display_number=?
            WHERE namespace=? AND instance=? AND uid=?
        """,
    'channels_del':
        """
        DELETE FROM channels WHERE updated LIKE ?
        AND namespace LIKE ? AND instance LIKE ?
        """,
    'channels_get':
        """
        SELECT * FROM channels WHERE namespace LIKE ?
        AND instance LIKE ? ORDER BY CAST(number as FLOAT), namespace, instance
        """,
    'channels_one_get':
        """
        SELECT * FROM channels WHERE uid=? AND namespace LIKE ?
        AND instance LIKE ?
        """,
    'channels_name_get':
        """
        SELECT DISTINCT namespace FROM channels
        """,
    'channels_instance_get':
        """
        SELECT DISTINCT namespace,instance FROM channels
        """,

    'status_add':
        """
        INSERT OR REPLACE INTO status (
            namespace, instance, last_update
            ) VALUES ( ?, ?, ? )
        """,
    'status_get':
        """
        SELECT datetime(last_update, 'localtime') FROM status WHERE
            namespace=? AND instance=?
        """,
    'status_del':
        """
        DELETE FROM status WHERE
            namespace LIKE ? AND instance LIKE ?
        """,
    'zones_add':
        """
        INSERT OR REPLACE INTO zones (
            namespace, instance, uid, name
            ) VALUES ( ?, ?, ?, ? )
        """,
    'zones_get':
        """
        SELECT uid, name FROM zones WHERE
            namespace=? AND instance=?
        """

}


class DBChannels(DB):

    def __init__(self, _config):
        super().__init__(_config, _config['datamgmt'][DB_CONFIG_NAME], sqlcmds)

    def save_channel_list(self, _namespace, _instance, _ch_dict, save_edit_groups=True):
        """
        Assume the list is complete and will remove any old channels not updated
        """
        if _instance is None or _namespace is None:
            self.logger.warning(
                'Saving Channel List: Namespace or Instance is None {}:{}'
                .format(_namespace, _instance))
        self.update(DB_CHANNELS_TABLE + '_updated', (_namespace, _instance,))
        for ch in _ch_dict:
            if save_edit_groups:
                edit_groups = ch['groups_other']
            else:
                edit_groups = None
            try:
                self.add(DB_CHANNELS_TABLE, (
                    _namespace,
                    _instance,
                    True,
                    ch['id'],
                    ch['number'],
                    ch['number'],
                    ch['name'],
                    edit_groups,
                    ch['thumbnail'],
                    str(ch['thumbnail_size']),
                    True,
                    json.dumps(ch)))
            except sqlite3.IntegrityError as ex:
                self.update(DB_CHANNELS_TABLE, (
                    ch['number'],
                    True,
                    json.dumps(ch),
                    _namespace,
                    _instance,
                    ch['id']
                ))

            self.add(DB_STATUS_TABLE, (
                _namespace, _instance, datetime.datetime.now()))
        self.delete(DB_CHANNELS_TABLE, (False, _namespace, _instance,))

    def update_channel(self, _ch):
        """
        Updates the editable fields for one channel
        """
        self.update(DB_CHANNELS_TABLE + '_editable', (
            _ch['enabled'],
            _ch['display_number'],
            _ch['display_name'],
            _ch['group_tag'],
            _ch['thumbnail'],
            str(_ch['thumbnail_size']),
            _ch['namespace'],
            _ch['instance'],
            _ch['uid']
        ))

    def del_channels(self, _namespace, _instance):
        if not _namespace:
            _namespace = '%'
        if not _instance:
            _instance = '%'
        return self.delete(DB_CHANNELS_TABLE, ('%', _namespace, _instance,))

    def del_status(self, _namespace=None, _instance=None):
        if not _namespace:
            _namespace = '%'
        if not _instance:
            _instance = '%'
        return self.delete(DB_STATUS_TABLE, (_namespace, _instance,))

    def get_status(self, _namespace, _instance):
        result = self.get(DB_STATUS_TABLE, (_namespace, _instance))
        if result:
            last_update = result[0][0]
            if last_update is not None:
                return datetime.datetime.fromisoformat(last_update)
            else:
                return None
        else:
            return None

    def get_channels(self, _namespace, _instance):
        if not _namespace:
            _namespace = '%'
        if not _instance:
            _instance = '%'

        rows_dict = {}
        rows = self.get_dict(DB_CHANNELS_TABLE, (_namespace, _instance,))
        if rows is None:
            return None
        for row in rows:
            ch = json.loads(row['json'])
            row['json'] = ch
            row['thumbnail_size'] = ast.literal_eval(row['thumbnail_size'])
            if row['atsc'] is not None:
                row['atsc'] = ast.literal_eval(row['atsc'])
            # handles the uid multiple times across instances
            if row['uid'] in rows_dict.keys():
                rows_dict[row['uid']].append(row)
            else:
                rows_dict[row['uid']] = []
                rows_dict[row['uid']].append(row)

        return rows_dict

    def get_channel_names(self):
        return self.get_dict(DB_CHANNELS_TABLE + '_name')

    def get_channel_instances(self):
        return self.get_dict(DB_CHANNELS_TABLE + '_instance')

    def get_channel(self, _uid, _namespace, _instance):
        if not _namespace:
            _namespace = '%'
        if not _instance:
            _instance = '%'

        rows = self.get_dict(DB_CHANNELS_TABLE + '_one', (_uid, _namespace, _instance,))
        for row in rows:
            ch = json.loads(row['json'])
            row['json'] = ch
            if row['atsc'] is not None:
                row['atsc'] = ast.literal_eval(row['atsc'])
            return row
        return None

    def update_channel_atsc(self, _ch):
        """
        Updates the atsc field for one channel
        """
        atsc_str = str(_ch['atsc'])
        self.update(DB_CHANNELS_TABLE + '_atsc', (
            atsc_str,
            _ch['namespace'],
            _ch['instance'],
            _ch['uid']
        ))

    def update_channel_json(self, _ch, _namespace, _instance):
        """
        Updates the json field for one channel
        """
        json_str = json.dumps(_ch)
        self.update(DB_CHANNELS_TABLE + '_json', (
            json_str,
            _namespace,
            _instance,
            _ch['id']
        ))

    def update_channel_number(self, _ch):
        """
        Updates the display_number field for one channel
        """
        display_number = str(_ch['display_number'])
        self.update(DB_CHANNELS_TABLE + '_chnum', (
            display_number,
            _ch['namespace'],
            _ch['instance'],
            _ch['uid']
        ))

    def get_sorted_channels(self, _namespace, _instance,
                            _first_sort_key=[None, True], _second_sort_key=[None, True]):
        """
        Using dynamic SQl to create a SELECT statement and send to the DB
        keys are [name_of_column, direction_asc=True]
        """
        where = ' WHERE namespace LIKE ? AND instance LIKE ? '
        orderby_front = ' ORDER BY '
        orderby_end = ' CAST(number as FLOAT), namespace, instance '
        orderby1 = self.get_channels_orderby(_first_sort_key[0], _first_sort_key[1])
        orderby2 = self.get_channels_orderby(_second_sort_key[0], _second_sort_key[1])
        sqlcmd = ''.join(['SELECT * FROM channels ', where, orderby_front, orderby1, orderby2, orderby_end])

        if not _namespace:
            _namespace = '%'
        if not _instance:
            _instance = '%'
        rows = self.get_dict(None, (_namespace, _instance,), sql=sqlcmd)
        for row in rows:
            ch = json.loads(row['json'])
            row['json'] = ch
            row['thumbnail_size'] = ast.literal_eval(row['thumbnail_size'])
        return rows

    def get_channels_orderby(self, _column, _ascending):
        str_types = ['namespace', 'instance', 'enabled', 'display_name', 'group_tag', 'thumbnail']
        float_types = ['uid', 'display_number']
        json_types = ['HD', 'callsign']
        if _ascending:
            dir_ = 'ASC'
        else:
            dir_ = 'DESC'
        if _column is None:
            return ''
        elif _column in str_types:
            return ''.join([_column, ' ', dir_, ', '])
        elif _column in float_types:
            return ''.join(['CAST(', _column, ' as FLOAT) ', dir_, ', '])
        elif _column in json_types:
            return ''.join(['JSON_EXTRACT(json, "$.', _column, '") ', dir_, ', '])

    def add_zone(self, _namespace, _instance, _uid, _name):
        self.add(DB_ZONE_TABLE, (_namespace, _instance, _uid, _name))

    def get_zones(self, _namespace, _instance):
        return self.get_dict(DB_ZONE_TABLE, (_namespace, _instance,))

    @Backup(DB_CONFIG_NAME)
    def backup(self, backup_folder):
        self.export_sql(backup_folder)

    @Restore(DB_CONFIG_NAME)
    def restore(self, backup_folder):
        msg = self.import_sql(backup_folder)
        if msg is None:
            return 'Channels Database Restored'
        else:
            return msg
