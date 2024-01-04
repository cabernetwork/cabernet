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

from lib.web.pages.templates import web_templates
from lib.common.decorators import getrequest
from lib.common.decorators import postrequest


@getrequest.route('/api/configform')
def get_configform_html(_webserver):
    if 'area' in _webserver.query_data:
        configform = ConfigFormHTML()
        form = configform.get(_webserver.plugins.config_obj.defn_json.get_defn(
            _webserver.query_data['area']), _webserver.query_data['area'], _webserver.plugins.config_obj.data)
        _webserver.do_mime_response(200, 'text/html', form)
    else:
        _webserver.do_mime_response(404, 'text/html', web_templates['htmlError'].format('404 - Area Not Found'))


@postrequest.route('/api/configform')
def post_configform_html(_webserver):
    if _webserver.config['web']['disable_web_config']:
        _webserver.do_mime_response(
            501, 'text/html', web_templates['htmlError']
            .format('501 - Config pages disabled. '
            'Set [web][disable_web_config] to False in the config file to enable'))
    else:
        # Take each key and make a [section][key] to store the value
        config_changes = {}
        area = _webserver.query_data['area'][0]
        del _webserver.query_data['area']
        del _webserver.query_data['name']
        del _webserver.query_data['instance']
        for key in _webserver.query_data:
            key_pair = key.split('-', 1)
            if key_pair[0] not in config_changes:
                config_changes[key_pair[0]] = {}
            config_changes[key_pair[0]][key_pair[1]] = _webserver.query_data[key]
        results = _webserver.plugins.config_obj.update_config(area, config_changes)
        _webserver.do_mime_response(200, 'text/html', results)


class ConfigFormHTML:

    def __init__(self):
        self.area = None
        self.config_defn = None
        self.config = None

    def get(self, _config_defn, _area, _config):
        self.area = _area
        self.config = _config
        self.config_defn = _config_defn
        return ''.join([self.header, self.body])

    @property
    def header(self):
        return ''.join([
            '<!DOCTYPE html><html><head>',
            '<meta charset="utf-8"/><meta name="author" content="rocky4546">',
            '<meta name="description" content="config editor for Cabernet">',
            '<title>Settings Editor</title>',
            '<meta name="viewport" content="width=device-width, ',
            'minimum-scale=1.0, maximum-scale=1.0">',
            '<link rel="stylesheet" type="text/css" href="/modules/tabs/tabs.css">',
            '<script src="/modules/tabs/tabs.js"></script>',
            '<script src="/modules/pages/configform.js"></script></head>'])

    @property
    def title(self):
        return ''.join([
            '<body><div class="container">',
            '<h2>Settings Editor - ',
            self.config_defn['label'],
            '</h2><div>',
            self.config_defn['description'],
            '<ul style="list-style: none; float:right; ',
            'margin: 0px; padding-left:0px;">',
            '<li><form>',
            '<select style="background-color: #F0F0F0; float:right;"',
            ' class="dlevelsetting"  name="display-display_level">',
            '<option value="">default</option>',
            '<option value="0-Basic">0-Basic</option>',
            '<option value="1-Standard">1-Standard</option>',
            '<option value="2-Expert">2-Expert</option>',
            '<option value="3-Advanced">3-Advanced</option>',
            '</select></form></li></ul></div>'
        ])

    @property
    def tabs(self):
        active_tab = ' activeTab'
        area_html = ''.join(['<ul class="tabs">'])
        for section, section_data in self.config_defn['sections'].items():
            area_html = ''.join([
                area_html,
                '<li><a id="tab', section_data['name'], '" class="form',
                section_data['name'], ' configTab', active_tab, '" href="#">',
                '<i class="md-icon tabIcon">',
                section_data['icon'], '</i>',
                section_data['label'], '</a></li>'
            ])
            active_tab = ''
        area_html = ''.join([area_html, '</ul>'])
        return area_html

    @property
    def forms(self):
        area_html = ''
        for section in self.config_defn['sections'].keys():
            area_html = ''.join([area_html, self.get_form(section)])
        return area_html

    def get_form(self, _section):
        input_html = "*** UNKNOWN INPUT TYPE ***"
        section_data = self.config_defn['sections'][_section]
        form_html = ''.join([
            '<form id="form', section_data['name'], '" class="sectionForm" ',
            'action="/api/configform" method="post">',
            section_data['description'],
            '<div style="display: flex;"><table>'
        ])
        section_html = '<tbody>'
        subsection = None
        is_section_new = False
        
        plugin_image = ''
        for setting, setting_data in section_data['settings'].items():
            if setting_data['level'] == 4:
                continue
            title = ''
            readonly = ''

            new_section = None
            if '-' in setting:
                new_section = setting.split('-', 1)[0]
            if new_section != subsection and new_section is not None:
                is_section_new = True
                subsection = new_section

            background_color = '#F0F0F0'
            if setting_data['help'] is not None:
                title = ''.join([' title="', setting_data['help'], '"'])

            if 'writable' in setting_data and not setting_data['writable']:
                readonly = ' readonly'
                background_color = '#C0C0C0'

            if setting_data['type'] == 'string' \
                    or setting_data['type'] == 'path':
                input_html = ''.join([
                    '<input STYLE="background-color: ',
                    background_color, ';"  type="text"', readonly,
                    ' name="', section_data['name'], '-', setting, '">'])

            if setting_data['type'] == 'password':
                input_html = ''.join([
                    '<input STYLE="background-color: ',
                    background_color, ';"  type="password"', readonly,
                    ' name="', section_data['name'], '-', setting, '">'])

            elif setting_data['type'] == 'integer' \
                    or setting_data['type'] == 'float':
                input_html = ''.join([
                    '<input STYLE="background-color: ',
                    background_color, ';" type="number"', readonly,
                    ' name="', section_data['name'], '-', setting, '">'])

            elif setting_data['type'] == 'boolean':
                if 'writable' in setting_data and not setting_data['writable']:
                    readonly = ' disabled'

                input_html = ''.join([
                    '<input value="1" STYLE="background-color: ',
                    background_color, ';" type="checkbox"', readonly,
                    ' name="', section_data['name'], '-', setting, '">'
                                                                   '<input value="0" id="', setting,
                    'hidden" type="hidden"',
                    ' name="', section_data['name'], '-', setting, '">'
                ])

            elif setting_data['type'] == 'list':
                dlsetting = ''
                if section_data['name'] == 'display' and setting == 'display_level':
                    dlsetting = ' class="dlsetting" '

                option_html = ''.join(['<option value="">default</option>'])
                for value in setting_data['values']:
                    option_html += ''.join([
                        '<option value=', str(value), '>', str(value), '</option>'])
                input_html = ''.join([
                    '<select STYLE="background-color: ',
                    background_color, ';"', readonly,
                    dlsetting,
                    'name="', section_data['name'], '-', setting, '">',
                    option_html, '</select>'])

            elif setting_data['type'] == 'image':
                if setting != 'plugin_image':
                    input_html = ''.join([
                        '<img src="" width="128" ', 
                        'style="border: var(--line-background) solid 1px;" ',
                        'alt="',
                        section_data['name'], '-', setting,
                        '">'])
                else:
                    input_html = None
                    img_size = self.lookup_config_size()
                    plugin_image = ''.join([
                        '<div style="left: 5%;position: relative;top: 20%;margin-top: 10px;">',
                        '<img src="/api/manifest?plugin=',
                        section_data['label'],
                        '&key=icon" width="',
                        str(img_size), '" ', 
                        'style="border: var(--line-background) solid 1px;" ',
                        'alt="',section_data['name'], '-', setting,'">',
                        '</div>'
                        ])
            if is_section_new:
                is_section_new = False
                section_html = ''.join([section_html,
                                        '<tr class="hlevel"><td><hr><h3>', subsection.upper(), '</h3></td></tr>'])
            if input_html:
                section_html = ''.join([section_html,
                                        '<tr class="dlevel', str(setting_data['level']),
                                        '"><td><label ', title,
                                        '>', setting_data['label'], '</label></td><td>', input_html,
                                        '</td></tr>'])
        return ''.join([
            form_html, section_html, '</tbody></table>', plugin_image,
            '</div><button id="submit" class="button" STYLE="margin:1em" ',
            'type="submit"><b>Save changes</b></button>',
            '<input type=hidden name="area" value="', self.area, '"></form>'])

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
            return None


    @property
    def body(self):
        if self.config_defn is None:
            return ''.join([
                '<html><body><div>',
                '</div></body></html>'])
        else:
            return ''.join([
                self.title,
                self.tabs,
                self.forms,
                '<section id="status"></section>',
                '<footer><p>Not all configuration parameters are listed.  ',
                'Edit the config file directly to change any parameters.</p>',
                '</footer></div></body></html>'])
