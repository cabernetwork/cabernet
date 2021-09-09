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

import subprocess
import time

class Video:

    def __init__(self, _config):
        self.config = _config
        self.video_data = None

    def terminate(self):
        self.video_data = None

    @property
    def data(self):
        return self.video_data

    @data.setter
    def data(self, _video_data):
        self.video_data = _video_data
