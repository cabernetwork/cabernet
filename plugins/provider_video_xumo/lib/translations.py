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

xumo_base = 'gfpMXf5BjIUNkbL7yZl/kqC3XfWPybpKj83CybHFkNUPjRkIjG=='
xumo_icons = 'gfpMXf5BjIU/ybd8tqSJzbCQjZlQyqUN5qU6gxdFyZrEXIU6gxdFyZrEjRPUjKhL58eC542FXxS8uRpSXxhUkNUEyRi1yNSwyxd6gG=='
xumo_channel = 'kN33yZS7yf5QkN33yZS7ywUT1qUYXZU3txl3XRnFg8lQy6U+yRrIusPU'
xumo_channels = 'kN33yZS7yf5Qyx7KzwUT1qSAXNUFuNz7yM7ousPU'
xumo_program = 'kslKtspKjNdKXNrMjRPUjZ/KyNJVt6CMgspEtqtZusaIyRt/txrIXItZubp7XNlIgsaMgbUFXItZusiCy8p/ybhZt6C3zZd/yxdYyxr4gbS6tn=='

xumo_groups = {
    'Comedy':               groups['COMEDY'],
    'Entertainment':        groups['ENTERTAINMENT'],
    'Food, Drink & Travel': groups['TRAVEL'],
    'Kids & Family':        groups['KIDS'],
    'Halloween HQ':         groups['HOLIDAY'],
    'Holiday':              groups['HOLIDAY'],
    'Holiday Hub':          groups['HOLIDAY'],
    'Latino':               groups['SPANISH'],
    'Latinx':               groups['SPANISH'],
    'Latinx Heritage Month': groups['SPANISH'],
    'Lifestyle':            groups['LIFESTYLE'],
    'Local News':           groups['LOCAL'],
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
    "Holiday": [ tvh_genres['SPIRITUAL'] ],
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