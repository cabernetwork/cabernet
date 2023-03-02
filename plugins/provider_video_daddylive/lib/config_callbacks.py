"""
MIT License

Copyright (C) 2023 ROCKY4546
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


def license_confirmation(_config_obj, _section, _key):
    if _config_obj.data[_section][_key] == 'ALL':
        return ''.join([
            'Make sure the EPG default instances used by DaddyLive are enabled<script>',
            'confirm_r = confirm("Licensing for these EPG plugins are for personal use only.  ',
            'Change to None if Cabernet is being used for non-personal use");</script>'])
    else:
        return 'EPG plugin usage has been disabled'
