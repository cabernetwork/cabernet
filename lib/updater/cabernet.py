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

MANIFEST_FILE = 'manifest.json'
TMP_ZIPFILE = utils.CABERNET_NAMESPACE + '.zip'

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
            next_version = self.get_next_release(release_data_list)
            manifest['version'] = current_version
            manifest['next_version'] = next_version
            manifest['latest_version'] = last_version
            self.save_manifest(manifest)

    def import_manifest(self):
        """
        Loads the manifest for cabernet from a file
        """
        json_settings = importlib.resources.read_text(self.config['paths']['resources_pkg'], MANIFEST_FILE)
        settings = json.loads(json_settings)
        return settings
        
    def load_manifest(self):
        """
        Loads the cabernet manifest from DB
        """
        manifest_list = self.plugin_db.get_plugins(utils.CABERNET_NAMESPACE)
        if manifest_list is None:
            return None
        else:
            return manifest_list[0]

    def save_manifest(self, _manifest):
        """
        Saves to DB the manifest for cabernet
        """
        self.plugin_db.save_plugin(_manifest)
        
    def github_releases(self, _manifest):
        url = ''.join([
            _manifest['github_repo_' + self.config['main']['upgrade_quality'] ],
            '/releases'
            ])
        return self.get_uri_data(url)

    @handle_json_except 
    @handle_url_except 
    def get_uri_data(self, _uri):
        header = {'Content-Type': 'application/json', 
            'User-agent': utils.DEFAULT_USER_AGENT}
        req = urllib.request.Request(_uri, headers=header)
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            x = json.load(resp)
        return x

    def get_next_release(self, release_data_list):
        current_version = self.config['main']['version']
        x = self.version_re.match(current_version)
        c_version_float = float(re.findall(r'\d+\.(\d+\.\d+).\d+', current_version)[0])
        prev_version = release_data_list[0]['tag_name']
        for data in release_data_list:
            numbers = re.findall(r'\d+\.(\d+)\.(\d+).\d+', data['tag_name'])[0]
            version_float = float('{:01d}.{:02d}'.format(int(numbers[0]), int(numbers[1])))
            if version_float-0.101 < c_version_float:
                break
        prev_version = data['tag_name']
        return prev_version

    def upgrade_app(self, _web_status):
        """
        Initial request to perform an upgrade
        """
        c_manifest = self.load_manifest()
        if c_manifest is None:
            return False
        if c_manifest['next_version'] == c_manifest['version']:
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
                c_manifest['github_repo_' + self.config['main']['upgrade_quality'] ], 
                'zipball', c_manifest['next_version']
                ])):
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
        files_present = ['build', 'lib', 'misc', 'plugins',
            '.dockerignore', '.gitignore', 'CHANGELOG.md', 'CONTRIBUTING.md',
            'Dockerfile', 'Dockerfile_l2p', 'Dockerfile_tvh', 'Dockerfile_tvh_crypt.alpine',
            'Dockerfile_tvh_crypt.slim-buster', 'LICENSE', 'README.md',
            'TVHEADEND.md', 'docker-compose.yml', 'requirements.txt', 'tvh_main.py',
            'data', 'config.ini', 'is_container', '.git', 'cabernet.url', 'ffmpeg', 
            'README.txt', 'uninst.exe' ]

        filelist = [os.path.basename(x) for x in 
            glob.glob(os.path.join(self.config['paths']['main_dir'], '*'))]
        response = True
        for file in filelist:
            if file not in files_present:
                _web_status.data += '#### Extra file(s) found in install directory, aborting upgrade. FILE: {}<br>\r\n'.format(file)
                response = False
        return response

    @handle_json_except
    @handle_url_except
    def download_zip(self, _zip_url):
                          
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
        dir = self.config['paths']['tmp_dir']
        for files in os.listdir(dir):
            path = os.path.join(dir, files)
            try:
                shutil.rmtree(path)
            except OSError:
                os.remove(path)
