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

import binascii
import struct
import datetime
import logging
import lib.common.utils as utils
from lib.common.algorithms import Crc
from lib.common.models import CrcModels

ATSC_EXTENDED_CHANNEL_DESCR_TAG = b'\xA0'
ATSC_SERVICE_LOCATION_DESCR_TAG = b'\xA1'
ATSC_VIRTUAL_CHANNEL_TABLE_TAG = b'\xC8'
ATSC_MASTER_GUIDE_TABLE_TAG = b'\xC7'
ATSC_SERVICE_DESCR_TABLE_TAG = b'\x42'
MPEG2_PROGRAM_SYSTEM_TIME_TABLE_TAG = b'\xCD'
MPEG2_PROGRAM_ASSOCIATION_TABLE_TAG = b'\x00'
MPEG2_CONDITIONAL_ACCESS_TABLE_TAG = b'\x01'
MPEG2_PROGRAM_MAP_TABLE_TAG = b'\x02'

ATSC_MSG_LEN = 188
LEAP_SECONDS_1980 = 19
LEAP_SECONDS_2021 = 37  # this has not changed since 2017


class ATSCMsg:
    # class that generates most of the ATSC UDP protocol messages

    msg_counter = {}

    # UDP msgs for ATSC
    # https://www.atsc.org/wp-content/uploads/2015/03/Program-System-Information-Protocol-for-Terrestrial-Broadcast-and-Cable-1.pdf

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        models = CrcModels()
        crc32_mpeg_model = models.get_params('crc-32-mpeg')
        self.crc_width = crc32_mpeg_model['width']
        self.crc_poly = crc32_mpeg_model['poly']
        self.crc_reflect_in = crc32_mpeg_model['reflect_in']
        self.crc_xor_in = crc32_mpeg_model['xor_in']
        self.crc_reflect_out = crc32_mpeg_model['reflect_out']
        self.crc_xor_out = crc32_mpeg_model['xor_out']
        self.crc_table_idx_width = 8
        self.atsc_blank_section = b'\x47\x1f\xff\x10\x00'.ljust(ATSC_MSG_LEN, b'\xff')
        self.type_strings = []

    def gen_crc_mpeg(self, _msg):
        alg = Crc(
            width=self.crc_width,
            poly=self.crc_poly,
            reflect_in=self.crc_reflect_in,
            xor_in=self.crc_xor_in,
            reflect_out=self.crc_reflect_out,
            xor_out=self.crc_xor_out,
            table_idx_width=8,
        )
        crc_int = alg.bit_by_bit(_msg)
        crc = struct.pack('>I', crc_int)
        return crc

    def gen_header(self, _pid):
        # pid is an integer
        # pid = PMT channel pid
        #       STT 1FFB
        #       VCT 1FFB
        #       PAT 0
        #       CAT 1
        # set the msg_counter for this pid
        if _pid not in self.msg_counter.keys():
            self.msg_counter[_pid] = 0

        sync = 0x47400000  # 1195376640   # 4740 0000
        pid_shifted = _pid << 8
        msg_int = sync | pid_shifted | (self.msg_counter[_pid] + 16)  # x10
        msg = struct.pack('>I', msg_int) + b'\x00'
        self.msg_counter[_pid] += 1
        if self.msg_counter[_pid] > 15:
            self.msg_counter[_pid] = 0
        return msg

    def gen_multiple_string_structure(self, _names):
        # Table 6.39 Multiple String Structure
        # event titles, long channel names, the ETT messages, and RRT text items
        # allows for upto 255 character strings
        # 8bit = array size
        # for each name
        #    3byte ISO_639_language_string = 'eng'
        #    1byte segments = normally 0x01
        #    for each segment
        #        1byte compression = 0x00 (not compression)
        #        1byte mode = 0x00 (used with unicode 2 byte letters, assume ASCII)
        #        1byte length in bytes = calculated
        #        string in byte format.  1 byte per character
        msg = utils.set_u8(len(_names))
        for name in _names:
            lang = self.gen_lang(b'eng')
            segment_len = utils.set_u8(1)
            compress_mode = utils.set_u16(0)
            name_bytes = utils.set_str(name.encode(), False)
            msg += lang + segment_len + compress_mode + name_bytes
        return msg

    def gen_channel_longnames(self, names):
        # Table 6.28 Extended Channel Name Descriptor
        # channel  name  for  the  virtual  channel  containing this descriptor
        # allows for upto 245 character strings
        # 8bit = tag = 0xA0
        # 8bit = description length
        # long_channel_name_text = gen_multiple_string_structure()
        long_name = self.gen_multiple_string_structure(names)
        return ATSC_EXTENDED_CHANNEL_DESCR_TAG + utils.set_u8(len(long_name)) + long_name

    def gen_vct_channel_descriptor(self, xxx):
        #    111111 static bits
        #    10bits description_length = long channel name length
        #       a list of descriptor()   possible descriptors listed in Table 6.25a

        # expected descriptors
        # A0 = channel long names
        # A1 = Service Location
        pass

    def gen_pid(self, _prog_number):
        # the PID is based on the program number and returns an integer (not bytes)
        # 30,40,50,60,130,140,150,160,230,...
        # Base_PID = prog_num << 4
        # Video Stream Element = Base_PID + 1 with the 12th bit set
        # Audio Stream Elements = Vide Stream PID + 4 with the 12th bit set, then +1 for each additional lang
        pid_lookup = [0x00, 0x30, 0x40, 0x50, 0x60, 0x70, 0x80, 0x90,
            0x130, 0x140, 0x150, 0x160, 0x170, 0x180, 0x190, 0x230, 0x240]
        return pid_lookup[_prog_number]

    def gen_lang(self, _name):
        return struct.pack('%ds' % (len(_name)), _name)

    def update_sdt_names(self, _video, _service_provider, _service_name):
        if _video.data is None:
            return
        i = 0
        video_len = len(_video.data)
        msg = None
        while True:
            if i+ATSC_MSG_LEN > video_len: 
                break
            packet = _video.data[i:i+ATSC_MSG_LEN]
            program_fields = self.decode_ts_packet(packet)
            if program_fields is None:
                i += ATSC_MSG_LEN
                continue
            if program_fields['transport_error_indicator']:
                i += ATSC_MSG_LEN
                continue
            if program_fields['pid'] == 0x0011:
                descr = b'\x01' \
                        + utils.set_str(_service_provider, False) \
                        + utils.set_str(_service_name, False)
                descr = b'\x48' + utils.set_u8(len(descr)) + descr
                msg = packet[8:20] + utils.set_u8(len(descr)) + descr
                length = utils.set_u16(len(msg) + 4 + 0xF000)
                msg = ATSC_SERVICE_DESCR_TABLE_TAG + length + msg
                crc = self.gen_crc_mpeg(msg)
                msg = packet[:5] + msg + crc
                msg = msg.ljust(len(packet), b'\xFF')
                _video.data = b''.join([
                    _video.data[:i],
                    msg,
                    _video.data[i+ATSC_MSG_LEN:]
                    ])
            i += ATSC_MSG_LEN
        if msg is None:
            self.logger.debug('Missing ATSC SDT Msg in stream, unable to update provider and service name')
        else:
            self.logger.debug('Updating ATSC SDT with service info {} {}' \
                .format(_service_provider, _service_name))

    def gen_sld(self, _base_pid, _elements):
        # Table 6.29 Service Location Descriptor
        # Appears in each channel in the VCT
        # 8bit = tag = 0xA1
        # 8bit = description length
        # 3bits = 111 static bits
        # 13bits = PCR_PID = 0x1FFF or the program ID value found in the TS_prog_map
        # 8bits = number of elements
        # for each element
        #    8bits = stream_type = 0x02 (video stream) or 0x81 (audio stream)
        #    3bits = 111 static bits
        #    13bits = PCR_PID = (same as abovefor video stream) unique for audio
        #    8*3bytes = lang (spa, eng, mul, null for video stream
        #
        # element is an array of languages

        # the PID is based on the program number.
        # Base_PID = prog_num << 4
        # Video Stream Element = Base_PID + 1 with the 12th bit set
        # Audio Stream Elements = Vide Stream PID + 4 with the 12th bit set, then +1 for each additional lang

        elem_len = utils.set_u8(len(_elements) + 1)
        video_pid = utils.set_u16(_base_pid + 1 + 57344)  # E000
        stream_type = b'\x02'
        lang_0 = b'\x00\x00\x00'
        msg = stream_type + video_pid + lang_0
        stream_type = b'\x81'
        audio_pid_int = _base_pid + 3 + 57344  # E000 (starts at 0x34 and increments by 1)
        for lang in _elements:
            audio_pid_int += 1
            audio_pid = utils.set_u16(audio_pid_int)
            lang_msg = struct.pack('%ds' % (len(lang)),
                lang.encode())
            msg += stream_type + audio_pid + lang_msg
        msg = video_pid + elem_len + msg
        length = utils.set_u8(len(msg))
        return ATSC_SERVICE_LOCATION_DESCR_TAG + length + msg

    def gen_vct_channel(self, _tsid, _short_name, _channel):
        # Channel part of Table 6.4 Terrestrial Virtual Channel Table
        #    7*2byte characters short name = dict key
        #    1111 static bits
        #    10bits major channel number
        #    10bits minor channel number
        #    1byte modulation_mode = 0x04
        #    4bytes carrier_freq = 0
        #    2bytes channel_tsid = same as VCT TSID
        #    2bytes program number = index from 1 to n
        #    2bits ETM_location = 00 (no location)
        #    1bit access_control = 0
        #    1bit hidden = 0
        #    11 static bits
        #    1bit hide_guide = 0
        #    111 static bits
        #    6bits service_type = 000010
        #    2bytes source_id = index from 1 to n (same as prog_num)
        #    111111 static bits
        #    10bits description_length = long channel name length
        #       descriptor() = gen_extended_channel_descriptor(names)
        #    111111 static bits
        #    10bits additional_description_length = long channel name length = 0
        #       no additional descriptions are used

        # chnum_maj
        # chnum_min
        # prog_num
        # long_name
        u16name = b''
        short_name7 = _short_name.ljust(7, '\x00')

        for ch in short_name7:
            u16name += utils.set_u16(ord(ch))
        ch_num = _channel['chnum_maj'] << 10
        ch_num |= 15728640  # 0xf00000 static bits
        ch_num |= _channel['chnum_min']
        u3bch_num = utils.set_u32(ch_num)[1:]
        mod_mode = b'\x04'
        freq = b'\x00\x00\x00\x00'
        prog_num = utils.set_u16(_channel['prog_num'])
        pid = self.gen_pid(_channel['prog_num'])
        misc_bits = b'\x0d\xc2'  # 0000 1101 1100 0010
        source_id = prog_num
        descr = _channel['descr']
        descr_msg = b''
        for key in descr.keys():
            if key == 'long_names':
                descr_msg += self.gen_channel_longnames(descr[key])
            elif key == 'lang':
                descr_msg += self.gen_sld(pid, descr[key])
        descr_len = utils.set_u16(len(descr_msg) + 0xFC00)

        return u16name + u3bch_num + mod_mode + freq + _tsid + prog_num + misc_bits + \
            source_id + descr_len + descr_msg

    def gen_pat_channels(self, _channels):
        # for each section (sids):
        #    2bytes = program number (non-zero) 1..n
        #    3bits = 111 static bits
        #    13bits = multiples of 10 30,40,50,60,130,140,150,160,230,...
        msg = b''
        for i in range(1, len(_channels) + 1):
            pid = utils.set_u16(self.gen_pid(i) + 57344)  # E000
            msg += utils.set_u16(i) + pid
        return msg

    def gen_pat(self, _mux_stream):
        # Table Program Association Table : MPEG-2 protocol
        # 1byte table_id = 0x00
        # 1011 static bits
        # 12bits length including crc
        # 2bytes = tsid  (0000 11xx xxxx xxxx)
        # 2bits = 11 static bits
        # 5bits version_no = 1
        # 1bit current_next_indicator = 1
        # 1byte section_number = 0 (only one section)
        # 1byte last_section_number = 0 (only one section)
        # gen_pat_channels()
        # crc
        tsid = _mux_stream['tsid']
        ver_sect = b'\xc3\x00\x00'
        channels_len = utils.set_u8(len(_mux_stream['channels']))
        for i in range(len(_mux_stream['channels'])):
            pid = self.gen_pid(i)
        msg = tsid + ver_sect + self.gen_pat_channels(_mux_stream['channels'])
        length = utils.set_u16(len(msg) + 4 + 0xB000)
        msg = MPEG2_PROGRAM_ASSOCIATION_TABLE_TAG + length + msg
        crc = self.gen_crc_mpeg(msg)
        msg = self.gen_header(0) + msg + crc
        return self.format_video_packets([msg])

    def gen_vct(self, _mux_stream):
        # Table 6.4 Terrestrial Virtual Channel Table
        # 1byte table_id = 0xc8
        # 1111 static bits
        # 12bits length including crc
        # 2bytes TSID (transport stream id) = 0x0b21 (how is this generated?)
        # 11 static bits
        # 5bits version_no = 1
        # 1bit current_next_indicator = 1
        # 1byte section_number = 0 (only one section)
        # 1bytes last_section_number = 0 (only one section)
        # 1byte protocol_version = 0
        # 1byte number of channels
        #    gen_vct_channel(channel)
        # CRC_32
        msg = b''
        tsid = _mux_stream['tsid']
        ver_sect_last_sect_proto = b'\xc3\x00\x00\x00'
        channels_len = utils.set_u8(len(_mux_stream['channels']))
        for short_name in _mux_stream['channels'].keys():
            msg += self.gen_vct_channel(tsid, short_name, _mux_stream['channels'][short_name])
        extra_empty_descr = b'\xfc\x00'
        msg = tsid + ver_sect_last_sect_proto + channels_len + msg + extra_empty_descr
        length = utils.set_u16(len(msg) + 4 + 0xF000)

        msg = ATSC_VIRTUAL_CHANNEL_TABLE_TAG + length + msg
        crc = self.gen_crc_mpeg(msg)
        msg = self.gen_header(0x1ffb) + msg + crc

        # channels is a dict with the key being the primary channel name (short_name)
        return self.format_video_packets([msg])

    def gen_stt(self):
        # Table 6.1 System Time Table
        # 1byte table_id = 0xcd
        # 1111 static bits
        # 12bits length including crc
        # 2bytes table id extension = 0x0000
        # 2bits = 11 static bits
        # 5bits version_no = 1
        # 1bit current_next_indicator = 1
        # 1byte section_number = 0 (only one section)
        # 1byte last_section_number = 0 (only one section)
        # 1byte protocol_version = 0
        # 4bytes system time = time since 1980 (GPS)
        # 1byte GPS_UTC_offset = 12 (last checked 2021)
        # 2bytes daylight_saving = 0x60
        #  1bit ds_status 
        #  2bits 11 static bits
        #  5bits DS day of month
        #  8bits DS hour
        # CRC_32

        #         475f fb17 00cd f011 0000 c100 0000  ..G_............
        # 0x01b0:  4d3c e809 1060 00f3 30ca 76
        # 1295837193
        table_id_ext = b'\x00\x00'
        ver_sect_proto = b'\xc1\x00\x00\x00'

        time_gps = datetime.datetime.utcnow() - datetime.datetime(1980, 1, 6) \
            - datetime.timedelta(seconds=LEAP_SECONDS_2021 - LEAP_SECONDS_1980)
        time_gps_sec = int(time_gps.total_seconds())
        system_time = utils.set_u32(time_gps_sec)
        delta_time = utils.set_u8(LEAP_SECONDS_2021 - LEAP_SECONDS_1980)
        daylight_savings = b'\x60'

        msg = table_id_ext + ver_sect_proto + system_time + \
            delta_time + daylight_savings + b'\x00'
        length = utils.set_u16(len(msg) + 4 + 0xF000)
        msg = MPEG2_PROGRAM_SYSTEM_TIME_TABLE_TAG + length + msg
        crc = self.gen_crc_mpeg(msg)
        msg = self.gen_header(0x1ffb) + msg + crc
        return self.format_video_packets([msg])

    def gen_pmt(self, _channels):
        # Table Program Map Table : MPEG-2 protocol
        # 
        # DATA EXAMPLE
        # 0001 b009 ffff c300 00d5 dcfb 4c
        # 1byte table_id = 0x02
        # 1011 static bits
        # 12bits length including crc
        # 2bytes = program number (like 6)
        # 2bits = 11 static bits
        # 5bits version_no = 1
        # 1bit current_next_indicator = 1
        # 1byte section_number = 0 (only one section)
        # 1byte last_section_number = 0 (only one section)
        # 3bits = 111 static bits
        # 13bits = PCR_PID (like for prog_num 3 = 61. seems to always end in a 1)
        # 4bits = 1111 static bits
        # 12bits = program_info_length
        #    for loop of descriptors
        #        05 name of the channel (GA94)
        #

        msgs = []
        prog_num_int = 0
        for short_name in _channels.keys():
            prog_num_int += 1
            prog_num_bytes = utils.set_u16(prog_num_int)
            ver_sect = b'\xc1\x00\x00'
            base_pid_int = self.gen_pid(prog_num_int)
            pid_video_int = base_pid_int + 1
            pid_video = utils.set_u16(pid_video_int + 0xE000)
            pid_audio_int = pid_video_int + 3
            pid_audio = utils.set_u16(pid_audio_int + 0xE000)
            descr_prog = b'\xf0\x00'
            descr_video = b'\x02' + pid_video + b'\xF0\x00'
            descr_audio = b'\x81' + pid_audio + b'\xF0\x00'
            msg = prog_num_bytes + ver_sect + pid_video + descr_prog + descr_video + descr_audio
            length = utils.set_u16(len(msg) + 4 + 0xB000)
            msg = MPEG2_PROGRAM_MAP_TABLE_TAG + length + msg
            crc = self.gen_crc_mpeg(msg)
            msgs.append(self.gen_header(base_pid_int) + msg + crc)
        return [self.format_video_packets(msgs)]

    def gen_mgt(self, _mux_stream):
        # Table 6.2 Master Guide Table
        # 1byte table_id = 0xc7
        # 1111 static bits
        # 12bits length including crc
        # 16bits 0x0000 static bits
        # 2bits = 11 = static bits
        # 5bits version_no = 1
        # 1bit current_next_indicator = 1
        # 1byte section_number = 0 (only one section)
        # 1byte last_section_number = 0 (only one section)
        # 1byte protocol_version = 0
        # 2bytes number of tables

        msg = ATSC_MASTER_GUIDE_TABLE_TAG
        return msg

    def gen_cat(self):
        # Table Conditional Access Table : MPEG-2 protocol
        # 
        # DATA EXAMPLE
        # 0001 b009 ffff c300 00d5 dcfb 4c
        # 1byte table_id = 0x01
        # 1011 static bits
        # 12bits length including crc
        # 18bits 1111 1111 1111 1111 11
        # 5bits version_no = 1
        # 1bit current_next_indicator = 1
        # 1byte section_number = 0 (only one section)
        # 1byte last_section_number = 0 (only one section)
        # c10000 (5) c30000 (2,3,4,5,6)  d50000 (7) c50000 (3) d30000 (5)
        # c70000 (3) dd0000 (4)
        # for each section (sids):
        #    2bytes = program number (non-zero)
        #    3bits = 111 static bits
        #    13bits = multiples of 10
        #    0001 e0 30
        #    0002 e0 40
        #    0003 e0 50
        #    0004 e0 60
        # crc
        # NOTE: all transmissions had a zero sections transmission
        # search 0x0020.*0001  ...
        return b'\x00\x01\xb0\x09\xff\xff\xc3\x00\x00\xd5\xdc\xfb\x4c'

    def format_video_packets(self, _msgs=None):
        # atsc packets are 1316 in length with 7 188 sections
        # each section has a 471f ff10 00 when no data is present

        # finally the controls and msg counter byte is added (10) no msg counter
        # for continuation it had 471f fb1b 0000 previously 475f fb1a
        # 471f fb15 00  475f fb14 00 (c8 or c7)
        # 
        # pid = PMT channel pid
        #       STT 1FFB
        #       VCT 1FFB
        #       PAT 0
        #       CAT 1
        # 7 sections per packet
        sections = [
            self.atsc_blank_section,
            self.atsc_blank_section,
            self.atsc_blank_section,
            self.atsc_blank_section,
            self.atsc_blank_section,
            self.atsc_blank_section,
            self.atsc_blank_section,
        ]

        if _msgs is None:
            return b''.join(sections)
        
        # for now assume the msgs are less than 1316
        if len(_msgs) > 7:
            self.logger.error('ATSC: TOO MANY MESSAGES={}'.format(len(_msgs)))
            return None
        for i in range(len(_msgs)):
            if len(_msgs[i]) > ATSC_MSG_LEN:
                self.logger.error('ATSC: MESSAGE LENGTH TOO LONG={}'.format(len(_msgs[i])))
                return None
            else:
                sections[i] = _msgs[i].ljust(ATSC_MSG_LEN, b'\xff')

        return b''.join(sections)
        # TBD need to handle large msg and more than 7 msgs

    def extract_psip(self, _video_data):
        packet_list = []
        if _video_data is None:
            return
        i = 0
        video_len = len(_video_data)
        prev_pid = -1
        pmt_pids = None
        pat_found = False
        pmt_found = False
        seg_counter = 0
        
        #print('writing out segment')
        #f = open('/tmp/data/segment.ts', 'wb')
        #f.write(_video_data)
        #f.close()
        
        while True:
            if i+ATSC_MSG_LEN > video_len: 
                break
            packet = _video_data[i:i+ATSC_MSG_LEN]
            i += ATSC_MSG_LEN
            program_fields = self.decode_ts_packet(packet)

            seg_counter += 1
            if seg_counter > 7:
                #self.logger.debug('###### SENDING BACK {} PACKETS'.format(len(packet_list)))
                break
            else:
                packet_list.append(packet)
                continue

            if program_fields is None:
                continue
            if program_fields['transport_error_indicator']:
                continue

            if program_fields['pid'] == 0x0000:
                pmt_pids = self.decode_pat(program_fields['payload'])
                #self.logger.debug('###### EXPECTED PMT PIDS: {}'.format(pmt_pids))
                if not pat_found:
                    packet_list.append(packet)
                    pat_found = True
            if pmt_pids and program_fields['pid'] in pmt_pids.keys():
                program = pmt_pids[program_fields['pid']]
                self.decode_pmt(program_fields['pid'], program, program_fields['payload'])
                if not pmt_found:
                    #self.logger.debug('###### FOUND PMT PID: {}'.format(program_fields['pid']))
                    packet_list.append(packet)
                    pmt_found = True
                continue
            elif program_fields['pid'] == 0x1ffb:
                self.logger.info('Packet Table indicator 0x1ffb, not implemented {}'.format(i))
                continue
            #elif program_fields['pid'] == 0x0011:
            #    self.logger.info('Service Description Table (SDT) 0x0011, not implemented {}'.format(i))
            #    continue
            #elif program_fields['pid'] == 0x0000 or \
            #        program_fields['pid'] == 0x0100 or \
            #        program_fields['pid'] == 0x0101:
            #    continue
            #else:
            #    self.logger.info('Unknown PID {}'.format(program_fields['pid']))                
            prev_pid = program_fields['pid']
        return packet_list

    def sync_audio_video(self, _video_data):
        """
        Trims the audio or video to sync the PTS for both
        and return the video data with the removed parts
        """
        packet_list = []
        if _video_data is None:
            return
        i = 0
        video_len = len(_video_data)
        prev_pid = -1
        pmt_pids = None
        pat_found = False
        pmt_found = False
        seg_counter = 0
        
        #print('writing out segment')
        #f = open('/tmp/data/segment.ts', 'wb')
        #f.write(_video_data)
        #f.close()
        
        while True:
            if i+ATSC_MSG_LEN > video_len: 
                break
            packet = _video_data[i:i+ATSC_MSG_LEN]
            i += ATSC_MSG_LEN
            program_fields = self.decode_ts_packet(packet)

            seg_counter += 1
            if seg_counter > 7:
                #self.logger.debug('###### SENDING BACK {} PACKETS'.format(len(packet_list)))
                break
            else:
                packet_list.append(packet)
                continue

            if program_fields is None:
                continue
            if program_fields['transport_error_indicator']:
                continue

            if program_fields['pid'] == 0x0000:
                pmt_pids = self.decode_pat(program_fields['payload'])
                #self.logger.debug('###### EXPECTED PMT PIDS: {}'.format(pmt_pids))
                if not pat_found:
                    packet_list.append(packet)
                    pat_found = True
            if pmt_pids and program_fields['pid'] in pmt_pids.keys():
                program = pmt_pids[program_fields['pid']]
                self.decode_pmt(program_fields['pid'], program, program_fields['payload'])
                if not pmt_found:
                    #self.logger.debug('###### FOUND PMT PID: {}'.format(program_fields['pid']))
                    packet_list.append(packet)
                    pmt_found = True
                continue
            elif program_fields['pid'] == 0x1ffb:
                self.logger.info('Packet Table indicator 0x1ffb, not implemented {}'.format(i))
                continue
            #elif program_fields['pid'] == 0x0011:
            #    self.logger.info('Service Description Table (SDT) 0x0011, not implemented {}'.format(i))
            #    continue
            #elif program_fields['pid'] == 0x0000 or \
            #        program_fields['pid'] == 0x0100 or \
            #        program_fields['pid'] == 0x0101:
            #    continue
            #else:
            #    self.logger.info('Unknown PID {}'.format(program_fields['pid']))                
            prev_pid = program_fields['pid']
        return packet_list
        
    def decode_ts_packet(self, _packet_188):
        fields = {}
        word = struct.unpack('!I', _packet_188[0:4])[0]
        sync = (word & 0xff000000) >> 24
        if sync != 0x47:
            return None

        fields['transport_error_indicator'] = (word & 0x800000) != 0
        # Set when a demodulator can't correct errors from FEC data; indicating the packet is corrupt
        # print transport_error_indicator

        # Set when a PES, PSI, or DVB-MIP packet begins immediately following the header.
        fields['payload_unit_start_indicator'] = (word & 0x400000) != 0

        # "Set when the current packet has a higher priority than other packets with the same PID.
        fields['transport_priority'] = (word & 0x200000) != 0

        # Packet Identifier, describing the payload data.
        fields['pid'] = (word & 0x1fff00) >> 8
        # '00' = Not scrambled.
        # For DVB-CSA and ATSC DES only:[8]
        # '01' (0x40) = Reserved for future use
        # '10' (0x80) = Scrambled with even key
        # '11' (0xC0) = Scrambled with odd key
        fields['scrambling_control'] = (word & 0xc0) >> 6

        # 01 – no adaptation field, payload only,
        # 10 – adaptation field only, no payload,
        # 11 – adaptation field followed by payload,
        # 00 - RESERVED for future use [9]
        fields['adaptation_field_control'] = (word & 0x30) >> 4

        if fields['adaptation_field_control'] == 1:
            has_adapt = False
            has_payload = True
        elif fields['adaptation_field_control'] == 2:
            has_adapt = True
            has_payload = False
        elif fields['adaptation_field_control'] == 3:
            has_adapt = True
            has_payload = True
        else:
            # 00 - RESERVED for future use
            # hence tstools "### Packet PID 14ae has adaptation field control = 0
            #    which is a reserved value (no payload, no adaptation field)"
            # just assume payload, don't spam, and mark it corrupted
            has_adapt = False
            has_payload = True
            fields['corrupted_adaption_control_field'] = True

        # Sequence number of payload packets (0x00 to 0x0F) within each stream (except PID 8191)
        # Incremented per-PID, only when a payload flag is set.
        fields['cont_counter'] = word & 0xf

        payload_start = 5
        if has_adapt:
            adapt_length = struct.unpack('b', bytes([_packet_188[5]]))[0]
            if 6 + adapt_length > len(_packet_188):
                return None

            fields['adapt'] = _packet_188[6:6 + adapt_length]
            payload_start = 6 + adapt_length

        if has_payload:
            fields['payload'] = _packet_188[payload_start:]
        else:
            # No payload here according to the bitfields - save it anyways
            extra = _packet_188[payload_start:]
            if len(extra) != 0:
                fields['corrupt_payload'] = extra

        return fields

    def decode_pmt(self, pid, program, payload):
        t = binascii.b2a_hex(payload)
        if t not in self.type_strings:
            self.type_strings.append(t)

        pcr_pid = struct.unpack("!H", payload[8:10])[0]
        reserved = (pcr_pid & 0xe000) >> 13
        pcr_pid &= 0x1fff
        desc1 = payload[12:]
        #self.logger.debug('###### PMT DESCR {} {}'.format(pcr_pid, desc1))
        #descriptors = decode_descriptors(desc1)


    def decode_pat(self, payload):
        t = binascii.b2a_hex(payload)
        if t not in self.type_strings:
            self.type_strings.append(t)

        # http://www.etherguidesystems.com/Help/SDOs/MPEG/Syntax/TableSections/Pat.aspx

        section_length = (payload[1] & 0xf << 8) | payload[2]  # 12-bit field
        program_map_pids = {}

        # after extra fields (transport_stream_id to last_section_num, by size, minus CRC-32 at end
        program_count = (section_length - 5) / 4 - 1

        if section_length > 20:
            #print(section_length, program_count, len(payload))
            #self.logger.warning('{} {} {}'.format(section_length, program_count, len(payload)))
            # log for corrupted atsc msg
            return program_map_pids


        for i in range(0, int(program_count)):
            at = 8 + (i * 4)  # skip headers, just get to the program numbers table
            program_number = struct.unpack("!H", payload[at:at + 2])[0]
            if at + 2 > len(payload):
                break
            #print(len(payload), at)
            program_map_pid = struct.unpack("!H", payload[at + 2:at + 2 + 2])[0]

            # the pid is only 13 bits, upper 3 bits of this field are 'reserved' (I see 0b111)
            reserved = (program_map_pid & 0xe000) >> 13
            program_map_pid &= 0x1fff

            program_map_pids[program_map_pid] = program_number
            i += 1
        return program_map_pids

