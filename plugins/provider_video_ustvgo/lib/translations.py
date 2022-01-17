# pylama:ignore=E203,E221
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

from lib.tvheadend.epg_category import groups
from lib.tvheadend.epg_category import tvh_genres


ustvgo_channels = 'gfpMXf5BjIUCXRpNtNHFzfkQzft8zb7otqUFksp/yNS3ywSAXNUF'
ustvgo_png = 'gfpMXf5BjIUKzxdMgb5FXRpItbdPyx7NtqSMyIU/ybd8ts5QzfkQis5FXxS8'
ustvgo_stream = 'gfpMXf5BjIUCXRpNtNHFzfkQXxL30brIj8a+XcUKzfi7kbMUis5='
ustvgo_epg = 'gfpMXf5BjIUCXRpNtNHFzfkQzft8zb7otqUvhMUm5YH7XISAXNUFuIrK'
ustvgo_program = 'gfpMXf5BjIU6ybXPXfiQtwS3Xx78tbhFyZrMjRkLjR33XxoQzftKkN37tfrEts5Qzft8zb7otqUGXZU8XZdPtxrMkb7EXIH7XIURtb2='

ustvgo_groups = {
    }

ustvgo_genres = {
    "Action & Adventure": [ tvh_genres['ADVENTURE'] ],
    "Arts": [ tvh_genres['CULTURE'] ],
    "Business": [ tvh_genres['NEWS'] ],
    "Comedy": [ tvh_genres['COMEDY'] ],
    "Documentary": [ tvh_genres['DOCUMENTARY'] ],
    "Drama": [ tvh_genres['MOVIE'] ],
    "Educational": [ tvh_genres['EDUCATIONAL'] ],
    "Events & Specials": [ tvh_genres['SPORT_SPECIAL'] ],
    "Family": [ tvh_genres['KIDS'] ],
    "Fantasy": [ tvh_genres['SF'] ],
    "Food & Cooking": [ tvh_genres['COOKING'] ],
    "Game Show": [ tvh_genres['GAME'] ],
    "Health & Lifestyle": [ tvh_genres['FITNESS'] ],
    "Horror": [ tvh_genres['SF'] ],
    "Kids": [ tvh_genres['KIDS'] ],
    "Music": [ tvh_genres['MUSIC'] ],
    "None": None,
    "Other": None,
    "Pro Sports": [ tvh_genres['SPORT'] ],
    "Reality": [ tvh_genres['GAME'] ],
    "Science": [ tvh_genres['SCIENCE'] ],
    "Science Fiction": [ tvh_genres['SF'] ],
    "Sports": [ tvh_genres['SPORT'] ],
    "Suspense": [ tvh_genres['SF'] ],
    "Talk & Interview": [ tvh_genres['TALK_SHOW'] ],
    "Tech & Gaming": [ tvh_genres['TECHNOLOGY'] ],
    "Travel": [ tvh_genres['TRAVEL'] ],
    "Variety Shows": [ tvh_genres['VARIETY'] ]
    }
