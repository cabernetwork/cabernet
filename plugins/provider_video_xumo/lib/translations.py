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

xumo_base = 'gfpMXf5BjIUNkbL7yZl/kqC3XfWPybpKj83CybHFkNUPjRkIjG=='
xumo_icons = 'gfpMXf5BjIU/ybd8tqSJzbCQjZlQyqUN5qU6gxdFyZrEXIU6gxdFyZrEjRPUjKhL58eC542FXxS8uRpSXxhUkNUEyRi1yNSwyxd6gG=='
xumo_channel = 'kN33yZS7yf5QkN33yZS7ywUT1qUYXZU3txl3XRnFg8lQy6U+yRrIusPU'
xumo_channels = 'kN33yZS7yf5Qyx7KzwUT1qSAXNUF'
xumo_program = ''.join(['kslKtspKjNdKXNrMjRPUjZ/KyNJVt6CMgspEtqtZusaIyRt/txrIXItZ',
                        'ubp7XNlIgsaMgbUFXItZusiCy8p/ybhZt6C3zZd/yxdYyxr4gbS6tn=='])

xumo_groups = {
    'Action & Drama': groups['DRAMA'],
    'Black Voices. Black Stories.': groups['ENTERTAINMENT'],
    'Classic TV': groups['CLASSICS'],
    'Combat Sports': groups['SPORTS'],
    'Comedy': groups['COMEDY'],
    'Crime TV': groups['MYSTERY'],
    'Entertainment': groups['ENTERTAINMENT'],
    'Faith & Family': groups['RELIGION'],
    'Food': groups['LIFESTYLE'],
    'Food, Drink & Travel': groups['TRAVEL'],
    'Game Shows': groups['GAMING'],
    'Kids & Family': groups['KIDS'],
    'Halloween HQ': groups['HOLIDAY'],
    'History & Learning': groups['DOCUMENTARIES'],
    'Holiday': groups['HOLIDAY'],
    'Holiday Hub': groups['HOLIDAY'],
    'Home & Design': groups['DIY'],
    'Horror & Sci-Fi': groups['MYSTERY'],
    'International': groups['INTERNATIONAL'],
    'Kids': groups['KIDS'],
    'Latino': groups['SPANISH'],
    'Latinx': groups['SPANISH'],
    'Latinx Heritage Month': groups['SPANISH'],
    'Lifestyle': groups['LIFESTYLE'],
    'Local News': groups['LOCAL'],
    'Movies': groups['MOVIES'],
    'Music': groups['MUSIC'],
    'Music & Radio': groups['MUSIC'],
    'Nature & Wildlife TV': groups['DOCUMENTARIES'],
    'News': groups['NEWS'],
    'Reality TV': groups['REALITY'],
    'Pop Culture': groups['ENTERTAINMENT'],
    'Science & Tech': groups['SCIENCE'],
    'Sports': groups['SPORTS'],
    'Travel & Lifestyle': groups['TRAVEL'],
    'TV & Movies': groups['MOVIES'],
    'Weather': groups['NEWS'],
    'Westerns & Country': groups['WESTERNS']
}

xumo_tv_genres = {
    "Classics": [tvh_genres['MOVIE']],
    "Comedy": [tvh_genres['COMEDY']],
    "DIY": [tvh_genres['HANDICRAFT']],
    "Documentaries": [tvh_genres['DOCUMENTARY']],
    "Drama": [tvh_genres['MOVIE']],
    "Entertainment": [tvh_genres['GAME']],
    "Gaming": [tvh_genres['SPORT']],
    "Holiday": [tvh_genres['SPIRITUAL']],
    "International": [tvh_genres['FOREIGN']],
    "Kids": [tvh_genres['KIDS']],
    "Lifestyle": [tvh_genres['CULTURE']],
    "Local": [tvh_genres['NEWS']],
    "Movies": [tvh_genres['MOVIE']],
    "Music": [tvh_genres['MUSIC']],
    "Mystery": [tvh_genres['MOVIE']],
    "News": [tvh_genres['NEWS']],
    "Reality": [tvh_genres['GAME']],
    "Religion": [tvh_genres['RELIGION']],
    "Science": [tvh_genres['SCIENCE']],
    "Spanish": [tvh_genres['LANGUAGES']],
    "Sports": [tvh_genres['SPORT']],
    "Travel": [tvh_genres['TRAVEL']],
    "Westerns": [tvh_genres['ADVENTURE']]
}
