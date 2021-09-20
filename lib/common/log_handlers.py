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

from logging.handlers import RotatingFileHandler

class MPRotatingFileHandler(RotatingFileHandler):
    """
    Supports multiprocessing logging.  Main issue is when the
    file rotates, the other process need to be notified and
    move their file pointers to the new file and not
    create yet another rotation.
    """

    def shouldRollover(self, record):
        """
        Override method
        """
        if super().shouldRollover(record):
            if self.stream is not None:
                self.stream.close()
                self.stream = self._open()
            return super().shouldRollover(record)
        return 0
