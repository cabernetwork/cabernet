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
import urllib

import lib.common.utils as utils
from lib.common.decorators import getrequest
from lib.db.db_plugins import DBPlugins
from lib.db.db_scheduler import DBScheduler


@getrequest.route('/api/index.js')
def pages_index_js(_webserver):
    indexjs = IndexJS()
    _webserver.do_mime_response(200, 'text/javascript', indexjs.get(_webserver.config))
    return True


class IndexJS:

    @staticmethod
    def get(_config):
        js = ''.join([
            'var upgrading = "running"; ',
            '$(document).ready(setTimeout(function(){',
                '$(\'head\').append(\'<link rel="stylesheet"',
                    ' href="/modules/themes/',
                    _config['display']['theme'],
                    '/theme.css"',
                    ' type="text/css" />',
                    '<script type="text/javascript"',
                    ' src="/modules/themes/',
                    _config['display']['theme'],
                    '/theme.js"></script>',
                    '\');',
                    
                '$(\'#content\').html(\'<!DOCTYPE html><html><head>'
                '<title>Dashboard</title>',
                '<meta name="viewport" content="width=device-width, ',
                'minimum-scale=1.0, maximum-scale=1.0"/>',
                '<link rel=\"stylesheet\" type="text/css" href=\"/modules/dashboard/dashboard.css\">',
                '<link rel=\"stylesheet\" type=\"text/css\" href=\"/modules/table/table.css\">',
                '<script src=\"/modules/dashboard/dashboard.js\"></script>',
                '</head>\');',
                    
                '$(\'#content\').append(\'<div id=\"logo\"></div>',
                    IndexJS.get_version_div(_config),
                    '<div id=\"dashboard\"></div>',
                    '\');',
                'logo = getComputedStyle(document.documentElement)',
                    '.getPropertyValue("--logo-url");',
                'if ( logo == \"\" ) { ',
                    'setTimeout(function() {',
                        'logo = getComputedStyle(document.documentElement)',
                            '.getPropertyValue("--logo-url");',
                        '$(\'#logo\').html(\'<img class=\"splash\" src=\"\'+logo+\'\">',
                        '\');',
                        '}, 2000);'
                '} else {'
                    '$(\'#logo\').html(\'<img class=\"splash\" src=\"\'+logo+\'\">',
                    '\');',
                '}',
                '}, 1000));',
            'function load_url(url) {',
                '$(\"#content\").load(url);}',
            'function load_status_url(url) {',
                'if ( upgrading == "running" ) { ',
                '$(\"#status\").load(url, function( resp, s, xhr ) {',
                'if ( s == \"error\" ) {',
                '$(\"#status\").text( xhr.status + \" \" + xhr.statusText ); ',
                '} else {setTimeout(function(){',
                'load_status_url(url);}, 700);',
                '}});} else if ( upgrading == "success" ) {$(\"#status\").append(\"Upgrade complete, reload page\");',
                ' upgrading = "running";',
                '} else {$(\"#status\").append(\"Upgrade aborted\"); upgrading = "running";}};'
        ])
        return js


    @staticmethod
    def get_version_div(_config):
        plugin_db = DBPlugins(_config)
        manifest_list = plugin_db.get_plugins(utils.CABERNET_NAMESPACE)
        if manifest_list is None:
            current_version = utils.VERSION
            next_version = None
            latest_version = None
            upgrade_js = ''
        else:
            current_version = manifest_list[0]['version']
            next_version = manifest_list[0]['next_version']
            latest_version = manifest_list[0]['latest_version']
            if current_version == next_version:
                upgrade_js = ''
            else:
                upgrade_js = ''.join([
                    'A new version of Cabernet is available!<br>',
                    'Latest Version ', latest_version, ' &nbsp; ',
                    '<a style=\"border: 1px; border-radius: 0.5em; padding-bottom: 5px; padding-top: 5px; text-decoration: none; color: inherit; background: var(--theme-button-hover-color);\" ',
                    ' href=\"#\" onClick=\"load_status_url(\\\'/api/upgrade?id=Cabernet\\\'',
                    ');\" title=\"Upgrade Cabernet\">',
                    '<i style=\"font-size: 150%;\" class=\"md-icon\">upgrade</i>',
                    '<b>Upgrade to ', next_version, '</b> &nbsp; </a> '
                ])

        version_js = ''.join([
                '<div style=\"padding: 1em; background: var(--docked-drawer-background); margin-left: auto;margin-right: auto;width: max-content;\">',
                'Version: ', current_version, '<br>',
                upgrade_js,
                '</div>'
        ])
        return version_js
