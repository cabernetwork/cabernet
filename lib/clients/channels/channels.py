"""
MIT License

Copyright (C) 2023 ROCKY4546
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
import logging
import urllib.request
from io import StringIO
from xml.sax.saxutils import escape

import lib.common.utils as utils
from lib.clients.channels.templates import ch_templates
from lib.common.decorators import getrequest
from lib.db.db_channels import DBChannels
import lib.image_size.get_image_size as get_image_size
from lib.common.decorators import handle_url_except


@getrequest.route('/playlist')
def playlist(_webserver):
    _webserver.send_response(302)
    _webserver.send_header('Location', _webserver.path.replace('playlist', 'channels.m3u'))
    _webserver.end_headers()


@getrequest.route('/channels.m3u')
def channels_m3u(_webserver):
    _webserver.do_mime_response(200, 'audio/x-mpegurl', get_channels_m3u(
        _webserver.config, _webserver.stream_url,
        _webserver.query_data['name'],
        _webserver.query_data['instance'],
        _webserver.plugins.plugins
    ))


@getrequest.route('/lineup.xml')
def lineup_xml(_webserver):
    _webserver.do_mime_response(200, 'application/xml', get_channels_xml(
        _webserver.config, _webserver.stream_url,
        _webserver.query_data['name'],
        _webserver.query_data['instance'],
        _webserver.plugins.plugins
    ))


@getrequest.route('/lineup.json')
def lineup_json(_webserver):
    _webserver.do_mime_response(200, 'application/json', get_channels_json(
        _webserver.config, _webserver.stream_url,
        _webserver.query_data['name'],
        _webserver.query_data['instance'],
        _webserver.plugins.plugins
    ))


def get_channels_m3u(_config, _base_url, _namespace, _instance, _plugins):
    format_descriptor = '#EXTM3U'
    record_marker = '#EXTINF'
    ch_obj = ChannelsURL(_config, _base_url)

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
            if not sid_data['enabled'] \
                    or not _plugins.get(sid_data['namespace']) \
                    or not _plugins[sid_data['namespace']].enabled:
                continue
            if not _plugins[sid_data['namespace']] \
                    .plugin_obj.instances[sid_data['instance']].enabled:
                continue
            config_section = utils.instance_config_section(sid_data['namespace'], sid_data['instance'])            
            if not _config[config_section]['enabled']:
                continue
            sids_processed.append(sid)
            stream = _config[config_section]['player-stream_type']
            if stream == 'm3u8redirect' and sid_data['json'].get('stream_url'):
                uri = sid_data['json']['stream_url']
            else:
                uri = ch_obj.set_uri(sid_data)

            # NOTE tvheadend supports '|' separated names in two attributes
            # either 'group-title' or 'tvh-tags'
            # if a ';' is used in group-title, tvheadend will use the 
            # entire string as a tag
            groups = "" 
            namespace_in_m3u = _config.get(config_section, {}).get('channel-namespace_in_groups')            
            inst_group = _config[config_section]['channel-group_name']
            if namespace_in_m3u is not None:
               if namespace_in_m3u == 'True':
                   groups = sid_data['namespace']
            else:
                groups = sid_data['namespace']
            if inst_group is not None:
               if groups:
                   groups += '|' + inst_group
               else:
                   groups += inst_group
            if sid_data['group_tag']:
                if groups:
                    groups += '|' + '|'.join([sid_data['group_tag']])
                else:
                    groups += '|'.join([sid_data['group_tag']])
            if sid_data['json']['HD']:
                if sid_data['json']['group_hdtv']:
                    if groups:
                        groups += '|' + sid_data['json']['group_hdtv']
                    else:
                        groups += sid_data['json']['group_hdtv']
            elif sid_data['json']['group_sdtv']:
                if groups:
                    groups += '|' + sid_data['json']['group_sdtv']
                else:
                    groups += sid_data['json']['group_sdtv']
            updated_chnum = utils.wrap_chnum(
                str(sid_data['display_number']), sid_data['namespace'],
                sid_data['instance'], _config)
            service_name = ch_obj.set_service_name(sid_data)
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
                        'group-title=\'' + groups + '\',' + service_name
                )
            )
            fakefile.write(
                '%s\n' % (
                    (
                        uri
                    )
                )
            )
    return fakefile.getvalue()


def get_channels_json(_config, _base_url, _namespace, _instance, _plugins):
    db = DBChannels(_config)
    ch_obj = ChannelsURL(_config, _base_url)
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
            if not _plugins.get(sid_data['namespace']):
                continue
            if not _plugins[sid_data['namespace']].enabled:
                continue
            if not _plugins[sid_data['namespace']] \
                    .plugin_obj.instances[sid_data['instance']].enabled:
                continue
            config_section = utils.instance_config_section(sid_data['namespace'], sid_data['instance'])
            if not _config[config_section]['enabled']:
                continue
            sids_processed.append(sid)
            stream = _config[config_section]['player-stream_type']
            if stream == 'm3u8redirect':
                uri = sid_data['json']['stream_url']
            else:
                uri = ch_obj.set_uri(sid_data)
            updated_chnum = utils.wrap_chnum(
                str(sid_data['display_number']), sid_data['namespace'],
                sid_data['instance'], _config)
            return_json = return_json + ch_templates['jsonLineup'].format(
                sid_data['json']['callsign'],
                updated_chnum,
                sid_data['display_name'],
                uri,
                sid_data['json']['HD'])
            return_json = return_json + ','
    return "[" + return_json[:-1] + "]"


def get_channels_xml(_config, _base_url, _namespace, _instance, _plugins):
    db = DBChannels(_config)
    ch_obj = ChannelsURL(_config, _base_url)
    ch_data = db.get_channels(_namespace, _instance)
    return_xml = ''
    sids_processed = []
    for sid, sid_data_list in ch_data.items():
        for sid_data in sid_data_list:
            if sid in sids_processed:
                continue
            if not sid_data['enabled']:
                continue
            if not _plugins.get(sid_data['namespace']):
                continue
            if not _plugins[sid_data['namespace']].enabled:
                continue
            if not _plugins[sid_data['namespace']] \
                    .plugin_obj.instances[sid_data['instance']].enabled:
                continue

            config_section = utils.instance_config_section(sid_data['namespace'], sid_data['instance'])
            if not _config[config_section]['enabled']:
                continue
            sids_processed.append(sid)
            stream = _config[config_section]['player-stream_type']
            if stream == 'm3u8redirect':
                uri = sid_data['json']['stream_url']
                uri = escape(uri)
            else:
                uri = escape(ch_obj.set_uri(sid_data))
            updated_chnum = utils.wrap_chnum(
                str(sid_data['display_number']), sid_data['namespace'],
                sid_data['instance'], _config)
            return_xml = return_xml + ch_templates['xmlLineup'].format(
                updated_chnum,
                escape(sid_data['display_name']),
                uri,
                sid_data['json']['HD'])
    return "<Lineup>" + return_xml + "</Lineup>"


class ChannelsURL:

    def __init__(self, _config, _base_url):
        self.logger = logging.getLogger(__name__)
        self.config = _config
        self.base_url = _base_url

    def update_channels(self, _namespace, _query_data):
        db = DBChannels(self.config)
        ch_data = db.get_channels(_namespace, None)
        results = 'Status Results<ul>'
        for key, values in _query_data.items():
            key_pair = key.split('-', 2)
            uid = key_pair[0].replace('%2d', '-')
            instance = key_pair[1]
            name = key_pair[2]
            value = values[0]
            if name == 'enabled':
                value = int(value)

            db_value = None
            ch_db = None
            for ch_db in ch_data[uid]:
                if ch_db['instance'] == instance:
                    db_value = ch_db[name]
                    break
            if value != db_value:
                if value is None:
                    lookup_name = self.translate_main2json(name)
                    if lookup_name is not None:
                        value = ch_db['json'][lookup_name]
                if name == 'display_number':
                    config_section = utils.instance_config_section(ch_db['namespace'], instance)
                    start_ch = self.config[config_section].get('channel-start_ch_num')
                    if start_ch > -1:
                        results += ''.join(['<li>ERROR: Starting Ch Number setting is not default (-1) [', uid, '][', instance, '][', name, '] not changed', '</li>'])
                        continue
                results += ''.join(['<li>Updated [', uid, '][', instance, '][', name, '] to ', str(value), '</li>'])
                ch_db[name] = value
                if name == 'thumbnail':
                    thumbnail_size = self.get_thumbnail_size(value)
                    ch_db['thumbnail_size'] = thumbnail_size
                db.update_channel(ch_db)
        results += '</ul><hr>'
        return results

    def translate_main2json(self, _name):
        if _name == 'display_number':
            return 'number'
        elif _name == 'display_name':
            return 'name'
        elif _name == 'thumbnail':
            return _name
        else:
            return None

    @handle_url_except()
    def get_thumbnail_size(self, _thumbnail):
        thumbnail_size = (0, 0)
        if _thumbnail is None or _thumbnail == '':
            return thumbnail_size
        h = {'User-Agent': utils.DEFAULT_USER_AGENT,
             'Accept': '*/*',
             'Accept-Encoding': 'identity',
             'Connection': 'Keep-Alive'
             }
        req = urllib.request.Request(_thumbnail, headers=h)
        with urllib.request.urlopen(req) as resp:
            img_blob = resp.read()
            fp = io.BytesIO(img_blob)
            sz = len(img_blob)
            thumbnail_size = get_image_size.get_image_size_from_bytesio(fp, sz)
        return thumbnail_size

    def set_service_name(self, _sid_data):
        """
        Returns the service name used to sync with the EPG channel name
        """
        updated_chnum = utils.wrap_chnum(
            str(_sid_data['display_number']), _sid_data['namespace'],
            _sid_data['instance'], self.config)
        if self.config['epg']['epg_channel_number']:
            return updated_chnum + \
                ' ' + _sid_data['display_name']
        else:
            return _sid_data['display_name']

    def set_uri(self, _sid_data):
        if self.config['epg']['epg_use_channel_number']:
            updated_chnum = utils.wrap_chnum(
                str(_sid_data['display_number']), _sid_data['namespace'],
                _sid_data['instance'], self.config)
            uri = '{}{}/{}/auto/v{}'.format(
                'http://', self.base_url, _sid_data['namespace'], updated_chnum)
        else:
            uri = '{}{}/{}/watch/{}'.format(
                'http://', self.base_url, _sid_data['namespace'], str(_sid_data['uid']))
        return uri