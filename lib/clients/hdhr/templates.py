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

hdhr_templates = {

    'jsonDiscover':
        """{{
            "FriendlyName": "{0}",
            "ModelNumber": "{1}",
            "FirmwareName": "{2}",
            "FirmwareVersion": "{3}",
            "DeviceID": "{4}",
            "TunerCount": {5},
            "BaseURL": "http://{6}{7}",
            "LineupURL": "http://{6}{7}/lineup.json"
        }}""",

    'jsonLineupStatusScanning':
        """{{
            "ScanInProgress":1,
            "Progress":{},
            "Found":{}
        }}""",

    'jsonLineupStatusIdle':
        """{
            "ScanInProgress":0,
            "ScanPossible":1,
            "Source":"Antenna",
            "SourceList":["Antenna"]
        }""",

    'xmlDevice':
        """<?xml version="1.0" encoding="utf-8"?>
        <root xmlns="urn:schemas-upnp-org:device-1-0" xmlns:dlna="urn:schemas-dlna-org:device-1-0">
            <specVersion>
                <major>1</major>
                <minor>0</minor>
            </specVersion>
            <device>
                <dlna:X_DLNADOC>DMS-1.50</dlna:X_DLNADOC>
                <deviceType>urn:schemas-upnp-org:device:MediaServer:1</deviceType>
                <friendlyName>{0} HDHomeRun</friendlyName>
                <presentationURL>/</presentationURL>
                <manufacturer>Silicondust</manufacturer>
                <manufacturerURL>{4}</manufacturerURL>
                <modelDescription>{0}</modelDescription>
                <modelName>{0}</modelName>
                <modelNumber>{1}</modelNumber>
                <modelURL>{4}</modelURL>
                <serialNumber>{2}</serialNumber>
                <UDN>uuid:{3}</UDN>
            </device>
        </root>""",

}
