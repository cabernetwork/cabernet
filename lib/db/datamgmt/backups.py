"""
MIT License

Copyright (C) 2023 ROCKY4546
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

import datetime
import glob
import logging
import os
import pathlib
import shutil
import zipfile

import lib.common.utils as utils
from lib.db.db_scheduler import DBScheduler
from lib.common.decorators import Backup
from lib.common.decorators import Restore
from lib.db.db_config_defn import DBConfigDefn

BACKUP_FOLDER_NAME = 'CabernetBackup'
CODE_DIRS_TO_IGNORE = ['__pycache__', 'data', '.git', 'ffmpeg', 'streamlink', '.github', 'build', 'misc']
CODE_FILES_TO_IGNORE = ['config.ini', 'is_container', 'uninst.exe']


def scheduler_tasks(config):
    scheduler_db = DBScheduler(config)
    if scheduler_db.save_task(
            'Applications',
            'Backup',
            'internal',
            None,
            'lib.db.datamgmt.backups.backup_data',
            20,
            'thread',
            'Backs up cabernet data including databases and config'
    ):
        scheduler_db.save_trigger(
            'Applications',
            'Backup',
            'weekly',
            dayofweek='Sunday',
            timeofday='02:00'
        )
    # Backup.log_backups()


def backup_data(_plugins):
    b = Backups(_plugins)
    b.backup_data()
    return True


class Backups:
    def __init__(self, _plugins):
        self.logger = logging.getLogger(__name__)
        self.plugins = _plugins
        self.config = _plugins.config_obj.data
        if self.config['paths']['external_plugins_pkg'] not in CODE_DIRS_TO_IGNORE:
            CODE_DIRS_TO_IGNORE.append(self.config['paths']['external_plugins_pkg'])

    def backup_data(self):
        # get the location where the backups will be stored
        # also deal with the number of backup folder limit and clean up
        backups_to_retain = self.config['datamgmt']['backups-backupstoretain'] - 1
        backups_location = self.config['datamgmt']['backups-location']
        folderlist = sorted(glob.glob(os.path.join(backups_location, BACKUP_FOLDER_NAME + '*')))

        while len(folderlist) > backups_to_retain:
            try:
                shutil.rmtree(folderlist[0])
            except PermissionError as e:
                logging.warning(e)
                break
            folderlist = sorted(glob.glob(os.path.join(backups_location, BACKUP_FOLDER_NAME + '*')))
        new_backup_folder = BACKUP_FOLDER_NAME +'_'+ utils.VERSION + datetime.datetime.now().strftime('_%Y%m%d_%H%M')
        new_backup_path = pathlib.Path(backups_location, new_backup_folder)

        for key in Backup.backup2func.keys():
            Backup.call_backup(key, self.config, backup_folder=new_backup_path)
        return new_backup_folder

    def restore_data(self, _folder, _key):
        """
        key is what the Back and Restore decorators use to lookup the function call_backup
        and is also tied to the config defn lookup under datamgmt
        """
        full_path = pathlib.Path(self.config['datamgmt']['backups-location'], _folder)
        if os.path.isdir(full_path):
            return Restore.call_restore(_key, self.config, backup_folder=full_path)
        else:
            return 'Folder does not exist: {}'.format(full_path)

    def backup_list(self):
        """
        A list of dicts that contain what is backed up for use with restore.
        """
        db_confdefn = DBConfigDefn(self.config)
        dm_section = db_confdefn.get_one_section_dict('general', 'datamgmt')
        bkup_defn = {}
        for key in Restore.restore2func.keys():
            bkup_defn[key] = dm_section['datamgmt']['settings'][key]
        return bkup_defn

    def backup_all(self):
        backup_folder = self.backup_data()
        if backup_folder is None:
            return False
        return self.backup_code(backup_folder)

    def backup_code(self, _backup_folder):
        """
        Zips up the code with an exclusion regexp that is compiled.
        using os.walk() along with the regexp, it will gen a zip file in the backup_folder
        """
        # default compression is 6
        zf = zipfile.ZipFile(pathlib.Path(
            self.config['datamgmt']['backups-location'], _backup_folder,
            'cabernet_code.zip'),
            'w', compression=zipfile.ZIP_DEFLATED)

        base_path = os.path.dirname(self.config['paths']['main_dir'])
        dir_count = 0
        for dirname, subdirs, files in os.walk(
                self.config['paths']['main_dir']):
            dir_count += 1
            # max count is normally around 70 folders
            if dir_count > 200:
                logging.warning('Unexpected folder count exceeded, aborting code backup')
                return False

            for d in CODE_DIRS_TO_IGNORE:
                if d in subdirs:
                    subdirs.remove(d)
            rel_dirname = dirname.replace(base_path, '.')
            zf.write(dirname, arcname=rel_dirname)
            for filename in files:
                zf.write(os.path.join(dirname, filename),
                         arcname=pathlib.Path(rel_dirname, filename))
        zf.close()
        return True

    def delete_code(self):
        for dirname, subdirs, files in os.walk(
                self.config['paths']['main_dir']):
            for d in CODE_DIRS_TO_IGNORE:
                if d in subdirs:
                    subdirs.remove(d)
            for filename in files:
                if filename not in CODE_FILES_TO_IGNORE:
                    try:
                        os.remove(os.path.join(dirname, filename))
                    except PermissionError as ex:
                        self.logger.notice(
                            'Exception: {}  Unable to delete file prior to overlaying upgrade'
                            .format(str(ex)))
        return True

    def restore_code(self, _folder):
        """
        Provides the folder relative to the tmp folder where the
        code to restore resides.  The code may contain non-code
        files, so standard code filtering is required.
        """
        new_code_path = os.path.join(self.config['paths']['tmp_dir'],
                                     _folder)
        for dirname, subdirs, files in os.walk(new_code_path):
            for d in CODE_DIRS_TO_IGNORE:
                if d in subdirs:
                    subdirs.remove(d)
            rel_dirname = dirname.replace(new_code_path, '.')
            for filename in files:
                os.makedirs(os.path.join(self.config['paths']['main_dir'], rel_dirname),
                            exist_ok=True)
                try:
                    dest = shutil.move(os.path.join(dirname, filename),
                                os.path.join(self.config['paths']['main_dir'], rel_dirname))
                except shutil.Error as ex:
                    self.logger.notice(
                        'Exception: {}  Unable to overlay new file'
                        .format(str(ex)))

    def check_code_write_permissions(self):
        result = ''
        for dirname, subdirs, files in os.walk(self.config['paths']['main_dir']):
            for d in CODE_DIRS_TO_IGNORE:
                if d in subdirs:
                    subdirs.remove(d)
            if not os.access(dirname, os.W_OK):
                self.logger.info('Aborting upgrade, folder not writable: {}'.format(dirname))
                result += '#### Folder not writeable, aborting upgrade. FOLDER: {}<br>\r\n'.format(dirname)
        if result == '':
            return None
        else:
            return result
