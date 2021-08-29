# coding: utf-8
# Copyright 2014 Globo.com Player authors. All rights reserved.
# Use of this source code is governed by a MIT License
# license that can be found in the LICENSE file.

import sys
import ssl
import os
import posixpath
import urllib

from lib.m3u8.model import (M3U8, Segment, SegmentList, PartialSegment,
                        PartialSegmentList, Key, Playlist, IFramePlaylist,
                        Media, MediaList, PlaylistList, Start,
                        RenditionReport, RenditionReportList, ServerControl,
                        Skip, PartInformation)
from lib.m3u8.parser import parse, is_url, ParseError

__all__ = ('M3U8', 'Segment', 'SegmentList', 'PartialSegment',
           'PartialSegmentList', 'Key', 'Playlist', 'IFramePlaylist',
           'Media', 'MediaList', 'PlaylistList', 'Start', 'RenditionReport',
           'RenditionReportList', 'ServerControl', 'Skip', 'PartInformation',
           'loads', 'load', 'parse', 'ParseError')


def loads(content, uri=None, custom_tags_parser=None):
    '''
    Given a string with a m3u8 content, returns a M3U8 object.
    Optionally parses a uri to set a correct base_uri on the M3U8 object.
    Raises ValueError if invalid content
    '''

    if uri is None:
        return M3U8(content, custom_tags_parser=custom_tags_parser)
    else:
        base_uri = _parsed_url(uri)
        return M3U8(content, base_uri=base_uri, custom_tags_parser=custom_tags_parser)


def load(uri, timeout=None, headers={}, custom_tags_parser=None, verify_ssl=True):
    '''
    Retrieves the content from a given URI and returns a M3U8 object.
    Raises ValueError if invalid content or IOError if request fails.
    '''
    if is_url(uri):
        return _load_from_uri(uri, timeout, headers, custom_tags_parser, verify_ssl)
    else:
        return _load_from_file(uri, custom_tags_parser)

# Support for python3 inspired by https://github.com/szemtiv/m3u8/


def _load_from_uri(uri, timeout=None, headers={}, custom_tags_parser=None, verify_ssl=True):
    request = urllib.request.Request(uri, headers=headers)
    context = None
    if not verify_ssl:
        context = ssl._create_unverified_context()
    resource = urllib.request.urlopen(request, timeout=timeout, context=context)
    base_uri = _parsed_url(resource.geturl())
    content = _read_python(resource)
    return M3U8(content, base_uri=base_uri, custom_tags_parser=custom_tags_parser)


def _parsed_url(url):
    parsed_url = urllib.parse.urlparse(url)
    prefix = parsed_url.scheme + '://' + parsed_url.netloc
    base_path = posixpath.normpath(parsed_url.path + '/..')
    return urllib.parse.urljoin(prefix, base_path)


def _read_python(resource):
    return resource.read().decode(
        resource.headers.get_content_charset(failobj="utf-8")
    )


def _load_from_file(uri, custom_tags_parser=None):
    with open(uri) as fileobj:
        raw_content = fileobj.read().strip()
    base_uri = os.path.dirname(uri)
    return M3U8(raw_content, base_uri=base_uri, custom_tags_parser=custom_tags_parser)
