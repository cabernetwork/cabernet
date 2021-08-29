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

import copy
import configparser
import json
import logging
import pathlib
import os
import shutil
import time
import urllib

import lib.common.utils as utils
import lib.config.config_defn as config_defn
from lib.common.utils import clean_exit
from lib.common.decorators import getrequest
from lib.db.db_config_defn import DBConfigDefn
from lib.web.pages.templates import web_templates
from lib.common.decorators import Backup
from lib.common.decorators import Restore


CONFIG_BKUP_NAME = 'backups-config_ini'
CONFIG_FILENAME = 'config.ini'

def get_config(script_dir, opersystem, args):
    return TVHUserConfig(script_dir, opersystem, args)


@getrequest.route('/config.json')
def config_json(_webserver):
    if _webserver.config['web']['disable_web_config']:
        _webserver.do_mime_response(501, 'text/html', web_templates['htmlError']
            .format('501 - Config pages disabled.'
                    ' Set [web][disable_web_config] to False in the config file to enable'))
    else:
        _webserver.do_mime_response(200, 'application/json', json.dumps(_webserver.plugins.config_obj.filter_config_data()))


class TVHUserConfig:

    config_handler = configparser.ConfigParser(interpolation=None)

    def __init__(self, _script_dir=None, _opersystem=None, _args=None, _config=None):
        self.logger = None
        self.defn_json = None
        self.script_dir = str(_script_dir)
        self.defn_json = config_defn.load_default_config_defns()
        self.data = self.defn_json.get_default_config()
        if _script_dir is not None:
            config_file = TVHUserConfig.get_config_path(_script_dir, _args)
            self.import_config(config_file)
            self.defn_json.call_oninit(self)
            utils.logging_setup(self.data)
            # at this point, the config is setup
            self.db = DBConfigDefn(self.data)
            self.db.reinitialize_tables()
            self.defn_json.set_config(self.data)
            self.defn_json.save_defn_to_db()
        else:
            self.set_config(_config)
            self.defn_json.garbage_collect()
        self.db = DBConfigDefn(self.data)
        self.db.add_config(self.data)
        
    def refresh_config_data(self):
        self.data = self.db.get_config()

    def set_config(self, _config):
        self.data = copy.deepcopy(_config)
        self.config_handler.read(self.data['paths']['config_file'])
        self.logger = logging.getLogger(__name__)

    def init_logger_config(self):
        log_sections = ['loggers', 'logger_root', 'handlers', 'formatters',
            'handler_filehandler', 'handler_loghandler', 
            'formatter_extend', 'formatter_simple']
        for section in log_sections:
            try:
                self.config_handler.add_section(section)
            except configparser.DuplicateSectionError:
                pass
            for key, value in self.data[section].items():
                self.config_handler.set(section, key, str(value))
        with open(self.data['paths']['config_file'], 'w') as config_file:
            self.config_handler.write(config_file)
        utils.logging_setup(self.data)

    def import_config(self, config_file):
        self.config_handler.read(config_file)
        self.data['paths']['config_file'] = str(config_file)
        try:
            utils.logging_setup(self.data)
        except KeyError:
            self.init_logger_config()
        self.logger = logging.getLogger(__name__)
        self.logger.info("Loading Configuration File: " + str(config_file))

        for each_section in self.config_handler.sections():
            lower_section = each_section.lower()
            if lower_section not in self.data.keys():
                self.data.update({lower_section: {}})
            for (each_key, each_val) in self.config_handler.items(each_section):
                lower_key = each_key.lower()
                self.data[lower_section][lower_key] = \
                    self.fix_value_type(lower_section, lower_key, each_val)

    @staticmethod
    def get_config_path(_script_dir, args=None):
        config_file = None
        if args is not None and args.cfg:
            config_file = pathlib.Path(str(args.cfg))
        else:
            for x in [CONFIG_FILENAME, 'data/'+CONFIG_FILENAME]:
                poss_config = pathlib.Path(_script_dir).joinpath(x)
                if os.path.exists(poss_config):
                    config_file = poss_config
                    break
        if config_file and os.path.exists(config_file):
            return config_file
        else:
            print('ERROR: Config file missing {}, Exiting...'.format(poss_config))
            clean_exit(1)

    def fix_value_type(self, _section, _key, _value):
        try:
            val_type = self.defn_json.get_type(_section, _key, _value)
            if val_type == 'boolean':
                return self.config_handler.getboolean(_section, _key)
            elif val_type == 'list':
                if isinstance(_value, str) and _value.isdigit():
                    _value = int(_value)
                if not self.defn_json.validate_list_item(_section, _key, _value):
                    logging.info('INVALID VALUE ({}) FOR CONFIG ITEM [{}][{}]'
                        .format(_value, _section, _key))
                return _value
            elif val_type == 'integer':
                return int(_value)
            elif val_type == 'float':
                return float(_value)
            elif val_type is None:
                return _value
            else:
                return _value
        except (configparser.NoOptionError, configparser.NoSectionError, TypeError):
            return _value
        except ValueError:
            return None

    # removes sensitive data from config and returns a copy
    def filter_config_data(self):
        restricted_list = self.defn_json.get_restricted_items()
        filtered_config = copy.deepcopy(self.data)
        for item in restricted_list:
            del filtered_config[item[0]][item[1]]
        return filtered_config

    def detect_change(self, _section, _key, _updated_data):
        current_value = self.data[_section][_key]
        if type(current_value) is int:
            if _updated_data[_section][_key][0] is not None:
                _updated_data[_section][_key][0] = int(_updated_data[_section][_key][0])
        elif type(current_value) is bool:
            _updated_data[_section][_key][0] = bool(int(_updated_data[_section][_key][0]))
        elif type(current_value) is str:
            pass
        elif current_value is None:
            pass
        else:
            self.logger.debug('unknown value type for [{}][{}]  type is {}'
                .format(_section, _key, type(self.data[_section][_key])))

        if self.data[_section][_key] != _updated_data[_section][_key][0]:
            if len(_updated_data[_section][_key]) > 1:
                _updated_data[_section][_key][1] = True
            else:
                _updated_data[_section][_key].append(True)
        else:
            if len(_updated_data[_section][_key]) > 1:
                _updated_data[_section][_key][1] = False
            else:
                _updated_data[_section][_key].append(False)

    def merge_config(self, _delta_config_dict):
        self.data = utils.merge_dict(self.data, _delta_config_dict, ignore_conflicts=True)

    def update_config(self, _area, _updated_data):
        # make sure the config_handler has all the data from the file
        self.config_handler.read(self.data['paths']['config_file'])

        area_data = self.defn_json.get_defn(_area)
        for section, section_data in area_data['sections'].items():
            if section in _updated_data:
                for setting, setting_data in section_data['settings'].items():
                    if setting in _updated_data[section]:
                        if setting_data['level'] == 4:
                            pass
                        elif 'writable' in setting_data and not setting_data['writable']:
                            if setting in _updated_data[section]:
                                _updated_data[section][setting].append(False)
                        elif 'hidden' in setting_data and setting_data['hidden']:
                            if _updated_data[section][setting][0] is None:
                                _updated_data[section][setting].append(False)
                            else:
                                _updated_data[section][setting].append(True)
                                _updated_data[section][setting].append(True)
                        else:
                            self.detect_change(section, setting, _updated_data)

        # save the changes to config.ini and self.data
        results = '<hr><h3>Status Results</h3><ul>'

        config_defaults = self.defn_json.get_default_config_area(_area)
        for key in _updated_data.keys():
            results += self.save_config_section(key, _updated_data, config_defaults)
        with open(self.data['paths']['config_file'], 'w') as config_file:
            self.config_handler.write(config_file)

        # need to inform things that changes occurred...
        restart = False
        results += self.defn_json.call_onchange(_area, _updated_data, self)
        self.db.add_config(self.data)
        if restart:
            results += '</ul><b>Service may need to be restarted if not all changes were implemented</b><hr><br>'
        else:
            results += '</ul><hr><br>'
        return results

    def save_config_section(self, _section, _updated_data, _config_defaults):
        results = ''
        for (key, value) in _updated_data[_section].items():
            if value[1]:
                if value[0] is None:
                    # use default and remove item from config.ini
                    try:
                        self.config_handler.remove_option(_section, key)
                    except configparser.NoSectionError:
                        pass
                    self.data[_section][key] \
                        = _config_defaults[_section][key]
                    self.logger.debug(
                        'Config Update: Removed [{}][{}]'.format(_section, key))
                    results += \
                        '<li>Removed [{}][{}] from {}, using default value</li>' \
                        .format(_section, key, CONFIG_FILENAME)
                else:
                    # set new value
                    if len(_updated_data[_section][key]) == 3:
                        self.logger.debug(
                            'Config Update: Changed [{}][{}] updated'
                                .format(_section, key))
                    else:
                        self.logger.debug(
                            'Config Update: Changed [{}][{}] to {}'
                                .format(_section, key, _updated_data[_section][key][0]))

                    try:
                        self.config_handler.set(
                            _section, key, str(_updated_data[_section][key][0]))
                    except configparser.NoSectionError:
                        self.config_handler.add_section(_section)
                        self.config_handler.set(
                            _section, key, str(_updated_data[_section][key][0]))
                    self.data[_section][key] = _updated_data[_section][key][0]
                    if len(_updated_data[_section][key]) == 3:
                        results += '<li>Updated [{}][{}] updated</li>' \
                            .format(_section, key)
                    else:
                        results += '<li>Updated [{}][{}] to {}</li>' \
                            .format(_section, key, _updated_data[_section][key][0])
        return results

    def write(self, _section, _key, _value):
        self.data[_section][_key] = _value
        try:
            self.config_handler.set(_section, _key, _value)
        except configparser.NoSectionError:
            self.config_handler.add_section(_section)
            self.config_handler.set(_section, _key, _value)
        with open(self.data['paths']['config_file'], 'w') as config_file:
            self.config_handler.write(config_file)

class BackupConfig:

    def __init__(self, _config):
        self.logger = logging.getLogger(__class__.__name__)
        self.config = _config

    @Backup(CONFIG_BKUP_NAME)
    def backup(self, backup_folder):
        self.logger.debug('Running backup for {}'.format(CONFIG_FILENAME))
        try:
            if not os.path.isdir(backup_folder):
                os.mkdir(backup_folder)
            backup_file = pathlib.Path(backup_folder, CONFIG_FILENAME)
            shutil.copyfile(self.config['paths']['config_file'], 
                backup_file)
        except PermissionError as e:
            self.logger.warning(e)
            self.logger.warning('Unable to make backups')

    @Restore(CONFIG_BKUP_NAME)
    def restore(self, backup_folder):
        self.logger.debug('Running restore for {}'.format(CONFIG_FILENAME))
        if not os.path.isdir(backup_folder):
            msg = 'Backup folder does not exist: {}'.format(backup_folder)
            self.logger.warning(msg)
            return msg
        backup_file = pathlib.Path(backup_folder, CONFIG_FILENAME)
        if not os.path.isfile(backup_file):
            msg = 'Backup file does not exist, skipping: {}'.format(backup_file)
            self.logger.info(msg)
            return msg
        shutil.copyfile(backup_file, 
            self.config['paths']['config_file'])
        return CONFIG_FILENAME+' restored, please restart the app'
