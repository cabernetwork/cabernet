"""
MIT License

Copyright (C) 2021 ROCKY4546
https://github.com/rocky4546

This file is part of Cabernet

Permission is hereby granted, free of charge, to any person obtaining a copy of this software
and associated documentation files (the “Software”), to deal in the Software without restriction,
including without limitation the rights to use, copy, modify, merge, publish, distribute,
sublicense, and/or sell copies of the Software, and to permit persons to whom the Software
is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or
substantial portions of the Software.
"""

from .templates import hdhr_templates
from lib.common.decorators import getrequest
from lib.common.decorators import postrequest
import lib.common.utils as utils

from lib.web.pages.templates import web_templates


@getrequest.route('/discover.json')
def discover_json(_webserver):
    ns_inst_path = _webserver.get_ns_inst_path(_webserver.query_data)
    if _webserver.query_data['name'] is None:
        name = ''
    else:
        name = _webserver.query_data['name']+' '
        
    namespace = None
    for area, area_data in _webserver.config.items():
        if 'player-tuner_count' in area_data.keys():
            namespace = area

    _webserver.do_mime_response(200,
        'application/json',
        hdhr_templates['jsonDiscover'].format(
            name+_webserver.config['hdhomerun']['reporting_friendly_name'],
            _webserver.config['hdhomerun']['reporting_model'],
            _webserver.config['hdhomerun']['reporting_firmware_name'],
            _webserver.config['main']['version'],
            _webserver.config['hdhomerun']['hdhr_id'],
            _webserver.config[namespace]['player-tuner_count'],
            _webserver.web_admin_url, ns_inst_path))


@getrequest.route('/device.xml')
def device_xml(_webserver):
    if _webserver.query_data['name'] is None:
        name = ''
    else:
        name = _webserver.query_data['name']+' '
    _webserver.do_mime_response(200,
        'application/xml',
        hdhr_templates['xmlDevice'].format(
            name+_webserver.config['hdhomerun']['reporting_friendly_name'],
            _webserver.config['hdhomerun']['reporting_model'],
            _webserver.config['hdhomerun']['hdhr_id'],
            _webserver.config['main']['uuid'],
            utils.CABERNET_URL
        ))


@getrequest.route('/lineup_status.json')
def lineup_status_json(_webserver):
    # Assumes only one scan can be active at a time.
    if _webserver.scan_state < 0:
        return_json = hdhr_templates['jsonLineupStatusIdle'] \
            .replace("Antenna", _webserver.config['hdhomerun']['tuner_type'])
    else:
        _webserver.scan_state += 20
        if _webserver.scan_state > 100:
            _webserver.scan_state = 100
        num_of_channels = len(_webserver.channels_db.get_channels(_webserver.query_data['name'], None))
        return_json = hdhr_templates['jsonLineupStatusScanning'].format(
            _webserver.scan_state,
            int(num_of_channels * _webserver.scan_state / 100))

        if _webserver.scan_state == 100:
            _webserver.scan_state = -1
            _webserver.update_scan_status(_webserver.query_data['name'], 'Idle')
    _webserver.do_mime_response(200, 'application/json', return_json)


@postrequest.route('/lineup.post')
def lineup_post(_webserver):
    if _webserver.query_data['scan'] == 'start':
        _webserver.scan_state = 0
        _webserver.update_scan_status(_webserver.query_data['name'], 'Scan')
        _webserver.do_mime_response(200, 'text/html')
    elif _webserver.query_data['scan'] == 'abort':
        _webserver.do_mime_response(200, 'text/html')
        _webserver.scan_state = -1
        _webserver.update_scan_status(_webserver.query_data['name'], 'Idle')
    else:
        _webserver.logger.warning("Unknown scan command " + _webserver.query_data['scan'])
        _webserver.do_mime_response(400, 'text/html',
            web_templates['htmlError'].format(
                _webserver.query_data['scan'] + ' is not a valid scan command'))
