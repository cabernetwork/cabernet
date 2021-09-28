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

import logging
import os
import pathlib
import sqlite3
import threading
import time

DB_EXT = '.db'
BACKUP_EXT = '.sql'

# trailers used in sqlcmds.py
SQL_CREATE_TABLES = 'ct'
SQL_DROP_TABLES = 'dt'
SQL_ADD_ROW = '_add'
SQL_UPDATE = '_update'
SQL_GET = '_get'
SQL_DELETE = '_del'


class DB:
    conn = {}

    def __init__(self, _config, _db_name, _sqlcmds):
        self.logger = logging.getLogger(__name__+str(threading.get_ident()))
        self.config = _config
        self.db_name = _db_name
        self.sqlcmds = _sqlcmds
        self.cur = None

        self.db_fullpath = pathlib.Path(self.config['paths']['db_dir']) \
            .joinpath(_db_name + DB_EXT)
        if not os.path.exists(self.db_fullpath):
            self.logger.debug('Creating new database: {} {}'.format(_db_name, self.db_fullpath))
            self.create_tables()
        self.check_connection()
        DB.conn[self.db_name][threading.get_ident()].commit()

    def sql_exec(self, _sqlcmd, _bindings=None):
        try:
            self.check_connection()
            if _bindings:
                return DB.conn[self.db_name][threading.get_ident()].execute(_sqlcmd, _bindings)
            else:
                return DB.conn[self.db_name][threading.get_ident()].execute(_sqlcmd)
        except sqlite3.IntegrityError as e:
            DB.conn[self.db_name][threading.get_ident()].close()
            del DB.conn[self.db_name][threading.get_ident()]
            raise e

    def add(self, _table, _values):
        cur = None
        sqlcmd = self.sqlcmds[''.join([_table, SQL_ADD_ROW])]
        try:
            cur = self.sql_exec(sqlcmd, _values)
            DB.conn[self.db_name][threading.get_ident()].commit()
            lastrow = cur.lastrowid
            cur.close()
            return lastrow
        except sqlite3.OperationalError as e:
            self.logger.warning('Add request ignored, {}'.format(e))
            DB.conn[self.db_name][threading.get_ident()].rollback()
            if cur is not None:
                cur.close()
            return None

    def delete(self, _table, _values):
        cur = None
        sqlcmd = self.sqlcmds[''.join([_table, SQL_DELETE])]
        try:
            cur = self.sql_exec(sqlcmd, _values)
            DB.conn[self.db_name][threading.get_ident()].commit()
            lastrow = cur.lastrowid
            cur.close()
            return lastrow
        except sqlite3.OperationalError as e:
            self.logger.warning('Delete request ignored, {}'.format(e))
            DB.conn[self.db_name][threading.get_ident()].rollback()
            if cur is not None:
                cur.close()
            return None

    def update(self, _table, _values=None):
        cur = None
        sqlcmd = self.sqlcmds[''.join([_table, SQL_UPDATE])]
        try:
            cur = self.sql_exec(sqlcmd, _values)
            DB.conn[self.db_name][threading.get_ident()].commit()
            lastrow = cur.lastrowid
            cur.close()
            return lastrow
        except sqlite3.OperationalError as e:
            self.logger.warning('Update request ignored, {}'.format(e))
            DB.conn[self.db_name][threading.get_ident()].rollback()
            if cur is not None:
                cur.close()
            return None

    def commit(self):
        DB.conn[self.db_name][threading.get_ident()].commit()

    def get(self, _table, _where=None):
        cur = None
        sqlcmd = self.sqlcmds[''.join([_table, SQL_GET])]
        i = 2
        while i > 0:
            i -= 1
            try:
                cur = self.sql_exec(sqlcmd, _where)
                result = cur.fetchall()
                cur.close()
                return result
            except sqlite3.OperationalError as e:
                self.logger.warning('GET request ignored retrying {}, {}'.format(i, e))
                DB.conn[self.db_name][threading.get_ident()].rollback()
                if cur is not None:
                    cur.close()
                time.sleep(1)
        return None

    def get_dict(self, _table, _where=None, sql=None):
        if sql is None:
            sqlcmd = self.sqlcmds[''.join([_table, SQL_GET])]
        else:
            sqlcmd = sql
        cur = self.sql_exec(sqlcmd, _where)
        records = cur.fetchall()
        rows = []
        for row in records:
            rows.append(dict(zip([c[0] for c in cur.description], row)))
        cur.close()
        return rows

    def get_init(self, _table, _where=None):
        """
            Cursor must remain active following the call.
            runs the query and returns the first row
            while maintaining the cursor.
            Get_dict_next returns the next row
        """
        sqlcmd = self.sqlcmds[''.join([_table, SQL_GET])]
        self.cur = self.sql_exec(sqlcmd, _where)

    def get_dict_next(self):
        """
            Cursor must remain active following the call.
            Termination of the cursor mut be handled externally
        """    
        row = self.cur.fetchone()
        row_dict = None
        if row:
            row_dict = dict(zip([c[0] for c in self.cur.description], row))
        return row_dict

    def reinitialize_tables(self):
        self.drop_tables()
        self.create_tables()

    def create_tables(self):
        for table in self.sqlcmds[''.join([SQL_CREATE_TABLES])]:
            cur = self.sql_exec(table)
        DB.conn[self.db_name][threading.get_ident()].commit()
            

    def drop_tables(self):
        for table in self.sqlcmds[SQL_DROP_TABLES]:
            cur = self.sql_exec(table)
        DB.conn[self.db_name][threading.get_ident()].commit()

    def export_sql(self, backup_folder):
        self.logger.debug('Running backup for {} database'.format(self.db_name))
        try:
            if not os.path.isdir(backup_folder):
                os.mkdir(backup_folder)
            self.check_connection()
            backup_file = pathlib.Path(backup_folder, self.db_name + BACKUP_EXT)
            with open(backup_file, 'w') as export_f:
                for line in DB.conn[self.db_name][threading.get_ident()].iterdump():
                    export_f.write('%s\n' % line)
        except PermissionError as e:
            self.logger.warning(e)
            self.logger.warning('Unable to make backups')
            
    def import_sql(self, backup_folder):
        self.logger.debug('Running restore for {} database'.format(self.db_name))
        if not os.path.isdir(backup_folder):
            msg = 'Backup folder does not exist: {}'.format(backup_folder)
            self.logger.warning(msg)
            return msg
        backup_file = pathlib.Path(backup_folder, self.db_name + BACKUP_EXT)
        if not os.path.isfile(backup_file):
            msg = 'Backup file does not exist, skipping: {}'.format(backup_file)
            self.logger.info(msg)
            return msg
        self.check_connection()
        self.drop_tables()
        with open(backup_file, 'r') as import_f:
            cmd = ''
            for line in import_f:
                cmd += line
                if ';' in line[-3:]:
                    DB.conn[self.db_name][threading.get_ident()].execute(cmd)
                    cmd = ''
        return None

    def close(self):
        thread_id = threading.get_ident()
        DB.conn[self.db_name][thread_id].close()
        del DB.conn[self.db_name][thread_id]
        self.logger.debug('{} database closed for thread:{}'.format(self.db_name, thread_id))

    def check_connection(self):
        if self.db_name not in DB.conn:
            DB.conn[self.db_name] = {}
        db_conn_dbname = DB.conn[self.db_name]
        
        if threading.get_ident() not in db_conn_dbname:
            db_conn_dbname[threading.get_ident()] = sqlite3.connect(
                self.db_fullpath, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        else:
            try:
                db_conn_dbname[threading.get_ident()].total_changes
            except sqlite3.ProgrammingError:
                self.logger.debug('Reopening {} database for thread:{}'.format(self.db_name, threading.get_ident()))
                db_conn_dbname[threading.get_ident()] = sqlite3.connect(
                    self.db_fullpath, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
