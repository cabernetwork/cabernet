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
    'Action Sports & Outdoors':  groups['SPORTS'],
    'Amped Up Action':           groups['REALITY'],
    'Black History Month':       groups['DOCUMENTARIES'],
    'Classic TV':                groups['CLASSICS'],
    'Combat Sports':             groups['SPORTS'],
    'Comedy':                    groups['COMEDY'],
    'Comedy & Drama TV':         groups['COMEDY'],
    'Crime TV':                  groups['CRIME'],
    'Documentaries':             groups['DOCUMENTARIES'],
    'Entertainment':             groups['ENTERTAINMENT'],
    'Faith & Family':            groups['RELIGION'],
    'Food, Drink & Travel':      groups['TRAVEL'],
    'Food TV':                   groups['REALITY'],
    'Game Shows & Daytime TV':   groups['ENTERTAINMENT'],
    'Kids & Family':             groups['KIDS'],
    'Halloween HQ':              groups['HOLIDAY'],
    'Holiday':                   groups['HOLIDAY'],
    'Holiday Hub':               groups['HOLIDAY'],
    'Horror & Sci-Fi':           groups['SCIFI'],
    'Humor':                     groups['COMEDY'],
    'International':             groups['INTERNATIONAL'],
    'Kids':                      groups['KIDS'],
    'Latino':                    groups['SPANISH'],
    'Latinx':                    groups['SPANISH'],
    'Latinx Heritage Month':     groups['SPANISH'],
    'Lifestyle':                 groups['LIFESTYLE'],
    'Local News':                groups['LOCAL'],
    'Movies':                    groups['MOVIES'],
    'Music':                     groups['MUSIC'],
    'Music & Radio':             groups['MUSIC'],
    'Nature & Wildlife TV':      groups['SCIENCE'],
    'News':                      groups['NEWS'],
    'Pop Culture':               groups['ENTERTAINMENT'],
    'Reality TV':                groups['REALITY'],
    'Science, History & Learning':  groups['SCIENCE'],
    'Science & Tech':            groups['SCIENCE'],
    'Sports':                    groups['SPORTS'],
    'Travel & Lifestyle TV':     groups['TRAVEL'],
    'TV & Movies':               groups['MOVIES'],
    'Weather':                   groups['NEWS']
    }

xumo_tv_genres = {
    "ActionSportsOutdoors": [ tvh_genres['SPORT'] ],
    "Classics": [ tvh_genres['SHOW'] ],
    "ClassicTV": [ tvh_genres['SHOW'] ],
    "CombatSports": [ tvh_genres['SPORT'] ],
    "Comedy": [ tvh_genres['COMEDY'] ],
    "ComedyDramaTV": [ tvh_genres['COMEDY'] ],
    "Crime": [ tvh_genres['THRILLER'] ],
    "CrimeTV": [ tvh_genres['THRILLER'] ],
    "Entertainment": [ tvh_genres['GAME'] ],
    "FaithFamily": [ tvh_genres['RELIGION'] ],
    "FoodTV": [ tvh_genres['COOKING'] ],
    "GameShowsDaytimeTV": [ tvh_genres['GAME'] ],
    "Holiday": [ tvh_genres['SPIRITUAL'] ],
    "HorrorSci-Fi": [ tvh_genres['SF'] ],
    "Humor": [ tvh_genres['COMEDY'] ],
    "International": [ tvh_genres['FOREIGN'] ],
    "Kids": [ tvh_genres['KIDS'] ],
    "Lifestyle": [ tvh_genres['CULTURE'] ],
    "Local": [ tvh_genres['NEWS'] ],
    "Movies": [ tvh_genres['MOVIE'] ],
    "Music": [ tvh_genres['MUSIC'] ],
    "MusicRadio": [ tvh_genres['MUSIC'] ],
    "NatureWildlifeTV": [ tvh_genres['NATURE'] ],
    "News": [ tvh_genres['NEWS'] ],
    "Reality": [ tvh_genres['GAME'] ],
    "RealityTV": [ tvh_genres['GAME'] ],
    "Religion": [ tvh_genres['RELIGION'] ],
    "Sci-Fi": [ tvh_genres['SF'] ],
    "Science": [ tvh_genres['SCIENCE'] ],
    "ScienceHistoryLearning": [ tvh_genres['SCIENCE'] ],
    "Spanish": [ tvh_genres['LANGUAGES'] ],
    "Sports": [ tvh_genres['SPORT'] ],
    "Travel": [ tvh_genres['TRAVEL'] ],
    "TravelLifestyleTV": [ tvh_genres['TRAVEL'] ],
    "Weather": [ tvh_genres['WEATHER'] ],
    }