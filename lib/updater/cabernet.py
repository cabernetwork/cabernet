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

import glob
import importlib
import importlib.resources
import json
import logging
import os
import pathlib
import re
import time
import urllib.request
import shutil
import zipfile

import lib.common.utils as utils
import lib.db.datamgmt.backups as backups
from lib.db.db_plugins import DBPlugins
from lib.common.decorators import handle_url_except
from lib.common.decorators import handle_json_except
from lib.common.tmp_mgmt import TMPMgmt

TMP_ZIPFILE = utils.CABERNET_ID + '.zip'

class CabernetUpgrade:

    def __init__(self, _plugins):
        self.logger = logging.getLogger(__name__)
        self.version_re = re.compile(r'(\d+\.\d+)\.\d+')
        self.plugins = _plugins
        self.config_obj = _plugins.config_obj
        self.config = _plugins.config_obj.data
        self.plugin_db = DBPlugins(self.config)
        self.tmp_mgmt = TMPMgmt(self.config)

    def update_version_info(self):
        """
        Updates the database with the latest version release data
        from github for cabernet and plugins loaded
        """
        manifest = self.import_manifest()
        release_data_list = self.github_releases(manifest)
        if release_data_list is not None:
            current_version = utils.VERSION
            last_version = release_data_list[0]['tag_name']
            last_stable_version = release_data_list[0]['tag_name']
            next_version = self.get_next_release(release_data_list)
            manifest['version']['current'] = current_version
            manifest['version']['next'] = next_version
            manifest['version']['latest'] = last_version
            manifest['version']['installed'] = True
            self.save_manifest(manifest)
            # need to have the task take at least 1 second to register the time
            time.sleep(1)

    def import_manifest(self):
        """
        Loads the manifest for cabernet
        """
        json_settings = self.plugin_db.get_repos(utils.CABERNET_ID)
        if json_settings:
            json_settings = json_settings[0]
        return json_settings

    def load_manifest(self):
        """
        Loads the cabernet manifest from DB
        """
        manifest_list = self.plugin_db.get_repos(utils.CABERNET_ID)
        if manifest_list is None:
            return None
        else:
            return manifest_list[0]

    def save_manifest(self, _manifest):
        """
        Saves to DB the manifest for cabernet
        """
        self.plugin_db.save_repo(_manifest)

    def github_releases(self, _manifest):
        url = ''.join([
            _manifest['dir']['github_repo_' + self.config['main']['upgrade_quality']],
            '/releases'
        ])
        return self.get_uri_data(url, 2)

    @handle_json_except
    @handle_url_except
    def get_uri_data(self, _uri, _retries):
        header = {'Content-Type': 'application/json',
                  'User-agent': utils.DEFAULT_USER_AGENT}
        req = urllib.request.Request(_uri, headers=header)
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            x = json.load(resp)
        return x

    def get_next_release(self, release_data_list):
        current_version = self.config['main']['version']
        cur_version_float = utils.get_version_index(current_version)
        next_version_int = (int(cur_version_float/100)+2)*100
        prev_version = release_data_list[0]['tag_name']
        data = None
        for data in release_data_list:
            version_float = utils.get_version_index(data['tag_name'])
            if version_float < next_version_int:
                break
        prev_version = data['tag_name']
        return prev_version

    def get_stable_release(self, release_data_list):
        """
        Get the latest stable release with the format z.y.x.w without additional text...
        
        """
        pass




    def upgrade_app(self, _web_status):
        """
        Initial request to perform an upgrade
        """
        c_manifest = self.load_manifest()
        if c_manifest is None:
            self.logger.info('Cabernet manifest not found, aborting')
            _web_status.data += 'Cabernet manifest not found, aborting<br>\r\n'
            return False
        if not c_manifest['version'].get('next'):
            return False
        if c_manifest['version'].get('next') == c_manifest['version'].get('current'):
            self.logger.info('Cabernet is on the current version, not upgrading')
            _web_status.data += 'Cabernet is on the current version, not upgrading<br>\r\n'
            return False

        # This checks to see if additional files or folders are in the 
        # basedir area. if so, abort upgrade.
        # It is basically for the case where we have the wrong directory
        _web_status.data += 'Checking current install area for expected files...<br>\r\n'
        if not self.check_expected_files(_web_status):
            return False

        b = backups.Backups(self.plugins)

        # recursively check all folders from the basedir to see if they are writable
        _web_status.data += 'Checking write permissions...<br>\r\n'
        resp = b.check_code_write_permissions()
        if resp is not None:
            _web_status.data += resp
            return False

        # simple call to run a backup of the data and source
        # use a direct call to the backup methods instead of calling the scheduler
        _web_status.data += 'Creating backup of code and data...<br>\r\n'
        if not b.backup_all():
            _web_status.data += 'Backup failed, aborting upgrade<br>\r\n'
            return False

        _web_status.data += 'Downloading new version from website...<br>\r\n'
        if not self.download_zip('/'.join([
            c_manifest['dir']['github_repo_' + self.config['main']['upgrade_quality']],
            'zipball', c_manifest['version']['next']
        ]), 2):
            _web_status.data += 'Download of the new version failed, aborting upgrade<br>\r\n'
            return False

        # skip integrity checks using SHA256 or SHA512 for now

        # Unzips the downloaded file to a temp area and check the version
        # contained in the utils.py that it is the same as expected.
        _web_status.data += 'Extracting zip...<br>\r\n'
        # folder is relative to tmp folder
        unpacked_code = self.extract_code()
        if unpacked_code is None:
            _web_status.data += 'Extracting from zip failed, aborting upgrade<br>\r\n'
            return False

        # Deletes the non-data and non-plugin files
        # maybe save the pycache folders?
        # this helps in case a file has no modify permission.
        # it can still be removed and added.
        # *.py, *.html, *.js, *.png, ...

        _web_status.data += 'Deleting old code...<br>\r\n'
        if b.delete_code() is None:
            _web_status.data += 'Deleting old files failed, aborting upgrade<br>\r\n'
            return False

        # does a move of the unzipped files to the source area
        _web_status.data += 'Moving new code in place...<br>\r\n'
        b.restore_code(unpacked_code)

        return True

    def check_expected_files(self, _web_status):
        """
        Check the base directory files to see if all are expected.
        """
        files_present = ['build', 'lib', 'misc',
                         '.dockerignore', '.gitignore', 'CHANGELOG.md', 'CONTRIBUTING.md',
                         'Docker_entrypoint.sh', 'Dockerfile', 'Dockerfile_tvh_crypt.alpine',
                         'Dockerfile_tvh_crypt.slim-buster', 'LICENSE', 'README.md',
                         'TVHEADEND.md', 'docker-compose.yml', 'requirements.txt', 'tvh_main.py',
                         'data', 'config.ini', 'is_container', '.git', 'cabernet.url', 'ffmpeg',
                         'README.txt', 'uninst.exe']

        files_present.extend([self.config['paths']['internal_plugins_pkg'],  self.config['paths']['external_plugins_pkg']])

        filelist = [os.path.basename(x) for x in
                    glob.glob(os.path.join(self.config['paths']['main_dir'], '*'))]
        response = True
        for file in filelist:
            if file not in files_present:
                _web_status.data += '#### Extra file(s) found in install directory, aborting upgrade. FILE: {}<br>\r\n'\
                    .format(file)
                response = False
        return response

    @handle_json_except
    @handle_url_except
    def download_zip(self, _zip_url, _retries):

        buf_size = 2 * 16 * 16 * 1024
        save_path = pathlib.Path(self.config['paths']['tmp_dir']).joinpath(TMP_ZIPFILE)
        h = {'Content-Type': 'application/zip', 'User-agent': utils.DEFAULT_USER_AGENT}
        req = urllib.request.Request(_zip_url, headers=h)
        with urllib.request.urlopen(req) as resp:
            with open(save_path, 'wb') as out_file:
                while True:
                    chunk = resp.read(buf_size)
                    if not chunk:
                        break
                    out_file.write(chunk)
        return True

    def extract_code(self):
        try:
            file_to_extract = pathlib.Path(self.config['paths']['tmp_dir']).joinpath(TMP_ZIPFILE)
            out_folder = pathlib.Path(self.config['paths']['tmp_dir']).joinpath('code')
            with zipfile.ZipFile(file_to_extract, 'r') as z:
                files = z.namelist()
                top_folder = files[0]
                z.extractall(out_folder)
            return pathlib.Path('code', top_folder)
        except (zipfile.BadZipFile, FileNotFoundError):
            return None

    def cleanup_tmp(self):
        dir_ = self.config['paths']['tmp_dir']
        for files in os.listdir(dir_):
            path = os.path.join(dir_, files)
            try:
                shutil.rmtree(path)
            except OSError:
                os.remove(path)
