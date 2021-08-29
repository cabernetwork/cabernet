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
Collection of CRC models. This module contains the CRC models known to pycrc.

To print the parameters of a particular model:

    import pycrc.models as cm

    models = cm.CrcModels()
    print(", ".join(models.names()))
    m = models.get_params("crc-32")
    if m != None:
        print("Width:        {width:d}".format(**m))
        print("Poly:         {poly:#x}".format(**m))
        print("ReflectIn:    {reflect_in}".format(**m))
        print("XorIn:        {xor_in:#x}".format(**m))
        print("ReflectOut:   {reflect_out}".format(**m))
        print("XorOut:       {xor_out:#x}".format(**m))
        print("Check:        {check:#x}".format(**m))
    else:
        print("model not found.")
"""


class CrcModels(object):
    """
    CRC Models.

    All models are defined as constant class variables.
    """

    models = []

    models.append({
        'name':         'crc-5',
        'width':         5,
        'poly':          0x05,
        'reflect_in':    True,
        'xor_in':        0x1f,
        'reflect_out':   True,
        'xor_out':       0x1f,
        'check':         0x19,
    })
    models.append({
        'name':         'crc-8',
        'width':         8,
        'poly':          0x07,
        'reflect_in':    False,
        'xor_in':        0x0,
        'reflect_out':   False,
        'xor_out':       0x0,
        'check':         0xf4,
    })
    models.append({
        'name':         'dallas-1-wire',
        'width':         8,
        'poly':          0x31,
        'reflect_in':    True,
        'xor_in':        0x0,
        'reflect_out':   True,
        'xor_out':       0x0,
        'check':         0xa1,
    })
    models.append({
        'name':         'crc-12-3gpp',
        'width':         12,
        'poly':          0x80f,
        'reflect_in':    False,
        'xor_in':        0x0,
        'reflect_out':   True,
        'xor_out':       0x0,
        'check':         0xdaf,
    })
    models.append({
        'name':         'crc-15',
        'width':         15,
        'poly':          0x4599,
        'reflect_in':    False,
        'xor_in':        0x0,
        'reflect_out':   False,
        'xor_out':       0x0,
        'check':         0x59e,
    })
    models.append({
        'name':         'crc-16',
        'width':         16,
        'poly':          0x8005,
        'reflect_in':    True,
        'xor_in':        0x0,
        'reflect_out':   True,
        'xor_out':       0x0,
        'check':         0xbb3d,
    })
    models.append({
        'name':         'crc-16-usb',
        'width':         16,
        'poly':          0x8005,
        'reflect_in':    True,
        'xor_in':        0xffff,
        'reflect_out':   True,
        'xor_out':       0xffff,
        'check':         0xb4c8,
    })
    models.append({
        'name':         'crc-16-modbus',
        'width':         16,
        'poly':          0x8005,
        'reflect_in':    True,
        'xor_in':        0xffff,
        'reflect_out':   True,
        'xor_out':       0x0,
        'check':         0x4b37,
    })
    models.append({
        'name':         'crc-16-genibus',
        'width':         16,
        'poly':          0x1021,
        'reflect_in':    False,
        'xor_in':        0xffff,
        'reflect_out':   False,
        'xor_out':       0xffff,
        'check':         0xd64e,
    })
    models.append({
        'name':         'crc-16-ccitt',
        'width':         16,
        'poly':          0x1021,
        'reflect_in':    False,
        'xor_in':        0x1d0f,
        'reflect_out':   False,
        'xor_out':       0x0,
        'check':         0xe5cc,
    })
    models.append({
        'name':         'r-crc-16',
        'width':         16,
        'poly':          0x0589,
        'reflect_in':    False,
        'xor_in':        0x0,
        'reflect_out':   False,
        'xor_out':       0x0001,
        'check':         0x007e,
    })
    models.append({
        'name':         'kermit',
        'width':         16,
        'poly':          0x1021,
        'reflect_in':    True,
        'xor_in':        0x0,
        'reflect_out':   True,
        'xor_out':       0x0,
        'check':         0x2189,
    })
    models.append({
        'name':         'x-25',
        'width':         16,
        'poly':          0x1021,
        'reflect_in':    True,
        'xor_in':        0xffff,
        'reflect_out':   True,
        'xor_out':       0xffff,
        'check':         0x906e,
    })
    models.append({
        'name':         'xmodem',
        'width':         16,
        'poly':          0x1021,
        'reflect_in':    False,
        'xor_in':        0x0,
        'reflect_out':   False,
        'xor_out':       0x0,
        'check':         0x31c3,
    })
    models.append({
        'name':         'zmodem',
        'width':         16,
        'poly':          0x1021,
        'reflect_in':    False,
        'xor_in':        0x0,
        'reflect_out':   False,
        'xor_out':       0x0,
        'check':         0x31c3,
    })
    models.append({
        'name':         'crc-24',
        'width':         24,
        'poly':          0x864cfb,
        'reflect_in':    False,
        'xor_in':        0xb704ce,
        'reflect_out':   False,
        'xor_out':       0x0,
        'check':         0x21cf02,
    })
    models.append({
        'name':         'crc-32',
        'width':         32,
        'poly':          0x4c11db7,
        'reflect_in':    True,
        'xor_in':        0xffffffff,
        'reflect_out':   True,
        'xor_out':       0xffffffff,
        'check':         0xcbf43926,
    })
    models.append({
        'name':         'crc-32c',
        'width':         32,
        'poly':          0x1edc6f41,
        'reflect_in':    True,
        'xor_in':        0xffffffff,
        'reflect_out':   True,
        'xor_out':       0xffffffff,
        'check':         0xe3069283,
    })
    models.append({
        'name':         'crc-32-mpeg',
        'width':         32,
        'poly':          0x4c11db7,
        'reflect_in':    False,
        'xor_in':        0xffffffff,
        'reflect_out':   False,
        'xor_out':       0x0,
        'check':         0x0376e6e7,
    })
    models.append({
        'name':         'crc-32-bzip2',
        'width':         32,
        'poly':          0x04c11db7,
        'reflect_in':    False,
        'xor_in':        0xffffffff,
        'reflect_out':   False,
        'xor_out':       0xffffffff,
        'check':         0xfc891918,
    })
    models.append({
        'name':         'posix',
        'width':         32,
        'poly':          0x4c11db7,
        'reflect_in':    False,
        'xor_in':        0x0,
        'reflect_out':   False,
        'xor_out':       0xffffffff,
        'check':         0x765e7680,
    })
    models.append({
        'name':         'jam',
        'width':         32,
        'poly':          0x4c11db7,
        'reflect_in':    True,
        'xor_in':        0xffffffff,
        'reflect_out':   True,
        'xor_out':       0x0,
        'check':         0x340bc6d9,
    })
    models.append({
        'name':         'xfer',
        'width':         32,
        'poly':          0x000000af,
        'reflect_in':    False,
        'xor_in':        0x0,
        'reflect_out':   False,
        'xor_out':       0x0,
        'check':         0xbd0be338,
    })
    models.append({
        'name':         'crc-64',
        'width':         64,
        'poly':          0x000000000000001b,
        'reflect_in':    True,
        'xor_in':        0x0,
        'reflect_out':   True,
        'xor_out':       0x0,
        'check':         0x46a5a9388a5beffe,
    })
    models.append({
        'name':         'crc-64-jones',
        'width':         64,
        'poly':          0xad93d23594c935a9,
        'reflect_in':    True,
        'xor_in':        0xffffffffffffffff,
        'reflect_out':   True,
        'xor_out':       0x0,
        'check':         0xcaa717168609f281,
    })
    models.append({
        'name':         'crc-64-xz',
        'width':         64,
        'poly':          0x42f0e1eba9ea3693,
        'reflect_in':    True,
        'xor_in':        0xffffffffffffffff,
        'reflect_out':   True,
        'xor_out':       0xffffffffffffffff,
        'check':         0x995dc9bbdf1939fa,
    })

    def names(self):
        """
        This function returns the list of supported CRC models.
        """
        return [model['name'] for model in self.models]

    def get_params(self, model):
        """
        This function returns the parameters of a given model.
        """
        model = model.lower()
        for i in self.models:
            if i['name'] == model:
                return i
        return None
