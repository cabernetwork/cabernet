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

import importlib
import json
import logging
import threading
from importlib import resources

import lib.common.utils as utils
from lib.config import config_callbacks
from lib.db.db_config_defn import DBConfigDefn

CONFIG_DEFN_PATH = 'lib.resources.config_defn'


def load_default_config_defns():
    """ loads all definition files from the default
        folder and returns the ConfigDefn object
    """
    defn_obj = ConfigDefn()
    for defn_file in sorted(
            importlib.resources.contents(CONFIG_DEFN_PATH)):
        if str(defn_file).endswith('.json'):
            defn_obj.merge_defn_file(CONFIG_DEFN_PATH, defn_file)
    return defn_obj


class ConfigDefn:

    def __init__(self, _defn_path=None, _defn_file=None, _config=None, _is_instance=False):
        self.logger = None
        self.config_defn = {}
        self.config = None
        self.db = None
        self.is_instance_defn = _is_instance
        self.restricted_items = []
        if _config:
            self.set_config(_config)
        if _defn_file and _defn_path:
            self.merge_defn_file(_defn_path, _defn_file)

    def set_config(self, _config):
        self.config = _config
        if self.db is None:
            self.db = DBConfigDefn(self.config)
            if self.config_defn:
                self.save_defn_to_db()
        self.logger = logging.getLogger(__name__)

    def merge_defn_file(self, _defn_path, _defn_file):
        """ Merges a definition file into the current object
        """
        json_file = resources.read_text(_defn_path, _defn_file)
        defn = json.loads(json_file)
        self.call_ondefnload(defn)
        self.merge_defn_dict(defn)

    def merge_defn_dict(self, _defn_dict):
        """ Merges a definition file into the current object
        """
        self.config_defn = utils.merge_dict(self.config_defn, _defn_dict)
        self.update_restricted_items(_defn_dict)
        if self.db is not None:
            self.save_defn_to_db(_defn_dict)

    def merge_defn_obj(self, _defn_obj):
        """ will merge and terminate defn object
        """
        self.config_defn = utils.merge_dict(self.config_defn, _defn_obj.config_defn)
        self.update_restricted_items(_defn_obj.config_defn)

    def garbage_collect(self):
        self.logger.debug('garbage collecting for Thread:{}'.format(threading.get_ident()))
        self.config_defn = None

    def get_default_config(self):
        """
        JSON format: [module]['sections'][section]['settings'][setting][metadata]
        section is the section in the ini file
        setting is the name in the ini file
        """
        config_defaults = {}
        if self.db is not None:
            areas = self.get_areas()
            for area in areas:
                area_dict = self.get_defn(area)
                defaults_dict = self.get_default_config_area(area, area_dict)
                config_defaults = utils.merge_dict(config_defaults, defaults_dict)
        else:
            for area, area_dict in self.config_defn.items():
                defaults_dict = self.get_default_config_area(area, area_dict)
                config_defaults = utils.merge_dict(config_defaults, defaults_dict)
        return config_defaults

    def get_default_config_area(self, _area, _area_dict=None):
        config_defaults = {}
        if _area_dict is None:
            area_dict = self.get_defn(_area)
        else:
            area_dict = _area_dict

        for section in list(area_dict['sections'].keys()):
            if section not in list(config_defaults.keys()):
                config_defaults[section] = {}
            for setting in list(area_dict['sections'][section]['settings'].keys()):
                value = area_dict['sections'][section]['settings'][setting]['default']
                config_defaults[section][setting] = value
        return config_defaults

    def get_defn(self, _area):
        area_dict = self.db.get_area_dict(_area)[0]
        sections = self.db.get_sections_dict(_area)
        area_dict['sections'] = sections
        return area_dict

    def get_areas(self):
        return self.db.get_areas()

    def call_oninit(self, _config_obj):
        for module in list(self.config_defn.keys()):
            for section in list(self.config_defn[module]['sections'].keys()):
                for key, settings in list(self.config_defn[module]['sections'][section]['settings'].items()):
                    if 'onInit' in settings:
                        config_callbacks.call_function(settings['onInit'], section, key, _config_obj)

    def call_onchange(self, _area, _updated_data, _config_obj):
        results = ''
        area_data = self.get_defn(_area)
        for section, section_data in area_data['sections'].items():
            if section in _updated_data:
                for key, setting_data in section_data['settings'].items():
                    if key in _updated_data[section] and \
                            _updated_data[section][key][1] and \
                            'onChange' in setting_data:
                        status = config_callbacks.call_function(setting_data['onChange'], section, key, _config_obj)
                        if status is None:
                            results += '<li>[{}][{}] implemented</li>'.format(section, key)
                        else:
                            results += '<li>[{}][{}] {}</li>'.format(section, key, status)
        return results

    def call_ondefnload(self, _defn):
        for module in list(_defn.keys()):
            for section in list(_defn[module]['sections'].keys()):
                for key, settings in list(_defn[module]['sections'][section]['settings'].items()):
                    if 'onDefnLoad' in settings:
                        config_callbacks.call_ondefnload_function(settings['onDefnLoad'], section, key, self.config, _defn)


    def save_defn_to_db(self, _delta_defn=None):
        if _delta_defn:
            delta_defn = _delta_defn
        else:
            delta_defn = self.config_defn
        for area, area_data in delta_defn.items():
            if 'icon' in area_data:
                self.db.add_area(area, area_data)
            for section, section_data in area_data['sections'].items():
                if self.is_instance_defn:
                    self.db.add_instance(area, section, section_data)
                else:
                    self.db.add_section(area, section, section_data)

    def save_instance_defn_to_db(self, _delta_defn=None):
        if _delta_defn:
            delta_defn = _delta_defn
        else:
            delta_defn = self.config_defn
        for area, area_data in delta_defn.items():
            if 'icon' in area_data:
                self.db.add_area(area, area_data)
            for section, section_data in area_data['sections'].items():
                self.db.add_instance(area, section, section_data)



    def get_type(self, _section, _key, _value):
        """ Returns the expected type of the setting
        """
        for module in list(self.config_defn.keys()):
            for section in list(self.config_defn[module]['sections'].keys()):
                if section == _section:
                    for setting in list(self.config_defn[module]['sections'][section]['settings'].keys()):
                        if setting == _key:
                            return self.config_defn[module]['sections'][section]['settings'][setting]['type']
        return None

    def validate_list_item(self, _section, _key, _value):
        """ for list settings, will determine if the value
            is in the list
        """
        for module in list(self.config_defn.keys()):
            for section in list(self.config_defn[module]['sections'].keys()):
                if section == _section:
                    for setting in list(self.config_defn[module]['sections'][section]['settings'].keys()):
                        if setting == _key:
                            if _value in str(self.config_defn[module]['sections'][section]['settings'][setting]['values']):
                                return True
                            else:
                                return False
        return None

    def update_restricted_items(self, _defn_file):
        for area, area_data in _defn_file.items():
            self.update_restricted_items_area(area_data)

    def update_restricted_items_area(self, _defn_area):
        for section, section_data in _defn_area['sections'].items():
            for key, settings in section_data['settings'].items():
                if settings['level'] == 4:
                    self.restricted_items.append([section, key])
                elif 'hidden' in settings and settings['hidden']:
                    self.restricted_items.append([section, key])

    def get_restricted_items(self):
        if not self.restricted_items:
            area_list = self.db.get_areas()
            for area in area_list:
                area_dict = self.get_defn(area)
                self.update_restricted_items_area(area_dict)
        return self.restricted_items

    @property
    def defn_path(self):
        return CONFIG_DEFN_PATH

    def terminate(self):
        self.db.close()
        self.config_defn = None
        self.config = None
        self.db = None
        self.restricted_items = None
        self.logger.debug('Database terminated for thread:{}'.format(threading.get_ident()))
