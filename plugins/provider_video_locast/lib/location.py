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

import json
import logging
import re
import urllib.request

import lib.common.exceptions as exceptions
from lib.common.decorators import handle_url_except
from lib.common.decorators import handle_json_except
from . import constants


class Location:
    logger = None

    def __init__(self, _locast_inst):
        self.config_obj = _locast_inst.config_obj
        config_section = _locast_inst.config_section
        self.zipcode = self.config_obj.data[config_section]["overrides-zipcode"]
        self.latitude = self.config_obj.data[config_section]["overrides-latitude"]
        self.longitude = self.config_obj.data[config_section]["overrides-longitude"]
        self.dma = None
        self.city = None
        self.active = None
        self.has_dma_changed = False

        if self.find_location():
            self.logger.debug("Got location as {} - DMA {}"
                .format(self.city, self.dma))
        else:
            raise exceptions.CabernetException("Unable to retrieve DMA location")

        # Check that Locast reports this market is currently active and available.
        if not self.active:
            self.logger.error("Locast reports that this DMA/Market area is not currently active!")
            raise exceptions.CabernetException("Locast indicates DMA location not active")
        if 'dma' in self.config_obj.data[config_section] \
                and self.config_obj.data[config_section]['dma'] \
                != self.dma:
            self.logger.debug('DMA has changed, purging old DMA data for this instance')
            self.has_dma_changed = True
        # update config file with DMA and City
        self.config_obj.write(config_section, 'dma', self.dma)
        self.config_obj.write(config_section, 'city', self.city)

    def set_location(self, geoloc):
        self.latitude = str(geoloc['latitude'])
        self.longitude = str(geoloc['longitude'])
        self.dma = str(geoloc['DMA'])
        self.active = geoloc['active']
        self.city = str(geoloc['name'])

    def find_location(self):
        """
        Note, lat/long is of the location given to the service, not the lat/lon
        of the DMA

        Ways to get location:
        1) https://api.locastnet.org/api/watch/dma/ip directly from locast
        2) http://ip-api.com/json gives zipcode, lat/lon and ip
        3) validation response provides the DMA last used
        4) https://api.locastnet.org/api/watch/dma/zip/{} gets DMA for a zipcode
        5) https://api.locastnet.org/api/watch/dma/{}/{} gets DMA for a lat/lon
        6) https://ipinfo.io/ip gets the external ip address
        Note it is possible that the ISP used is far enough away that it may not realize your area
        Best alternate is to use the zip code
        """
        zip_format = re.compile(r'^[0-9]{5}$')
        if self.latitude and self.longitude:
            location_type = "LAT/LONG"
            geo_data = self.get_coord_location()
        elif self.zipcode and zip_format.match(self.zipcode):
            location_type = "ZIP CODE"
            geo_data = self.get_zip_location()
        else:
            location_type = "IP ADDRESS"
            geo_data = self.get_ip_location()
        if not geo_data:
            self.logger.error("Unable to retrieve DMA location by %s." % location_type)
            return False
        self.set_location(geo_data)
        return True

    @handle_json_except
    @handle_url_except
    def get_url_json(self, loc_url):
        loc_headers = {'Content-Type': 'application/json', 'User-agent': constants.DEFAULT_USER_AGENT}
        loc_req = urllib.request.Request(loc_url, headers=loc_headers)
        with urllib.request.urlopen(loc_req) as resp:
            loc_rsp = json.load(resp)
        return loc_rsp

    def get_zip_location(self):
        self.logger.debug("Getting location via provided zipcode {}".format(self.zipcode))
        loc_url = 'https://api.locastnet.org/api/watch/dma/zip/{}'.format(self.zipcode)
        return self.get_url_json(loc_url)

    def get_coord_location(self):
        self.logger.info(
            'Getting location via provided lat/lon coordinates: {}/{}'.format(self.latitude, self.longitude))
        loc_url = 'https://api.locastnet.org/api/watch/dma/{}/{}' \
            .format(self.latitude, self.longitude)
        return self.get_url_json(loc_url)

    def get_ip_location(self):
        self.logger.debug("Getting location via IP Address.")
        loc_url = 'https://api.locastnet.org/api/watch/dma/ip'
        return self.get_url_json(loc_url)


Location.logger = logging.getLogger(__name__)
