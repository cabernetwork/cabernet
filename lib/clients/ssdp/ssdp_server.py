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

import ipaddress
import logging
import random
import socket
import struct
import sys
from email.utils import formatdate
from errno import ENOPROTOOPT
from ipaddress import IPv4Network
from ipaddress import IPv4Address

import lib.common.utils as utils

SSDP_PORT = 1900
SSDP_ADDR = '239.255.255.250'
SERVER_ID = 'HDHomeRun/1.0 UPnP/1.0'


def ssdp_process(config):
    ssdp = SSDPServer(config)
    ssdp.register('local',
        'uuid:' + config["main"]["uuid"] + '::upnp:rootdevice',
        'upnp:rootdevice',
        'http://' + config["web"]["plex_accessible_ip"] + ':' +
        str(config["web"]["web_admin_port"]) + '/device.xml')

    ssdp.run(config["web"]["bind_ip"])


class SSDPServer:
    """A class implementing a SSDP server.  The notify_received and
    searchReceived methods are called when the appropriate type of
    datagram is received by the server."""
    known = {}

    def __init__(self, _config):
        self.config = _config
        self.sock = None
        utils.logging_setup(self.config['paths'])
        self.logger = logging.getLogger(__name__)

    def run(self, _bind_ip=''):
    
        if self.config['ssdp']['udp_netmask'] is None:
            self.logger.error('Config setting [ssdp][udp_netmask] required. Exiting ssdp service')
            return
        try:
            net = IPv4Network(self.config['ssdp']['udp_netmask'])
        except (ipaddress.AddressValueError, ValueError) as err:
            self.logger.error('Illegal value in [ssdp][udp_netmask].  Format must be #.#.#.#/#. Exiting hdhr service. ERROR: {}'.format(err))
            return
    
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, "SO_REUSEPORT"):
            try:
                self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except socket.error as le:
                # RHEL6 defines SO_REUSEPORT but it doesn't work
                if le.errno == ENOPROTOOPT:
                    pass
                else:
                    raise

        self.sock.bind(('0.0.0.0', SSDP_PORT))

        # more info about this from here
        mreq = struct.pack('4sl', socket.inet_aton(SSDP_ADDR), socket.INADDR_ANY)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        self.sock.settimeout(1)

        while True:
            try:
                data, addr = self.sock.recvfrom(1024)
                self.datagram_received(data, addr)
            except socket.timeout:
                continue
        self.shutdown()

    def shutdown(self):
        for st in self.known:
            if self.known[st]['MANIFESTATION'] == 'local':
                self.do_byebye(st)

    def datagram_received(self, data, host_port):
        """Handle a received multicast datagram."""
        (host, port) = host_port

        if self.config['ssdp']['udp_netmask'] is None:
            is_allowed = True
        else:
            try:
                net = IPv4Network(self.config['ssdp']['udp_netmask'])
            except (ipaddress.AddressValueError, ValueError) as err:
                self.logger.error(
                    'Illegal value in [ssdp][udp_netmask].  '
                    'Format must be #.#.#.#/#. Exiting hdhr service. ERROR: {}'.format(err))
                sys.exit(1)
            is_allowed = IPv4Address(host) in net

        if not is_allowed:
            return

        self.logger.debug("SSDP:: {}".format(host_port))
        try:
            header, payload = data.decode().split('\r\n\r\n')[:2]
        except ValueError as err:
            self.logger.error(err)
            return

        lines = header.split('\r\n')
        cmd = lines[0].split(' ')
        lines = [x.replace(': ', ':', 1) for x in lines[1:]]
        lines = [x for x in lines if len(x) > 0]

        headers = [x.split(':', 1) for x in lines]
        headers = dict([(x[0].lower(), x[1]) for x in headers])

        self.logger.debug('SSDP command %s %s - from %s:%d' % (cmd[0], cmd[1], host, port))
        self.logger.debug('with headers: {}.'.format(headers))
        if cmd[0] == 'M-SEARCH' and cmd[1] == '*':
            # SSDP discovery
            self.discovery_request(headers, (host, port))
        elif cmd[0] == 'NOTIFY' and cmd[1] == '*':
            # SSDP presence
            self.logger.debug('NOTIFY *')
        else:
            self.logger.debug('Unknown SSDP command %s %s' % (cmd[0], cmd[1]))

    def register(self, manifestation, usn, st, location, server=SERVER_ID,
            cache_control='max-age=1800', silent=False, host=None):
        """Register a service or device that this SSDP server will
        respond to."""

        self.logger.debug('Registering %s (%s)' % (st, location))

        self.known[usn] = {}
        self.known[usn]['Server'] = server
        self.known[usn]['ST'] = st
        self.known[usn]['Location'] = location
        self.known[usn]['Cache-Control'] = cache_control
        self.known[usn]['USN'] = usn
        self.known[usn]['Ext'] = None
        self.known[usn]['Content-Length'] = 0

        self.known[usn]['MANIFESTATION'] = manifestation
        self.known[usn]['SILENT'] = silent
        self.known[usn]['HOST'] = host

        if manifestation == 'local' and self.sock:
            self.do_notify(usn)

    def unregister(self, usn):
        self.logger.debug("Un-registering %s" % usn)
        del self.known[usn]

    def is_known(self, usn):
        return usn in self.known

    def send_it(self, response, destination, delay, usn):
        self.logger.debug('send discovery response delayed by %ds for %s to %r' % (delay, usn, destination))
        try:
            self.sock.sendto(response.encode(), destination)
        except (AttributeError, socket.error) as msg:
            self.logger.error("failure sending out byebye notification: %r" % msg)

    def discovery_request(self, headers, host_port):
        """Process a discovery request.  The response must be sent to
        the address specified by (host, port)."""

        (host, port) = host_port

        self.logger.debug('Discovery request from (%s,%d) for %s' % (host, port, headers['st']))

        # Do we know about this service?
        for i in list(self.known.values()):
            if i['MANIFESTATION'] == 'remote':
                continue
            if headers['st'] == 'ssdp:all' and i['SILENT']:
                continue
            if i['ST'] == headers['st'] or headers['st'] == 'ssdp:all':
                response = ['HTTP/1.1 200 OK']

                usn = None
                for k, v in list(i.items()):
                    if k == 'USN':
                        usn = v
                    if k not in ('MANIFESTATION', 'SILENT', 'HOST'):
                        if v is None:
                            response.append('%s:' % k)
                        else:
                            response.append('%s: %s' % (k, v))

                if usn:
                    response.append('Date: %s' % formatdate(timeval=None, localtime=False, usegmt=True))

                    response.extend(('', ''))
                    delay = random.randint(0, int(headers['mx']))

                    self.send_it('\r\n'.join(response), (host, port), delay, usn)

    def do_notify(self, usn):
        """Do notification"""

        if self.known[usn]['SILENT']:
            return

        self.logger.debug('Sending alive notification for %s' % usn)

        resp = [
            'NOTIFY * HTTP/1.1',
            'HOST: %s:%d' % (SSDP_ADDR, SSDP_PORT),
            'NTS: ssdp:alive',
        ]
        stcpy = dict(list(self.known[usn].items()))
        stcpy['NT'] = stcpy['ST']
        del stcpy['ST']
        del stcpy['MANIFESTATION']
        del stcpy['SILENT']
        del stcpy['HOST']
        del stcpy['last-seen']

        resp.extend([': '.join(x) for x in list(stcpy.items())])
        resp.extend(('', ''))

        self.logger.debug('do_notify content', resp)

        try:
            self.sock.sendto('\r\n'.join(resp).encode(), (SSDP_ADDR, SSDP_PORT))
            self.sock.sendto('\r\n'.join(resp).encode(), (SSDP_ADDR, SSDP_PORT))
        except (AttributeError, socket.error) as msg:
            self.logger.debug("failure sending out alive notification: %r" % msg)

    def do_byebye(self, usn):
        """Do byebye"""

        self.logger.debug('Sending byebye notification for %s' % usn)

        resp = [
            'NOTIFY * HTTP/1.1',
            'HOST: %s:%d' % (SSDP_ADDR, SSDP_PORT),
            'NTS: ssdp:byebye',
        ]
        try:
            stcpy = dict(list(self.known[usn].items()))
            stcpy['NT'] = stcpy['ST']
            del stcpy['ST']
            del stcpy['MANIFESTATION']
            del stcpy['SILENT']
            del stcpy['HOST']
            del stcpy['last-seen']
            resp.extend([': '.join(x) for x in list(stcpy.items())])
            resp.extend(('', ''))
            self.logger.debug('do_byebye content', resp)
            if self.sock:
                try:
                    self.sock.sendto('\r\n'.join(resp), (SSDP_ADDR, SSDP_PORT))
                except (AttributeError, socket.error) as msg:
                    self.logger.error("failure sending out byebye notification: %r" % msg)
        except KeyError as msg:
            self.logger.error("error building byebye notification: %r" % msg)
