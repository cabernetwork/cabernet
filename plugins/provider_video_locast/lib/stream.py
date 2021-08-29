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

import logging
import time


class Stream:
    logger = None

    def __init__(self, _locast_instance):
        self.locast_instance = _locast_instance

    def is_time_to_refresh(self, _last_refresh):
        if self.locast_instance.config_obj.data[self.locast_instance.config_section]['is_free_account']:
            delta_time = time.time() - _last_refresh
            refresh_rate = int(self.locast_instance.config_obj.data[self.locast_instance.locast.name.lower()]['player-refresh_rate'])
            if refresh_rate > 0 and delta_time > int(
                    self.locast_instance.config_obj.data[self.locast_instance.locast.name.lower()]['player-refresh_rate']):
                self.logger.info('Refresh time expired. Refresh rate is {} seconds'
                    .format(self.locast_instance.config_obj.data[self.locast_instance.locast.name.lower()]['player-refresh_rate']))
                return True
        return False


Stream.logger = logging.getLogger(__name__)
