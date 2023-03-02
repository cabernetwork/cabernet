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

DB_TEMP_TABLE = 'temp'
DB_CONFIG_NAME = 'db_files-temp_db'

sqlcmds = {
    'ct': [
        """
        CREATE TABLE IF NOT EXISTS temp (
            namespace VARCHAR(255) NOT NULL,
            instance  VARCHAR(255) NOT NULL,
            value     VARCHAR(255) NOT NULL,
            last_update TIMESTAMP,
            json      TEXT NOT NULL,
            UNIQUE(namespace, instance, value)
            )
        """
    ],
    'dt': [
        """
        DROP TABLE IF EXISTS temp
        """,
    ],

    'temp_add':
        """
        INSERT OR REPLACE INTO temp (
            namespace, instance, value, last_update, json
            ) VALUES ( ?, ?, ?, ?, ? )
        """,
    'temp_by_day_del':
        """
        DELETE FROM temp WHERE namespace LIKE ? AND instance LIKE ? AND last_update < DATETIME('NOW',?)
        """,

    'temp_del':
        """
        DELETE FROM temp WHERE namespace=? AND instance LIKE ?
        """,
    'temp_get':
        """
        SELECT * FROM temp WHERE
            namespace=? AND instance=? AND value=?
        """
}


class DBTemp(DB):

    def __init__(self, _config):
        super().__init__(_config, _config['datamgmt'][DB_CONFIG_NAME], sqlcmds)

    def save_json(self, _namespace, _instance, _value, _json):
        """
        saves the json blob under a value item for the namespace/instance
        """
        self.add(DB_TEMP_TABLE, (
            _namespace,
            _instance,
            _value,
            datetime.datetime.utcnow(),
            json.dumps(_json),))

    def cleanup_temp(self, _namespace, _instance, _hours='-6 hours'):
        """
        Removes all records for this namespace/instance that are over 1 hour old
        """
        if not _namespace:
            _namespace = '%'
        if not _instance:
            _instance = '%'
        deleted = self.delete(DB_TEMP_TABLE + '_by_day', (_namespace, _instance, _hours,))

    def del_instance(self, _namespace, _instance):
        """
        Removes all records for this namespace/instance
        """
        if not _instance:
            _instance = '%'
        return self.delete(DB_TEMP_TABLE, (_namespace, _instance,))

    def get_record(self, _namespace, _instance, _value):
        return self.get_dict(DB_TEMP_TABLE, (_namespace, _instance, _value))

    @Backup(DB_CONFIG_NAME)
    def backup(self, backup_folder):
        self.export_sql(backup_folder)

    @Restore(DB_CONFIG_NAME)
    def restore(self, backup_folder):
        return self.import_sql(backup_folder)
