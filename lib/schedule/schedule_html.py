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

import datetime
import logging
import time

from lib.common.decorators import getrequest
from lib.common.decorators import postrequest
from lib.db.db_scheduler import DBScheduler


@getrequest.route('/api/schedulehtml')
def get_schedule_html(_webserver):
    schedule_html = ScheduleHTML(_webserver.config, _webserver.sched_queue)
    if 'run' in _webserver.query_data:
        schedule_html.run_task(_webserver.query_data['task'])
        time.sleep(0.05)
        html = schedule_html.get(_webserver.query_data)
    elif 'deltask' in _webserver.query_data:
        schedule_html.del_task(_webserver.query_data['task'])
        time.sleep(0.05)
        html = schedule_html.get(_webserver.query_data)
    elif 'delete' in _webserver.query_data:
        schedule_html.del_trigger(_webserver.query_data['trigger'])
        time.sleep(0.05)
        html = schedule_html.get_task(_webserver.query_data['task'])
    elif 'trigger' in _webserver.query_data:
        html = schedule_html.get_trigger(_webserver.query_data['task'])
    elif 'task' in _webserver.query_data:
        html = schedule_html.get_task(_webserver.query_data['task'])
    else:
        html = schedule_html.get(_webserver.query_data)
    _webserver.do_mime_response(200, 'text/html', html)


@postrequest.route('/api/schedulehtml')
def post_schedule_html(_webserver):
    schedule_html = ScheduleHTML(_webserver.config, _webserver.sched_queue)
    html = schedule_html.post_add_trigger(_webserver.query_data)
    _webserver.do_mime_response(200, 'text/html', html)


class ScheduleHTML:

    def __init__(self, _config, _queue):
        self.logger = logging.getLogger(__name__)
        self.config = _config
        self.queue = _queue
        self.query_data = None
        self.scheduler_db = DBScheduler(self.config)

    def get(self, _query_data):
        self.query_data = _query_data
        return ''.join([self.header, self.body])

    @property
    def header(self):
        return ''.join([
            '<!DOCTYPE html><html><head>',
            '<meta charset="utf-8"/><meta name="author" content="rocky4546">',
            '<meta name="description" content="schedule task management for Cabernet">',
            '<title>Scheduled Tasks</title>',
            '<meta name="viewport" content="width=device-width, ',
            'minimum-scale=1.0, maximum-scale=1.0">',
            '<script src="https://code.jquery.com/jquery-3.5.1.min.js"></script>',
            '<link rel="stylesheet" type="text/css" href="/modules/scheduler/scheduler.css">',
            '<script src="/modules/scheduler/scheduler.js"></script>'
        ])

    @property
    def body(self):
        return ''.join(['<body>', self.title, self.schedule_tasks,
                        self.task, '</body>'])

    @property
    def title(self):
        return ''.join([
            '<div class="container">',
            '<h2>Scheduled Tasks</h2>'
        ])

    @property
    def schedule_tasks(self):
        tasks = self.scheduler_db.get_tasks()
        current_area = None

        html = ''.join([
            '<div id="schedtasks" class="schedShow">',
            '<table class="schedTable" width=95%>'
        ])
        i = 0
        for task_dict in tasks:
            i += 1
            if task_dict['area'] != current_area:
                if i > 1:
                    html = ''.join([html,
                                    '</div></div></div></td></tr>'
                                    ])
                current_area = task_dict['area']
                if current_area in self.query_data:
                    checked = "checked"
                else:
                    checked = ""
                html = ''.join([
                    html,
                    '<tr><td colspan=3>',
                    '<div>',
                    '<input id="schedcoll', str(i), '" class="toggle" type="checkbox" ', checked, '>',
                    '<label for="schedcoll', str(i),
                    '" class="label-toggle navDrawerCollapseButton navCollapsibleButton navButton schedSection">',
                    current_area, '<span id="', current_area,
                    '_sect" style="max-width: 20%; margin-left: 1em;" class=""></span></label>',
                    '<div class="collapsible-content">',
                    '<div class="collapseContent navDrawerCollapseContent content-inner" style="height: auto;">'
                ])

            if task_dict['lastran'] is None:
                lastran_delta = 'Never'
                dur_delta = ''
            else:
                lastran_delta = datetime.datetime.utcnow() - task_dict['lastran']
                lastran_secs = int(lastran_delta.total_seconds())
                lastran_mins = lastran_secs // 60
                lastran_hrs = lastran_mins // 60
                lastran_days = lastran_hrs // 24
                if lastran_days != 0:
                    lastran_delta = str(lastran_days) + ' days'
                elif lastran_hrs != 0:
                    lastran_delta = str(lastran_hrs) + ' hours'
                elif lastran_mins != 0:
                    lastran_delta = str(lastran_mins) + ' minutes'
                else:
                    lastran_delta = str(lastran_secs) + ' seconds'

                dur_mins = task_dict['duration'] // 60
                dur_hrs = dur_mins // 60
                dur_days = dur_hrs // 24
                if dur_days != 0:
                    dur_delta = str(dur_days) + ' days'
                elif dur_hrs != 0:
                    dur_delta = str(dur_hrs) + ' hours'
                elif dur_mins != 0:
                    dur_delta = str(dur_mins) + ' minutes'
                else:
                    dur_delta = str(task_dict['duration']) + ' seconds'
            html = ''.join([html,
                            '<div style="display: flex;" title="', task_dict['title'], '">',
                            '<div class="schedIcon">',
                            '<a href="#" onclick=\'load_task_url("/api/schedulehtml?task=',
                            task_dict['taskid'], '")\'>',
                            '<i class="md-icon">schedule</i></a></div>',
                            '<div class="schedTask">',
                            '<a href="#" onclick=\'load_task_url("/api/schedulehtml?task=',
                            task_dict['taskid'], '")\'>',
                            '<div class="schedTitle">', task_dict['title'], '</div>',
                            '<div>Plugin: ', task_dict['namespace']
                            ])
            if task_dict['active']:
                html = ''.join([html,
                                ' -- Currently Running</div><div class="progress-line"></div>'
                                ])
                play_name = ''
                play_icon = ''
                delete_icon = ''
                delete_name = ''
            else:
                html = ''.join([html,
                                ' -- Last ran ', lastran_delta, ' ago, taking ',
                                dur_delta, '</div><div class=""></div>'
                                ])
                play_name = '&run=1'
                play_icon = 'play_arrow'
                delete_icon = 'delete_forever'
                delete_name = '&deltask=1'

            html = ''.join([html,
                            '</a></div><div class="schedIcon">',
                            '<a href="#" onclick=\'load_sched_url("/api/schedulehtml?task=',
                            task_dict['taskid'], play_name, '")\'>',
                            '<i class="md-icon">', play_icon, '</i></a>',
                            '<br>',
                            '<a href="#" title="After deleting, restart app to restore tasks to default" ',
                            'onclick=\'load_sched_url("/api/schedulehtml?task=',
                            task_dict['taskid'], delete_name, '")\'>',
                            '<i class="md-icon">', delete_icon, '</i></a>',
                            '</div></div><hr style="margin-top: 0;">'
                            ])
        html = ''.join([html,
                        '</div></div></div></td></tr></table></div>'
                        ])
        return html

    @property
    def task(self):
        return ''.join([
            '<div id="schedtask" class="schedTable schedHide"></div>'
        ])

    def get_task(self, _id):
        task_dict = self.scheduler_db.get_task(_id)
        if task_dict is None:
            self.logger.warning('get_task: Invalid task id: {}'.format(_id))
            return ''

        html = ''.join([
            '<table style="display: contents" width=95%>',
            '<tr>',
            '<td class="schedIcon">',
            '<a href="#" onclick=\'display_tasks()\'>',
            '<div ><i class="md-icon">arrow_back</i></div></a></td>',
            '<td colspan=2 ><div class="schedSection">',
            str(task_dict['title']), '</div></td>',
            '</tr>',
            '<tr>',
            '<td class="schedIcon"></td>',
            '<td colspan=2>', str(task_dict['description']), '</div></td>'
                                                             '</tr>',
            '<td class="schedIcon"></td>',
            '<td colspan=2><b>Namespace:</b> ', str(task_dict['namespace']),
            ' &nbsp; <b>Instance:</b> ', str(task_dict['instance']),
            ' &nbsp; <b>Priority:</b> ', str(task_dict['priority']),
            ' &nbsp; <b>Thread Type:</b> ', str(task_dict['threadtype']),
            '</div></td>',
            '<tr>',
            '<tr><td>&nbsp;</td></tr>',
            '<td colspan=3><div class="schedSection">Task Triggers',
            '<button class="schedIconButton" onclick=\'load_task_url(',
            '"/api/schedulehtml?task=', _id, '&trigger=1");return false;\'>',
            '<i class="schedIcon md-icon" style="padding-left: 1px; text-align: left;">add</i></button>',
            '</div></td>',
            '</tr>',
        ])

        trigger_array = self.scheduler_db.get_triggers(_id)
        for trigger_dict in trigger_array:
            if trigger_dict['timetype'] == 'startup':
                trigger_str = 'At startup'
            elif trigger_dict['timetype'] == 'daily':
                trigger_str = 'Daily at ' + trigger_dict['timeofday']
            elif trigger_dict['timetype'] == 'weekly':
                trigger_str = ''.join([
                    'Every ', trigger_dict['dayofweek'],
                    ' at ', trigger_dict['timeofday']
                ])
            elif trigger_dict['timetype'] == 'interval':
                interval_mins = trigger_dict['interval']
                remainder_hrs = interval_mins % 60
                if remainder_hrs != 0:
                    interval_str = str(interval_mins) + ' minutes'
                else:
                    interval_hrs = interval_mins // 60
                    interval_str = str(interval_hrs) + ' hours'
                trigger_str = 'Every ' + interval_str
                if trigger_dict['randdur'] != -1:
                    trigger_str += ' with random maximum added time of ' + str(trigger_dict['randdur']) + ' minutes'

            else:
                trigger_str = 'UNKNOWN'

            html = ''.join([
                html,
                '<tr>',
                '<td class="schedIcon">',
                '<i class="md-icon">schedule</i></td>',
                '<td class="schedTask">',
                trigger_str,
                '</td>',
                '<td class="schedIcon">',
                '<a href="#" onclick=\'load_task_url("/api/schedulehtml?task=', _id,
                '&trigger=', trigger_dict['uuid'], '&delete=1")\'>',
                '<i class="md-icon">delete_forever</i></a></td>',
                '</tr>'
            ])

        return ''.join([
            html,
            '</table>'
        ])

    def get_trigger(self, _id):
        task_dict = self.scheduler_db.get_task(_id)
        if task_dict is None:
            self.logger.warning('get_trigger: Invalid task id: {}'.format(_id))
            return ''
        if task_dict['namespace'] is None:
            namespace = ""
        else:
            namespace = task_dict['namespace']
        if task_dict['instance'] is None:
            instance = ""
        else:
            instance = task_dict['instance']

        return "".join([
            '<script src="/modules/scheduler/trigger.js"></script>',
            '<form id="triggerform" action="/api/schedulehtml" method="post">',
            '<input type="hidden" name="name" value="', namespace, '" >',
            '<input type="hidden" name="instance" value="', instance, '" >',
            '<input type="hidden" name="area" value="', task_dict['area'], '" >',
            '<table style="display: contents" width=95%>',
            '<tr>',
            '<td style="display: flex;">',
            '<a href="#" onclick=\'load_task_url("/api/schedulehtml?task=', _id, '");\'>',
            '<div ><i class="schedIcon md-icon">arrow_back</i></div></a>',
            '<div class="schedSection">',
            'Add Trigger</div></td>'
            '</tr>',
            '<tr>',
            '<td><b>Task: ', task_dict['title'],
            '<input type="hidden" name="title" value="', task_dict['title'], '" >',
            '</b><br><br></td>'
            '</tr>',
            '<tr><td><label title="Interval will reset each time the task is requested">Trigger Type: &nbsp; </label>',
            '<select id="timetype" name="timetype"</select>',
            '<option value="daily">Daily</option>',
            '<option value="weekly">Weekly</option>',
            '<option value="interval">On an interval</option>',
            '<option value="startup">On Startup</option>',
            '</select><br><br>',
            '<script>',
            '$("#timetype").change(function(){ onChangeTimeType( this ); });',
            '</script>',
            '</td></tr>',
            '<tr><td><div id="divDOW" class="schedHide">Day: &nbsp; ',
            '<select name="dayofweek"</select>',
            '<option value="">Not Set</option>',
            '<option value="Sunday">Sunday</option>',
            '<option value="Monday">Monday</option>',
            '<option value="Tuesday">Tuesday</option>',
            '<option value="Wednesday">Wednesday</option>',
            '<option value="Thursday">Thursday</option>',
            '<option value="Friday">Friday</option>',
            '<option value="Saturday">Saturday</option>',
            '</select>',
            '<br><br>',
            '</div></td></tr>',
            '<tr><td><div id="divTOD" class="schedShow"><label title="Local time">Time: &nbsp; </label>',
            '<select name="timeofdayhr"</select>',
            '<option value="">Not set</option>',
            '<option value="12">12AM</option>',
            '<option value="01">1AM</option>',
            '<option value="02">2AM</option>',
            '<option value="03">3AM</option>',
            '<option value="04">4AM</option>',
            '<option value="05">5AM</option>',
            '<option value="06">6AM</option>',
            '<option value="07">7AM</option>',
            '<option value="08">8AM</option>',
            '<option value="09">9AM</option>',
            '<option value="10">10AM</option>',
            '<option value="11">11AM</option>',
            '<option value="12">12PM</option>',
            '<option value="13">1PM</option>',
            '<option value="14">2PM</option>',
            '<option value="15">3PM</option>',
            '<option value="16">4PM</option>',
            '<option value="17">5PM</option>',
            '<option value="18">6PM</option>',
            '<option value="19">7PM</option>',
            '<option value="20">8PM</option>',
            '<option value="21">9PM</option>',
            '<option value="22">10PM</option>',
            '<option value="23">11PM</option>',
            '</select> : ',
            '<select name="timeofdaymin"</select>',
            '<option value="">Not set</option>',
            '<option value="00">00 min</option>',
            '<option value="05">05 min</option>',
            '<option value="10">10 min</option>',
            '<option value="15">15 min</option>',
            '<option value="20">20 min</option>',
            '<option value="25">25 min</option>',
            '<option value="30">30 min</option>',
            '<option value="35">35 min</option>',
            '<option value="40">40 min</option>',
            '<option value="45">45 min</option>',
            '<option value="50">50 min</option>',
            '<option value="55">55 min</option>',
            '</select>', '<br><br>',
            '</td></tr>',
            '<tr><td><div id="divINTL" class="schedHide">Every: &nbsp; ',
            '<select name="interval"</select>',
            '<option value="">Not Set</option>',
            '<option value="15">15 minutes</option>',
            '<option value="30">30 minutes</option>',
            '<option value="45">45 minutes</option>',
            '<option value="60">1 hour</option>',
            '<option value="90">1.5 hours</option>',
            '<option value="120">2 hours</option>',
            '<option value="150">2.5 hours</option>',
            '<option value="165">2:45</option>',
            '<option value="180">3 hours</option>',
            '<option value="210">3.5 hours</option>',
            '<option value="225">3:45</option>',
            '<option value="240">4 hours</option>',
            '<option value="330">5:30</option>',
            '<option value="360">6 hours</option>',
            '<option value="420">7 hours</option>',
            '<option value="450">7:30</option>',
            '<option value="480">8 hours</option>',
            '<option value="690">11:30</option>',
            '<option value="720">12 hours</option>',
            '<option value="1380">23 hours</option>',
            '<option value="1410">23:30</option>',
            '<option value="1440">24 hours</option>',
            '<option value="2820">47 hours</option>',
            '<option value="2880">2 days</option>',
            '<option value="8640">6 days</option>',
            '<option value="10080">weekly</option>',
            '<option value="20160">2 weeks</option>',
            '</select><br><br>',
            '</td></tr>',
            '<tr><td><div id="divRND" class="schedHide">Max Random Added Time: &nbsp; ',
            '<select name="randdur"</select>',
            '<option value="-1">Not set</option>',
            '<option value="5">5 min</option>',
            '<option value="10">10 min</option>',
            '<option value="15">15 min</option>',
            '<option value="20">20 min</option>',
            '<option value="30">30 min</option>',
            '<option value="60">1 hour</option>',
            '<option value="120">2 hours</option>'
            '<option value="240">4 hours</option>'
            '<option value="480">8 hours</option>'
            '<option value="720">12 hours</option>'
            '<option value="960">16 hours</option>'
            '<option value="1440">24 hours</option>'
            '</select><br><br>',
            '</td></tr>',
            '<tr><td><button type="submit">Add</button>',
            ' &nbsp; <button onclick=\'load_task_url("/api/schedulehtml?task=', _id,
            '"); return false;\' >Cancel</button>',
            '<tr><td>&nbsp;</td></tr>',
            '</table></form>',
            '<section id="status"></section>'
        ])

    def post_add_trigger(self, query_data):
        if query_data['timetype'][0] == 'startup':
            self.queue.put({'cmd': 'add', 'trigger': {
                'area': query_data['area'][0],
                'title': query_data['title'][0],
                'timetype': query_data['timetype'][0]
            }})
            time.sleep(0.05)
            return 'Startup Trigger added'

        elif query_data['timetype'][0] == 'daily':
            if query_data['timeofdayhr'][0] is None or query_data['timeofdaymin'][0] is None:
                return 'Time of Day is not set and is required'
            self.queue.put({'cmd': 'add', 'trigger': {
                'area': query_data['area'][0],
                'title': query_data['title'][0],
                'timetype': query_data['timetype'][0],
                'timeofday': query_data['timeofdayhr'][0] + ':' + query_data['timeofdaymin'][0]
            }})
            time.sleep(0.05)
            return 'Daily Trigger added'

        elif query_data['timetype'][0] == 'weekly':
            if query_data['dayofweek'][0] is None:
                return 'Day of Week is not set and is required'
            if query_data['timeofdayhr'][0] is None or query_data['timeofdaymin'][0] is None:
                return 'Time of Day is not set and is required'
            self.queue.put({'cmd': 'add', 'trigger': {
                'area': query_data['area'][0],
                'title': query_data['title'][0],
                'timetype': query_data['timetype'][0],
                'timeofday': query_data['timeofdayhr'][0] + ':' + query_data['timeofdaymin'][0],
                'dayofweek': query_data['dayofweek'][0]
            }})
            time.sleep(0.05)
            return 'Weekly Trigger added'

        elif query_data['timetype'][0] == 'interval':
            if query_data['interval'][0] is None:
                return 'Interval is not set and is required'
            self.queue.put({'cmd': 'add', 'trigger': {
                'area': query_data['area'][0],
                'title': query_data['title'][0],
                'timetype': query_data['timetype'][0],
                'interval': query_data['interval'][0],
                'randdur': query_data['randdur'][0]
            }})
            time.sleep(0.05)
            return 'Interval Trigger added'
        return 'UNKNOWN'

    def del_trigger(self, _uuid):
        if self.scheduler_db.get_trigger(_uuid) is None:
            return None
        self.queue.put({'cmd': 'del', 'uuid': _uuid})
        time.sleep(0.05)
        return 'Interval Trigger deleted'

    def run_task(self, _taskid):
        self.queue.put({'cmd': 'runtask', 'taskid': _taskid})
        return None

    def del_task(self, _taskid):
        self.queue.put({'cmd': 'deltask', 'taskid': _taskid})
        return None
