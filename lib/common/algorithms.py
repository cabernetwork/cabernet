#  pycrc -- parameterisable CRC calculation utility and C source code generator
#
#  Copyright (c) 2006-2017  Thomas Pircher  <tehpeh-web@tty1.net>
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to
#  deal in the Software without restriction, including without limitation the
#  rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
#  sell copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#  FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
#  IN THE SOFTWARE.


"""
CRC algorithms implemented in Python.
If you want to study the Python implementation of the CRC routines, then this
is a good place to start from.

The algorithms Bit by Bit, Bit by Bit Fast and Table-Driven are implemented.

This module can also be used as a library from within Python.

Examples
========

This is an example use of the different algorithms:

    from pycrc.algorithms import Crc

    crc = Crc(width = 16, poly = 0x8005,
            reflect_in = True, xor_in = 0x0000,
            reflect_out = True, xor_out = 0x0000)
    print("{0:#x}".format(crc.bit_by_bit("123456789")))
    print("{0:#x}".format(crc.bit_by_bit_fast("123456789")))
    print("{0:#x}".format(crc.table_driven("123456789")))
"""


class Crc(object):
    """
    A base class for CRC routines.
    """
    # pylint: disable=too-many-instance-attributes

    def __init__(self, width, poly, reflect_in, xor_in, reflect_out, xor_out, table_idx_width=None, slice_by=1):
        """The Crc constructor.

        The parameters are as follows:
            width
            poly
            reflect_in
            xor_in
            reflect_out
            xor_out
        """
        # pylint: disable=too-many-arguments

        self.width = width
        self.poly = poly
        self.reflect_in = reflect_in
        self.xor_in = xor_in
        self.reflect_out = reflect_out
        self.xor_out = xor_out
        self.tbl_idx_width = table_idx_width
        self.slice_by = slice_by

        self.msb_mask = 0x1 << (self.width - 1)
        self.mask = ((self.msb_mask - 1) << 1) | 1
        if self.tbl_idx_width is not None:
            self.tbl_width = 1 << self.tbl_idx_width
        else:
            self.tbl_idx_width = 8
            self.tbl_width = 1 << self.tbl_idx_width

        self.direct_init = self.xor_in
        self.nondirect_init = self.__get_nondirect_init(self.xor_in)
        if self.width < 8:
            self.crc_shift = 8 - self.width
        else:
            self.crc_shift = 0

    def __get_nondirect_init(self, init):
        """
        return the non-direct init if the direct algorithm has been selected.
        """
        crc = init
        for dummy_i in range(self.width):
            bit = crc & 0x01
            if bit:
                crc ^= self.poly
            crc >>= 1
            if bit:
                crc |= self.msb_mask
        return crc & self.mask

    def reflect(self, data, width):
        """
        reflect a data word, i.e. reverts the bit order.
        """
        # pylint: disable=no-self-use

        res = data & 0x01
        for dummy_i in range(width - 1):
            data >>= 1
            res = (res << 1) | (data & 0x01)
        return res

    def bit_by_bit(self, in_data):
        """
        Classic simple and slow CRC implementation.  This function iterates bit
        by bit over the augmented input message and returns the calculated CRC
        value at the end.
        """
        # If the input data is a string, convert to bytes.
        if isinstance(in_data, str):
            in_data = bytearray(in_data, 'utf-8')

        reg = self.nondirect_init
        for octet in in_data:
            if self.reflect_in:
                octet = self.reflect(octet, 8)
            for i in range(8):
                topbit = reg & self.msb_mask
                reg = ((reg << 1) & self.mask) | ((octet >> (7 - i)) & 0x01)
                if topbit:
                    reg ^= self.poly

        for i in range(self.width):
            topbit = reg & self.msb_mask
            reg = ((reg << 1) & self.mask)
            if topbit:
                reg ^= self.poly

        if self.reflect_out:
            reg = self.reflect(reg, self.width)
        return (reg ^ self.xor_out) & self.mask

    def bit_by_bit_fast(self, in_data):
        """
        This is a slightly modified version of the bit-by-bit algorithm: it
        does not need to loop over the augmented bits, i.e. the Width 0-bits
        wich are appended to the input message in the bit-by-bit algorithm.
        """
        # If the input data is a string, convert to bytes.
        if isinstance(in_data, str):
            in_data = bytearray(in_data, 'utf-8')

        reg = self.direct_init
        for octet in in_data:
            if self.reflect_in:
                octet = self.reflect(octet, 8)
            for i in range(8):
                topbit = reg & self.msb_mask
                if octet & (0x80 >> i):
                    topbit ^= self.msb_mask
                reg <<= 1
                if topbit:
                    reg ^= self.poly
            reg &= self.mask
        if self.reflect_out:
            reg = self.reflect(reg, self.width)
        return reg ^ self.xor_out

    def gen_table(self):
        """
        This function generates the CRC table used for the table_driven CRC
        algorithm.  The Python version cannot handle tables of an index width
        other than 8.  See the generated C code for tables with different sizes
        instead.
        """
        table_length = 1 << self.tbl_idx_width
        tbl = [[0 for i in range(table_length)] for j in range(self.slice_by)]
        for i in range(table_length):
            reg = i
            if self.reflect_in:
                reg = self.reflect(reg, self.tbl_idx_width)
            reg = reg << (self.width - self.tbl_idx_width + self.crc_shift)
            for dummy_j in range(self.tbl_idx_width):
                if reg & (self.msb_mask << self.crc_shift) != 0:
                    reg = (reg << 1) ^ (self.poly << self.crc_shift)
                else:
                    reg = (reg << 1)
            if self.reflect_in:
                reg = self.reflect(reg >> self.crc_shift, self.width) << self.crc_shift
            tbl[0][i] = (reg >> self.crc_shift) & self.mask

        for j in range(1, self.slice_by):
            for i in range(table_length):
                tbl[j][i] = (tbl[j - 1][i] >> 8) ^ tbl[0][tbl[j - 1][i] & 0xff]
        return tbl

    def table_driven(self, in_data):
        """
        The Standard table_driven CRC algorithm.
        """
        # pylint: disable = line-too-long

        # If the input data is a string, convert to bytes.
        if isinstance(in_data, str):
            in_data = bytearray(in_data, 'utf-8')

        tbl = self.gen_table()

        if not self.reflect_in:
            reg = self.direct_init << self.crc_shift
            for octet in in_data:
                tblidx = ((reg >> (self.width - self.tbl_idx_width + self.crc_shift)) ^ octet) & 0xff
                reg = ((reg << (self.tbl_idx_width - self.crc_shift)) ^
                       (tbl[0][tblidx] << self.crc_shift)) & (self.mask << self.crc_shift)
            reg = reg >> self.crc_shift
        else:
            reg = self.reflect(self.direct_init, self.width)
            for octet in in_data:
                tblidx = (reg ^ octet) & 0xff
                reg = ((reg >> self.tbl_idx_width) ^ tbl[0][tblidx]) & self.mask
            reg = self.reflect(reg, self.width) & self.mask

        if self.reflect_out:
            reg = self.reflect(reg, self.width)
        return reg ^ self.xor_out
