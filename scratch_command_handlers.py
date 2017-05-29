# -*- coding: utf-8 -*-

"""
Created on Wed Nov  25 13:17:15 2013

@author: Alan Yorinks
Copyright (c) 2013-14 Alan Yorinks All right reserved.

@co-author: Sjoerd Dirk Meijer, fromScratchEd.nl (language support)

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

import datetime, logging, select, socket, sys
from urllib import parse
from pychat.pychat_util import Room, Hall, Player
from pychat import pychat_util

READ_BUFFER = 4096
#END_OF_LINE = '\r\n'
END_OF_LINE = '\n'

class ScratchCommandHandlers:
    """
    This class processes any command received from Scratch 2.0

    If commands need to be added in the future, a command handler method is
    added to this file and the command_dict at the end of this file is
    updated to contain the method. Command names must be the same in the json .s2e Scratch
    descriptor file.
    """

    def __init__(self, chatserver):
        """
        The class constructor
        """
        self.debug = 'On'
        self.first_poll_received = False
        self.chatserver = chatserver
        self.server_connection = None
        self.room = None
        self.last_message = ' '
        self.last_speaker = ' '

    def do_command(self, command):
        """
        This method looks up the command that resides in element zero of the command list
        within the command dictionary and executes the method for the command.
        Each command returns string that will be eventually be sent to Scratch
        @param command: This is a list containing the Scratch command and all its parameters
        @return: String to be returned to Scratch via HTTP
        """
        method = self.command_dict.get(command[0])

        if command[0] != "poll":
            # turn on debug logging if requested
            if self.debug == 'On':
                debug_string = "DEBUG: "
                debug_string += str(datetime.datetime.now())
                debug_string += ": "
                for data in command:
                    debug_string += "".join(map(str, data))
                    debug_string += ' '
                logging.debug(debug_string)
                print(debug_string)

        return method(self, command)

    def connect_as(self, command):
        username = parse.unquote(command[1])
        print('connect as {}'.format(username))
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.connect((self.chatserver, pychat_util.PORT))
        msg = s.recv(READ_BUFFER)
        if not msg:
            print("Server down!")
        else:
            if 'Please tell us your name' in msg.decode():
                msg = 'name: {}'.format(username)
                s.sendall(msg.encode())
                self.server_connection = s
                print('Connected as {}'.format(username))
            else:
                print('Server did not as for name!')
        return 'okay'

    def join_room(self, command):
        if self.server_connection:
            room = parse.unquote(command[1])
            print('join room {}'.format(room))
            msg = '<join> {}'.format(room)
            self.server_connection.sendall(msg.encode())
            self.room = room
        else:
            print('Not connected. Please connect first.')
        return 'okay'

    def say(self, command):
        if self.server_connection is None:
            print('Not connected. Please connect first.')
            return
        if self.room is None:
            print('Please join a room before chatting.')
            return
        msg = parse.unquote(command[1]) + END_OF_LINE
        print('say: "{}"'.format(msg))
        self.server_connection.sendall(msg.encode())
        return 'okay'

    #noinspection PyUnusedLocal
    def reset_all(self, command):
        """
        This method resets any internal state and returns 'okay'
        @param command: This is a list containing the Scratch command and all its parameters It is unused
        @return: 'okay'
        """
        if self.server_connection:
            self.server_connection.sendall('<quit>'.encode())
        self.server_connection = None
        self.room = None
        self.last_message = ' '
        self.last_speaker = ' '
        return 'okay'

    #noinspection PyUnusedLocal
    def poll(self, command):
        """
        This method resets any internal state and returns 'okay'
        @param command: This is a list containing the Scratch command and all its parameters It is unused
        @return: 'okay'
        """
        # look for first poll and when received let the world know we are ready!
        if not self.first_poll_received:
            logging.info('Scratch detected! Ready to rock and roll...')
            print('Scratch detected! Ready to rock and roll...')
            self.first_poll_received = True

        msg = None
        if self.server_connection:
            read_socks, _, _ = select.select([self.server_connection], [], [], 0)
            if len(read_socks) > 0:
                s = read_socks[0]
                msg = s.recv(READ_BUFFER)
                msg = msg.decode()
                print(msg)

        chat_info  = ''
        if msg and msg != ' ':
            parts = msg.split(':')
            if parts[0] != 'Instructions' and parts[0] != self.room + ' welcomes':
                self.last_speaker = parts[0]
            else:
                self.last_speaker = ' '
            self.last_message = parts[1]
            chat_info += 'last_speaker ' + parse.quote(self.last_speaker) + END_OF_LINE
            chat_info += 'last_message ' + parse.quote(self.last_message) + END_OF_LINE

        return chat_info + 'okay'

    #noinspection PyUnusedLocal
    def send_cross_domain_policy(self, command):
        """
        This method returns cross domain policy back to Scratch upon request.
        It keeps Flash happy.
        @param command: Command and all possible parameters in list form
        @return: policy string
        """
        policy = "<cross-domain-policy>\n"
        policy += "  <allow-access-from domain=\"*\" to-ports=\""
        policy += str(self.com_port)
        policy += "\"/>\n"
        policy += "</cross-domain-policy>\n\0"
        return policy

    # This table must be at the bottom of the file because Python does not provide forward referencing for
    # the methods defined above.
    command_dict = { 'crossdomain.xml': send_cross_domain_policy,
                     'reset_all': reset_all, 'poll': poll,
                     'connect_as': connect_as, 'join_room': join_room, 'say': say }

