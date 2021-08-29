#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Show PSIP data (and other packets) from MPEG TS streams from ATSC broadcasts
# Warning: very rough, incomplete, you're probably better off using VLC 3.0 (show Media Information,
# go to Codec Details, then scroll down to the EPG (electronic program guide) sections)

import sys
import struct
import binascii

type_strings = []


def decode_ts_packet(packet):
    fields = {}

    # 32-bit field
    # comments from https://en.wikipedia.org/wiki/MPEG_transport_stream#Packet
    word = struct.unpack('!I', packet[0:4])[0]

    # Bit pattern of 0x47 (ASCII char 'G')
    sync = (word & 0xff000000) >> 24
    if sync != 0x47:
        print('Bad packet sync byte (desync?):', [packet])
        raise SystemExit

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
        adapt_length = struct.unpack('b', bytes([packet[5]]))[0]
        if 6 + adapt_length > len(packet):
            print("adaptation field beyond length of packet", [packet], adapt_length, len(packet))
            raise SystemExit

        fields['adapt'] = packet[6:6 + adapt_length]
        payload_start = 6 + adapt_length
        # TODO: decode Adaptation Field Format

    if has_payload:
        fields['payload'] = packet[payload_start:]
    else:
        # No payload here according to the bitfields - save it anyways
        extra = packet[payload_start:]
        if len(extra) != 0:
            fields['corrupt_payload'] = extra

    return fields


def ascii_dump(s):
    s2 = ''
    printable = 0
    for c in s:
        if ord(' ') <= c <= ord('~'):
            s2 += str(c)
            printable += 1
        else:
            s2 += '.'
    return s2, printable


def decode_pat(payload):
    t = binascii.b2a_hex(payload)
    if t not in type_strings:
        type_strings.append(t)

    print('PAT', binascii.b2a_hex(payload))
    # http://www.etherguidesystems.com/Help/SDOs/MPEG/Syntax/TableSections/Pat.aspx

    section_length = (payload[1] & 0xf << 8) | payload[2]  # 12-bit field
    print(section_length)

    # after extra fields (transport_stream_id to last_section_num, by size, minus CRC-32 at end
    program_count = (section_length - 5) / 4 - 1

    program_map_pids = {}

    print("PAT:")
    for i in range(0, int(program_count)):
        at = 8 + (i * 4)  # skip headers, just get to the program numbers table
        program_number = struct.unpack("!H", payload[at:at + 2])[0]
        if at + 2 > len(payload):
            break
        program_map_pid = struct.unpack("!H", payload[at + 2:at + 2 + 2])[0]

        # the pid is only 13 bits, upper 3 bits of this field are 'reserved' (I see 0b111)
        reserved = (program_map_pid & 0xe000) >> 13
        program_map_pid &= 0x1fff

        print(i, "%.4x %.4x" % (program_number, program_map_pid))
        program_map_pids[program_map_pid] = program_number
        i += 1
    return program_map_pids


DESC_NAMES = {
    # http://www.etherguidesystems.com/Help/SDOs/MPEG/semantics/mpeg-2/descriptors/Default.aspx
    0: 'Reserved',
    1: 'Reserved',
    2: 'video_stream_descriptor',  # 13818-1
    3: 'audio_stream_descriptor',  # '13818-1
    4: 'hierarchy_descriptor:',  # 13818-1
    5: 'registration_descriptor',  # 13818-1
    6: 'data_stream_alignment_descriptor',  # 13818-1
    7: 'target_background_grid_descriptor',  # 13818-1
    8: 'video_window_descriptor',  # 13818-1
    9: 'CA_descriptor',  # 13818-1
    10: 'ISO_639_language_descriptor',  # 13818-1
    11: 'system_clock_descriptor',  # 13818-1
    12: 'multiplex_buffer_utilization_descriptor',  # 13818-1
    13: 'copyright_descriptor',  # 13818-1
    14: 'maximum_bitrate_descriptor',  # 13818-1
    15: 'private_data_indicator_descriptor',  # 13818-1
    16: 'smoothing_buffer_descriptor',  # 13818-1
    17: 'STD_descriptor',  # 3818-1
    18: 'IBP_descriptor:',  # 13818-1
    27: 'MPEG-4_video_descriptor',  # 3818-1
    28: 'MPEG-4_audio_descriptor',  # 13818-1
    29: 'IOD_descriptor',  # 13818-1
    30: 'SL_descriptor',  # 14496-1
    31: 'FMC_descriptor',  # 13818-1
    32: 'External_ES_ID_descriptor:',  # 13818-1
    33: 'MuxCode_descriptor',  # 13818-1
    34: 'FmxBufferSize_descriptor:',  # 14496
    35: 'MultiplexBuffer_descriptor',  # 14496
    36: 'FlexMuxTiming_descriptor',  # 14496
    # http://www.etherguidesystems.com/Help/SDOs/atsc/semantics/descriptors/Default.aspx
    129: 'AC-3 Descriptor',  # PMT, EIT	 	A/52
    20: 'association_tag descriptor',  # A/52
    173: 'ATSC Private Information descriptor',  # PMT, EIT	1 or more	A/52
    134: 'Caption Service Descriptor',  # PMT, EIT	 	A/65
    163: 'Component name descriptor',  # PMT	 	A/65
    135: 'Content Advisory Descriptor',  # PMT, EIT	 	A/65
    198: 'Content Identifier descriptor',  # PMT, EIT	 	A/57
    164: 'Data Service descriptor',  # PMT, EIT	 	A/65
    166: 'Download descriptor',  # PMT, EIT	 	A/90
    169: 'DCC Arriving request descriptor',  # DCCT	 	A/65
    168: 'DCC Departing request descriptor',  # DCCT	 	A/65
    178: 'Enhanced Signaling descriptor',  # PMT	 	A/53
    160: 'Extended Channel name descriptor',  # VCT	 	A/65
    167: 'Multiprotocol Encapsulation descriptor',  # A/90
    165: 'pid_count descriptor',  # VCT	 	A/65
    171: 'Genre descriptor',  # VCT	 	A/65
    170: 'Redistribution Control descriptor',  # EIT, PMT	 	A/65
    161: 'Service location descriptor',  # VCT	 	A/65
    128: 'Stuffing Descriptor',  # any	 	A/65
    162: 'Time-shifted service descriptor',  # VCT	 	A/65hdtv $
}


# http://www.etherguidesystems.com/Help/SDOs/MPEG/semantics/mpeg-2/descriptor__loop.aspx
# "A descriptor() designation in a table denotes the location of a
# descriptor loop that may contain zero or more individual descriptors"
# http://www.etherguidesystems.com/Help/SDOs/MPEG/semantics/mpeg-2/descriptors/Default.aspx
# a simple repeated type(tag)-length-value format
def decode_descriptors(data):
    at = 0
    descriptors = {}

    while True:
        if at + 2 > len(data):
            break

        tag = data[at]
        at += 1
        length = data[at]
        at += 1
        value = data[at:at + length]
        at += length

        name = DESC_NAMES.get(tag)
        if name is None:
            name = 'unknown-%d' % (tag,)
        print("descriptor %d (%s) %s" % (tag, name, [value]))
        descriptors[name] = value

    return descriptors


# http://www.etherguidesystems.com/Help/SDOs/MPEG/Syntax/TableSections/PMTs.aspx
def decode_pmt(pid, program, payload):
    t = binascii.b2a_hex(payload)
    if t not in type_strings:
        type_strings.append(t)
    print('PMT for Program %d at PID %.4x: %s' % (pid, program, [payload]))

    pcr_pid = struct.unpack("!H", payload[8:10])[0]
    reserved = (pcr_pid & 0xe000) >> 13
    pcr_pid &= 0x1fff
    # http://www.etherguidesystems.com/Help/SDOs/MPEG/semantics/mpeg-2/PCR_PID.aspx
    # program clock reference, not too interesting
    # print "PCR PID: %.4x" % (pcr_pid,)

    desc1 = payload[12:]
    descriptors = decode_descriptors(desc1)
    # TODO: parse descriptors inside loop (per stream), after first descriptor list


def decode_psip(payload):
    print('Found PSIP full', [payload])

    table_id = ord(payload[0])
    # print 'PSIP table %.2x' % (table_id,)

    # TODO: decode these
    # https://web.archive.org/web/20070221145014/http://www.atsc.org/standards/a_69.pdf pg. 84 table m.1
    # Table M.1 Bit Stream Syntax for the Master Guide Table
    if table_id == 0xc7:
        print('PSIP MGT', [payload])
        decode_mgt(payload)
    # Table M.2 Bit Stream Syntax for the Terrestrial Virtual Channel Table
    elif table_id == 0xc8:
        print('PSIP VCT', payload.encode('hex'), '\n', 'PSIP VCT', [payload])
        # note: for(i=0; i<num_channels_in_section; i++) {
        #   short_name 7*16 unicode BMP - is 16-bit Unicode! K\x00I\x00C\x00U\x00-\x00H\x00D = KICU-HD 
        decode_vct(payload)
    # Table M.3 Bit Stream Syntax for the Event Information Table
    elif table_id == 0xcb:
        print('PSIP EIT', [payload])
    # Table M.4 Bit Stream Syntax for the Extended Text Table
    elif table_id == 0xcc:
        print('PSIP ETT', [payload])
    # Table M.5 Bit Stream Syntax for the System Time Table
    elif table_id == 0xcd:
        print('PSIP STT', [payload])
    # Table M.6 Bit Stream Syntax for the Rating Region Table
    elif table_id == 0xca:
        print('PSIP RRT', [payload])
    # Table M.7 Bit Stream Syntax for the Directed Channel Change Table
    elif table_id == 0xd3:
        print('PSIP DCCT', [payload])
    else:
        print('PSIP unknown table id %.2x' % (table_id,))


def decode_mgt_table_type(x):
    # table_type here is a 16-bit type:
    # https://web.archive.org/web/20070423004711/http://www.atsc.org/standards/a_65cr1_with_amend_1.pdf
    # Table 6.3 Table Types, pg. 27
    if x == 0x0000:
        return 'Terrestrial VCT with current_next_indicator=1'
    elif x == 0x0001:
        return 'Terrestrial VCT with current_next_indicator=0'
    elif x == 0x0002:
        return 'Cable VCT with current_next_indicator=1'
    elif x == 0x0003:
        return 'Cable VCT with current_next_indicator=0'
    elif x == 0x004:
        return 'Channel ETT'
    elif x == 0x005:
        return 'DCCSCT'
    # elif x >= 0x006 and x <= 0x00ff:
    #    return 'Reserved for future ATSC use-%.4x' % (x,)
    elif 0x0100 <= x <= 0x017f:
        return 'EIT-%d' % (x - 0x0100)
    # elif x >= 0x0180 and x <= 0x01ff:
    #    return 'Reserved for future ATSC use-%.4x' % (x,)
    elif 0x0200 <= x <= 0x027f:
        return 'Event ETT-%d' % (x - 0x0200)
    # elif x >= 0x0280 and x <= 0x0300:
    #    return 'Reserved for future ATSC use-%.4x' % (x,)
    elif 0x0301 <= x <= 0x03ff:
        return 'RRT with rating_region-%d' % (x - 0x0301)
    elif 0x0400 <= x <= 0x0fff:
        return 'User private-%.4x' % (x,)
    # elif x >= 0x1000 and x <= 0x13ff:
    #    return 'Reserved for future ATSC use-%.4x' % (x,)
    elif 0x1400 <= x <= 0x14ff:
        return 'DCCT with dcc_id-%d' % (x - 0x1400)
    # elif x >= 0x1500 and x <= 0x1fff:
    #    return 'Reserved for future ATSC use-%.4x' % (x,)
    else:
        return 'Reserved for future ATSC use-%.4x' % (x,)


psip_table_pids = {}


# Table M.1 Bit Stream Syntax for the Master Guide Table
def decode_mgt(payload):
    t = binascii.b2a_hex(payload)
    if t not in type_strings:
        type_strings.append(t)
    print('PSIP MGT', payload.encode('hex'))
    assert payload[0] == '\xc7', 'decodeMGT not MGT'

    section_length = struct.unpack('!H', payload[1:3])[0]
    section_length &= 0xfff
    print('PSIP MGT section_length', section_length)

    table_id_extension = struct.unpack('!H', payload[3:5])[0]
    print('PSIP MGT table_id_extension', table_id_extension)

    # reserved, version_number, current_next_indicator
    version_etc = ord(payload[5])
    print('PSIP MGT version_etc %.2x' % (version_etc,))

    # 0x00 in spec
    section_number = ord(payload[6])
    assert section_number == 0, 'decodeMGT section_number != 0'

    last_section_number = ord(payload[7])
    assert last_section_number == 0, 'decodeMGT last_section_number != 0'

    protocol_version = ord(payload[8])
    print('PSIP MGT protocol_version', protocol_version)

    # This 16-bit unsigned has a range of 6 – 370 (for terrestrial) and 2 – 370 for cable.
    tables_defined = struct.unpack('!H', payload[9:11])[0]
    print('PSIP MGT tables_defined', tables_defined)

    at = 11
    tables = []
    for i in range(0, tables_defined):
        if at > len(payload):
            # off end of payload TODO: probably have a bug in stitching together packets
            break

        table_type = struct.unpack('!H', payload[at:at + 2])[0]
        table_type_name = decode_mgt_table_type(table_type)
        print('PSIP MGT %i table_type %.4x %s' % (i, table_type, table_type_name))
        at += 2
        # table_type here is a 16-bit type:
        # https://web.archive.org/web/20070423004711/http://www.atsc.org/standards/a_65cr1_with_amend_1.pdf
        # Table 6.3 Table Types, pg. 27

        table_type_pid = struct.unpack('!H', payload[at:at + 2])[0]
        table_type_pid &= 0x1fff
        print('PSIP MGT %i table_type_pid %.4x' % (i, table_type_pid))
        at += 2

        # reserved, table_type_version_number
        reserved_version = ord(payload[at])
        print('PSIP MGT %i reserved_version %.2x' % (i, reserved_version))
        at += 1

        # number of bytes of the table in the referenced pid
        if at + 4 > len(payload):
            break
        number_bytes = struct.unpack('!I', payload[at:at + 4])[0]
        print('PSIP MGT %i number_bytes %d' % (i, number_bytes))
        at += 4

        table_type_descriptors_length = struct.unpack('!H', payload[at:at + 2])[0]
        table_type_descriptors_length &= 0xfff
        print('PSIP MGT %i table_type_descriptors_length %d' % (i, table_type_descriptors_length))
        at += 2

        # skip over variable-length descriptors data TODO: decode?
        descriptors_data = payload[at:at + table_type_descriptors_length]
        at += table_type_descriptors_length

        # save the pid, then we can recognize EIT and ETT tables (non-0x1ffb PIDs)
        psip_table_pids[table_type_pid] = table_type_name

    return tables  # TODO: other info?


# Table M.2 Bit Stream Syntax for the Terrestrial Virtual Channel Table
def decode_vct(payload):
    t = binascii.b2a_hex(payload)
    if t not in type_strings:
        type_strings.append(t)
    num_channels_in_section = ord(payload[9:10])
    print('VCT number of channels:', num_channels_in_section)
    short_name = payload[11:11 + 13]
    short_name = short_name.replace('\0', '')  # TODO: decode UTF-16 BE
    print('VCT channel short_name:', short_name)

    chinfo = struct.unpack("!I", payload[24:24 + 4])[0]
    print("VCT chinfo %.4x" % (chinfo,))
    reserved = (chinfo & 0xf0000000) >> 28
    assert reserved == 0xf, '%x != 0xf in chinfo' % (reserved,)

    major_channel_number = (chinfo & 0x0cff0000) >> 18
    minor_channel_number = (chinfo & 0x000cff00) >> 8
    print("VCT virtual channel %d-%d" % (major_channel_number, minor_channel_number))

    modulation_mode = chinfo & 0xff
    if modulation_mode == 4:
        modulation_mode_name = '8VSB'
    else:
        modulation_mode_name = None
    print("VCT modulation mode", modulation_mode, modulation_mode_name)

    carrier_frequency = struct.unpack("!I", payload[28:28 + 4])[0]
    print("VCT carrier frequency", carrier_frequency)

    # "The FCC will12 issue a TSID for each digital station upon licensing.", odd for digital, even analog
    channel_tsid = struct.unpack("!H", payload[32:32 + 2])[0]
    print("VCT channel TSID", channel_tsid)

    program_number = struct.unpack("!H", payload[34:34 + 2])[0]
    print("VCT program number", program_number)

    # EMT_location, access_controlled, hidden, reserved, hide_guide, reserved, service_type
    flags = struct.unpack("!H", payload[34:34 + 2])[0]
    print("VCT misc flags %.4x" % (flags,))
    service_type = flags & 0x3f
    # a_69.pdf page 29
    # 1 denotes an NTSC analog service
    # 2 denotes an ATSC full digital TV service including video, audio (if present) and data (if present)
    # 3 denotes an ATSC audio and data (if present) service
    # 4 denotes a ATSC data service
    service_types = {
        1: 'NTSC analog',
        2: 'ATSC full digital',
        3: 'ATSC audio and data',
        4: 'ATSC data'
    }

    print("VCT service type", service_type, service_types.get(service_type))

    source_id = struct.unpack("!H", payload[36:36 + 2])[0]
    # "The source_id is a critical internal index13 for representing the particular logical channel.
    # Broadcasters can assign arbitrary source_id numbers from 1 to 4095 for non registered sources14"
    print("VCT source id", source_id, ("%.4x" % source_id))

    desc_len = struct.unpack("!H", payload[38:38 + 2])[0]
    # 6 bits top reserved, lower 10 are descriptors_length
    desc_len &= 0x3ff
    print("VCT descriptors length", desc_len)

    print("VCT descriptors", decode_descriptors(payload[40:40 + desc_len]))

    # TODO: decode all in loop


# Table M.3 Bit Stream Syntax for the Event Information Table
def decode_eit(payload, table_type_name):
    t = binascii.b2a_hex(payload)
    if t not in type_strings:
        type_strings.append(t)
    # print 'EIT',table_type_name,[payload]
    # not bothering to fully decode table here, just dumping ASCII text good enough to see program names...
    # example:
    # EIT EIT-0 ('............D........eng....Gag Concert.....eng.?....
    # (../..eng..D........eng....School 2013.....eng.?....
    # (../..eng..D........eng....Marry Me, Mary.....eng.?....
    # (../..eng..............', 75)
    # TODO: fully parse

    print('EIT', table_type_name, ascii_dump(payload))


def main():
    if len(sys.argv) > 1:
        f = open(sys.argv[1], 'rb')
    else:
        f = sys.stdin

    packet_count = 0

    program_map_pids = None
    accumulated_1ffb_payload = None

    while True:
        # Packets are all 188 bytes
        # https://en.wikipedia.org/wiki/MPEG_transport_stream#Important_elements_of_a_transport_stream
        packet = f.read(188)
        if len(packet) == 0:
            break

        if len(packet) != 188:
            print("%d != %d" % (len(packet), 188))
            print("Incomplete packet:", [packet])
            raise SystemExit

        fields = decode_ts_packet(packet)

        if fields['transport_error_indicator']:
            # print 'corrupted'
            # skip corrupted packets TODO: although could TRY to decode, usually fruitless
            continue

        # the PAT, of pid 0000, is where it all begins
        if fields['pid'] == 0x0000:
            program_map_pids = decode_pat(fields['payload'])

        # once we know the PAT, watch for pids that match it
        if program_map_pids and fields['pid'] in program_map_pids.keys():
            program = program_map_pids[fields['pid']]
            decode_pmt(fields['pid'], program, fields['payload'])
            print('PAYLOAD')
            print(binascii.b2a_hex(fields['payload']))
            print('PACKET')
            print(binascii.b2a_hex(packet))

        # http://www.bretl.com/mpeghtml/ATSCPSIP.HTM
        # "The base tables (Sytem Time Table, STT; Rating Region table, RRT;
        # Master Guide Table, MGT; and Virtual Channel Table, VCT)
        # are all labeled with the base packet ID (base PID), 0x1FFB."
        # Wikipedia confusingly labels 0x1ffb (8187)
        # https://en.wikipedia.org/wiki/MPEG_transport_stream#Packet_Identifier_.28PID.29
        # as "Used by DigiCipher 2/ATSC MGT metadata"
        # (well, I found it confusing - sounded like it was for encryption, but actually used by ATSC for PSIP!)
        # MGT = Master Guide Table, links to all other tables, example:
        # http://pastebin.com/XNArF3QZ http://archive.is/tSbne
        if fields['pid'] == 0x1ffb:
            print('Found 1ffb psip', fields)
            if fields['payload_unit_start_indicator']:  # TODO: reconstruct all packets
                if accumulated_1ffb_payload and len(accumulated_1ffb_payload) != 0:
                    # when see start of next, decode previous, if have one
                    # accumulated_1ffb_payload

                    def trim_array(a):
                        s1 = ''
                        started = False
                        for elem in a:
                            if elem is not None:
                                s1 += elem
                                started = True
                            else:
                                if started:
                                    # print 'Skipping PSIP MGT with corrupted packets',[s]
                                    #: maybe try partial decode anyway,
                                    # but for now hoping get complete uncorrupted stream later
                                    # return False # holes, not full decode
                                    pass  # TODO?
                        return s1

                    print('Accumulated 1ffb psip', accumulated_1ffb_payload)
                    full = trim_array(accumulated_1ffb_payload)
                    if full:
                        decode_psip(full)

                accumulated_1ffb_payload = [None] * 16

            if accumulated_1ffb_payload is not None:  # if didn't start in middle (only accumulate full start->end)
                accumulated_1ffb_payload[fields['cont_counter']] = fields['payload']

        elif fields['pid'] in psip_table_pids.keys():
            table_type_name = psip_table_pids[fields['pid']]
            print('TABLE TYPE NAME %.4x %s' % (fields['pid'], table_type_name))

            if table_type_name == 'Channel EIT' or table_type_name.startswith('EIT-'):
                if 'payload' in fields:
                    # Event Information Tables
                    decode_eit(fields['payload'], table_type_name)
            else:
                # TODO
                pass

        if fields.get('payload'):
            s, printable = ascii_dump(fields['payload'])
            # show packet payloads that probably are text
            if printable > 100:
                print("PID w/ text: %.4x %s" % (fields['pid'], s))
                # print [fields['payload']]

        packet_count += 1
        if packet_count % 100000 == 0:
            print('#####################################################################')
            print('', file=sys.stderr)
            for t in type_strings:
                print(t, file=sys.stderr)
            print('#####################################################################')

    print("Read %s packets\n\n" % (packet_count,))
    print('#####################################################################')
    for t in type_strings:
        print(t, file=sys.stderr)
    print('#####################################################################\n\n')


# TODO: decode by packet identifiers
# https://en.wikipedia.org/wiki/MPEG_transport_stream#Packet_Identifier_.28PID.29
# 32-8186   0x0020-0x1FFA   May be assigned as needed to Program Map Tables, elementary streams and other data tables
# 8188-8190 0x1FFC-0x1FFE   May be assigned as needed to Program Map Tables, elementary streams and other data tables
# PAT (pid 0000) -> 
# PMT
# NIT (from PAT or 0x0010)
# ./tstools/bin/tsreport mpeg.ts -justpid 0x1e00 |grep -v adapt|unhex

main()
