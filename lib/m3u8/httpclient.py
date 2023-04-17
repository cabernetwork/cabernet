import posixpath
import ssl
import sys
import urllib
from urllib.error import HTTPError
from urllib.parse import urlparse, urljoin
import urllib.request

from lib.common.decorators import handle_url_except


def _parsed_url(url):
    parsed_url = urlparse(url)
    prefix = parsed_url.scheme + '://' + parsed_url.netloc
    base_path = posixpath.normpath(parsed_url.path + '/..')
    return urljoin(prefix, base_path)


class DefaultHTTPClient:

    def __init__(self, proxies=None):
        self.proxies = proxies
        self.base_uri = None

    def download(self, uri, timeout=10, headers={}, verify_ssl=True):
        content = self.get_uri(uri, timeout, headers, verify_ssl)
        return content, self.base_uri

    def get_uri(self, uri, timeout, headers, verify_ssl):
        proxy_handler = urllib.request.ProxyHandler(self.proxies)
        https_handler = HTTPSHandler(verify_ssl=verify_ssl)
        opener = urllib.request.build_opener(proxy_handler, https_handler)
        opener.addheaders = headers.items()
        resource = opener.open(uri, timeout=timeout)
        self.base_uri = _parsed_url(resource.geturl())
        content = resource.read().decode(
            resource.headers.get_content_charset(failobj="utf-8")
        )
        return content


class HTTPSHandler:

    def __new__(self, verify_ssl=True):
        context = ssl.create_default_context()
        if not verify_ssl:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        return urllib.request.HTTPSHandler(context=context)
