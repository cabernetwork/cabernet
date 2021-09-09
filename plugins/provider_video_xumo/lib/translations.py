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

xumo_groups = {
    'Comedy':               groups['COMEDY'],
    'Entertainment':        groups['ENTERTAINMENT'],
    'Food, Drink & Travel': groups['TRAVEL'],
    'Kids & Family':        groups['KIDS'],
    'Latinx':               groups['SPANISH'],
    'Lifestyle':            groups['LIFESTYLE'],
    'Music':                groups['MUSIC'],
    'News':                 groups['NEWS'],
    'Pop Culture':          groups['ENTERTAINMENT'],
    'Science & Tech':       groups['SCIENCE'],
    'Sports':               groups['SPORTS'],
    'TV & Movies':          groups['MOVIES']
    }

xumo_tv_genres = {
    "Comedy": [ tvh_genres['COMEDY'] ],
    "Entertainment": [ tvh_genres['GAME'] ],
    "Kids": [ tvh_genres['KIDS'] ],
    "Lifestyle": [ tvh_genres['CULTURE'] ],
    "Movies": [ tvh_genres['MOVIE'] ],
    "Music": [ tvh_genres['MUSIC'] ],
    "News": [ tvh_genres['NEWS'] ],
    "Science": [ tvh_genres['SCIENCE'] ],
    "Spanish": [ tvh_genres['LANGUAGES'] ],
    "Sports": [ tvh_genres['SPORT'] ],
    "Travel": [ tvh_genres['TRAVEL'] ],
    }