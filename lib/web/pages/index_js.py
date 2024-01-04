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

import lib.common.utils as utils
from lib.common.decorators import getrequest
from lib.db.db_plugins import DBPlugins


@getrequest.route('/api/index.js')
def pages_index_js(_webserver):
    indexjs = IndexJS(_webserver.config)
    _webserver.do_mime_response(200, 'text/javascript', indexjs.get())
    return True


class IndexJS:

    def __init__(self, _config):
        self.config = _config
        self.plugin_db = DBPlugins(_config)

    def check_upgrade_status(self):
        plugin_defns = self.plugin_db.get_plugins(
            True, None, None)
        if plugin_defns:
            for plugin_defn in plugin_defns:
                latest_version = plugin_defn['version']['latest']
                upgrade_available = ''
                if plugin_defn['external'] and latest_version != plugin_defn['version']['current']:
                    return '$(\"#pluginStatus\").text("Upgrade");'
        return ''

    def get(self):
        js = ''.join([
            'var upgrading = "running"; ',
            'var lookup_title = new Map(); ',
            'lookup_title.set("/html/links.html", "Cabernet Links"); ',
            'lookup_title.set("/api/configform?area=general", "Cabernet Settings:Internal"); ',
            'lookup_title.set("/api/configform?area=streams", "Cabernet Settings:Streams"); ',
            'lookup_title.set("/api/configform?area=epg", "Cabernet Settings:EPG"); ',
            'lookup_title.set("/api/configform?area=clients", "Cabernet Settings:Clients"); ',
            'lookup_title.set("/api/configform?area=logging", "Cabernet Settings:Logging"); ',
            'lookup_title.set("/api/channels", "Cabernet Channel Editor"); ',
            'lookup_title.set("/api/schedulehtml", "Cabernet Scheduler"); ',
            'lookup_title.set("/api/datamgmt", "Cabernet Data Management"); ',
            'lookup_title.set("/api/plugins", "Cabernet Plugins"); ',
            'function load_url(url, title) {',
            '$(\"#content\").load(url);',
            'document.title = title;',
            'newurl = window.location.pathname+"?content="+encodeURIComponent(url);',
            'window.history.pushState({}, null, newurl);',
            '}',

            'function load_status_url(url) {',
            'if ( upgrading == "running" ) { ',
            '$(\"#status\").load(url, function( resp, s, xhr ) {',
            'if ( s == \"error\" ) {',
            '$(\"#status\").text( xhr.status + \" \" + xhr.statusText ); ',
            '} else {setTimeout(function(){',
            'load_status_url(url);}, 700);',
            '}});} else if ( upgrading == "success" ) {$(\"#status\").append(\"Upgrade complete, reload page\");',
            ' upgrading = "running";',
            '} else {$(\"#status\").append(\"Upgrade aborted\"); upgrading = "running";}};',

            '$(document).ready(setTimeout(function(){',
            '$(\'head\').append(\'<link rel="stylesheet"',
            ' href="/modules/themes/',
            self.config['display']['theme'],
            '/theme.css"',
            ' type="text/css" />',
            '<script type="text/javascript"',
            ' src="/modules/themes/',
            self.config['display']['theme'],
            '/theme.js"></script>',
            '\');',

            'if ( !window.location.search ) {',
            '$(\'#content\').html(\'<!DOCTYPE html><html><head>'
            '<title>Dashboard</title>',
            '<meta name="viewport" content="width=device-width, ',
            'minimum-scale=1.0, maximum-scale=1.0"/>',
            '<link rel=\"stylesheet\" type="text/css" href=\"/modules/dashboard/dashboard.css\">',
            '<link rel=\"stylesheet\" type=\"text/css\" href=\"/modules/table/table.css\">',
            '<script src=\"/modules/dashboard/dashboard.js\"></script>',
            '</head>\');',

            '$(\'#content\').append(\'<div id=\"logo\"></div>',
            self.get_version_div(),
            '<div id=\"dashboard\"></div>',
            '\');',
            '} else {',
            'const urlSearchParams = new URLSearchParams(window.location.search);',
            'const params = Object.fromEntries(urlSearchParams.entries());',
            'if (params.content) {'
            'load_url.call(this, params.content, ',
            'lookup_title.get(params.content));', 
            '}',
            '}',
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
            self.check_upgrade_status(),
            '}, 1000));'
        ])
        return js

    def get_version_div(self):
        manifest_list = self.plugin_db.get_repos(utils.CABERNET_ID)
        if not manifest_list:
            current_version = utils.VERSION
            upgrade_js = ''
        else:
            current_version = manifest_list[0]['version']['current']
            
            next_version = manifest_list[0]['version'].get('next')
            if not next_version:
                current_version = 'TBD'
                next_version = 'TBD'
            latest_version = manifest_list[0]['version'].get('latest')
            if not latest_version:
                current_version = 'TBD'
                latest_version = 'TBD'
            if current_version == next_version:
                upgrade_js = ''
            else:
                upgrade_js = ''.join([
                    'A new version of Cabernet is available!<br>',
                    'Latest Version ', latest_version, ' &nbsp; ',
                    '<a style=\"border: 1px; border-radius: 0.5em;',
                    ' padding-bottom: 5px; padding-top: 5px; text-decoration: none;',
                    ' color: inherit; background: var(--theme-button-hover-color);\" ',
                    ' href=\"#\" onClick=\"load_status_url(\\\'/api/upgrade?id=cabernet\\\'',
                    ');\" title=\"Upgrade Cabernet\">',
                    '<i style=\"font-size: 150%;\" class=\"md-icon\">upgrade</i>',
                    '<b>Upgrade to ', next_version, '</b> &nbsp; </a> '
                ])

        version_js = ''.join([
            '<div style=\"padding: 1em; background: var(--docked-drawer-background);',
            ' margin-left: auto;margin-right: auto;width: max-content;\">',
            'Version: ', current_version, '<br>',
            upgrade_js,
            '</div>'
        ])
        return version_js
