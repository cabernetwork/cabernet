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

import datetime
import json
import logging
import os
import pathlib
import ssl
import urllib
import urllib.request
import zipfile

from lib.common.filelock import FileLock

import lib.common.utils as utils
from lib.common.decorators import handle_url_except

fcc_ssl_context = ssl.SSLContext()
fcc_ssl_context.set_ciphers('HIGH:!DH:!aNULL')


class FCCData:
    """
    NOTE THIS OBJECT IS CURRENTLY NOT USED AND IS DEPENDENT ON DATEUTIL THAT IS NOT AVAILABLE ON WINDOWS
    """
    logger = None

    def __init__(self, _locast):
        self.locast = _locast
        self.refresh_fcc_stations()

    def refresh_fcc_stations(self):
        fcc_cache_dir = pathlib.Path(self.locast.config['paths']['stations_dir'])
        fcc_zip_path = pathlib.Path(fcc_cache_dir).joinpath("facility.zip")
        if utils.is_file_expired(
                fcc_zip_path,
                days=self.locast.config['locast']['fcc_timeout']):
            self.logger.debug('FCC file is expired, downloading FCC file')
            return self.download_fcc_stations()
        else:
            return False

    @handle_url_except
    def download_fcc_stations(self):
        """ Returning False/None means no update occurred
            If successful, a new facility.json file is generated
        """
        fcc_url = 'https://transition.fcc.gov/ftp/Bureaus/MB/Databases/cdbs/facility.zip'
        fcc_cache_dir = pathlib.Path(self.locast.config['paths']['stations_dir'])
        fcc_zip_path = pathlib.Path(fcc_cache_dir).joinpath("facility.zip")
        fcc_unzipped_dat = pathlib.Path(fcc_cache_dir).joinpath("facility.dat")
        fcc_json_path = pathlib.Path(fcc_cache_dir).joinpath("facility.json")
        fcc_cached_file_lock = pathlib.Path(fcc_cache_dir).joinpath("facility.json.lock")

        if os.path.exists(fcc_zip_path):
            os.remove(fcc_zip_path)
        if os.path.exists(fcc_unzipped_dat):
            os.remove(fcc_unzipped_dat)
        if not os.path.exists(fcc_zip_path):
            with urllib.request.urlopen(fcc_url, context=fcc_ssl_context) as resp:
                online_file_time = resp.headers['Last-modified'].replace(" GMT", "")
                online_file_time = datetime.datetime.strptime(online_file_time, '%a, %d %b %Y %H:%M:%S')
                from_zone = tz.tzutc()
                to_zone = tz.tzlocal()
                online_file_time = online_file_time.replace(tzinfo=from_zone).astimezone(to_zone)
                if os.path.exists(fcc_json_path):
                    json_file_time = datetime.datetime.utcfromtimestamp(os.path.getmtime(fcc_json_path))
                    json_file_time = json_file_time.replace(tzinfo=from_zone).astimezone(to_zone)
                    if json_file_time < online_file_time:
                        self.logger.debug('Online time is older than json file, stopping download')
                        resp.close()
                        return False
                fcc_facility_data = resp.read()
                resp.close()
            with open(fcc_zip_path, 'wb') as fcc_facility_file:
                fcc_facility_file.write(fcc_facility_data)

        if (not os.path.exists(fcc_unzipped_dat)) and (os.path.exists(fcc_zip_path)):
            try:
                with zipfile.ZipFile(fcc_zip_path, 'r') as zip_ref:
                    zip_ref.extractall(fcc_cache_dir)
            except zipfile.BadZipFile as e:
                self.logger.warning('Unable to unzip FCC file. {}'.format(str(e)))
                return False

        if os.path.exists(fcc_unzipped_dat) and os.path.getsize(fcc_unzipped_dat) > 7000000:
            with open(fcc_unzipped_dat, "r") as fac_file:
                lines = fac_file.readlines()
            facility_list = []
            for fac_line in lines:
                formatteddict = FCCData.fcc_dat_to_json(fac_line)
                if formatteddict:
                    facility_list.append(formatteddict)
            self.logger.debug('Found ' + str(len(facility_list)) + ' stations.')
            facility_json = {
                "fcc_station_list": facility_list
            }
            json_file_lock = FileLock(fcc_cached_file_lock)
            with json_file_lock:
                if os.path.exists(fcc_json_path):
                    os.remove(fcc_json_path)

                with open(fcc_json_path, "w") as write_file:
                    json.dump(facility_json, write_file, indent=2, sort_keys=True)
                    self.logger.debug('Updated Facility JSON file')
            return True
        else:
            return False

    @staticmethod
    def fcc_dat_to_json(_fac_line):
        current_date = datetime.datetime.utcnow()

        clean_line = _fac_line.strip()
        fac_line_split = clean_line.split('|')

        fac_template = {
            "comm_city": "",
            "comm_state": "",
            "eeo_rpt_ind": "",
            "fac_address1": "",
            "fac_address2": "",
            "fac_callsign": "",
            "fac_channel": "",
            "fac_city": "",
            "fac_country": "",
            "fac_frequency": "",
            "fac_service": "",
            "fac_state": "",
            "fac_status_date": "",
            "fac_type": "",
            "facility_id": "",
            "lic_expiration_date": "",
            "fac_status": "",
            "fac_zip1": "",
            "fac_zip2": "",
            "station_type": "",
            "assoc_facility_id": "",
            "callsign_eff_date": "",
            "tsid_ntsc": "",
            "tsid_dtv": "",
            "digital_status": "",
            "sat_tv": "",
            "network_affil": "",
            "nielsen_dma": "",
            "tv_virtual_channel": "",
            "last_change_date": "",
            "end_of_record": "",
        }
        formatteddict = {}
        key_num = 0
        for fcc_key in list(fac_template.keys()):
            insert_value = None
            if fac_line_split[key_num] != '':
                insert_value = fac_line_split[key_num]
            formatteddict[fcc_key] = insert_value
            key_num += 1

        # Check if expired
        if (not formatteddict['fac_status'] or formatteddict['fac_status'] != 'LICEN'
                or not formatteddict['lic_expiration_date']):
            return None

        fac_lic_expiration_date_split = formatteddict["lic_expiration_date"].split('/')
        fac_lic_expiration_date_datetime = datetime.datetime(int(fac_lic_expiration_date_split[2]),
            int(fac_lic_expiration_date_split[0]),
            int(fac_lic_expiration_date_split[1]),
            23, 59, 59, 999999)
        if fac_lic_expiration_date_datetime < current_date:
            return None

        # Check if we have a correct signal type
        if formatteddict['fac_service'] not in ['DT', 'TX', 'TV', 'TB', 'LD', 'DC']:
            return None

        return formatteddict


FCCData.logger = logging.getLogger(__name__)
