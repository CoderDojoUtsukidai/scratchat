#!/usr/bin/env python

# -*- coding: utf-8 -*-

"""
@author: Antoine Choppin
Copyright (c) 2016 Antoine Choppin All right reserved.

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 2.1 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this library; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

"""
import os
import sys
import logging
import scratch_http_server
from scratch_command_handlers import ScratchCommandHandlers
import time


#noinspection PyBroadException
def scratchat(chatserver):
    """
    This is the "main" function of the program.
    It will instantiate the command handlers class.
    It will the start the HTTP server to communicate with Scratch 2.0
    @return : This is the main loop and should never return
    """
    # make sure we have a log directory and if not, create it.
    if not os.path.exists('log'):
        os.makedirs('log')

    # turn on logging
    logging.basicConfig(filename='./log/scratchat_debugging.log', filemode='w', level=logging.DEBUG)
    logging.info('scratchat Copyright(C) 2016 Antoine Choppin All Rights Reserved')
    print('scratchat Copyright(C) 2016 Antoine Choppin All Rights Reserved')

    # tcp server port - must match that in the .s2e descriptor file
    port = 50355

    # instantiate the command handler
    scratch_command_handler = ScratchCommandHandlers(chatserver)

    try:
        scratch_http_server.start_server(port, scratch_command_handler)

    except Exception:
        logging.debug('Exception in scratchat.py %s' % str(Exception))
        return

    except KeyboardInterrupt:
        # give control back to the shell that started us
        logging.info('scratchat.py: keyboard interrupt exception')
        return

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 scratchat.py [server]", file = sys.stderr)
        sys.exit(1)
    scratchat(sys.argv[1])
