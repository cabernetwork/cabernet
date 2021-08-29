import urllib
import zipfile
import os
import sys
import datetime
import json

os.chdir(os.path.dirname(sys.argv[0]))

print('Downloading the latest FCC facilities database...')

urllib.urlretrieve("https://transition.fcc.gov/ftp/Bureaus/MB/Databases/cdbs/facility.zip", "facility.zip")

print('Unzipping FCC facilities database...')

with zipfile.ZipFile("facility.zip", 'r') as zip_ref:
    zip_ref.extractall(".")

print('Reading Database...')

tv_facility_list = []
tv_dma_list = []
fac_loop_mod_count = 0
fac_found_count = 0

with open("facility.dat", "r") as fac_file:
    for fac_line in fac_file:
        if (fac_loop_mod_count % 5) == 0:
            sys.stdout.write('.')
            sys.stdout.flush()

        fac_loop_mod_count = fac_loop_mod_count + 1

        clean_line = fac_line.strip()
        fac_line_split = clean_line.split('|')
        current_date = datetime.datetime.now()

        if fac_line_split[12] != '':
            fac_status_date_split = fac_line_split[12].split('/')

        if fac_line_split[15] != '':
            fac_lic_expiration_date_split = fac_line_split[15].split('/')
            fac_lic_expiration_date_datetime = datetime.datetime(int(fac_lic_expiration_date_split[2]),
                                                                 int(fac_lic_expiration_date_split[0]),
                                                                 int(fac_lic_expiration_date_split[1]),
                                                                 23, 59, 59, 999999)

        if fac_line_split[21] != '':
            fac_callsign_eff_date_split = fac_line_split[21].split('/')

        if fac_line_split[29] != '':
            fac_last_change_date_split = fac_line_split[29].split('/')

        fac_obj = {
            "comm_city": fac_line_split[0],
            "comm_state": fac_line_split[1],
            "eeo_rpt_ind": fac_line_split[2],
            "fac_address1": fac_line_split[3],
            "fac_address2": fac_line_split[4],
            "fac_callsign": fac_line_split[5],
            "fac_channel": fac_line_split[6],
            "fac_city": fac_line_split[7],
            "fac_country": fac_line_split[8],
            "fac_frequency": fac_line_split[9],
            "fac_service": fac_line_split[10],
            "fac_state": fac_line_split[11],
            "fac_status_date": fac_line_split[12],
            "fac_type": fac_line_split[13],
            "facility_id": fac_line_split[14],
            "lic_expiration_date": fac_line_split[15],
            "fac_status": fac_line_split[16],
            "fac_zip1": fac_line_split[17],
            "fac_zip2": fac_line_split[18],
            "station_type": fac_line_split[19],
            "assoc_facility_id": fac_line_split[20],
            "callsign_eff_date": fac_line_split[21],
            "tsid_ntsc": fac_line_split[22],
            "tsid_dtv": fac_line_split[23],
            "digital_status": fac_line_split[24],
            "sat_tv": fac_line_split[25],
            "network_affil": fac_line_split[26],
            "nielsen_dma": fac_line_split[27],
            "tv_virtual_channel": fac_line_split[28],
            "last_change_date": fac_line_split[29]
        }

        if ((fac_obj['fac_status'] == 'LICEN')
                and (fac_lic_expiration_date_datetime is not None)
                and (fac_lic_expiration_date_datetime > current_date)
                and (fac_obj['fac_service'] in ('DT', 'TX', 'TV', 'TB', 'LD', 'DC'))):
            sys.stdout.write(fac_obj['fac_callsign'] + '.')
            sys.stdout.flush()
            fac_found_count = fac_found_count + 1
            tv_facility_list.append(fac_obj)

        if (fac_obj['nielsen_dma'] != '') and (fac_obj['nielsen_dma'] not in tv_dma_list):
            tv_dma_list.append(fac_obj['nielsen_dma'])

print('\nWriting out found list...')

json_tv_facility_file = open("tv_facilities.json", "w")
json_tv_facility_file.write(json.dumps(tv_facility_list))
json_tv_facility_file.close()


print('\nWriting deduped DMA list...')

with open("fcc_dma_markets_deduped.txt", "w") as tv_dma_file:
    for dma_list_item in tv_dma_list:
        tv_dma_file.write("%s\n" % dma_list_item)

print('Complete!')
print('Found ' + str(fac_found_count) + ' items.')
