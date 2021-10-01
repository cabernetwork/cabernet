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

from lib.common.decorators import getrequest


@getrequest.route('/')
def root_url(_webserver):
    _webserver.send_response(302)
    _webserver.send_header('Location', 'html/index.html')
    _webserver.end_headers()


@getrequest.route('/favicon.ico')
def favicon(_webserver):
    _webserver.send_response(302)
    _webserver.send_header('Location', 'images/favicon.png')
    _webserver.end_headers()
