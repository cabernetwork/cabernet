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

import pathlib
import os

from lib.common.decorators import getrequest
from lib.web.pages.templates import web_templates
from lib.db.db_plugins import DBPlugins


@getrequest.route('/api/manifest')
def get_manifest_data(_webserver):
    if 'plugin' not in _webserver.query_data:
        pass
    elif 'key' not in _webserver.query_data:
        pass
    elif 'repo' not in _webserver.query_data:
        return send_file(_webserver)
    else:
        return send_file(_webserver)

    _webserver.do_mime_response(404, 'text/html', web_templates['htmlError'].format('404 - Manifest Not Found'))
    return False


def send_file(_webserver):
    repo = _webserver.query_data.get('repo')
    plugin = _webserver.query_data['plugin']
    key = _webserver.query_data['key']
    
    plugin_db = DBPlugins(_webserver.config)
    plugin_defn = plugin_db.get_plugins_by_name(None, repo, plugin)
    if not plugin_defn:
        _webserver.do_mime_response(
                404, 'text/html', web_templates['htmlError']
                .format('404 - Plugin Not Found'))
        return

    if len(plugin_defn) != 1:
        print('TOO MANY PLUGINS')
        _webserver.do_mime_response(
                404, 'text/html', web_templates['htmlError']
                .format('404 - DUPLICATE PLUGINS'))
        return
    plugin_defn = plugin_defn[0]
    if not plugin_defn['version']['installed']:
        thumbnail_path = _webserver.config['paths']['thumbnails_dir']
        plugin_id = plugin_defn['id']
        image_path = plugin_defn[key]
        full_cache = pathlib.Path(
            thumbnail_path, plugin_id, image_path)

        _webserver.do_file_response(200, None, full_cache)
        return
    else:
        try:
            base = os.path.dirname(_webserver.plugins.plugins[plugin].plugin_settings[key]).replace('/', '.')
            image_filename = os.path.basename(_webserver.plugins.plugins[plugin].plugin_settings[key])
            path_to_image = _webserver.plugins.plugins[plugin].plugin_path + '.' + base
            _webserver.do_file_response(200, path_to_image, image_filename)
        except KeyError:
            _webserver.do_mime_response(
                    404, 'text/html', web_templates['htmlError']
                    .format('404 - Not Found'))
    

