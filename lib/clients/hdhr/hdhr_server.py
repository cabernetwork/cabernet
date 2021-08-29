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
import string
import struct
import sys
import zlib
from ipaddress import IPv4Network
from ipaddress import IPv4Address
from multiprocessing import Process
from threading import Thread

import lib.common.utils as utils


HDHR_PORT = 65001
HDHR_ADDR = '224.0.0.255'  # multicast to local addresses only
# HDHR_ADDR = '239.255.255.250'
SERVER_ID = 'HDHR3'
HDHOMERUN_TYPE_DISCOVER_REQ = 2
HDHOMERUN_TYPE_DISCOVER_RSP = 3
HDHOMERUN_TYPE_GETSET_REQ = 4
HDHOMERUN_TYPE_GETSET_RSP = 5
HDHOMERUN_GETSET_NAME = 3
HDHOMERUN_GETSET_VALUE = 4
HDHOMERUN_ERROR_MESSAGE = 5
HDHOMERUN_GETSET_LOCKKEY = 21
START_SEND_UDP_ATSC_PKTS = 1
STOP_SEND_UDP_ATSC_PKTS = 0
HDHOMERUN_BASE_URL = 0x2A
HDHOMERUN_LINEUP_URL = 0x27
# HDHOMERUN_DEVICE_AUTH_STR = 0x2B
# HDHOMERUN_DEVICE_TYPE_WILDCARD = 0xFFFFFFFF
HDHOMERUN_DEVICE_TYPE_TUNER = 0x00000001
# HDHOMERUN_DEVICE_ID_WILDCARD = 0xFFFFFFFF

msgs = {
    'lockedErrMsg':
        """ERROR: resource locked by {}""",
    'scanErrMsg':
        """ERROR: tuner busy""",
}

tuner_status_msg = {
    'Idle': b'ch=none lock=none ss=0 snq=0 seq=0 bps=0 pps=0',
    'Stream': b'ch=8vsb:183000000 lock=8vsb ss=98 snq=80 seq=90 bps=12345678 pps=1234',
}

logger = None


def hdhr_process(config, _tuner_queue):
    global logger
    utils.logging_setup(config['paths'])
    logger = logging.getLogger(__name__)
    if config['hdhomerun']['udp_netmask'] is None:
        logger.error('Config setting [hdhomerun][udp_netmask] required. Exiting hdhr service')
        return

    try:
        net = IPv4Network(config['hdhomerun']['udp_netmask'])
    except (ipaddress.AddressValueError, ValueError) as err:
        logger.error(
            'Illegal value in [hdhomerun][udp_netmask].  '
            'Format must be #.#.#.#/#. Exiting hdhr service. ERROR: {}'.format(err))
        return
        
    hdhr = HDHRServer(config, _tuner_queue)
    # startup the multicast thread first which will exit when this function exits
    p_multi = Process(target=hdhr.run_multicast, args=(config["web"]["bind_ip"],))
    p_multi.daemon = True
    p_multi.start()

    # startup the standard tcp listener, but have this hang the process
    # the socket listener will terminate from main.py when the process is stopped
    hdhr.run_listener(config["web"]["bind_ip"])
    logger.info('hdhr_processing terminated')


def hdhr_validate_device_id(_device_id):
    hex_digits = set(string.hexdigits)
    if len(_device_id) != 8:
        logger.error('ERROR: HDHR Device ID must be 8 hexidecimal values')
        return False
    if not all(c in hex_digits for c in _device_id):
        logger.error('ERROR: HDHR Device ID characters must all be hex (0-A)')
        return False
    device_id_bin = bytes.fromhex(_device_id)
    cksum_lookup = [0xA, 0x5, 0xF, 0x6, 0x7, 0xC, 0x1, 0xB, 0x9, 0x2, 0x8, 0xD, 0x4, 0x3, 0xE, 0x0]
    device_id_int = int.from_bytes(device_id_bin, byteorder='big')
    cksum = 0
    cksum ^= cksum_lookup[(device_id_int >> 28) & 0x0F]
    cksum ^= (device_id_int >> 24) & 0x0F
    cksum ^= cksum_lookup[(device_id_int >> 20) & 0x0F]
    cksum ^= (device_id_int >> 16) & 0x0F
    cksum ^= cksum_lookup[(device_id_int >> 12) & 0x0F]
    cksum ^= (device_id_int >> 8) & 0x0F
    cksum ^= cksum_lookup[(device_id_int >> 4) & 0x0F]
    cksum ^= (device_id_int >> 0) & 0x0F
    return cksum == 0


# given a device id, will adjust the last 4 bits to make it valid and return the integer value
def hdhr_get_valid_device_id(_device_id):
    hex_digits = set(string.hexdigits)
    if len(_device_id) != 8:
        logger.error('ERROR: HDHR Device ID must be 8 hexadecimal values')
        return 0
    if not all(c in hex_digits for c in _device_id):
        logger.error('ERROR: HDHR Device ID characters must all be hex (0-A)')
        return 0
    device_id_bin = bytes.fromhex(_device_id)
    cksum_lookup = [0xA, 0x5, 0xF, 0x6, 0x7, 0xC, 0x1, 0xB, 0x9, 0x2, 0x8, 0xD, 0x4, 0x3, 0xE, 0x0]
    device_id_int = int.from_bytes(device_id_bin, byteorder='big')
    cksum = 0
    cksum ^= cksum_lookup[(device_id_int >> 28) & 0x0F]
    cksum ^= (device_id_int >> 24) & 0x0F
    cksum ^= cksum_lookup[(device_id_int >> 20) & 0x0F]
    cksum ^= (device_id_int >> 16) & 0x0F
    cksum ^= cksum_lookup[(device_id_int >> 12) & 0x0F]
    cksum ^= (device_id_int >> 8) & 0x0F
    cksum ^= cksum_lookup[(device_id_int >> 4) & 0x0F]
    new_dev_id = (device_id_int & 0xFFFFFFF0) + cksum
    return struct.pack('>I', new_dev_id).hex().upper()


def hdhr_gen_device_id():
    baseid = '105' + ''.join(random.choice('0123456789ABCDEF') for _ in range(4)) + '0'
    return hdhr_get_valid_device_id(baseid)


class HDHRServer:
    """A class implementing a HDHR server.  The notify_received and
    searchReceived methods are called when the appropriate type of
    datagram is received by the server."""
    known = {}

    def __init__(self, _config, _tuner_queue):
        self.config = _config
        self.logger = logging.getLogger(__name__ + '_tcp')
        self.tuner_queue = _tuner_queue
        self.sock_multicast = None
        self.sock_listener = None
        self._t = None
        self.tuners = {}
        for area, area_data in self.config.items():
            if 'player-tuner_count' in area_data.keys():
                self.tuners[area] = dict.fromkeys(range(self.config[area]['player-tuner_count']))
                for i in range(self.config[area]["player-tuner_count"]):
                    self.tuners[area][i] = {
                        'channel': None,
                        'status': 'Idle'
                    }

    def run_listener(self, _bind_ip=''):
        self.logger.info('TCP: Starting HDHR TCP listener server')
        self.sock_listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_address = (_bind_ip, HDHR_PORT)
        self.sock_listener.bind(server_address)
        self.sock_listener.listen(3)

        self._t = Thread(target=self.process_queue,
            args=(self.tuner_queue,))
        self._t.daemon = True
        self._t.start()

        while True:
            # wait for a connection
            connection, client_address = self.sock_listener.accept()
            t_conn = Thread(target=self.process_client_connection, args=(connection, client_address,))
            t_conn.daemon = True
            t_conn.start()

    def process_client_connection(self, _connection, _address):
        # multi-threading multiple clients talking to the device at one time
        # buffer must be large enough to hold a full rcvd packets
        self.logger.debug('TCP: New connection established {}'.format(_address))
        try:
            while True:
                msg = _connection.recv(1316)
                if not msg:
                    # client disconnect
                    self.logger.debug('TCP: Client terminated connection {}'.format(_address))
                    break
                self.logger.debug('TCP: data rcvd={}'.format(msg))
                frame_type = HDHRServer.get_frame_type(msg)
                if frame_type == HDHOMERUN_TYPE_GETSET_REQ:
                    req_dict = self.parse_getset_request(msg)
                    response = self.create_getset_response(req_dict, _address)
                    if response is not None:
                        self.logger.debug('TCP: Sending response={}'.format(response))
                        _connection.sendall(response)
                else:
                    self.logger.error('TCP: Unknown frame/message type from {} type={}'.format(_address, frame_type))
        finally:
            _connection.close()

    def process_queue(self, _queue):
        while True:
            queue_item = _queue.get()
            # queue item has a command and arguments which are based on the command.
            self.tuners[queue_item['namespace'].lower()][queue_item['tuner']] = {
                'channel': queue_item['channel'],
                'status': queue_item['status']
            }

    @staticmethod
    def get_frame_type(_msg):
        """
        Get the type of message requested
        :param _msg:
        :return:
        """
        # msg is in the first 2 bytes of the string
        (frame_type,) = struct.unpack('>H', _msg[:2])
        return frame_type

    @staticmethod
    def gen_err_response(_frame_type, _tag, _text):
        # This is a tag type of HDHOMERUN_ERROR_MESSAGE
        # does not include the crc
        msg = msgs[_tag].format(*_text).encode()
        tag = utils.set_u8(HDHOMERUN_ERROR_MESSAGE)
        err_resp = utils.set_str(msg, True)
        msg_len = utils.set_u16(len(tag) + len(err_resp))
        response = _frame_type + msg_len + tag + err_resp
        return response

    def create_getset_response(self, _req_dict, _address):
        (host, port) = _address
        frame_type = utils.set_u16(HDHOMERUN_TYPE_GETSET_RSP)
        name = _req_dict[HDHOMERUN_GETSET_NAME]
        name_str = name.decode('utf-8')
        # if HDHOMERUN_GETSET_VALUE in _req_dict.keys():
        #     value = _req_dict[HDHOMERUN_GETSET_VALUE]
        # else:
        #     value = None

        if name == b'/sys/model':
            # required to id the device
            name_resp = utils.set_u8(HDHOMERUN_GETSET_NAME) + utils.set_str(name, True)
            value_resp = utils.set_u8(HDHOMERUN_GETSET_VALUE) + utils.set_str(b'hdhomerun4_atsc', True)
            msg_len = utils.set_u16(len(name_resp) + len(value_resp))
            response = frame_type + msg_len + name_resp + value_resp
            x = zlib.crc32(response)
            crc = struct.pack('<I', x)
            response += crc
            return response

        elif name_str.startswith('/tuner'):
            tuner_index = int(name_str[6])
            if name_str.endswith('/lockkey'):
                self.logger.error('TCP: NOT IMPLEMENTED GETSET LOCKKEY MSG REQUEST: {} '.format(_req_dict))
                response = HDHRServer.gen_err_response(frame_type, 'lockedErrMsg', [host])
                x = zlib.crc32(response)
                crc = struct.pack('<I', x)
                response += crc
                return response
            elif name_str.endswith('/status'):
                response = None
                tuner_status = None
                for area, area_data in self.tuners.items():
                    if area_data[tuner_index]['status'] == 'Scan':
                        response = HDHRServer.gen_err_response(frame_type, 'scanErrMsg', [host])
                        break
                    else:
                        tuner_status = area_data[tuner_index]['status']
                if response is None:
                    value_resp = utils.set_u8(HDHOMERUN_GETSET_VALUE) \
                                 + utils.set_str(tuner_status_msg[tuner_status], True)
                    name_resp = utils.set_u8(HDHOMERUN_GETSET_NAME) + utils.set_str(name, True)
                    msg_len = utils.set_u16(len(name_resp) + len(value_resp))
                    response = frame_type + msg_len + name_resp + value_resp
                x = zlib.crc32(response)
                crc = struct.pack('<I', x)
                response += crc
                return response

            elif name_str.endswith('/vchannel'):
                tuner_status = self.tuners[tuner_index]['status']
                if tuner_status == 'Stream':
                    value_resp = utils.set_u8(HDHOMERUN_GETSET_VALUE) \
                                 + utils.set_str(self.tuners[tuner_index]['channel'].encode(), True)
                else:
                    value_resp = utils.set_u8(HDHOMERUN_GETSET_VALUE) \
                                 + utils.set_str('none', True)
                name_resp = utils.set_u8(HDHOMERUN_GETSET_NAME) + utils.set_str(name, True)
                msg_len = utils.set_u16(len(name_resp) + len(value_resp))
                response = frame_type + msg_len + name_resp + value_resp
                x = zlib.crc32(response)
                crc = struct.pack('<I', x)
                response += crc
                return response

            else:
                self.logger.error('TCP: NOT IMPLEMENTED GETSET MSG REQUEST: {} '.format(_req_dict))
                return None
        else:
            self.logger.error('TCP: 3 UNKNOWN GETSET MSG REQUEST: {} '.format(_req_dict))
            return None

    def parse_getset_request(self, _msg):
        (crc_rcvd,) = struct.unpack('I', _msg[-4:])
        crc_calc = zlib.crc32(_msg[0:-4])
        if crc_calc == crc_rcvd:
            # Pull first id/value
            offset = 4
            request_info = {}
            while True:
                (msg_type, value, offset) = HDHRServer.get_id_value(_msg, offset)
                if msg_type is None:
                    break
                request_info[msg_type] = value
        else:
            self.logger.info('TCP: type/value CRC failed, ignoring packet')
            return None

        return request_info

    @staticmethod
    def get_id_value(_msg, _offset):
        """
        Obtains the next type/value in the message and moves the offset to the next spot

        :param _msg:
        :param _offset:
        :return:
        """
        if _offset >= len(_msg) - 4:
            return None, None, None
        (msg_type, length) = struct.unpack('BB', _msg[_offset:_offset + 2])
        _offset += 2
        (value,) = struct.unpack('%ds' % (length - 1), _msg[_offset:_offset + length - 1])
        _offset += length
        return msg_type, value, _offset

    def run_multicast(self, _bind_ip=''):
        utils.logging_setup(self.config['paths'])
        self.logger = logging.getLogger(__name__ + '_udp')
        self.logger.info('UDP: Starting HDHR multicast server')
        self.sock_multicast = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock_multicast.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        self.sock_multicast.bind(('0.0.0.0', HDHR_PORT))
        mreq = struct.pack('4sl', socket.inet_aton(HDHR_ADDR), socket.INADDR_ANY)
        self.sock_multicast.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        self.sock_multicast.settimeout(2)

        while True:
            try:
                data, addr = self.sock_multicast.recvfrom(1024)
                self.datagram_received(data, addr)
            except socket.timeout:
                continue

    def datagram_received(self, _data, _host_port):
        """Handle a received multicast datagram."""

        (host, port) = _host_port
        if self.config['hdhomerun']['udp_netmask'] is None:
            is_allowed = True
        else:
            try:
                net = IPv4Network(self.config['hdhomerun']['udp_netmask'])
            except (ipaddress.AddressValueError, ValueError) as err:
                self.logger.error(
                    'Illegal value in [hdhomerun][udp_netmask].  '
                    'Format must be #.#.#.#/#. Exiting hdhr service. ERROR: {}'.format(err))
                sys.exit(1)
            is_allowed = IPv4Address(host) in net

        if not is_allowed:
            return

        self.logger.debug('UDP: from {}:{}'.format(host, port))
        try:
            (frame_type, msg_len, device_type, sub_dt_len, sub_dt, device_id, sub_did_len, sub_did) = \
                struct.unpack('>HHBBIBBI', _data[0:-4])
            # (crc,) = struct.unpack('<I', _data[-4:])
        except ValueError as err:
            self.logger.error('UDP: {}'.format(err))
            return

        if frame_type != HDHOMERUN_TYPE_DISCOVER_REQ:
            self.logger.error('UDP: Unknown from type = {}'.format(frame_type))
        else:
            msg_type = bytes.fromhex('0003')
            header = bytes.fromhex('010400000001')
            device_id = bytes.fromhex('0204' + self.config['hdhomerun']['hdhr_id'])
            base_url = 'http://' + \
                       self.config['web']['plex_accessible_ip'] + \
                       ':' + str(self.config['web']['web_admin_port'])
            base_url_msg = b'\x2a' + utils.set_str(base_url.encode(), False)
            
            namespace = None
            for area, area_data in self.config.items():
                if 'player-tuner_count' in area_data.keys():
                    namespace = area
            tuner_count = b'\x10\x01' + utils.set_u8(
                self.config[namespace]['player-tuner_count'])

            lineup_url = base_url + '/lineup.json'
            lineup_url = b'\x27' + utils.set_str(lineup_url.encode(), False)
            msg = header + device_id + base_url_msg + tuner_count + lineup_url
            msg_len = utils.set_u16(len(msg))
            response = msg_type + msg_len + msg

            x = zlib.crc32(response)
            crc = struct.pack('<I', x)
            response += crc
            self.logger.debug('UDP Response={} {}'.format(_host_port, response))
            self.sock_multicast.sendto(response, _host_port)
