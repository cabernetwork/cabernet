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
        self.atsc_blank_section = b'\x47\x1f\xff\x10\x00'.ljust(188, b'\xff')

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

    def update_sdt_names(self, _sdt_msg, _service_provider, _service_name):
        # must start with x474011  (pid for SDT is x0011
        # update the full msg length 2 bytes with first 4 bits as xF at position 7-8  (includes crc)
        # update descriptor length lower 12 bits at position 20-21 (remaining bytes - crc)
        # x48 service descriptor tag
        # 1 byte length of service provider
        # byte string of the service provider
        # 1 byte length of service name
        # byte string of the service name
        # crc
        if _sdt_msg[:3] != b'\x47\x40\x11':
            self.logger.info('WRONG ATSC MSG {}'.format(bytes(_sdt_msg[:20]).hex()))
            return _sdt_msg

        descr = b'\x01' \
                + utils.set_str(_service_provider, False) \
                + utils.set_str(_service_name, False)
        descr = b'\x48' + utils.set_u8(len(descr)) + descr
        msg = _sdt_msg[8:20] + utils.set_u8(len(descr)) + descr
        length = utils.set_u16(len(msg) + 4 + 0xF000)
        msg = ATSC_SERVICE_DESCR_TABLE_TAG + length + msg
        crc = self.gen_crc_mpeg(msg)
        msg = _sdt_msg[:5] + msg + crc
        msg = msg.ljust(len(_sdt_msg), b'\xFF')
        return msg

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

        # 1bytes = stream_type = x02
        # 3bits = 111 static bits
        # 13bits = elem_PID
        # 4bits = 1111 static bits
        # 12bits = num of descr
        # for each descr

        # crc
        # NOTE: all transmissions had a zero sections transmission
        # search 0x0020.*0001  ...
        # there is one pmt per channel
        # returns an array of msgs to send. one per channel.
        #                                  4740 5016 0002  .....[.,..G@P...
        # 0x0030:  b042 0003 c300 00e0 51f0 1610 06c0 0271  .B......Q......q
        # 0x0040:  c000 0087 06c1 0101 00f2 0005 0447 4139  .............GA9
        # 0x0050:  3402 e051 f003 0601 0281 e054 f012 0504  4..Q.......T....
        # 0x0060:  4143 2d33 810a 0828 05ff 0f00 bf65 6e67  AC-3...(.....eng
        # 0x0070:  47ab 58d1

        # descriptors
        # 10 smoothing_buffer_descriptor
        # f0 1610 06c0 0271 c000 0087 06c1 0101 00f2 0005 0447 4139 34 KDTN-DT KPTD-LD KDTN-ES
        # f0 0810 06c0 bd62 c008 00 KUVN-DT Bounce ESCAPE LAFF KSTR-DT GRIT
        # f0 12 0a04 656e 6700 810a e828 05ff 0f01 bf65 6e67
        # f0 0810 06c0 bd62 c008 00 KTVT-DT StartTV DABL FAVE
        # f0 0605 0447 4139 34 KTXT-DT COMET CHARGE TBD SBN (31)
        # f0 1f05 0447 4139 3487 17c1 0102 00f3 04f1 0f01 656e 6701 0000 0754  562d 5047 2d56 KTXT-DT COMET CHARGE TBD SBN (51)
        # f0 1a05 0447 4139 3487 12c1 0101 00f2 0c01 656e 6701 0000 0454 562d 47 KTXT-DT COMET CHARGE TBD SBN (71)
        # f0 0605 0447 4139 34 KTXT-DT COMET CHARGE TBD SBN (61)
        # f0 3c05 0447 4139 3487 34c2 0101 00f3 0d01 656e 6701 0000
        #   0554 562d 5047 0201 00f4 1c01 656e 6701 0000 1450 4720 
        #   2853 7572 762e 2070 6172 656e 7461 6c65 29 KTXT-DT COMET CHARGE TBD SBN (41)
        # f0 00 TBN_HD Hilsng SMILE Enlace POSITIV (31 41 51 61 71)
        # f0 00 ION qubo IONPlus Shop QVC HSN (31 41 51 61 71 81)
        # f0 0810 06c0 bd62 c008 00 KXAS-DT COZI-TV NBCLX (31 41 51)
        # f0 0810 06c0 bd62 c008 00 KDAF-DT Antenna Court CHARGE (31 41 51 61)
        # f0 0810 06c0 bd62 c008 00 KTXA-DT MeTV ThisTV Circle HSN (31 41 51 61 71)
        # f0 1610 06c0 0271 c000 0087 06c1 0101 00f2 0005 0447 4139 34 KXDA-LD (EBETV) KXDA-LD (ALCANCE) KXDA-LD KXDA-LD (BIBLIATV) (31 41 51 61 71)
        # f0 0810 06c0 bd62 c008 00 DECADES KDFW-DT KDFW_D3 GetTV (31 41 51 61)
        # f0 1a87 12c1 0101 00f2 0c01 656e 6701 0000 0454 562d 4705 0447 4139 34 KERA-HD4 kids Create (31 41 51)
        # f0 00 KFWD BizTV 52_4 SBN JTV CRTV AChurch (31 41 51 61 71 81 91)
        #
        # Assume no base descriptors \xf0 \x00
        # Assume no video stream type descriptor 02 E0 xx F0 00
        # Assume no audio stream type descriptor 81 E0 xx F0 00
        #
        # 1bytes = stream_type = x02
        # 3bits = 111 static bits
        # 13bits = elem_PID
        # 4bits = 1111 static bits
        # 12bits = num of descr
        # for each descr
        #
        # 02 E0 31 F0 00 (31 is the PID)
        # 02 E0 51 F0 05
        # 02 E0 91 F0 0E
        # 02 E0 51 F0 03 06 01 02
        # 02 E0 31 F0 12 06 01 02
        # 02 E0 31 F0 12 06 01 02 86 0D E2 65 6E 67 C1 FF FF 65 6E 67 7E FF FF (x86 CCT)
        # Audio PIDs 34 35 36 44 54
        # 81 E0 74 F0 00 (a3 descr)
        # 81 E0 94 F0 00
        # 05 04 41 43 2D 33 (reg descr optional)
        # 81 E0 35 F0 18 
        # 81 0A 08 28 05 FF 37 01 BF 73 70 61
        # 0A 04 73 70 61 00
        # all audio is x4-x9 where x is the video PID so 31 is 34

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
        # for loop of tables
        # c7 f0df 0000 e100 0000 0013 0000 fffb f400
        # 0000 daf0 0000 04fe 80f0 0000 0060 f000
        # 0100 fd00 f000 0003 adf0 0001 01fd 01f0
        # 0000 0353 f000 0102 fd02 f000 0005 81f0
        # 0001 03fd 03f0 0000 0440 f000 0104 fd04
        # f000 0003 e5f0 0001 05fd 05f0 0000 02fb
        # f000 0106 fd06 f000 0003 99f0 0001 07fd
        # 07f0 0000 0484 f000 0200 fe00 f000 0006
        # d6f0 0002 01fe 01f0 0000 05ea f000 0202
        # fe02 f000 0009 d7f0 0002 03fe 03f0 0000
        # 07b5 f000 0204 fe04 f000 0006 7af0 0002
        # 05fe 05f0 0000 471f fb11 0392 f000 0206
        # fe06 f000 0007 92f0 0002 07fe 07f0 0000
        # 0899 f000 0301 fffb e000 0003 d3f0 00f0
        # 0016 e673 47

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

    def format_video_packets(self, _msgs):
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

        # for now assume the msgs are less than 1316
        if len(_msgs) > 7:
            self.logger.error('ATSC: TOO MANY MESSAGES={}'.format(len(_msgs)))
            return None
        for i in range(len(_msgs)):
            if len(_msgs[i]) > 188:
                self.logger.error('ATSC: MESSAGE LENGTH TOO LONG={}'.format(len(_msgs[i])))
                return None
            else:
                sections[i] = _msgs[i].ljust(188, b'\xff')

        return b''.join(sections)

        # TBD need to handle large msg and more than 7 msgs
