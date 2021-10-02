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

import importlib
import logging
import urllib.request
import time
from multiprocessing import Process
from threading import Thread

import lib.main as main
import lib.schedule.schedule
import lib.common.exceptions as exceptions
from lib.common.decorators import getrequest
from lib.db.db_scheduler import DBScheduler
from lib.web.pages.templates import web_templates


@getrequest.route('/api/scheduler')
def get_scheduler(_webserver):
    try:
        if _webserver.query_data['action'] == 'runtask':
            _webserver.sched_queue.put({'cmd': 'runtask', 'taskid': _webserver.query_data['taskid'] })
            time.sleep(0.1)
            _webserver.do_mime_response(200, 'text/html', 'action is ' + _webserver.query_data['action'])
            return
        else:
            _webserver.do_mime_response(501, 'text/html',
                web_templates['htmlError'].format('501 - Unknown action'))
    except KeyError:
        _webserver.do_mime_response(501, 'text/html', 
            web_templates['htmlError'].format('501 - Badly formed request'))
    

class Scheduler(Thread):
    """
    Assumed to be a singleton
    triggers are associated with a task in the database and define when a task runs
    jobs are listed in the Schedule object and run as cron jobs. Triggers with
    their associated tasks define jobs.
    Calls are from the sched_queue to run, delete or add triggers/jobs.
    Tasks are not managed by this class.
    Only one trigger/job can run from within a task at any point in time.
    """
    scheduler_obj = None


    def __init__(self, _plugins, _queue):
        Thread.__init__(self)
        self.logger = logging.getLogger(__name__)
        self.plugins = _plugins
        self.queue = _queue
        self.config_obj = _plugins.config_obj
        self.scheduler_db = DBScheduler(self.config_obj.data)
        self.scheduler_db.reset_activity()
        self.schedule = lib.schedule.schedule
        self.daemon = True
        self.stop_thread = False
        Scheduler.scheduler_obj = self

        def _queue_thread():
            while not self.stop_thread:
                queue_item = self.queue.get(True)
                self.process_queue(queue_item)
        _q_thread = Thread(target=_queue_thread, args=())
        _q_thread.start()
        self.start()

    def run(self):
        """
        Thread run method for the class.
        - Executes all startup tasks
        - Sets up the Schedule/Job objects based on database
        - Loops getting queue events and runs any pending triggers
        """
        self.setup_triggers()
        triggers = self.scheduler_db.get_triggers_by_type('startup')
        for trigger in triggers:
            self.exec_trigger(trigger)
        while not self.stop_thread:
            self.schedule.run_pending()
            for i in range(30):
                if self.stop_thread:
                    break
                time.sleep(1)

    def terminate(self):
        self.stop_thread = True
        self.queue.put({'cmd': 'noop'})

    def exec_trigger(self, _trigger):
        """
        Main entry for the Schedule Job to run a task/event
        """
        if self.scheduler_db.get_active_status(_trigger['taskid']):
            self.logger.debug('Task currently running, ignored request {}:{}'.format(
                _trigger['area'], _trigger['title']))
            return

        self.scheduler_db.start_task(_trigger['area'], _trigger['title'])
        if _trigger['threadtype'] == 'thread':
            self.logger.notice('Running threaded task {}:{}'.format(
                _trigger['area'], _trigger['title']))
            t_event = Thread(target=self.call_trigger, args=(_trigger,))
            t_event.start()
        elif _trigger['threadtype'] == 'process':
            self.logger.notice('Running process task {}:{}'.format(
                _trigger['area'], _trigger['title']))
            p_event = Process(target=self.call_trigger, args=(_trigger,))
            p_event.start()
        else:
            self.logger.notice('Running inline task {}:{}'.format(
                _trigger['area'], _trigger['title']))
            self.call_trigger(_trigger)

    def call_trigger(self, _trigger):
        """
        Calls the trigger function and times the result
        """
        start = time.time()
        try:
            if _trigger['namespace'] == 'internal':
                mod_name, func_name = _trigger['funccall'].rsplit('.', 1)
                mod = importlib.import_module(mod_name)
                call_f = getattr(mod, func_name)
                call_f(self.plugins)
            else:
                if _trigger['namespace'] not in self.plugins.plugins:
                    self.logger.debug('{} scheduled tasks ignored. plugin missing' \
                        .format(_trigger['namespace']))
                else:
                    plugin_obj = self.plugins.plugins[_trigger['namespace']].plugin_obj
                    if plugin_obj is None:
                        self.logger.debug('{} scheduled tasks ignored. plugin disabled' \
                            .format(_trigger['namespace']))
                    elif _trigger['instance'] is None:
                        call_f = getattr(plugin_obj, _trigger['funccall'])
                        call_f()
                    else:
                        call_f = getattr(plugin_obj.instances[_trigger['instance']], 
                            _trigger['funccall'])
                        call_f()
        except exceptions.CabernetException as ex:
            self.logger.warning('{}'.format(str(ex)))
        except Exception as ex:
            self.logger.exception('{}{}'.format(
                'UNEXPECTED EXCEPTION on GET=', ex))
        end = time.time()
        duration = int(end - start)
        time.sleep(0.2)
        self.scheduler_db.finish_task(_trigger['area'], _trigger['title'], duration)

    def setup_triggers(self):
        """
        Assumes the trigger is already in the database and adds the job
        to the Schedule object
        """
        triggers = self.scheduler_db.get_triggers_by_type('daily')
        for trigger_data in triggers:
            self.add_job(trigger_data)

        triggers = self.scheduler_db.get_triggers_by_type('weekly')
        for trigger_data in triggers:
            self.add_job(trigger_data)

        triggers = self.scheduler_db.get_triggers_by_type('interval')
        for trigger_data in triggers:
            self.add_job(trigger_data)

    def add_job(self, _trigger):
        """
        Adds a job to the schedule object using the trigger dict from the database
        """
        if  _trigger['timetype'] == 'daily':
            self.schedule.every().day.at(_trigger['timeofday']).do(
                self.exec_trigger, _trigger) \
                .tag(_trigger['uuid'])
        elif _trigger['timetype'] == 'weekly':
            getattr(self.schedule.every(), _trigger['dayofweek'].lower()) \
                .at(_trigger['timeofday']).do(
                self.exec_trigger, _trigger) \
                .tag(_trigger['uuid'])
        elif _trigger['timetype'] == 'interval':
            if  _trigger['randdur'] < 0:
                self.schedule.every(_trigger['interval']).minutes.do(
                    self.exec_trigger, _trigger) \
                    .tag(_trigger['uuid'])
            else:
                self.schedule.every(_trigger['interval']) \
                    .to(_trigger['interval'] + _trigger['randdur']) \
                    .minutes.do(self.exec_trigger, _trigger) \
                    .tag(_trigger['uuid'])
        elif _trigger['timetype'] == 'startup':
            pass
        else:
            self.logger.warning('Bad trigger timetype called {}'.format(_trigger))

        # Need to add UNTIL method to trigger when provided
        # database has timelimit in minutes and by default is set to -1.
        # until does not work that way.  Use a second trigger to clear the first if it is still running.
        # but only works when the randum generator is not used.
        # also it won't work for inline triggers since a second trigger cannot run.

    def process_queue(self, _queue_item):
        """
        cmd: run_job, arg: uuid
        cmd: del_job, arg: uuid
        cmd: add_job, arg: trigger data without uuid
        """
        try:
            if _queue_item['cmd'] == 'run':
                self.run_trigger(_queue_item['uuid'])
            elif _queue_item['cmd'] == 'runtask':
                self.run_task(_queue_item['taskid'])
            elif _queue_item['cmd'] == 'deltask':
                self.delete_task(_queue_item['taskid'])
            elif _queue_item['cmd'] == 'del':
                self.delete_trigger(_queue_item['uuid'])
            elif _queue_item['cmd'] == 'add':
                self.add_trigger(_queue_item['trigger'])
            elif _queue_item['cmd'] == 'noop':
                pass
            else:
                self.logger.warning('UNKNOWN Scheduler cmd from queue: {}'.format(_queue_item))
        except KeyError as e:
            self.logger.warning('Badly formed scheduled request {} {}'.format(_queue_item, repr(e)))
        
    def delete_trigger(self, _uuid):
        self.logger.notice('Deleting trigger {}'.format(_uuid))
        jobs = self.schedule.get_jobs(_uuid)
        for job in jobs:
            self.schedule.cancel_job(job)
        self.scheduler_db.del_trigger(_uuid)

    def run_trigger(self, _uuid):
        jobs = self.schedule.get_jobs(_uuid)
        if len(jobs) == 0:
            self.logger.info('Invalid trigger uuid job in schedule for run request {}'.format(_uuid))
        else:
            for job in jobs:
                job.run()

    def add_trigger(self, trigger):
        if trigger['timetype'] == 'startup':
            self.create_trigger(trigger['area'], trigger['title'],
                trigger['timetype'])
        elif trigger['timetype'] == 'daily':
            self.create_trigger(trigger['area'], trigger['title'],
                trigger['timetype'],
                timeofday=trigger['timeofday']
                )
        elif trigger['timetype'] == 'daily':
            self.create_trigger(trigger['area'], trigger['title'],
                trigger['timetype'],
                timeofday=trigger['timeofday']
                )
        elif trigger['timetype'] == 'weekly':
            self.create_trigger(trigger['area'], trigger['title'],
                trigger['timetype'],
                timeofday=trigger['timeofday'],
                dayofweek=trigger['dayofweek']
                )
        elif trigger['timetype'] == 'interval':
            self.create_trigger(trigger['area'], trigger['title'],
                trigger['timetype'],
                interval=trigger['interval'],
                randdur=trigger['randdur']
                )

    def create_trigger(self, _area, _title, _timetype, timeofday=None, 
            dayofweek=None, interval=-1, timelimit=-1, randdur=-1):
        self.logger.notice('Creating trigger {}:{}:{}'.format(_area, _title, _timetype))
        uuid = self.scheduler_db.save_trigger(_area, _title, _timetype, timeofday, 
            dayofweek, interval, timelimit, randdur)
        trigger = self.scheduler_db.get_trigger(uuid)
        self.add_job(trigger)

    def delete_task(self, _taskid):
        task = self.scheduler_db.get_task(_taskid)
        if task is not None:
            self.scheduler_db.del_task(task['area'], task['title'])

    def run_task(self, _taskid):
        triggers = self.scheduler_db.get_triggers(_taskid)
        if len(triggers) == 0:
            # check if the task has no triggers
            task = self.scheduler_db.get_task(_taskid)
            if task is not None:
                self.exec_trigger(task)
            else:
                self.logger.warning('Invalid taskid when requesting to run task')
            return

        is_run = False
        default_trigger = None
        for trigger in triggers:
            if trigger['timetype'] == 'startup':
                continue
            elif trigger['timetype'] == 'interval':
                self.queue.put({'cmd': 'run', 'uuid': trigger['uuid'] })
                is_run = True
                break
            else:
                default_trigger = trigger
        if not is_run:
            if default_trigger is not None:
                self.queue.put({'cmd': 'run', 'uuid': trigger['uuid'] })
            else:
                task = self.scheduler_db.get_task(_taskid)
                if task is not None:
                    self.exec_trigger(task)
                else:
                    self.logger.warning('Invalid taskid when requesting to run task')
