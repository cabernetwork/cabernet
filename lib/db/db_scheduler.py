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

import ast
import json
import datetime
import sqlite3
import threading
import uuid

from lib.db.db import DB
from lib.common.decorators import Backup
from lib.common.decorators import Restore


DB_TASK_TABLE = 'task'
DB_TRIGGER_TABLE = 'trigger'
DB_CONFIG_NAME = 'db_files-scheduler_db'


sqlcmds = {
    'ct': [
        """
        CREATE TABLE IF NOT EXISTS task (
            taskid      VARCHAR(255) NOT NULL,
            area      VARCHAR(255) NOT NULL,
            title     VARCHAR(255) NOT NULL,
            namespace VARCHAR(255) NOT NULL,
            instance  VARCHAR(255),
            funccall  VARCHAR(255) NOT NULL,
            lastran   TIMESTAMP,
            duration  INTEGER,
            priority  INTEGER,
            threadtype VARCHAR(255) 
                CHECK( threadtype IN ('inline', 'thread', 'process') ) NOT NULL,
            active    BOOLEAN DEFAULT 0,
            description TEXT,
            UNIQUE(area, title)
            )
        """,
        """
        CREATE TABLE IF NOT EXISTS trigger (
            uuid      VARCHAR(255) NOT NULL,
            area      VARCHAR(255) NOT NULL,
            title      VARCHAR(255) NOT NULL,
            timetype      VARCHAR(255)
                CHECK( timetype IN ('daily', 'weekly', 'interval', 'startup') ) NOT NULL,
            timelimit INTEGER,
            timeofday      VARCHAR(255),
            dayofweek VARCHAR(255)
                CHECK( dayofweek IN ('Sunday', 'Monday', 'Tuesday', 'Wednesday',
                'Thursday', 'Friday', 'Saturday') ),
            interval  INTEGER,
            randdur   INTEGER,
            UNIQUE(uuid)
            FOREIGN KEY(area, title) REFERENCES task(area, title)
            )
        """
    ],
    'dt': [
        """
        DROP TABLE IF EXISTS trigger
        """,
        """
        DROP TABLE IF EXISTS task
        """
        ],
    
    'task_add':
        """
        INSERT INTO task (
            taskid, area, title, namespace, instance, funccall,
            priority, threadtype, description
            ) VALUES ( ?, ?, ?, ?, ?, ?, ?, ?, ? )
        """,
    'task_active_update':
        """
        UPDATE task SET active=?
        WHERE area LIKE ? AND title LIKE ?
        """,
    'task_finish_update':
        """
        UPDATE task SET active=0,
        lastran=?, duration=?
        WHERE area=? AND title=?
        """,
    'task_get':
        """
        SELECT *
        FROM task
        WHERE area LIKE ? AND title LIKE ?
        ORDER BY task.area ASC, task.title ASC
        """,
    'task_name_get':
        """
        SELECT DISTINCT namespace FROM task
        """,
    'task_by_id_get':
        """
        SELECT *
        FROM task
        WHERE taskid LIKE ?
        ORDER BY task.area ASC, task.title ASC
        """,
    'task_by_name_get':
        """
        SELECT *
        FROM task
        WHERE namespace LIKE ?
        ORDER BY task.area ASC, task.title ASC
        """,
    'task_active_get':
        """
        SELECT active
        FROM task
        WHERE taskid = ?
        """,
    'task_del':
        """
        DELETE FROM task WHERE
        area = ? AND title = ?;
        """,
    'trigger_del':
        """
        DELETE FROM trigger WHERE
        area = ? AND title = ?;
        """,

    'trigger_add':
        """
        INSERT OR REPLACE INTO trigger (
        uuid, area, title, timetype, timelimit, timeofday, dayofweek, interval, randdur )
        VALUES ( ?, ?, ?, ?, ?, ?, ?, ?, ? )
        """,
    'trigger_by_uuid_get':
        """
        SELECT *
        FROM trigger 
        INNER JOIN task ON task.area = trigger.area
        AND task.title = trigger.title
        WHERE trigger.uuid = ?
        """,
    'trigger_by_taskid_get':
        """
        SELECT *
        FROM trigger 
        INNER JOIN task ON task.area = trigger.area
        AND task.title = trigger.title
        WHERE task.taskid LIKE ?
        ORDER BY task.area ASC, task.title ASC, trigger.timetype DESC
        """,
    'trigger_by_type_get':
        """
        SELECT *
        FROM trigger 
        INNER JOIN task ON task.area = trigger.area
        AND task.title = trigger.title
        WHERE trigger.timetype LIKE ?
        ORDER BY task.priority DESC
        """,
    'trigger_by_uuid_del':
        """
        DELETE FROM trigger WHERE uuid=?
        """
}


class DBScheduler(DB):

    def __init__(self, _config):
        super().__init__(_config, _config['datamgmt'][DB_CONFIG_NAME], sqlcmds)        

    def save_task(self, _area, _title, _namespace, _instance, _funccall, 
            _priority, _threadtype, _description):
        """
        Returns true if the record was saved.  If the record already exists,
        it will return false.
        """
        try:
            id = str(uuid.uuid1()).upper()
            self.add(DB_TASK_TABLE, (
                id,
                _area,
                _title,
                _namespace,
                _instance,
                _funccall,
                _priority,
                _threadtype,
                _description
            ))
            return True
        except sqlite3.IntegrityError:
            return False

    def del_task(self, _area=None, _title=None):
        """
        Deletes the task and associated triggers
        """
        if not _area:
            _area = '%'
        if not _title:
            _title = '%'
        self.delete(DB_TRIGGER_TABLE, (_area, _title,))
        self.delete(DB_TASK_TABLE, (_area, _title,))

    def get_tasks(self, _area=None, _title=None):
        if not _area:
            _area = '%'
        if not _title:
            _title = '%'
        return self.get_dict(DB_TASK_TABLE, (
            _area,
            _title,
        ))

    def get_tasks_by_name(self, _name=None):
        if not _name:
            _name = '%'
        return self.get_dict(DB_TASK_TABLE + '_by_name', (
            _name,
        ))



    def get_task(self, _id):
        task = self.get_dict(DB_TASK_TABLE + '_by_id', (
            _id,
        ))
        if len(task) == 1:
            return task[0]
        else:
            return None    

    def get_task_names(self):
        return self.get_dict(DB_TASK_TABLE + '_name')

    def start_task(self, _area, _title):
        self.update(DB_TASK_TABLE + '_active', (
            1,
            _area,
            _title,
        ))

    def finish_task(self, _area, _title, _duration):
        self.update(DB_TASK_TABLE + '_finish', (
            datetime.datetime.utcnow(),
            _duration,
            _area,
            _title,
        ))

    def reset_activity(self, _activity=False, _area=None, _title=None):
        if not _area:
            _area = '%'
        if not _title:
            _title = '%'
        self.update(DB_TASK_TABLE + '_active', (
            _activity,
            _area,
            _title,
        ))

    def get_active_status(self, _taskid):
        return self.get_dict(DB_TASK_TABLE + '_active', (_taskid,))[0]['active']

    def save_trigger(self, _area, _title, _timetype, timeofday=None, 
            dayofweek=None, interval=-1, timelimit=-1, randdur=-1):
        """
        timetype: daily, weekly, interval, startup
        timelimit: maximum time it can run before terminating. -1 is not used
        timeofday: used with daily and weekly. defines the time of day it runs
        dayofweek: string for the day of the week. ex: Wednesday
        interval: used with timetype: interval in minutes. task will run every x minutes
        randdur: maximum in minutes. Interval only. Will add a randum amount 
        to the event start time up to the maximum minutes.  -1 is not used.
        """
        id = str(uuid.uuid1()).upper()
        self.add(DB_TRIGGER_TABLE, (
            id,
            _area,
            _title,
            _timetype,
            timelimit,
            timeofday,
            dayofweek,
            interval,
            randdur,
        ))
        return id

    def get_triggers_by_type(self, _timetype):
        """
        Returns the list of triggers based on timetype and ordered 
        by priority
        """
        if not _timetype:
            _timetype = '%'
        return self.get_dict(DB_TRIGGER_TABLE + '_by_type', (_timetype,))

    def get_trigger(self, _uuid):
        trigger = self.get_dict(DB_TRIGGER_TABLE + '_by_uuid', (_uuid,))
        if len(trigger) == 1:
            return trigger[0]
        else:
            return None    

    def get_triggers(self, _taskid=None):
        """
        Returns all triggers ordered by area, name, timetype and
        also provides the task information on each trigger
        """
        if not _taskid:
            _taskid = '%'
        return self.get_dict(DB_TRIGGER_TABLE + '_by_taskid', (_taskid,))

    def del_trigger(self, _uuid):
        self.delete(DB_TRIGGER_TABLE + '_by_uuid', (_uuid,))

    @Backup(DB_CONFIG_NAME)
    def backup(self, backup_folder):
        self.export_sql(backup_folder)

    @Restore(DB_CONFIG_NAME)
    def restore(self, backup_folder):
        msg = self.import_sql(backup_folder)
        if msg is None:
            msg = 'Scheduler Database Restored'
        self.reset_activity()
        return msg
