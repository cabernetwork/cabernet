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

import io
from io import StringIO
import urllib.request
from xml.sax.saxutils import escape

import lib.common.utils as utils
from lib.clients.channels.templates import ch_templates
from lib.common.decorators import getrequest
from lib.db.db_channels import DBChannels
import lib.image_size.get_image_size as get_image_size


@getrequest.route('/playlist')
def playlist(_webserver):
    _webserver.send_response(302)
    _webserver.send_header('Location', _webserver.path.replace('playlist', 'channels.m3u'))
    _webserver.end_headers()


@getrequest.route('/channels.m3u')
def channels_m3u(_webserver):
    _webserver.plugins.refresh_channels(_webserver.query_data['name'])
    _webserver.do_mime_response(200, 'audio/x-mpegurl', get_channels_m3u(
        _webserver.config, _webserver.stream_url, 
        _webserver.query_data['name'], 
        _webserver.query_data['instance']))


@getrequest.route('/lineup.xml')
def lineup_xml(_webserver):
    _webserver.plugins.refresh_channels(_webserver.query_data['name'])
    _webserver.do_mime_response(200, 'application/xml', get_channels_xml(
        _webserver.config, _webserver.stream_url, _webserver.query_data['name'], 
        _webserver.query_data['instance']))


@getrequest.route('/lineup.json')
def lineup_json(_webserver):
    _webserver.plugins.refresh_channels(_webserver.query_data['name'])
    _webserver.do_mime_response(200, 'application/json', get_channels_json(
        _webserver.config, _webserver.stream_url, _webserver.query_data['name'], 
        _webserver.query_data['instance']))


def get_channels_m3u(_config, _base_url, _namespace, _instance):

    format_descriptor = '#EXTM3U'
    record_marker = '#EXTINF'

    db = DBChannels(_config)
    ch_data = db.get_channels(_namespace, _instance)
    fakefile = StringIO()
    fakefile.write(
            '%s\n' % format_descriptor
        )

    sids_processed = []
    for sid, sid_data_list in ch_data.items():
        for sid_data in sid_data_list:
            if sid in sids_processed:
                continue
            sids_processed.append(sid)
            if not sid_data['enabled']:
                continue
            # NOTE tvheadend supports '|' separated names in two attributes
            # either 'group-title' or 'tvh-tags'
            # if a ';' is used in group-title, tvheadend will use the 
            # entire string as a tag
            groups = sid_data['namespace']
            if sid_data['json']['groups_other']:
                groups += '|' + '|'.join(sid_data['json']['groups_other'])
            if sid_data['json']['HD']:
                if sid_data['json']['group_hdtv']:
                    groups += '|' + sid_data['json']['group_hdtv']
            elif sid_data['json']['group_sdtv']:
                groups += '|' + sid_data['json']['group_sdtv']

            updated_chnum = utils.wrap_chnum(
                str(sid_data['display_number']), sid_data['namespace'], 
                sid_data['instance'], _config)
            service_name = set_service_name(_config, sid_data)
            fakefile.write(
                '%s\n' % (
                    record_marker + ':-1' + ' ' +
                    'channelID=\'' + sid + '\' ' +
                    'tvg-num=\'' + updated_chnum + '\' ' +
                    'tvg-chno=\'' + updated_chnum + '\' ' +
                    'tvg-name=\'' + sid_data['display_name'] + '\' ' +
                    'tvg-id=\'' + sid + '\' ' +
                    (('tvg-logo=\'' + sid_data['thumbnail'] + '\' ')
                        if sid_data['thumbnail'] else '') +
                    'group-title=\''+groups+'\',' + service_name
                )
            )
            fakefile.write(
                '%s\n' % (
                    (
                        '%s%s/%s/watch/%s' %
                        ('http://', _base_url, sid_data['namespace'], str(sid))
                    )
                )
            )
    return fakefile.getvalue()

    
def get_channels_json(_config, _base_url, _namespace, _instance):
    db = DBChannels(_config)
    ch_data = db.get_channels(_namespace, _instance)
    return_json = ''

    sids_processed = []
    for sid, sid_data_list in ch_data.items():
        for sid_data in sid_data_list:
            if sid in sids_processed:
                continue
            sids_processed.append(sid)
            if not sid_data['enabled']:
                continue
            updated_chnum = utils.wrap_chnum(
                str(sid_data['display_number']), sid_data['namespace'], 
                sid_data['instance'], _config)
            return_json = return_json + \
                ch_templates['jsonLineup'].format(
                    updated_chnum,
                    sid_data['display_name'],
                    _base_url + '/' + sid_data['namespace'] + '/watch/' + sid,
                    sid_data['json']['HD'])
            return_json = return_json + ','
    return "[" + return_json[:-1] + "]"


def get_channels_xml(_config, _base_url, _namespace, _instance):
    db = DBChannels(_config)
    ch_data = db.get_channels(_namespace, _instance)
    return_xml = ''
    sids_processed = []
    for sid, sid_data_list in ch_data.items():
        for sid_data in sid_data_list:
            if sid in sids_processed:
                continue
            sids_processed.append(sid)
            if not sid_data['enabled']:
                continue
            updated_chnum = utils.wrap_chnum(
                str(sid_data['display_number']), sid_data['namespace'], 
                sid_data['instance'], _config)
            return_xml = return_xml + \
                ch_templates['xmlLineup'].format(
                    updated_chnum,
                    escape(sid_data['display_name']),
                    _base_url + '/' + sid_data['namespace'] + '/watch/' + sid,
                    sid_data['json']['HD'])
    return "<Lineup>" + return_xml + "</Lineup>"


def update_channels(_config, _namespace, _query_data):
    db = DBChannels(_config)
    ch_data = db.get_channels(_namespace, None)
    results = 'Status Results<ul>'
    for key, values in _query_data.items():
        key_pair = key.split('-', 2)
        uid = key_pair[0]
        instance = key_pair[1]
        name = key_pair[2]
        value = values[0]
        if name == 'enabled':
            value = int(value)
        
        db_value = None
        for ch_db in ch_data[uid]: 
            if ch_db['instance'] == instance:
                db_value = ch_db[name]
                break
        if value != db_value:
            if value is None:
                lookup_name = translate_main2json(name)
                if lookup_name is not None:
                    value = ch_db['json'][lookup_name]
            results += ''.join(['<li>Updated [', uid, '][', instance, '][', name, '] to ', str(value), '</li>'])
            ch_db[name] = value
            if name == 'thumbnail':
                thumbnail_size = get_thumbnail_size(value)
                ch_db['thumbnail_size'] = thumbnail_size
            db.update_channel(ch_db)
    results += '</ul><hr>'
    return results


def translate_main2json(_name):
    if _name == 'display_number':
        return 'number'
    elif _name == 'display_name':
        return 'name'
    elif _name == 'thumbnail':
        return _name
    else:
        return None

def get_thumbnail_size(_thumbnail):
    thumbnail_size = (0, 0)
    try:
        with urllib.request.urlopen(_thumbnail) as resp:
            img_blob = resp.read()
            fp = io.BytesIO(img_blob)
            sz = len(img_blob)
            thumbnail_size = get_image_size.get_image_size_from_bytesio(fp, sz)
    except urllib.error.URLError as e:
        pass
    return thumbnail_size

    
# returns the service name used to sync with the EPG channel name
def set_service_name(_config, _sid_data):
    updated_chnum = utils.wrap_chnum(
        str(_sid_data['display_number']), _sid_data['namespace'], 
        _sid_data['instance'], _config)
    service_name = updated_chnum + \
        ' ' + _sid_data['display_name']
    return service_name
