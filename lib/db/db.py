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
import random
import shutil
import sqlite3
import threading
import time

LOCK = threading.Lock()
DB_EXT = '.db'
BACKUP_EXT = '.sql'

# trailers used in sqlcmds.py
SQL_CREATE_TABLES = 'ct'
SQL_DROP_TABLES = 'dt'
SQL_ADD_ROW = '_add'
SQL_UPDATE = '_update'
SQL_GET = '_get'
SQL_DELETE = '_del'
FILE_LINK_ZIP = '_filelinks'

class DB:
    conn = {}

    def __init__(self, _config, _db_name, _sqlcmds):
        self.logger = logging.getLogger(__name__ + str(threading.get_ident()))
        self.config = _config
        self.db_name = _db_name
        self.sqlcmds = _sqlcmds
        self.cur = None
        self.offset = -1
        self.where = None
        self.sqlcmd = None

        self.db_fullpath = pathlib.Path(self.config['paths']['db_dir']) \
            .joinpath(_db_name + DB_EXT)
        if not os.path.exists(self.db_fullpath):
            self.logger.debug('Creating new database: {} {}'.format(_db_name, self.db_fullpath))
            self.create_tables()
        self.check_connection()
        DB.conn[self.db_name][threading.get_ident()].commit()

    def sql_exec(self, _sqlcmd, _bindings=None, _cursor=None):
        try:
            self.check_connection()
            if _bindings:
                if _cursor:
                    return _cursor.execute(_sqlcmd, _bindings)
                else:
                    return DB.conn[self.db_name][threading.get_ident()].execute(_sqlcmd, _bindings)
            else:
                if _cursor:
                    return _cursor.execute(_sqlcmd)
                else:
                    return DB.conn[self.db_name][threading.get_ident()].execute(_sqlcmd)
        except sqlite3.IntegrityError as e:
            DB.conn[self.db_name][threading.get_ident()].close()
            del DB.conn[self.db_name][threading.get_ident()]
            raise e

    def rnd_sleep(self, _sec):
        r = random.randrange(0, 50)
        sec = _sec + r / 100
        time.sleep(sec)

    def add(self, _table, _values):
        cur = None
        sqlcmd = self.sqlcmds[''.join([_table, SQL_ADD_ROW])]
        i = 10
        while i > 0:
            i -= 1
            try:
                self.check_connection()
                cur = DB.conn[self.db_name][threading.get_ident()].cursor()
                self.sql_exec(sqlcmd, _values, cur)
                DB.conn[self.db_name][threading.get_ident()].commit()
                lastrow = cur.lastrowid
                cur.close()
                return lastrow
            except sqlite3.OperationalError as e:
                self.logger.warning('{} Add request ignored, retrying {}, {}'
                                    .format(self.db_name, i, e))
                DB.conn[self.db_name][threading.get_ident()].rollback()
                if cur is not None:
                    cur.close()
                self.rnd_sleep(0.3)
        return None

    def delete(self, _table, _values):
        cur = None
        sqlcmd = self.sqlcmds[''.join([_table, SQL_DELETE])]
        i = 10
        while i > 0:
            i -= 1
            try:
                self.check_connection()
                cur = DB.conn[self.db_name][threading.get_ident()].cursor()
                self.sql_exec(sqlcmd, _values, cur)
                num_deleted = cur.rowcount
                DB.conn[self.db_name][threading.get_ident()].commit()
                cur.close()
                return num_deleted
            except sqlite3.OperationalError as e:
                self.logger.warning('{} Delete request ignored, retrying {}, {}'
                                    .format(self.db_name, i, e))
                DB.conn[self.db_name][threading.get_ident()].rollback()
                if cur is not None:
                    cur.close()
                self.rnd_sleep(0.3)
        return 0

    def update(self, _table, _values=None):
        cur = None
        sqlcmd = self.sqlcmds[''.join([_table, SQL_UPDATE])]
        i = 10
        while i > 0:
            i -= 1
            try:
                LOCK.acquire(True)
                self.check_connection()
                cur = DB.conn[self.db_name][threading.get_ident()].cursor()
                self.sql_exec(sqlcmd, _values, cur)
                DB.conn[self.db_name][threading.get_ident()].commit()
                lastrow = cur.lastrowid
                cur.close()
                LOCK.release()
                return lastrow
            except sqlite3.OperationalError as e:
                self.logger.notice('{} Update request ignored, retrying {}, {}'
                                    .format(self.db_name, i, e))
                DB.conn[self.db_name][threading.get_ident()].rollback()
                if cur is not None:
                    cur.close()
                LOCK.release()
                self.rnd_sleep(0.3)
        return None

    def commit(self):
        DB.conn[self.db_name][threading.get_ident()].commit()

    def get(self, _table, _where=None):
        cur = None
        sqlcmd = self.sqlcmds[''.join([_table, SQL_GET])]
        i = 10
        while i > 0:
            i -= 1
            try:
                self.check_connection()
                cur = DB.conn[self.db_name][threading.get_ident()].cursor()
                self.sql_exec(sqlcmd, _where, cur)
                result = cur.fetchall()
                cur.close()
                return result
            except sqlite3.OperationalError as e:
                self.logger.warning('{} GET request ignored retrying {}, {}'
                                    .format(self.db_name, i, e))
                DB.conn[self.db_name][threading.get_ident()].rollback()
                if cur is not None:
                    cur.close()
                self.rnd_sleep(0.3)
        return None

    def get_dict(self, _table, _where=None, sql=None):
        cur = None
        if sql is None:
            sqlcmd = self.sqlcmds[''.join([_table, SQL_GET])]
        else:
            sqlcmd = sql
        i = 10
        while i > 0:
            i -= 1
            try:
                LOCK.acquire(True)
                self.check_connection()
                cur = DB.conn[self.db_name][threading.get_ident()].cursor()
                self.sql_exec(sqlcmd, _where, cur)
                records = cur.fetchall()
                rows = []
                for row in records:
                    rows.append(dict(zip([c[0] for c in cur.description], row)))
                cur.close()
                LOCK.release()
                return rows
            except sqlite3.OperationalError as e:
                self.logger.warning('{} GET request ignored retrying {}, {}'
                                    .format(self.db_name, i, e))
                DB.conn[self.db_name][threading.get_ident()].rollback()
                if cur is not None:
                    cur.close()
                LOCK.release()
                self.rnd_sleep(0.3)
        return None

    def get_init(self, _table, _where=None):
        """
            Requires "LIMIT ? OFFSET ?" at the end of the sql statement
        """
        self.sqlcmd = self.sqlcmds[''.join([_table, SQL_GET])]
        self.where = list(_where)
        self.offset = 0

    def get_dict_next(self):
        w_list = self.where.copy()
        w_list.extend((1, self.offset))
        self.cur = self.sql_exec(self.sqlcmd, tuple(w_list))
        records = self.cur.fetchall()
        self.offset += 1
        if len(records) == 0:
            return None
        row = records[0]
        return dict(zip([c[0] for c in self.cur.description], row))

    def save_file(self, _keys, _blob):
        """
        Stores the blob in the folder with the db name with
        the filename of concatenated _keys
        _keys is the list of unique keys for the table
        Returns the filepath to the file generated
        """
        folder_path = pathlib.Path(self.config['paths']['db_dir']) \
            .joinpath(self.db_name)
        os.makedirs(folder_path, exist_ok=True)
        filename = '_'.join(str(x) for x in _keys) + '.txt'
        file_rel_path = pathlib.Path(self.db_name).joinpath(filename)
        filepath = folder_path.joinpath(filename)
        try:
            with open(filepath, mode='wb') as f:
                if isinstance(_blob, str):
                    f.write(_blob.encode())
                else:
                    f.write(_blob)
                f.flush()
                f.close()
        except PermissionError as ex:
            self.logger.warning('Unable to create linked database file {}'
                .format(file_rel_path))
            return None
        return file_rel_path

    def delete_file(self, _filepath):
        """
        _filepath is relative to the database path
        """
        fullpath = pathlib.Path(self.config['paths']['db_dir']) \
            .joinpath(_filepath)
        try:
            os.remove(fullpath)
            return True
        except PermissionError as ex:
            self.logger.warning('Unable to delete linked database file {}'
                .format(_filepath))
            return False
        except FileNotFoundError as ex:
            self.logger.warning('File missing, unable to delete linked database file {}'
                .format(_filepath))
            return False

    def get_file(self, _filepath):
        """
        _filepath is relative to the database path
        return the blob
        """
        fullpath = pathlib.Path(self.config['paths']['db_dir']) \
            .joinpath(_filepath)

        if not fullpath.exists():
            self.logger.warning('Linked database file Missing {}'.format(_filepath))
            return None
        try:
            with open(fullpath, mode='rb') as f:
                blob = f.read()
                f.close()
            return blob
        except PermissionError as ex:
            self.logger.warning('Unable to read linked database file {}'
                .format(_filepath))
            return None

    def get_file_by_key(self, _keys):
        filename = '_'.join(str(x) for x in _keys) + '.txt'
        file_rel_path = pathlib.Path(self.db_name).joinpath(filename)
        return self.get_file(file_rel_path)

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

            # Check for linked file folder and zip up if present
            db_linkfilepath = pathlib.Path(self.config['paths']['db_dir']) \
                .joinpath(self.db_name)
            if db_linkfilepath.exists():
                self.logger.debug('Linked file folder exists, backing up folder for db {}'.format(self.db_name))
                backup_filelink = pathlib.Path(backup_folder, self.db_name + FILE_LINK_ZIP)
                shutil.make_archive(backup_filelink, 'zip', db_linkfilepath)

            backup_file = pathlib.Path(backup_folder, self.db_name + BACKUP_EXT)
            with open(backup_file, 'w', encoding='utf-8') as export_f:
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

        # Check for linked file folder and zip up if present
        backup_filelink = pathlib.Path(backup_folder, self.db_name + FILE_LINK_ZIP + '.zip')
        db_linkfilepath = pathlib.Path(self.config['paths']['db_dir']) \
            .joinpath(self.db_name)
        if backup_filelink.exists():
            self.logger.debug('Linked file folder exists, restoring folder for db {}'.format(self.db_name))
            shutil.unpack_archive(backup_filelink, db_linkfilepath)

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
