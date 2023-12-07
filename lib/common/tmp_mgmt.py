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

import gzip
import logging
import os
import pathlib
import shutil
import time
import urllib.request
import zipfile


import lib.common.utils as utils
from lib.common.decorators import handle_url_except


class TMPMgmt:

    def __init__(self, _config):
        self.logger = logging.getLogger(__name__)
        self.config = _config

    @handle_url_except()
    def download_file(self, _url, _retries, _folder, _filename, _file_type):
        if _filename == None:
            _filename = '{}{}'.format(time.time(), _file_type)
        if _folder is None:
            save_path = pathlib.Path(
                self.config['paths']['tmp_dir']) \
                .joinpath(_filename)
        else:
            save_path = pathlib.Path(
                self.config['paths']['tmp_dir']) \
                .joinpath(_folder) \
                .joinpath(_filename)
        buf_size = 2 * 16 * 16 * 1024

        if not save_path.parent.is_dir():
            save_path.parent.mkdir()
        h = {'User-agent': utils.DEFAULT_USER_AGENT}
        req = urllib.request.Request(_url, headers=h)
        with urllib.request.urlopen(req) as resp:
            with open(save_path, 'wb') as out_file:
                while True:
                    chunk = resp.read(buf_size)
                    if not chunk:
                        break
                    out_file.write(chunk)
        return save_path

    def extract_gzip(self, _in_filename):
        try:
            out_filename = _in_filename.with_suffix('')
            with gzip.open(_in_filename, 'rb') as f_in:
                with open(out_filename, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            return out_filename
        except (gzip.BadGzipFile, FileNotFoundError) as ex:
            raise exceptions.CabernetException(
                'Unable to gunzip File, {} {}' \
                .format(_in_filename, str(ex)))

    def extract_zip(self, _in_filename, outfile=None, is_single_file=False):
        try:
            if out_file is None:
                out_folder = os.path.dirname(_filename)
            with zipfile.ZipFile(_filename, 'r') as z:
                files = z.namelist()
                if is_single_file and len(files) > 1:
                    raise exceptions.CabernetException(
                        'Zip file contains more than one file, aborting, {}' \
                        .format(files))
                top_folder = files[0]
                z.extractall(out_folder)
            return pathlib.Path(out_folder, top_folder)
        except (zipfile.BadZipFile, FileNotFoundError) as ex:
            raise exceptions.CabernetException(
                'Unable to unzip File, {} {}' \
                .format(_filename, str(ex)))

    def cleanup_tmp(self, folder=None):
        self.logger.debug('Cleaning up tmp folder, subfolder {}'.format(folder))
        if folder is None:
            dir = pathlib.Path(self.config['paths']['tmp_dir'])
            for files in os.listdir(dir):
                path = os.path.join(dir, files)
                try:
                    shutil.rmtree(path)
                except OSError:
                    os.remove(path)
        else:
            dir = pathlib.Path(self.config['paths']['tmp_dir']) \
                .joinpath(folder)
            shutil.rmtree(dir)
