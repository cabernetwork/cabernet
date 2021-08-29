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
import threading

from lib.db.db import DB
from lib.common.decorators import Backup
from lib.common.decorators import Restore


DB_AREA_TABLE = 'area'
DB_SECTION_TABLE = 'section'
DB_INSTANCE_TABLE = 'instance'
DB_CONFIG_TABLE = 'config'
DB_CONFIG_NAME = 'db_files-defn_db'

sqlcmds = {
    'ct': [
        """
        CREATE TABLE IF NOT EXISTS area (
            name VARCHAR(255) NOT NULL,
            icon VARCHAR(255) NOT NULL,
            label VARCHAR(255) NOT NULL,
            description TEXT NOT NULL,
            PRIMARY KEY(name)
            )
        """,
        """
        CREATE TABLE IF NOT EXISTS section (
            area VARCHAR(255) NOT NULL,
            name VARCHAR(255) NOT NULL,
            sort VARCHAR(255) NOT NULL,
            icon VARCHAR(255) NOT NULL,
            label VARCHAR(255) NOT NULL,
            description TEXT NOT NULL,
            settings TEXT NOT NULL,
            FOREIGN KEY(area) REFERENCES area(name),
            UNIQUE(area, name)
            )
        """,
        """
        CREATE TABLE IF NOT EXISTS config (
            key VARCHAR(255) NOT NULL,
            settings TEXT NOT NULL,
            PRIMARY KEY(key)
            )
        """,
        """
        CREATE TABLE IF NOT EXISTS instance (
            area VARCHAR(255) NOT NULL,
            name VARCHAR(255) NOT NULL,
            icon VARCHAR(255) NOT NULL,
            label VARCHAR(255) NOT NULL,
            description TEXT NOT NULL,
            settings TEXT NOT NULL,
            FOREIGN KEY(area) REFERENCES area(name),
            UNIQUE(area, name)
            )
        """
    ],

    'dt': [
        """
        DROP TABLE IF EXISTS area
        """,
        """
        DROP TABLE IF EXISTS section
        """,
        """
        DROP TABLE IF EXISTS config
        """,
        """
        DROP TABLE IF EXISTS instance
        """
        ],

    'area_add':
        """
        INSERT OR REPLACE INTO area (
            name, icon, label, description
            ) VALUES ( ?, ?, ?, ? )
        """,
    'area_get':
        """
        SELECT * from area WHERE name LIKE ? ORDER BY rowid
        """,
    'area_keys_get':
        """
        SELECT name from area ORDER BY rowid
        """,

    'section_add':
        """
        INSERT OR REPLACE INTO section (
            area, name, sort, icon, label, description, settings
            ) VALUES ( ?, ?, ?, ?, ?, ?, ? )
        """,
    'section_get':
        """
        SELECT * from section WHERE area = ? ORDER BY sort
        """,
    'section_one_get':
        """
        SELECT * from section WHERE area = ? AND name = ? ORDER BY sort
        """,    
    'section_name_get':
        """
        SELECT area from section WHERE name = ? ORDER BY sort
        """,

    'instance_add':
        """
        INSERT OR REPLACE INTO instance (
            area, name, icon, label, description, settings
            ) VALUES ( ?, ?, ?, ?, ?, ? )
        """,
    'instance_get':
        """
        SELECT * from instance WHERE area = ? ORDER BY rowid
        """,

    'config_add':
        """
        INSERT OR REPLACE INTO config (
            key, settings
            ) VALUES ( 'main', ? )
        """,
    'config_get':
        """
        SELECT settings from config
        """

}


class DBConfigDefn(DB):

    def __init__(self, _config):
        super().__init__(_config, _config['datamgmt'][DB_CONFIG_NAME], sqlcmds)

    def get_area_dict(self, _where=None):
        if not _where:
            _where = '%'
        return self.get_dict(DB_AREA_TABLE, (_where,))

    def get_area_json(self, _where=None):
        if not _where:
            _where = '%'
        return json.dumps(self.get_dict(DB_AREA_TABLE, (_where,)))

    def get_areas(self):
        """ returns an array of the area names in id order
        """
        area_tuple = self.get('area_keys')
        areas = [area[0] for area in area_tuple]
        return areas

    def add_area(self, _area, _area_data):
        self.add(DB_AREA_TABLE, (
            _area,
            _area_data['icon'],
            _area_data['label'],
            _area_data['description']
        ))

    def get_sections_dict(self, _where):
        rows_dict = {}
        rows = self.get_dict(DB_SECTION_TABLE, (_where,))
        for row in rows:
            settings = json.loads(row['settings'])
            row['settings'] = settings
            rows_dict[row['name']] = row
        return rows_dict

    def get_one_section_dict(self, _area, _section):
        rows_dict = {}
        rows = self.get_dict(DB_SECTION_TABLE+'_one', (_area, _section,))
        for row in rows:
            settings = json.loads(row['settings'])
            row['settings'] = settings
            rows_dict[row['name']] = row
        return rows_dict
        
    def get_area_by_section(self, _where):
        """ returns an array of the area names that match the section
        """
        area_tuple = self.get('section_name', (_where,))
        areas = [area[0] for area in area_tuple]
        return areas

    def add_section(self, _area, _section, _section_data):
        self.add(DB_SECTION_TABLE, (
            _area,
            _section,
            _section_data['sort'],
            _section_data['icon'],
            _section_data['label'],
            _section_data['description'],
            json.dumps(_section_data['settings'])
        ))

    def get_instance_dict(self, _where):
        rows_dict = {}
        rows = self.get_dict(DB_INSTANCE_TABLE, (_where,))
        for row in rows:
            settings = json.loads(row['settings'])
            row['settings'] = settings
            rows_dict[row['name']] = row
        return rows_dict

    def add_instance(self, _area, _section, _section_data):
        self.add(DB_INSTANCE_TABLE, (
            _area,
            _section,
            _section_data['icon'],
            _section_data['label'],
            _section_data['description'],
            json.dumps(_section_data['settings'])
        ))

    def add_config(self, _config):
        self.add(DB_CONFIG_TABLE, (
            json.dumps(_config),
        ))
    
    def get_config(self):
        return json.loads(self.get_dict(DB_CONFIG_TABLE)[0]['settings'])

    @Backup(DB_CONFIG_NAME)
    def backup(self, backup_folder):
        self.export_sql(backup_folder)

    @Restore(DB_CONFIG_NAME)
    def restore(self, backup_folder):
        msg = self.import_sql(backup_folder)
        if msg is None:
            return 'Config Database Restored'
        else:
            return msg
