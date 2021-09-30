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

import io
import urllib

import lib.image_size.get_image_size as get_image_size
import lib.common.utils as utils
from lib.common.decorators import getrequest
from lib.common.decorators import postrequest
from lib.clients.channels.channels import ChannelsURL


@getrequest.route('/api/channels_form')
def get_channels_form_html(_webserver, _namespace=None, _sort_col=None, _sort_dir=None, filter_dict=None):
    channels_form = ChannelsFormHTML(_webserver.channels_db, _webserver.config)
    if _namespace is None:
        name = _webserver.query_data['name']
    else:
        name = _namespace
    form = channels_form.get(name, _sort_col, _sort_dir, filter_dict)
    _webserver.do_mime_response(200, 'text/html', form)


@postrequest.route('/api/channels_form')
def post_channels_html(_webserver):
    # Take each key and make a [section][key] to store the value
    channel_changes = {}
    namespace = _webserver.query_data['name'][0]
    sort_col = _webserver.query_data['sort_col'][0]
    sort_dir = _webserver.query_data['sort_dir'][0]
    del _webserver.query_data['name']
    del _webserver.query_data['instance']
    del _webserver.query_data['sort_dir']
    del _webserver.query_data['sort_col']
    filter_dict = get_filter_data(_webserver.query_data)
    
    if sort_col is None:
        cu = ChannelsURL(_webserver.config)
        results = cu.update_channels(namespace, _webserver.query_data)
        _webserver.do_mime_response(200, 'text/html', results)
    else:
        get_channels_form_html(_webserver, namespace, sort_col, sort_dir, filter_dict)


class ChannelsFormHTML:

    def __init__(self, _channels_db, _config):
        self.db = _channels_db
        self.namespace = None
        self.config = _config
        self.active_tab_name = None
        self.num_of_channels = 0
        self.num_enabled = 0
        self.sort_column = None
        self.sort_direction = None

    def get(self, _namespace, _sort_col, _sort_dir, _filter_dict):
        self.sort_column = _sort_col
        self.sort_direction = _sort_dir
        self.namespace = _namespace
        self.filter_dict = _filter_dict
        sort_data = self.get_db_sort_data(_sort_col, _sort_dir)
        self.ch_data = self.db.get_sorted_channels(self.namespace, None, sort_data[0], sort_data[1])
        return ''.join([self.header,self.body])

    def get_db_sort_data(self, _sort_col, _sort_dir):
        if _sort_dir == 'sortdesc':
            ascending = False
        elif _sort_dir == 'sortasc':
            ascending = True
        else:
            _sort_col = None
            ascending = True
        db_column2 = None
        if _sort_col == 'enabled':
            db_column1 = 'enabled'
            db_column2 = 'instance'
        elif _sort_col == 'instance':
            db_column1 = 'instance'
        elif _sort_col == 'num':
            db_column1 = 'display_number'
        elif _sort_col == 'name':
            db_column1 = 'display_name'
        elif _sort_col == 'group':
            db_column1 = 'group_tag'
        elif _sort_col == 'thumbnail':
            db_column1 = 'thumbnail'
        elif _sort_col == 'metadata':
            db_column1 = 'HD'
            db_column2 = 'callsign'
        else:
            db_column1 = None
        return [[db_column1, ascending], [db_column2, ascending]]

    @property
    def header(self):
        return ''.join([
            '<html><head>',
            '<script src="/modules/channels/channelsform.js"></script>',
            '<script src="/modules/table/table.js"></script>',
            '<link rel="stylesheet" type="text/css" href="/modules/channels/channelsform.css">',
            '</head><body>'
            ])

    @property
    def form_header(self):
        header_dir = {
            'enabled':'sortnone',
            'instance':'sortnone',
            'num':'sortnone',
            'name':'sortnone',
            'group':'sortnone',
            'thumbnail':'sortnone',
            'metadata':'sortnone'
        }
        header_dir[self.sort_column] = self.sort_direction
        
        return ''.join([
            '<input type="hidden" name="name" value="', self.namespace, '" >',
            '<input type="hidden" name="sort_col" >',
            '<input type="hidden" name="sort_dir" >',
            '<table><tr><td>Total Unique Channels = ', str(self.num_of_channels), '</td></tr>',
            '<tr><td>Total Enabled Unique Channels = ', str(self.num_enabled), '</td>'
            '<td style="min-width:18ch; text-align: center">',
            '<button STYLE="background-color: #E0E0E0;" ',
            'type="submit"><b>Save changes</b></button>',
            '</td></tr></table>',
            '<table class="sortable" ><thead><tr>',
            '<th style="min-width: 7ch;" class="header"><label title="checkbox to enable/disable all displayed rows">',
            '<input id="enabled" type=checkbox></label>',
            '<label title="enabled=green, disabled=red, disabled dup=violet, duplicate=yellow indicator">',
            '<img class="sortit ', header_dir['enabled'], '">',
            '<img class="filterit"><span class=vertline><img></span></label></th>',
            '<th style="min-width: 11ch;" class="header"><label title="Table is for a plugin. Each row has an instance for a channel">',
            'instance',
            '<img class="sortit ', header_dir['instance'], '">',
            '<img class="filterit"><span class=vertline><img></span></label></th>',
            '<th style="min-width: 8ch;" class="header"><label title="Channel number.  DVR may require this to be a number">',
            'num',
            '<img class="sortit ', header_dir['num'], '">',
            '<img class="filterit"><span class=vertline><img></span></label></th>',
            '<th style="min-width: 10ch;" class="header"><label title="Channel display name">',
            'name',
            '<img class="sortit ', header_dir['name'], '">',
            '<img class="filterit"><span class=vertline><img></span></label></th>',
            '<th style="min-width: 10ch;" class="header"><label title="Group or tag name. Expects only one value">',
            'group',
            '<img class="sortit ', header_dir['group'], '">',
            '<img class="filterit"><span class=vertline><img></span></label></th>',
            '<th class="header"><label title="Use http:// https:// or (Linux) file:/// (Windows) file:///C:/ Be careful when using spaces in the path">',
            'thumbnail',
            '<img class="sortit ', header_dir['thumbnail'], '">',
            '<img class="filterit"><span class=vertline><img></span></label></th>',
            '<th class="header"><label title="Extra data used in filtering">',
            'metadata',
            '<img class="sortit ', header_dir['metadata'], '">',
            '<img class="filterit"><span class=vertline><img></span></label></th>',
            '</tr></thead>'

            '<div style="display: none;" id="enabled-menu" class="xmenu">',
            '<ul>',
            '<li style="list-style-type:none;">',
            self.get_filter_enable_checkbox('enabled'), ' Active Normal ',
            '</li>',
            '<li style="list-style-type:none;">',
            self.get_filter_enable_checkbox('duplicate'), ' Active Duplicates ',
            '</li>',
            '<li style="list-style-type:none;">',
            self.get_filter_enable_checkbox('disabled'), ' Disabled Normal ',
            '</li>',
            '<li style="list-style-type:none;">',
            self.get_filter_enable_checkbox('duplicate_disabled'), ' Disabled Duplicates ',
            '</li>',
            '</ul>',
            '</div>',

            '<div style="display: none;" id="instance-menu" class="xmenu">',
            '<center>instance</center>'
            '<ul>',
            '<li style="list-style-type:none;">',
            self.get_filter_text_chkbox('instance'), ' Filter: ', self.get_filter_textbox('instance'), 
            '</li>',
            '</ul>',
            '</div>',

            '<div style="display: none;" id="num-menu" class="xmenu">',
            '<center>num</center>'
            '<ul>',
            '<li style="list-style-type:none;">',
            self.get_filter_text_chkbox('num'), ' Filter: ', self.get_filter_textbox('num'), 
            '</li>',
            '</ul>',
            '</div>',
            '<div style="display: none;" id="name-menu" class="xmenu">',
            '<center>name</center>'
            '<ul>',
            '<li style="list-style-type:none;">',
            self.get_filter_text_chkbox('name'), ' Filter: ', self.get_filter_textbox('name'), 
            '</li>',
            '</ul>',
            '</div>',
            '<div style="display: none;" id="group-menu" class="xmenu">',
            '<center>group</center>'
            '<ul>',
            '<li style="list-style-type:none;">',
            self.get_filter_text_chkbox('group'), ' Filter: ', self.get_filter_textbox('group'), 
            '</li>',
            '</ul>',
            '</div>',
            '<div style="display: none;" id="thumbnail-menu" class="xmenu">',
            '<center>thumbnail</center>'
            '<ul>',
            '<li style="list-style-type:none;">',
            self.get_filter_text_chkbox('thumbnail'), ' Filter: ', self.get_filter_textbox('thumbnail'), 
            '</li>',
            '</ul>',
            '</div>',
            '<div style="display: none;" id="metadata-menu" class="xmenu">',
            '<center>metadata</center>'
            '<ul>',
            '<li style="list-style-type:none;">',
            self.get_filter_text_chkbox('metadata'), ' Filter: ', self.get_filter_textbox('metadata'),
            '</li>',
            '</ul>',
            '</div>',
            ])


    def get_filter_enable_checkbox(self, _name):
        name = _name + "-mi"
        if self.filter_dict is None:
            return '<input id="' + name + '" name="' + name + '" value="1" type=checkbox checked>'
        elif name in self.filter_dict:
            return '<input id="' + name + '" name="' + name + '" value="1" type=checkbox checked>'
        else:
            return '<input id="' + name + '" name="' + name + '" value="1" type=checkbox>'


    def get_filter_textbox(self, _name):
        name = _name + "-text"
        if self.filter_dict is not None and self.filter_dict[name] is not None:
            return '<input name="' + name + '" type=text size=7 value="' + self.filter_dict[name] + '">'
        else:
            return '<input name="' + name + '" type=text size=7>'

    def get_filter_text_chkbox(self, _name):
        name = _name + "-checkbox"
        if self.filter_dict is None:
            return '<input id="text-mi" name="' + name + '" value="1" type=checkbox>'        
        elif name in self.filter_dict:
            return '<input id="text-mi" name="' + name + '" value="1" type=checkbox checked>'
        else:
            return '<input id="text-mi" name="' + name + '" value="1" type=checkbox>'
        
    @property
    def form(self):
        t = self.table
        forms_html = ''.join(['<form id="channelform" ',
            'action="/api/channels_form" method="post">',
            self.form_header, t, '</form>'])
        return forms_html

    @property
    def table(self):
        table_html = '<tbody>'
        sids_processed = {}
        for sid_data in self.ch_data:
            sid = sid_data['uid']
            instance = sid_data['instance']
            if sid_data['enabled']:
                enabled = 'checked'
                enabled_status = "enabled"
            else:
                enabled = ''
                enabled_status = "disabled"
            if sid in sids_processed.keys():
                if sid_data['enabled']:
                    enabled_status = "duplicate"
                else:
                    enabled_status = "duplicate_disabled"
            else:
                sids_processed[sid] = sid_data['enabled']

            if sid_data['json']['HD']:
                quality = 'HD'
            else:
                quality = 'SD'
            if 'VOD' in sid_data['json']:
                if sid_data['json']['VOD']:
                    vod = 'VOD'
                else:
                    # Not sure what to call not VOD?
                    vod = 'Live'
            else:
                vod = ''
                
            max_image_size = self.lookup_config_size()
            if sid_data['thumbnail_size'] is not None:
                image_size = sid_data['thumbnail_size']
                thumbnail_url = utils.process_image_url(self.config, sid_data['thumbnail'])
                if max_image_size is None:
                    display_image = ''.join(['<img border=1 src="', thumbnail_url, '">'])
                elif max_image_size == 0:
                    display_image = ''
                else:
                    if image_size[0] < max_image_size:
                        img_width = str(image_size[0])
                    else:
                        img_width = str(max_image_size)
                    display_image = ''.join(['<img width="', img_width, '" border=1 src="', thumbnail_url, '">'])
            else:
                display_image = ''
                image_size = 'UNK'
                img_width = 0

            if sid_data['json']['groups_other'] is None:
                groups_other = ''
            else:
                groups_other = str(sid_data['json']['groups_other'])
                
            if sid_data['json']['thumbnail_size'] is not None:
                original_size = sid_data['json']['thumbnail_size']
            else:
                original_size = 'UNK'
            row = ''.join([
                '<tr><td style="text-align: center" class="', enabled_status, '">',
                '<input class="enabled" value="1" type=checkbox name="',
                self.get_input_name(sid, instance, 'enabled'),
                '" ', enabled, '>',
                '<input value="0" type="hidden" name="',
                self.get_input_name(sid, instance, 'enabled'),
                '">',
                '</td>',
                '<td style="text-align: center">', instance, '</td>',
                '<td style="text-align: center">', 
                self.get_input_text(sid_data, sid, instance, 'display_number'), '</td>',
                '<td style="text-align: center">', 
                self.get_input_text(sid_data, sid, instance, 'display_name'), '</td>',
                '<td style="text-align: center">', 
                self.get_input_text(sid_data, sid, instance, 'group_tag'), '</td>',
                '<td><table width="100%"><tr><td style="border: none; background: none;">', 
                self.get_input_text(sid_data, sid, instance, 'thumbnail'),
                '</td></tr><tr><td style="border: none; background: none;">',
                display_image,
                '</td></tr><tr><td style="border: none; background: none;">',
                'size=', str(image_size), '   original_size=', str(original_size),
                '</td></tr></table></td>',
                '<td style="text-align: center">', quality, ' ', vod, ' ',
                sid_data['json']['callsign'], ' ', sid,'<br>',
                groups_other,
                '</td>',
                '</tr>'
                ])
            table_html += row
        self.num_of_channels = len(sids_processed.keys())
        self.num_enabled = sum(x == True for x in sids_processed.values())
        return ''.join([table_html, '</tbody></table>'])

    def get_input_text(self, _sid_data, _sid, _instance, _title):
        if _sid_data[_title] is not None:
            size = len(_sid_data[_title]) 
            if size > 30:
                rows = 1
                if size > 70:
                    rows = 2
                return ''.join(['<textarea name="',
                    self.get_input_name(_sid, _instance, _title),
                    '" rows=', str(rows), ' cols=22>', _sid_data[_title], 
                    '</textarea>'])
            else:
                if size > 24:
                    size = 20
                elif size < 3:
                    size = 3
                return ''.join(['<input type="text" name="',
                    self.get_input_name(_sid, _instance, _title),
                    '" value="', _sid_data[_title], 
                    '" size="', str(int(size*.9)), '">'])
        else:
            return ''.join(['<input type="text" name="',
                self.get_input_name(_sid, _instance, _title),
                '" size="5">'])


    def get_input_name(self, _sid, _instance, _title):
        _sid = _sid.replace('-', '%2d')
        return  ''.join([_sid, '-', _instance, '-', _title])

    @property
    def body(self):
        return ''.join([
            '<section id="status"></section>',
            self.form,
            '<footer><p>Clearing any field and saving will revert to the default value. Sorting a column will clear any filters applied. ',
            ' Help is provided on the column titles.',
            ' First column displays the status of the channel: either enabled, disabled or duplicate (enabled or disabled).',
            ' The thumbnail field must have an entry; not using the thumbnail is a configuration parameter under Settings - Clients - EPG.',
            ' Thumbnail filtering is only on the URL.',
            ' The size of the thumbnail presented in the table is set using the configuration parameter under Settings - Internal - Channels.</p>',
            '</footer></body>'])

    def lookup_config_size(self):
        size_text = self.config['channels']['thumbnail_size']
        if size_text == 'None':
            return 0
        elif size_text == 'Tiny(16)':
            return 16
        elif size_text == 'Small(48)':
            return 48
        elif size_text == 'Medium(128)':
            return 128
        elif size_text == 'Large(180)':
            return 180
        elif size_text == 'X-Large(270)':
            return 270
        elif size_text == 'Full-Size':
            return None
        else:
            self.logger.warning('UNKNOWN [channels][thumbnail_size] = {}'.format(size_text))
            return None



def get_filter_data(query_data):
    filter_names_list = ['enabled-mi', 'duplicate-mi', 'disabled-mi', 'duplicate_disabled-mi',
        'instance-checkbox', 'instance-text', 'num-text', 'num-checkbox', 'name-text', 'name-checkbox', 'group-text', 
        'group-checkbox', 'thumbnail-text', 'thumbnail-checkbox',
        'metadata-text', 'metadata-checkbox']
    filter_dict = {}
    for name in filter_names_list:
        try:
            filter_dict[name] = query_data[name][0]
            del query_data[name]
        except KeyError:
            pass
    return filter_dict
