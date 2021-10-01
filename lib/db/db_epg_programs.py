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

import json
import datetime
import threading

from lib.db.db import DB
from lib.common.decorators import Backup
from lib.common.decorators import Restore


DB_PROGRAMS_TABLE = 'programs'
DB_CONFIG_NAME = 'db_files-epg_programs_db'

sqlcmds = {
    'ct': [
        """
        CREATE TABLE IF NOT EXISTS programs (
            namespace VARCHAR(255) NOT NULL,
            id        varchar(255) NOT NULL,
            last_update TIMESTAMP,
            json      TEXT NOT NULL,
            UNIQUE(namespace, id)
            )
        """
    ],
    'dt': [
        """
        DROP TABLE IF EXISTS programs
        """,
        ],

    'programs_add':
        """
        INSERT OR REPLACE INTO programs (
            namespace, id, last_update, json
            ) VALUES ( ?, ?, ?, ? )
        """,

    'programs_by_day_del':
        """
        DELETE FROM programs WHERE namespace=? AND last_update < DATE('now',?)
        """,
    'programs_del':
        """
        DELETE FROM programs WHERE namespace=?
        """,
    'programs_get':
        """
        SELECT * FROM programs WHERE
            namespace=? AND id=?
        """,
    'programs_name_get':
        """
        SELECT DISTINCT namespace FROM programs
        """,
}


class DBEpgPrograms(DB):

    def __init__(self, _config):
        super().__init__(_config, _config['datamgmt'][DB_CONFIG_NAME], sqlcmds)

    def save_program(self, _namespace, _id, _prog_dict):
        self.add(DB_PROGRAMS_TABLE, (
            _namespace,
            _id,
            datetime.datetime.utcnow(),
            json.dumps(_prog_dict),))

    def del_old_programs(self, _namespace, _instance):
        """
        Removes all records for this namespace/instance that are over xx days old
        """
        self.delete(DB_PROGRAMS_TABLE +'_by_day', (_namespace, '-30 day'))

    def del_namespace(self, _namespace):
        """
        Removes all records for this namespace
        """
        self.delete(DB_PROGRAMS_TABLE, (_namespace,))

    def get_program_names(self):
        return self.get_dict(DB_PROGRAMS_TABLE + '_name')

    def get_program(self, _namespace, _id):
        return self.get_dict(DB_PROGRAMS_TABLE, (_namespace, _id))
        
    @Backup(DB_CONFIG_NAME)
    def backup(self, backup_folder):
        self.export_sql(backup_folder)

    @Restore(DB_CONFIG_NAME)
    def restore(self, backup_folder):
        return self.import_sql(backup_folder)
