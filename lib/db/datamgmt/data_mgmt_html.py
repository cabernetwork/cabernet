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

import datetime
import glob
import logging
import platform
import re
import shutil
import os

from lib.common.decorators import getrequest
from lib.common.decorators import postrequest
import lib.db.datamgmt.backups as backups
from lib.db.db_channels import DBChannels
from lib.db.db_epg import DBepg
from lib.db.db_epg_programs import DBEpgPrograms
from lib.db.db_scheduler import DBScheduler
from lib.db.db_plugins import DBPlugins

BACKUP_FOLDER_NAME = 'CarbernetBackup'


@getrequest.route('/api/datamgmt')
def get_data_mgmt_html(_webserver):
    data_mgmt_html = DataMgmtHTML(_webserver.plugins)
    if 'delete' in _webserver.query_data:
        data_mgmt_html.del_backup(_webserver.query_data['delete'])
        html = data_mgmt_html.get()
    elif 'restore' in _webserver.query_data:
        html = data_mgmt_html.restore_form(_webserver.query_data['restore'])
    else:
        html = data_mgmt_html.get()
    _webserver.do_mime_response(200, 'text/html', html)


@postrequest.route('/api/datamgmt')
def post_data_mgmt_html(_webserver):
    if 'folder' in _webserver.query_data:
        html = restore_from_backup(_webserver.plugins, _webserver.query_data)
    elif 'action' in _webserver.query_data:
        action = _webserver.query_data['action'][0]
        if action == 'reset_channel':
            html = reset_channels(
                _webserver.plugins.config_obj.data,
                _webserver.query_data['name'][0], _webserver.query_data['resetedits'][0])
        elif action == 'reset_epg':
            html = reset_epg(
                _webserver.plugins.config_obj.data,
                _webserver.query_data['name'][0])
        elif action == 'reset_scheduler':
            html = reset_sched(
                _webserver.plugins.config_obj.data,
                _webserver.query_data['name'][0],
                _webserver.sched_queue)
        elif action == 'del_instance':
            html = del_instance(
                _webserver.plugins.config_obj.data,
                _webserver.query_data['name'][0])
        else:
            # database action request
            html = 'UNKNOWN action request: {}'.format(_webserver.query_data['action'][0])
    else:
        html = 'UNKNOWN REQUEST'
    _webserver.do_mime_response(200, 'text/html', html)


def reset_channels(_config, _name, _reset_edits):
    db_channel = DBChannels(_config)
    db_channel.del_status(_name)
    if _reset_edits == '1':
        db_channel.del_channels(_name, None)
    if _name is None:
        return 'Channels updated and will refresh all data on next request'
    else:
        return 'Channels for plugin {} updated and will refresh all data on next request' \
            .format(_name)


def reset_epg(_config, _name):
    db_epg = DBepg(_config)
    db_epg.del_instance(_name, None)
    db_epg.set_last_update(_name)
    # db_epg_programs = DBEpgPrograms(_config)
    # db_epg_programs.del_namespace(_name)

    if _name is None:
        return 'EPG updated and will refresh all days on next request'
    else:
        return 'EPG for plugin {} updated and will refresh all days on next request' \
            .format(_name)


def reset_sched(_config, _name, _sched_queue):
    db_scheduler = DBScheduler(_config)
    tasks = db_scheduler.get_tasks_by_name(_name)
    html = ''
    for task in tasks:
        _sched_queue.put({'cmd': 'deltask', 'taskid': task['taskid']})
        #db_scheduler.del_task(task['area'], task['title'])
        html = ''.join([html,
                        '<b>', task['area'], ':', task['title'],
                        '</b> deleted from Scheduler<br>'
                        ])
    return ''.join([html,
                    'Restart the app to re-populate the scheduler with defaults'])


def del_instance(_config, _name):
    if _name is None:
        return 'Instance set to None. No instances deleted'
    if ':' not in _name:
        return 'Invalid action. Request ignored'
    name_inst = _name.split(':', 1)

    html = ''
    db_plugins = DBPlugins(_config)
    num_del = db_plugins.del_instance(name_inst[0], name_inst[1])
    if num_del > 0:
        html = ''.join([html,
                        '<b>', _name, '</b> deleted from Plugins<br>'
                        ])

    db_channels = DBChannels(_config)
    db_channels.del_status(name_inst[0], name_inst[1])
    num_del = db_channels.del_channels(name_inst[0], name_inst[1])
    if num_del > 0:
        html = ''.join([html,
                        '<b>', _name, '</b> deleted from Channels<br>'
                        ])

    db_epg = DBepg(_config)
    db_epg.del_instance(name_inst[0], name_inst[1])
    if num_del > 0:
        html = ''.join([html,
                        '<b>', _name, '</b> deleted from EPG<br>'
                        ])

    db_programs = DBEpgPrograms(_config)
    db_programs.del_namespace(name_inst[0])
    if num_del > 0:
        html = ''.join([html,
                        '<b>', name_inst[0], '</b> deleted from EPG Programs<br>'
                        ])

    db_sched = DBScheduler(_config)
    task_list = db_sched.get_tasks_by_name(name_inst[0], name_inst[1])
    for task in task_list:
        db_sched.del_task(task['area'], task['title'])
    if len(task_list) > 0:
        html = ''.join([html,
                        '<b>', _name, '</b> deleted from Scheduler<br>'
                        ])
    return ''.join([html,
                    'Restart the app to re-populate the scheduler with defaults'])


def restore_from_backup(_plugins, _query_data):
    b = backups.Backups(_plugins)
    bkup_defn = b.backup_list()
    folder = _query_data['folder'][0]
    del _query_data['name']
    del _query_data['instance']
    del _query_data['folder']
    html = ''
    for restore_key, status in _query_data.items():
        if status[0] == '1':
            msg = b.restore_data(folder, restore_key)
            if msg is None:
                html = ''.join([html, bkup_defn[restore_key]['label'], ' Restored<br>'])
            else:
                html = ''.join([html, msg, '<br>'])
    return html


class DataMgmtHTML:

    def __init__(self, _plugins):
        self.logger = logging.getLogger(__name__)
        self.config = _plugins.config_obj.data
        self.bkups = backups.Backups(_plugins)

    def get(self):
        return ''.join([self.header, self.body])

    @property
    def header(self):
        return ''.join([
            '<!DOCTYPE html><html><head>',
            '<meta charset="utf-8"/><meta name="author" content="rocky4546">',
            '<meta name="description" content="data management for Cabernet">',
            '<title>Data Management</title>',
            '<meta name="viewport" content="width=device-width, ',
            'minimum-scale=1.0, maximum-scale=1.0">',
            '<script src="https://code.jquery.com/jquery-3.5.1.min.js"></script>',
            '<link rel="stylesheet" type="text/css" href="/modules/datamgmt/datamgmt.css">',
            '<script src="/modules/datamgmt/datamgmt.js"></script>'
        ])

    @property
    def title(self):
        return ''.join([
            '<body><div class="container">',
            '<h2>Data Management</h2>'
        ])

    @property
    def body(self):
        return ''.join(['<body>', self.title, self.db_updates, self.backups,
                        '</body>'
                        ])

    @property
    def db_updates(self):
        html = ''.join([
            '<section id="reset_status"></section>',
            '<form action="/api/datamgmt" method="post">',
            '<table class="dmTable" width=95%>',
            '<tr>',
            '<td class="dmIcon">',
            '<i class="md-icon">inventory_2</i></td>',
            '<td class="dmItem" >',
            '<div class="dmItemTitle">Reset Channel Data &nbsp; ',
            '<input type="hidden" name="action" value="reset_channel">',
            '<button class="button" type="submit">Reset</button></div>',
            '<div>Next channel request will force pull new data</div></td>',
        ])
        html_select = self.select_reset_channel
        html = ''.join([html, html_select,
                        '<tr><td colspan=3><hr></td></tr></table></form>',
                        '<form action="/api/datamgmt" method="post">',
                        '<table class="dmTable" width=95%>',
                        '<tr>',
                        '<td class="dmIcon">',
                        '<i class="md-icon">inventory_2</i></td>',
                        '<td class="dmItem">',
                        '<div class="dmItemTitle">Reset EPG Data &nbsp; ',
                        '<input type="hidden" name="action" value="reset_epg">',
                        '<button class="button" type="submit">Reset</button></div>',
                        '<div>Next epg request will pull all days</div></td>',
                        ])
        html_select = self.select_reset_epg
        html = ''.join([html, html_select,
                        '<tr><td colspan=3><hr></td></tr></table></form>',
                        '<form action="/api/datamgmt" method="post">',
                        '<table class="dmTable" width=95%>',
                        '<tr>',
                        '<td class="dmIcon">',
                        '<i class="md-icon">inventory_2</i></td>',
                        '<td class="dmItem">',
                        '<div class="dmItemTitle">Reset Scheduler Tasks &nbsp; ',
                        '<input type="hidden" name="action" value="reset_scheduler">',
                        '<button class="button" type="submit">Reset</button></div>',
                        '<div>Scheduler will reload default tasks on next app restart</div></td>',
                        ])
        html_select = self.select_reset_sched
        html = ''.join([html, html_select,
                        '<tr><td colspan=3><hr></td></tr></table></form>',
                        '<form action="/api/datamgmt" method="post">',
                        '<table class="dmTable" width=95%>',
                        '<tr>',
                        '<td class="dmIcon">',
                        '<i class="md-icon">inventory_2</i></td>',
                        '<td class="dmItem">',
                        '<div class="dmItemTitle">Delete Instance &nbsp; ',
                        '<input type="hidden" name="action" value="del_instance">',
                        '<button class="button" type="submit">Delete</button></div>',
                        '<div>Deletes the instance data from the database file.  Update config.ini, ',
                        'as needed, and restart app following a delete</div></td>',
                        ])
        html_select = self.select_del_instance
        html = ''.join([html, html_select,
                        '</select></td></tr>'
                        '<tr><td colspan=3><hr></td></tr>',
                        '</table></form><br>',
                        ])
        return html

    @property
    def backups(self):
        html = ''.join([
            '<div id="dmbackup">',
            '<table class="dmTable" width=95%>',
            '<tr>',
            '<td colspan=3><div class="dmSection">',
            'Current Backups</div></td>'
            '</tr>',
        ])
        backups_location = self.config['datamgmt']['backups-location']
        folderlist = sorted(glob.glob(os.path.join(
            backups_location, BACKUP_FOLDER_NAME + '*')), reverse=True)
        for folder in folderlist:
            filename = os.path.basename(folder)
            datetime_str = self.get_backup_date(filename)
            if datetime_str is None:
                continue
            html = ''.join([html,
                            '<tr>',
                            '<td class="dmIcon">',
                            '<a href="#" onclick=\'load_backup_url("/api/datamgmt?restore=',
                            filename, '")\'>',
                            '<i class="md-icon">folder</i></a></td>',
                            '<td class="dmItem">',
                            '<a href="#" onclick=\'load_backup_url("/api/datamgmt?restore=',
                            filename, '")\'>',
                            '<div class="dmItemTitle">', datetime_str, '</div>',
                            '<div>', folder, '</div></td>',
                            '<td class="dmIcon">',
                            '<a href="#" onclick=\'load_dm_url("/api/datamgmt?delete=',
                            filename, '")\'>',
                            '<i class="md-icon">delete_forever</i></a></td>',
                            '</tr>'
                            ])
        html = ''.join([html,
                        '</table>',
                        '</div>'
                        ])
        return html

    def del_backup(self, _folder):
        valid_regex = re.compile('^([a-zA-Z0-9_]+$)')
        if not valid_regex.match(_folder):
            self.logger.info('Invalid backup folder to delete: {}'.format(_folder))
            return
        backups_location = self.config['datamgmt']['backups-location']
        f_to_delete = os.path.join(backups_location, _folder)
        if os.path.isdir(f_to_delete):
            self.logger.info('Deleting backup folder {}'.format(_folder))
            shutil.rmtree(f_to_delete)
        else:
            self.logger.info('Backup folder not found to delete: {}'.format(_folder))

    def restore_form(self, _folder):
        datetime_str = self.get_backup_date(_folder)
        if datetime_str is None:
            return 'ERROR - UNKNOWN BACKUP FOLDER'

        html = ''.join([
            '<script src="/modules/datamgmt/restore_backup.js"></script>'
            '<form action="/api/datamgmt" method="post">',
            '<table class="dmTable" width=95%>',
            '<tr>',
            '<td class="dmIcon">',
            '<a href="#" onclick=\'load_dm_url("/api/datamgmt")\'>',
            '<div ><i class="md-icon">arrow_back</i></div></a></td>',
            '<td colspan=2 class="dmSection"><div >',
            'Backup from: ', datetime_str, '</div></td>'
                                           '</tr>',
            '<tr>',
            '<td></td>',
            '<td colspan=2><div>',
            'Select the items to restore</div></td>'
            '</tr>',
            '<tr><td colspan=3><section id="status"></section></td></tr>',
            '<tr><td colspan=3>',
            '<button class="button dmButton" id="submit" STYLE="color: var(--theme-text-color); background-color: var(--button-background); margin-top:1em" ',
            'type="submit"><b>Restore Now</b></button>',
            '</td></tr>'
        ])
        bkup_defn = self.bkups.backup_list()
        for key in bkup_defn.keys():
            html = ''.join([html,
                            '<tr>',
                            '<td class="dmIcon">',
                            '<input value="1" type="checkbox" name="', key, '" checked="checked">',
                            '<input name="', key, '" value="0" type="hidden">',
                            '</td>',
                            '<td colspan=2>',
                            bkup_defn[key]['label'],
                            '</td>',
                            '</tr>'
                            ])
        html = ''.join([html,
                        '</table>',
                        '<input type="hidden" name="folder" value="', _folder, '">',
                        '</form>'
                        ])
        return html

    def get_backup_date(self, _filename):
        try:
            datetime_obj = datetime.datetime.strptime(_filename,
                                                      BACKUP_FOLDER_NAME + '_%Y%m%d_%H%M')
        except ValueError as e:
            self.logger.info('Bad backup folder name {}: {}'.format(_filename, e))
            return None
        opersystem = platform.system()
        if opersystem in ['Windows']:
            return datetime_obj.strftime('%m/%d/%Y, %#I:%M %p')
        else:
            return datetime_obj.strftime('%m/%d/%Y, %-I:%M %p')

    @property
    def select_reset_channel(self):
        db_channel = DBChannels(self.config)
        plugins_channel = db_channel.get_channel_names()
        html_option = ''.join([
            '<td nowrap>Reset Edits: <select id="resetedits" name="resetedits"</select>',
            '<option value="0">No</option><option value="1">Yes</option></select> &nbsp; ',
            'Plugin: <select id="name" name="name"</select>',
            '<option value="">ALL</option>'
        ])
        for name in plugins_channel:
            html_option = ''.join([html_option,
                                   '<option value="', name['namespace'], '">', name['namespace'], '</option>',
                                   ])
        return ''.join([html_option, '</select></td></tr>'])

    @property
    def select_reset_epg(self):
        db_epg = DBepg(self.config)
        db_epg_programs = DBEpgPrograms(self.config)

        plugin_epg = db_epg.get_epg_names()
        plugin_programs = db_epg_programs.get_program_names()
        plugin_epg_names = [s['namespace'] for s in plugin_epg]
        plugin_programs_names = [s['namespace'] for s in plugin_programs]
        plugin_list = list(set(plugin_epg_names + plugin_programs_names))

        html_option = ''.join([
            '<td nowrap>Plugin: <select id="name" name="name"</select>',
            '<option value="">ALL</option>',
        ])
        for name in plugin_list:
            html_option = ''.join([html_option,
                                   '<option value="', name, '">', name, '</option>',
                                   ])
        return ''.join([html_option, '</select></td></tr>'])

    @property
    def select_reset_sched(self):
        db_sched = DBScheduler(self.config)
        plugins_sched = db_sched.get_task_names()
        html_option = ''.join([
            '<td nowrap>Plugin: <select id="name" name="name"</select>',
            '<option value="">ALL</option>',
        ])
        for name in plugins_sched:
            html_option = ''.join([html_option,
                                   '<option value="', name['namespace'], '">', name['namespace'], '</option>',
                                   ])
        return ''.join([html_option, '</select></td></tr>'])

    @property
    def select_del_instance(self):
        name_inst = []
        db_plugins = DBPlugins(self.config)
        name_inst_dict = db_plugins.get_instances()
        for ns, inst_list in name_inst_dict.items():
            for inst in inst_list:
                name_inst.append(''.join([
                    ns, ':', inst]))
        db_channels = DBChannels(self.config)
        name_inst_list = db_channels.get_channel_instances()
        self.update_ns_inst(name_inst, name_inst_list)
        db_epg = DBepg(self.config)
        name_inst_list = db_epg.get_epg_instances()
        self.update_ns_inst(name_inst, name_inst_list)
        db_sched = DBScheduler(self.config)
        name_inst_list = db_sched.get_task_instances()
        self.update_ns_inst(name_inst, name_inst_list)

        html_option = ''.join([
            '<td nowrap>Instance: <select id="name" name="name"</select>',
            '<option value="">None</option>',
        ])
        for name in name_inst:
            html_option = ''.join([html_option,
                                   '<option value="', name, '">', name, '</option>',
                                   ])
        return ''.join([html_option, '</select></td></tr>'])

    def update_ns_inst(self, _name_inst, _name_inst_list):
        for name_inst_dict in _name_inst_list:
            if name_inst_dict['instance'] is not None:
                ns_in = ''.join([
                    name_inst_dict['namespace'],
                    ':',
                    name_inst_dict['instance'],
                ])
                if ns_in not in _name_inst:
                    _name_inst.append(ns_in)
