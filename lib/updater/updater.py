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

import importlib
import importlib.resources
import json
import logging
import re
import time
from threading import Thread

import lib.common.utils as utils
from lib.db.db_scheduler import DBScheduler
from lib.db.db_plugins import DBPlugins
from lib.common.decorators import getrequest
from lib.web.pages.templates import web_templates
from lib.updater.cabernet import CabernetUpgrade
from lib.updater.plugins import PluginsUpgrade
from lib.common.string_obj import StringObj
from lib.common.tmp_mgmt import TMPMgmt
from lib.updater import cabernet
from lib.plugins.repo_handler import RepoHandler

STATUS = StringObj()
IS_UPGRADING = False


@getrequest.route('/api/upgrade')
def upgrade(_webserver):
    global STATUS
    global IS_UPGRADING
    v = Updater(_webserver.plugins)
    try:
        if 'id' in _webserver.query_data:
            if _webserver.query_data['id'] != utils.CABERNET_ID:
                _webserver.do_mime_response(501, 'text/html',
                                            web_templates['htmlError'].format('501 - Invalid ID'))
                return
            if not IS_UPGRADING:
                IS_UPGRADING = True
                v.sched_queue = _webserver.sched_queue
                STATUS.data = ''
                t = Thread(target=v.upgrade_app, args=(_webserver.query_data['id'],))
                t.start()
            _webserver.do_mime_response(200, 'text/html', ''.join([STATUS.data]))
            return
        else:
            _webserver.do_mime_response(501, 'text/html',
                                        web_templates['htmlError'].format('404 - Unknown action'))
    except KeyError:
        _webserver.do_mime_response(501, 'text/html',
                                    web_templates['htmlError'].format('501 - Badly formed request'))


def check_for_updates(plugins):
    v = Updater(plugins)
    v.update_version_info()
    return True


class Updater:

    def __init__(self, _plugins):
        self.logger = logging.getLogger(__name__)
        self.version_re = re.compile(r'(\d+\.\d+)\.\d+')
        self.plugins = _plugins
        self.config_obj = _plugins.config_obj
        self.config = _plugins.config_obj.data
        self.plugin_db = DBPlugins(self.config)
        self.sched_queue = None
        self.tmp_mgmt = TMPMgmt(self.config)

    def scheduler_tasks(self):
        scheduler_db = DBScheduler(self.config)
        if scheduler_db.save_task(
                'Applications',
                'Check for Updates',
                'internal',
                None,
                'lib.updater.updater.check_for_updates',
                99,
                'inline',
                'Checks cabernet and all plugins for updated versions'
        ):
            scheduler_db.save_trigger(
                'Applications',
                'Check for Updates',
                'interval',
                interval=2850,
                randdur=60
            )
            scheduler_db.save_trigger(
                'Applications',
                'Check for Updates',
                'startup')

    def update_version_info(self):
        self.logger.info('Updating Repo Cabernet-Repository versions')
        self.repos = RepoHandler(self.config_obj)
        self.repos.load_cabernet_repo()
        self.logger.info('Updating Cabernet versions')
        c = CabernetUpgrade(self.plugins)
        c.update_version_info()

    def import_manifest(self):
        """
        Loads the manifest for cabernet from a file
        """
        json_settings = importlib.resources.read_text(self.config['paths']['resources_pkg'], utils.CABERNET_REPO)
        settings = json.loads(json_settings)
        return settings

    def load_manifest(self, _manifest):
        """
        Loads the cabernet manifest from DB
        """
        return self.plugin_db.get_plugins(_installed=True, _namespace=_manifest)[0]

    def save_manifest(self, _manifest):
        """
        Saves to DB the manifest for cabernet
        """
        self.plugin_db.save_plugin(_manifest)

    def upgrade_app(self, _id):
        """
        Initial request to perform an upgrade
        """
        global STATUS
        global IS_UPGRADING

        STATUS.data = 'Starting upgrade...<br>\r\n'

        # upgrade the main cabernet app
        app = CabernetUpgrade(self.plugins)
        if not app.upgrade_app(STATUS):
            STATUS.data += '<script type="text/javascript">upgrading = "failed"</script>'
            time.sleep(1)
            IS_UPGRADING = False
            return

        # upgrade the installed external plugins
        p = PluginsUpgrade(self.plugins)
        if not p.upgrade_plugins(STATUS):
            STATUS.data += '<script type="text/javascript">upgrading = "failed"</script>'
            time.sleep(1)
            IS_UPGRADING = False
            return

        STATUS.data += 'Entering Maintenance Mode...<br>\r\n'
        # make sure the config_handler really has the config data uploaded
        self.config_obj.config_handler.read(self.config_obj.data['paths']['config_file'])
        self.config_obj.write('main', 'maintenance_mode', True)

        STATUS.data += 'Restarting app in 3...<br>\r\n'
        self.tmp_mgmt.cleanup_tmp()
        time.sleep(0.8)
        STATUS.data += '2...<br>\r\n'
        time.sleep(0.8)
        STATUS.data += '1...<br>\r\n'
        STATUS.data += '<script type="text/javascript">upgrading = "success"</script>'
        time.sleep(1)
        self.restart_app()
        IS_UPGRADING = False

    def restart_app(self):
        # get schedDB and find restart taskid.
        scheduler_db = DBScheduler(self.config)
        task = scheduler_db.get_tasks('Applications', 'Restart')[0]
        self.sched_queue.put({'cmd': 'runtask', 'taskid': task['taskid']})
