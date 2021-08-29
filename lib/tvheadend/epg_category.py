# pylama:ignore=E203,E221
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

# TVHEADEND CATEGORIES
MOVIE             = 'Movie / Drama'
THRILLER          = 'Detective / Thriller'
ADVENTURE         = 'Adventure / Western / War'
SF                = 'Science fiction / Fantasy / Horror'
COMEDY            = 'Comedy'
SOAP              = 'Soap / Melodrama / Folkloric'
ROMANCE           = 'Romance'
HISTORICAL        = 'Serious / Classical / Religious ' \
                    '/ Historical movie / Drama'
XXX               = 'Adult movie / Drama'

NEWS              = 'News / Current affairs'
WEATHER           = 'News / Weather report'
NEWS_MAGAZINE     = 'News magazine'
DOCUMENTARY       = 'Documentary'
DEBATE            = 'Discussion / Interview / Debate'
INTERVIEW         = 'Discussion / Interview / Debate'

SHOW              = 'Show / Game show'
GAME              = 'Game show / Quiz / Contest'
VARIETY           = 'Variety show'
TALK_SHOW         = 'Talk show'

SPORT             = 'Sports'
SPORT_SPECIAL     = 'Special events (Olympic Games; World Cup; etc.)'
SPORT_MAGAZINE    = 'Sports magazines'
FOOTBALL          = 'Football / Soccer'
TENNIS            = 'Tennis / Squash'
SPORT_TEAM        = 'Team sports (excluding football)'
ATHLETICS         = 'Athletics'
SPORT_MOTOR       = 'Motor sport'
SPORT_WATER       = 'Water sport'
SPORT_WINTER      = 'Winter sports'
SPORT_HORSES      = 'Equestrian'
MARTIAL_ARTS      = 'Martial sports'

KIDS              = "Children's / Youth programs"
KIDS_0_5          = "Pre-school children's programs"
KIDS_6_14         = 'Entertainment programs for 6 to 14'
KIDS_10_16        = 'Entertainment programs for 10 to 16'
EDUCATIONAL       = 'Informational / Educational / School programs'
CARTOON           = 'Cartoons / Puppets'

MUSIC             = 'Music / Ballet / Dance'
ROCK_POP          = 'Rock / Pop'
CLASSICAL         = 'Serious music / Classical music'
FOLK              = 'Folk / Traditional music'
JAZZ              = 'Jazz'
OPERA             = 'Musical / Opera'
BALLET            = 'Ballet'

CULTURE           = 'Arts / Culture (without music)'
PERFORMING        = 'Performing arts'
FINE_ARTS         = 'Fine arts'
RELIGION          = 'Religion'
POPULAR_ART       = 'Popular culture / Traditional arts'
LITERATURE        = 'Literature'
FILM              = 'Film / Cinema'
EXPERIMENTAL_FILM = 'Experimental film / Video'
BROADCASTING      = 'Broadcasting / Press'
NEW_MEDIA         = 'New media'
ARTS_MAGAZINE     = 'Arts magazines / Culture magazines'
FASHION           = 'Fashion'

SOCIAL            = 'Social / Political issues / Economics'
MAGAZINE          = 'Magazines / Reports / Documentary'
ECONOMIC          = 'Economics / Social advisory'
VIP               = 'Remarkable people'

SCIENCE           = 'Education / Science / Factual topics'
NATURE            = 'Nature / Animals / Environment'
TECHNOLOGY        = 'Technology / Natural sciences'
DIOLOGY           = 'Technology / Natural sciences'
MEDICINE          = 'Medicine / Physiology / Psychology'
FOREIGN           = 'Foreign countries / Expeditions'
SPIRITUAL         = 'Social / Spiritual sciences'
FURTHER_EDUCATION = 'Further education'
LANGUAGES         = 'Languages'

HOBBIES           = 'Leisure hobbies'
TRAVEL            = 'Tourism / Travel'
HANDICRAFT        = 'Handicraft'
MOTORING          = 'Motoring'
FITNESS           = 'Fitness and health'
COOKING           = 'Cooking'
SHOPPING          = 'Advertisement / Shopping'
GARDENING         = 'Gardening'

# LOCAST to TVHEADEND translation
TVHEADEND = {
    'Action'                : THRILLER,
    'Action sports'         : SPORT,
    'Adventure'             : ADVENTURE,
    'Agriculture'           : NATURE,
    'Animals'               : NATURE,
    'Anthology'             : FILM,
    'Art'                   : CULTURE,
    'Baseball'              : SPORT_TEAM,
    'Basketball'            : SPORT_TEAM,
    'Biography'             : VIP,
    'Boxing'                : SPORT,
    'Cartoon'               : CARTOON,
    'Children'              : KIDS,
    'Classic Sport Event'   : SPORT_SPECIAL,
    'Comedy'                : COMEDY,
    'Comedy drama'          : COMEDY,
    'Community'             : SOCIAL,
    'Consumer'              : SHOPPING,
    'Cooking'               : COOKING,
    'Crime'                 : THRILLER,
    'Crime drama'           : THRILLER,
    'Docudrama'             : DOCUMENTARY,
    'Documentary'           : DOCUMENTARY,
    'Drama'                 : MOVIE,
    'Educational'           : EDUCATIONAL,
    'Entertainment'         : GAME,
    'Exercise'              : FITNESS,
    # 'Fantasy'              :
    'financial'             : ECONOMIC,
    'Football'              : FOOTBALL,
    'Game show'             : GAME,
    'Golf'                  : SPORT_TEAM,
    'Health'                : MEDICINE,
    'Historical drama'      : HISTORICAL,
    'Hockey'                : SPORT_TEAM,
    'Home improvement'      : SCIENCE,
    'Horror'                : SF,
    'House/garden'          : GARDENING,
    'How-to'                : SCIENCE,
    'Interview'             : DEBATE,
    'Law'                   : SOCIAL,
    'Medical'               : MEDICINE,
    'Mixed martial arts'    : MARTIAL_ARTS,
    'Music'                 : MUSIC,
    'Musical'               : MUSIC,
    'Musical comedy'        : COMEDY,
    'Mystery'               : THRILLER,
    'News'                  : NEWS,
    'Newsmagazine'          : NEWS_MAGAZINE,
    'Olympics'              : SPORT,
    'Outdoors'              : SPORT,
    'Poker'                 : GAME,
    'Pro wrestling'         : MARTIAL_ARTS,
    'Public affairs'        : BROADCASTING,
    'Reality'               : GAME,
    'Religious'             : RELIGION,
    'Romance'               : ROMANCE,
    'Romantic comedy'       : ROMANCE,
    'Science'               : SCIENCE,
    'Science fiction'       : SF,
    'Self improvement'      : FURTHER_EDUCATION,
    'Shopping'              : SHOPPING,
    'Sitcom'                : COMEDY,
    'Soap'                  : SOAP,
    'Soccer'                : FOOTBALL,
    # 'Special'             :
    'Sports talk'           : SPORT,
    'Talk'                  : TALK_SHOW,
    'Thriller'              : THRILLER,
    'Travel'                : TRAVEL,
    'Variety'               : VARIETY,
    'Weightlifting'         : ATHLETICS,
    'Western'               : ADVENTURE,
}
