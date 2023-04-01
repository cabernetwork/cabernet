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
import datetime

from lib.db.db import DB
from lib.common.decorators import Backup
from lib.common.decorators import Restore

DB_EPG_TABLE = 'epg'
DB_CONFIG_NAME = 'db_files-epg_db'

sqlcmds = {
    'ct': [
        """
        CREATE TABLE IF NOT EXISTS epg (
            namespace VARCHAR(255) NOT NULL,
            instance  VARCHAR(255) NOT NULL,
            day       DATE NOT NULL,
            last_update TIMESTAMP,
            file      VARCHAR(255) NOT NULL,
            UNIQUE(namespace, instance, day)
            )
        """
    ],
    'dt': [
        """
        DROP TABLE IF EXISTS epg
        """
    ],

    'epg_column_names_get':
        """
        SELECT name FROM pragma_table_info('epg')
        """,

    'epg_add':
        """
        INSERT OR REPLACE INTO epg (
            namespace, instance, day, last_update, file
            ) VALUES ( ?, ?, ?, ?, ? )
        """,

    'epg_by_day_del':
        """
        DELETE FROM epg WHERE namespace LIKE ? AND instance LIKE ? AND day < DATE('now',?)
        """,
    'epg_by_day_get':
        """
        SELECT file FROM epg WHERE namespace LIKE ? AND instance LIKE ? AND day < DATE('now',?)
        """,

    'epg_instance_del':
        """
        DELETE FROM epg WHERE namespace=? AND instance LIKE ?
        """,

    'epg_instance_get':
        """
        SELECT file FROM epg WHERE namespace=? AND instance LIKE ?
        """,

    'epg_last_update_get':
        """
        SELECT datetime(last_update, 'localtime') FROM epg WHERE
            namespace=? AND instance LIKE ? and day=?
        """,

    'epg_last_update_update':
        """
        UPDATE epg SET 
            last_update=? WHERE namespace LIKE ? AND instance LIKE ?
        """,

    'epg_get':
        """
        SELECT * FROM epg WHERE
            namespace LIKE ? AND instance LIKE ? ORDER BY day LIMIT ? OFFSET ?
        """,
    'epg_one_get':
        """
        SELECT * FROM epg WHERE
            namespace=? AND instance=? AND day=?
        """,
    'epg_name_get':
        """
        SELECT DISTINCT namespace FROM epg
        """,
    'epg_instances_get':
        """
        SELECT DISTINCT namespace, instance FROM epg
        """
}


class DBepg(DB):

    def __init__(self, _config):
        super().__init__(_config, _config['datamgmt'][DB_CONFIG_NAME], sqlcmds)

    def get_col_names(self):
        return self.get(DB_EPG_TABLE + '_column_names')
    
    def save_program_list(self, _namespace, _instance, _day, _prog_list):
        filepath = self.save_file((DB_EPG_TABLE, _namespace, _instance, _day), json.dumps(_prog_list))
        if filepath:
            self.add(DB_EPG_TABLE, (
                _namespace,
                _instance,
                _day,
                datetime.datetime.utcnow(),
                str(filepath),))

    def del_old_programs(self, _namespace, _instance, _days='-2 day'):
        """
        Removes all records for this namespace/instance that are over 2 day old
        """

        if not _namespace:
            _namespace = '%'
        if not _instance:
            _instance = '%'
        files = self.get(DB_EPG_TABLE + '_by_day', (_namespace, _instance, _days,))
        files = [x[0] for x in files]
        for f in files:
            if not self.delete_file(f):
                return
        self.delete(DB_EPG_TABLE + '_by_day', (_namespace, _instance, _days,))

    def del_instance(self, _namespace, _instance):
        """
        Removes all records for this namespace/instance
        """
        if not _instance:
            _instance = '%'
        files = self.get(DB_EPG_TABLE + '_instance', (_namespace, _instance,))
        files = [x[0] for x in files]
        for f in files:
            if not self.delete_file(f):
                return
        return self.delete(DB_EPG_TABLE + '_instance', (_namespace, _instance,))

    def set_last_update(self, _namespace=None, _instance=None, _day=None):
        if not _namespace:
            _namespace = '%'
        if not _instance:
            _instance = '%'
        self.update(DB_EPG_TABLE + '_last_update', (
            _day,
            _namespace,
            _instance,
        ))

    def get_last_update(self, _namespace, _instance, _day):
        if not _instance:
            _instance = '%'
        result = self.get(DB_EPG_TABLE + '_last_update', (_namespace, _instance, _day,))
        if result is None or len(result) == 0:
            return None
        else:
            last_update = result[0][0]
            if last_update is not None:
                return datetime.datetime.fromisoformat(last_update)
            else:
                return None

    def get_epg_names(self):
        return self.get_dict(DB_EPG_TABLE + '_name')

    def get_epg_instances(self):
        return self.get_dict(DB_EPG_TABLE + '_instances')

    def get_epg_one(self, _namespace, _instance, _day):
        row = self.get_dict(DB_EPG_TABLE + '_one', (_namespace, _instance, _day))
        if len(row):
            blob = self.get_file_by_key((_namespace, _instance, _day,))
            if blob:
                row[0]['json'] = json.loads(blob)
                return row
        return []

    def init_get_query(self, _namespace, _instance):
        if not _namespace:
            _namespace = '%'
        if not _instance:
            _instance = '%'
        self.get_init(DB_EPG_TABLE, (_namespace, _instance,))

    def get_next_row(self):
        row = self.get_dict_next()
        namespace = None
        instance = None
        day = None
        if row:
            namespace = row['namespace']
            instance = row['instance']
            day = row['day']
            file = row['file']
            blob = self.get_file(file)
            if blob:
                json_data = json.loads(blob)
            else:
                json_data = []
            row = json_data
        return row, namespace, instance, day

    def close_query(self):
        self.cur.close()

    @Backup(DB_CONFIG_NAME)
    def backup(self, backup_folder):
        self.export_sql(backup_folder)

    @Restore(DB_CONFIG_NAME)
    def restore(self, backup_folder):
        return self.import_sql(backup_folder)
