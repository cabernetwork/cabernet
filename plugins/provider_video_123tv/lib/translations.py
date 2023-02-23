# pylama:ignore=E203,E221
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

from lib.tvheadend.epg_category import groups
from lib.tvheadend.epg_category import tvh_genres

tv123_base = 'gfpMXf5BjIHL56lMzYSEgst7'
tv123_additional_channels = 'jRzGjbdoyb7FjNdoyb7FjbdAkseFXx3G'
tv123_wp_more_ch_cmd = 'sK9I5RpNsNLQkbp1ybUItrUNgbp7yRl1t8iQyrU6gxdFyZrE'
tv123_stream_channel = 'jRz3zxl+jRPU'
tv123_referer = 'gfpMXf5BjIU8tsnF542KzfkFyx7NtqH='
tv123_ch_epg = 'jNrGtIUAXNUFjRPUjZ/KyNJ='
tv123_agpigee_referer = 'gfpMXf5BjIU8yNU8yxhFkNUP'
tv123_prog_details = 'gfpMXf5BjIU6ybXPXfiQtwS3Xx78tbhFyZrMjRkLjR33XxoQzftKkN37tfrEts5Qzft8zb7otqUGXZU8XZdPtxrMkb7EXIUT1qURtb2='
tv123_image = 'gfpMXf5BjIURzRXFzft8zb7otqS6yNMQkqU/ybXQkNdMkbLQtG=='


tv_genres = {
    "Action & Adventure": [ tvh_genres['THRILLER'] ],
    "Comedy": [ tvh_genres['COMEDY'] ],
    "Documentary": [ tvh_genres['DOCUMENTARY'] ],
    "Drama": [ tvh_genres['MOVIE'] ],
    "Family": [ tvh_genres['KIDS_6_14'] ],
    "Fantasy": [ tvh_genres['SF'] ],
    "Game Show": [ tvh_genres['GAME'] ],
    "Horror": [ tvh_genres['SF'] ],
    "Music": [ tvh_genres['MUSIC'] ],
    "Business": [ tvh_genres['NEWS'] ],
    "Other": None,
    "Pro Sports": [ tvh_genres['SPORT'] ],
    "Reality": [ tvh_genres['GAME'] ],
    "Science": [ tvh_genres['SCIENCE'] ],
    "Science Fiction": [ tvh_genres['SF'] ],
    "Suspense": [ tvh_genres['THRILLER'] ],
    "Talk & Interview": [ tvh_genres['TALK_SHOW'] ],
    "Travel" : [ tvh_genres['TRAVEL'] ]
    
 }