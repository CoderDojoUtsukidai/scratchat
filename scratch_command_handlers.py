# -*- coding: utf-8 -*-

"""
Scratchat - Scratch extension to communicate with PyChat server
@author: Antoine Choppin

This code is inspired by a Scratch Extension written by the following authors:
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

import datetime, logging, re, select, socket, sys
from urllib import parse
from pychat.pychat_util import Room, Hall, Player
from pychat import pychat_util

READ_BUFFER = 4096
END_OF_LINE = '\n'

def bool2str(b):
    if b:
        return 'true'
    return 'false'


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
        self.username = None
        self.room = None
        self.last_message = None
        self.last_message_for = {}
        self.last_speaker = None
        self.message_contains_text = False

    def do_command(self, command):
        """
        This method looks up the command that resides in element zero of the command list
        within the command dictionary and executes the method for the command.
        Each command returns string that will be eventually be sent to Scratch
        @param command: This is a list containing the Scratch command and all its parameters
        @return: String to be returned to Scratch via HTTP
        """
        method = self.command_dict.get(command[0])

        if command[0] != 'poll':
            # turn on debug logging if requested
            if self.debug == 'On':
                debug_string = 'DEBUG: '
                debug_string += str(datetime.datetime.now())
                debug_string += ": "
                for data in command:
                    debug_string += ''.join(map(str, data))
                    debug_string += ' '
                logging.debug(debug_string)
                print(debug_string)

        return method(self, command)

    def connect_as(self, command):
        """
        Command to connect to the pychat server, and announce oneself
        with a given username (handle).
        @param command: List of which the 2nd element should be the username/handle
        @return: 'okay'
        """
        username = parse.unquote(command[1])
        print('connect as {}'.format(username))
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.connect((self.chatserver, pychat_util.PORT))
        msg = s.recv(READ_BUFFER)
        if not msg:
            print('Server down!')
        else:
            if 'Please tell us your name' in msg.decode():
                msg = 'name: {}'.format(username)
                s.sendall(msg.encode())
                self.server_connection = s
                self.username = username
                print('Connected as {}'.format(username))
            else:
                print('Server did not as for name!')
        return 'okay'

    def join_room(self, command):
        """
        Command to join a chat room.
        The client must already have connected to the pychat server.
        @param command: List of which the 2nd element should be the room name
        @return 'okay'
        """
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
        """
        Command to say something (i.e. send a message to pychat server).
        @param command: List of which the 2nd element should be the message
        @return: 'okay'
        """
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

    def say_to(self, command):
        """
        Command to say something to someone, that is, prefix the message
        with @xyz, where xyz is the handle of the user to whom we speak.
        @param command: List of which the 2nd element should be the message
                        and the 3rd element the username/handle of the recipient
        @return: 'okay'
        """
        if self.server_connection is None:
            print('Not connected. Please connect first.')
            return
        if self.room is None:
            print('Please join a room before chatting.')
            return
        message = parse.unquote(command[1])
        recipient = parse.unquote(command[2])
        msg = '@' + recipient + ' ' + message + END_OF_LINE
        print('say: "{}"'.format(msg))
        self.server_connection.sendall(msg.encode())
        return 'okay'

    def check_message_contains(self, command):
        """
        Command to check whether a message contains a given text.
        Note: this is a "w" (wait) command, which means that the command is
        considered complete only when polling does not contain a "_busy"
        item for this command ID.  Since the test is immediate, a "_busy"
        item is never sent, but this ensures that polling is performed after
        this test to get the result of it.
        @param command: List of which the 1st element is the command ID (unused)
                        and the 2nd and 3rd elements are the message and 
                        text to find, respectively.
        @return: 'okay'
        """
        self.message_contains_text = False
        if len(command) != 4:
            return
        unused_command_id = parse.unquote(command[1])
        message = parse.unquote(command[2])
        text_to_find = parse.unquote(command[3])
        self.message_contains_text = text_to_find in message
        return 'okay'

    #noinspection PyUnusedLocal
    def reset_all(self, command):
        """
        This method resets any internal state and returns 'okay'
        @param command: unused
        @return: 'okay'
        """
        if self.server_connection:
            self.server_connection.sendall('<quit>'.encode())
        self.server_connection = None
        self.username = None
        self.room = None
        self.last_message = None
        self.last_message_for = {}
        self.last_speaker = None
        self.message_contains_text = False
        return 'okay'

    #noinspection PyUnusedLocal
    def poll(self, command):
        """
        This method first checks for any incoming chat message.
        It then returns the internal state, followed by 'okay'
        @param command: unused
        @return: internal state, including all variable/value pairs, following by 'okay'
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
                parts = msg.split(':')
                if parts[0] != 'Instructions' and parts[0] != self.room + ' welcomes':
                    self.last_speaker = parts[0]
                else:
                    self.last_speaker = None
                self.last_message = parts[1]
                # look for @xyz at the beginning of the message
                match = re.match('^@[a-zA-Z0-9_]+', self.last_message)
                if match:
                    recipient = match.group(0)[1:]
                    self.last_message_for[recipient] = self.last_message.replace('@'+recipient, '')

        chat_info  = ''
        chat_info += 'connected ' + bool2str(self.server_connection) + END_OF_LINE
        chat_info += 'username ' + parse.quote(self.username or ' ') + END_OF_LINE
        chat_info += 'room ' + parse.quote(self.room or ' ') + END_OF_LINE
        chat_info += 'last_speaker ' + parse.quote(self.last_speaker or ' ') + END_OF_LINE
        chat_info += 'last_message ' + parse.quote(self.last_message or ' ') + END_OF_LINE
        chat_info += 'contains_text ' + bool2str(self.message_contains_text) + END_OF_LINE
        for recipient in self.last_message_for.keys():
            chat_info += 'last_message_for/' + parse.quote(recipient) + ' ' + \
                    parse.quote(self.last_message_for[recipient]) + END_OF_LINE
            if recipient == self.username:
                chat_info += 'last_message_for_me ' + \
                        parse.quote(self.last_message_for[recipient]) + END_OF_LINE

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
                     'connect_as': connect_as, 'join_room': join_room, 'say': say, 'say_to': say_to,
                     'check_message_contains': check_message_contains }

