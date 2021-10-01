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

import importlib
import importlib.resources
import mimetypes
import random
import pathlib

from lib.web.pages.templates import web_templates
from lib.common.decorators import getrequest


@getrequest.route('/background')
def background(_webserver):
    send_random_image(_webserver)


def send_random_image(_webserver):
    if not _webserver.config['display']['backgrounds']:
        background_dir = _webserver.config['paths']['themes_pkg'] + '.' + \
                         _webserver.config['display']['theme']
        image_list = list(importlib.resources.contents(background_dir))
        image_found = False
        count = 10
        image = None
        while not image_found and count > 0:
            image = random.choice(image_list)
            mime_lookup = mimetypes.guess_type(image)
            if mime_lookup[0] is not None and \
                    mime_lookup[0].startswith('image'):
                image_found = True
            count -= 1
        if image_found:
            _webserver.do_file_response(200, background_dir, image)
        else:
            _webserver.logger.warning('No Background Image found: ' + background_dir)
            _webserver.do_mime_response(404, 'text/html', web_templates['htmlError']
                .format('404 - Background Image Not Found'))
    else:
        lbackground = _webserver.config['display']['backgrounds']
        try:
            image_found = False
            count = 10
            full_image_path = None
            while not image_found and count > 0:
                image = random.choice(list(pathlib.Path(lbackground).rglob('*.*')))
                full_image_path = pathlib.Path(lbackground).joinpath(image)
                mime_lookup = mimetypes.guess_type(str(full_image_path))
                if mime_lookup[0] is not None and mime_lookup[0].startswith('image'):
                    image_found = True
                count -= 1
            if image_found:
                _webserver.do_file_response(200, None, full_image_path)
                _webserver.logger.debug('Background Image: {}'.format(str(image).replace(lbackground,'.')))
            else:
                _webserver.logger.warning('Image not found at {}'.format(lbackground))
                _webserver.do_mime_response(404, 'text/html',
                    web_templates['htmlError'].format('404 - Background Image Not Found'))

        except (FileNotFoundError, IndexError):
            _webserver.logger.warning('Background Theme Folder not found: ' + lbackground)
            _webserver.do_mime_response(404, 'text/html', web_templates['htmlError']
                .format('404 - Background Folder Not Found'))
