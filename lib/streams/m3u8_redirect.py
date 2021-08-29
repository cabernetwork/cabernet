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

from lib.web.pages.templates import web_templates
from .stream import Stream


class M3U8Redirect(Stream):

    # There is no way to know the number of stream running on a redirect.
    # They can stop anytime without notification, so tuner tracking is
    # disabled

    def gen_m3u8_response(self, _channel_dict):
        """
        Returns dict  where the dict is consistent with
        the method do_dict_response requires as an argument
        """
        channel_uri = self.get_stream_uri(_channel_dict)
        if not channel_uri:
            self.logger.warning('Unknown channel:{}'.format(_channel_dict['uid']))
            return {
                'code': 501,
                'headers': {'Content-type': 'text/html'},
                'text': web_templates['htmlError'].format('501 - Unknown channel')}

        self.logger.info('Sending M3U8 file directly to client')
        return {
            'code': 302,
            'headers': {'Location': channel_uri},
            'text': None}
