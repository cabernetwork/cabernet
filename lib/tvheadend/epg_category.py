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

# KODI COLOR MAPPINGS
# 0 Other/Unknown Grey
# 16 Movie Orange
# 32 News Light Green
# 48 TV Show Yellow
# 64 Sports Red
# 80 Child Cyan
# 96 Music Green
# 112 Arts Blue
# 128 Social Light Grey
# 144 Science Purple
# 160 Hobby Light Purple
# 176 Special Light Blue
# 192 Other/Unknown Grey
# 208 Other/Unknown Grey
# 224 Other/Unknown Grey
# 240 Other/Unknown Grey

groups = {
    'COMEDY': 'Comedy',
    'CRIME': 'Crime',
    'CLASSICS': 'Classics',
    'DIY': 'DIY',
    'DOCUMENTARIES': 'Documentaries',
    'ENTERTAINMENT': 'Entertainment',
    'GAMING': 'Gaming',
    'HOLIDAY': 'Holiday',
    'INTERNATIONAL': 'International',
    'KIDS': 'Kids',
    'LIFESTYLE': 'Lifestyle',
    'LOCAL': 'Local',
    'MOVIES': 'Movies',
    'MUSIC': 'Music',
    'MYSTERY': 'Mystery',
    'NEW': 'New',
    'NEWS': 'News',
    'REALITY': 'Reality',
    'RELIGION': 'Religion',
    'SCIENCE': 'Science',
    'SCIFI': 'Sci-Fi',
    'SPANISH': 'Spanish',
    'SPORTS': 'Sports',
    'TRAVEL': 'Travel'
    }

# TVHEADEND CATEGORIES
tvh_genres = {
    'MOVIE':             'Movie / Drama',
    'THRILLER':          'Detective / Thriller',
    'ADVENTURE':         'Adventure / Western / War',
    'SF':                'Science fiction / Fantasy / Horror',
    'COMEDY':            'Comedy',
    'SOAP':              'Soap / Melodrama / Folkloric',
    'ROMANCE':           'Romance',
    'HISTORICAL':        'Serious / Classical / Religious ' \
        '/ Historical movie / Drama',
    'XXX':               'Adult movie / Drama',

    'NEWS':              'News / Current affairs',
    'WEATHER':           'News / Weather report',
    'NEWS_MAGAZINE':     'News magazine',
    'DOCUMENTARY':       'Documentary',
    'DEBATE':            'Discussion / Interview / Debate',
    'INTERVIEW':         'Discussion / Interview / Debate',

    'SHOW':              'Show / Game show',
    'GAME':              'Game show / Quiz / Contest',
    'VARIETY':           'Variety show',
    'TALK_SHOW':         'Talk show',

    'SPORT':             'Sports',
    'SPORT_SPECIAL':     'Special events (Olympic Games; World Cup; etc.)',
    'SPORT_MAGAZINE':    'Sports magazines',
    'FOOTBALL':          'Football / Soccer',
    'TENNIS':            'Tennis / Squash',
    'SPORT_TEAM':        'Team sports (excluding football)',
    'ATHLETICS':         'Athletics',
    'SPORT_MOTOR':       'Motor sport',
    'SPORT_WATER':       'Water sport',
    'SPORT_WINTER':      'Winter sports',
    'SPORT_HORSES':      'Equestrian',
    'MARTIAL_ARTS':      'Martial sports',

    'KIDS':              "Children's / Youth programs",
    'KIDS_0_5':          "Pre-school children's programs",
    'KIDS_6_14':         'Entertainment programs for 6 to 14',
    'KIDS_10_16':        'Entertainment programs for 10 to 16',
    'EDUCATIONAL':       'Informational / Educational / School programs',
    'CARTOON':           'Cartoons / Puppets',

    'MUSIC':             'Music / Ballet / Dance',
    'ROCK_POP':          'Rock / Pop',
    'CLASSICAL':         'Serious music / Classical music',
    'FOLK':              'Folk / Traditional music',
    'JAZZ':              'Jazz',
    'OPERA':             'Musical / Opera',
    'BALLET':            'Ballet',

    'CULTURE':           'Arts / Culture (without music)',
    'PERFORMING':        'Performing arts',
    'FINE_ARTS':         'Fine arts',
    'RELIGION':          'Religion',
    'POPULAR_ART':       'Popular culture / Traditional arts',
    'LITERATURE':        'Literature',
    'FILM':              'Film / Cinema',
    'EXPERIMENTAL_FILM': 'Experimental film / Video',
    'BROADCASTING':      'Broadcasting / Press',
    'NEW_MEDIA':         'New media',
    'ARTS_MAGAZINE':     'Arts magazines / Culture magazines',
    'FASHION':           'Fashion',

    'SOCIAL':            'Social / Political issues / Economics',
    'MAGAZINE':          'Magazines / Reports / Documentary',
    'ECONOMIC':          'Economics / Social advisory',
    'VIP':               'Remarkable people',

    'SCIENCE':           'Education / Science / Factual topics',
    'NATURE':            'Nature / Animals / Environment',
    'TECHNOLOGY':        'Technology / Natural sciences',
    'DIOLOGY':           'Technology / Natural sciences',
    'MEDICINE':          'Medicine / Physiology / Psychology',
    'FOREIGN':           'Foreign countries / Expeditions',
    'SPIRITUAL':         'Social / Spiritual sciences',
    'FURTHER_EDUCATION': 'Further education',
    'LANGUAGES':         'Languages',

    'HOBBIES':           'Leisure hobbies',
    'TRAVEL':            'Tourism / Travel',
    'HANDICRAFT':        'Handicraft',
    'MOTORING':          'Motoring',
    'FITNESS':           'Fitness and health',
    'COOKING':           'Cooking',
    'SHOPPING':          'Advertisement / Shopping',
    'GARDENING':         'Gardening'
    }

# Normal GENRES to TVHEADEND translation
TVHEADEND = {
    'Action'                : tvh_genres['THRILLER'],
    'Action sports'         : tvh_genres['SPORT'],
    'Adventure'             : tvh_genres['ADVENTURE'],
    'Agriculture'           : tvh_genres['NATURE'],
    'Animals'               : tvh_genres['NATURE'],
    'Anthology'             : tvh_genres['FILM'],
    'Art'                   : tvh_genres['CULTURE'],
    'Baseball'              : tvh_genres['SPORT_TEAM'],
    'Basketball'            : tvh_genres['SPORT_TEAM'],
    'Biography'             : tvh_genres['VIP'],
    'Boxing'                : tvh_genres['SPORT'],
    'Cartoon'               : tvh_genres['CARTOON'],
    'Children'              : tvh_genres['KIDS'],
    'Classic Sport Event'   : tvh_genres['SPORT_SPECIAL'],
    'Comedy'                : tvh_genres['COMEDY'],
    'Comedy drama'          : tvh_genres['COMEDY'],
    'Community'             : tvh_genres['SOCIAL'],
    'Consumer'              : tvh_genres['SHOPPING'],
    'Cooking'               : tvh_genres['COOKING'],
    'Crime'                 : tvh_genres['THRILLER'],
    'Crime drama'           : tvh_genres['THRILLER'],
    'Docudrama'             : tvh_genres['DOCUMENTARY'],
    'Documentary'           : tvh_genres['DOCUMENTARY'],
    'Drama'                 : tvh_genres['MOVIE'],
    'Educational'           : tvh_genres['EDUCATIONAL'],
    'Entertainment'         : tvh_genres['GAME'],
    'Exercise'              : tvh_genres['FITNESS'],
    # 'Fantasy'              :
    'financial'             : tvh_genres['ECONOMIC'],
    'Football'              : tvh_genres['FOOTBALL'],
    'Game show'             : tvh_genres['GAME'],
    'Golf'                  : tvh_genres['SPORT_TEAM'],
    'Health'                : tvh_genres['MEDICINE'],
    'Historical drama'      : tvh_genres['HISTORICAL'],
    'Hockey'                : tvh_genres['SPORT_TEAM'],
    'Home improvement'      : tvh_genres['HANDICRAFT'],
    'Horror'                : tvh_genres['SF'],
    'House/garden'          : tvh_genres['GARDENING'],
    'How-to'                : tvh_genres['SCIENCE'],
    'Interview'             : tvh_genres['DEBATE'],
    'Law'                   : tvh_genres['SOCIAL'],
    'Medical'               : tvh_genres['MEDICINE'],
    'Mixed martial arts'    : tvh_genres['MARTIAL_ARTS'],
    'Music'                 : tvh_genres['MUSIC'],
    'Musical'               : tvh_genres['MUSIC'],
    'Musical comedy'        : tvh_genres['COMEDY'],
    'Mystery'               : tvh_genres['THRILLER'],
    'News'                  : tvh_genres['NEWS'],
    'Newsmagazine'          : tvh_genres['NEWS_MAGAZINE'],
    'Olympics'              : tvh_genres['SPORT'],
    'Outdoors'              : tvh_genres['SPORT'],
    'Poker'                 : tvh_genres['GAME'],
    'Pro wrestling'         : tvh_genres['MARTIAL_ARTS'],
    'Public affairs'        : tvh_genres['BROADCASTING'],
    'Reality'               : tvh_genres['GAME'],
    'Religious'             : tvh_genres['RELIGION'],
    'Romance'               : tvh_genres['ROMANCE'],
    'Romantic comedy'       : tvh_genres['ROMANCE'],
    'Science'               : tvh_genres['SCIENCE'],
    'Science fiction'       : tvh_genres['SF'],
    'Self improvement'      : tvh_genres['FURTHER_EDUCATION'],
    'Shopping'              : tvh_genres['SHOPPING'],
    'Sitcom'                : tvh_genres['COMEDY'],
    'Soap'                  : tvh_genres['SOAP'],
    'Soccer'                : tvh_genres['FOOTBALL'],
    # 'Special'             :
    'Sports talk'           : tvh_genres['SPORT'],
    'Talk'                  : tvh_genres['TALK_SHOW'],
    'Thriller'              : tvh_genres['THRILLER'],
    'Travel'                : tvh_genres['TRAVEL'],
    'Variety'               : tvh_genres['VARIETY'],
    'Weightlifting'         : tvh_genres['ATHLETICS'],
    'Western'               : tvh_genres['ADVENTURE']
}
