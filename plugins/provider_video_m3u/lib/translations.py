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

pluto_base = 'gfpMXf5BjIU3XxoFXxLCzxHFzfkQz62QkN33yZS7yf5='

plutotv_groups = {
    'Classic TV': groups['CLASSICS'],
    'Comedy': groups['COMEDY'],
    'Crime': groups['MYSTERY'],
    'Curiosity': groups['DOCUMENTARIES'],
    'Drama': groups['MYSTERY'],
    'En Español': groups['SPANISH'],
    'Entertainment': groups['ENTERTAINMENT'],
    'Explore': groups['DOCUMENTARIES'],
    'Gaming + Anime': groups['GAMING'],
    'Home + DIY': groups['DIY'],
    'Kids': groups['KIDS'],
    'Local': groups['NEWS'],
    'Life + Style': groups['LIFESTYLE'],
    'Motor': groups['SPORTS'],
    'Movies': groups['MOVIES'],
    'Music': groups['MUSIC'],
    'New on Pluto TV': groups['NEW'],
    'News + Opinion': groups['NEWS'],
    'News + Info': groups['NEWS'],
    'Paranormal': groups['MYSTERY'],
    'Pluto TV': groups['CLASSICS'],
    'Reality': groups['REALITY'],
    'Samsung': groups['SPORTS'],
    'Sports': groups['SPORTS'],
    'Sports & Gaming': groups['SPORTS'],
    'Vizio': groups['MOVIES']
}

plutotv_tv_genres = {
    "Action & Adventure": [tvh_genres['ADVENTURE']],
    "Anime": [tvh_genres['CARTOON']],
    "Children & Family": [tvh_genres['KIDS']],
    "Classics": [tvh_genres['MOVIE']],
    "Comedy": [tvh_genres['COMEDY']],
    "Documentaries": [tvh_genres['DOCUMENTARY']],
    "Drama": [tvh_genres['MOVIE']],
    "Faith and Spirituality": [tvh_genres['RELIGION']],
    "Horror": [tvh_genres['SF']],
    "Independent": [tvh_genres['NEWS_MAGAZINE']],
    "Instructional & Educational": [tvh_genres['EDUCATIONAL']],
    "Music": [tvh_genres['MUSIC']],
    "Musicals": [tvh_genres['MUSIC']],
    "News and Information": [tvh_genres['NEWS']],
    "Reality": [tvh_genres['GAME']],
    "Romance": [tvh_genres['ROMANCE']],
    "Sci-Fi & Fantasy": [tvh_genres['SF']],
    "Thrillers": [tvh_genres['THRILLER']],
    "No information available": None,
    "Other": None,
    "Gay & Lesbian": None
}
