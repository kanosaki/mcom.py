#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import with_statement

import argparse
import sys
import socket
import json
import zlib
# import binascii
from collections import deque

DEFAULT_PORT = 23344
DEFAULT_GROUP = '234.56.54.32'
MCAST_TTL = 1  # localnet only
MESSAGE_SIZE_LIMIT = 1024  # 1KiB
DEFAULT_SERIALIZER = None  # assigned at JsonGZipSerilalizer

APP_DESCRIPTION = """
mcom.py -- Simple IP Multicast Communication Tool
"""[1:-1]

APP_EPILOG = """
"""[1:-1]

# TODOs:
#
# Multicast Type:
#   - IPv4: Almost
#   - IPv6: not yet
#
# Platform:
#   - Mac OS X: It works.
#   - Linux: not yet
#   - Windos: not yet
#
# Arbitrary message length
# - Not yet!


# -------------------------------------------------
# Common Libraries
# -------------------------------------------------

class DataSizeError(RuntimeError):
    pass


class EndpointMixin(object):
    @property
    def host(self): return self.endpoint[0]

    @property
    def port(self): return self.endpoint[1]

    mcast_group = host


class Mcom(EndpointMixin):
    def __init__(self,
                 group_addr,
                 port=DEFAULT_PORT,
                 serializer=None):
        self.endpoint = (group_addr, port)
        self.serializer = serializer or DEFAULT_SERIALIZER
        self.handlers = deque()
        self._init_variables()
        self._init_sockets()

    def _init_sockets(self):
        if self.ip_version == 4:
            self.listener = IPv4MulticastListener(self.endpoint,
                                                  self.on_next_frame)
            self.sender = IPv4MulticastSender(self.endpoint)
        elif self.ip_version == 6:
            raise RuntimeError('Sorry not implemented yet')
        else:
            raise RuntimeError('Never here')

    def _init_variables(self):
        self.ip_version = self._address_family()

    def _address_family(self):
        # ai: addrinfo,  af: address family(AF_*)
        ais = socket.getaddrinfo(*self.endpoint)
        for ai in ais:
            af, _, _, _, _ = ai
            if af == socket.AF_INET:
                return 4
            elif af == socket.AF_INET6:
                return 6
            else:
                raise RuntimeError(
                    'Unkwon address family {} Info: {}'.
                    format(af, str(ai)))

    def send(self, obj):
        data = self.serializer.pack(obj)
        if len(data) > MESSAGE_SIZE_LIMIT:
            raise DataSizeError(obj)
        self.sender.send(data)

    def on_next_frame(self, sender, frame):
        obj = self.serializer.unpack(frame)
        for h in self.handlers:
            h(self, sender, obj)

    def add_handler(self, handler):
        if handler is None:
            raise Exception("handler cannot be None")
        self.handlers.append(handler)

    def watch(self):
        self.listener.receive_loop()


class JsonGZipSerilalizer(object):
    def pack(self, obj):
        return zlib.compress(json.dumps(obj))

    def unpack(self, packetdata):
        return json.loads(zlib.decompress(packetdata))

DEFAULT_SERIALIZER = JsonGZipSerilalizer()


class SocketWrapperMixin(EndpointMixin):
    """Utilities for socket handling

    Requires:
        - def create_socket(self)
            - Creates socket instance
        - self.endpoint
            - An IP Endpoint tuple like ('192.168.0.1', 1234)
    """
    @property
    def socket(self):
        try:
            return self._sock
        except AttributeError:
            self._sock = self.create_socket()
            return self._sock

    sock = socket


class IPv4MulticastSender(SocketWrapperMixin):
    def __init__(self, endpoint):
        self.endpoint = endpoint

    def create_socket(self):
        sock = socket.socket(socket.AF_INET,
                             socket.SOCK_DGRAM,
                             socket.IPPROTO_UDP)
        sock.setsockopt(socket.IPPROTO_IP,
                        socket.IP_MULTICAST_TTL,
                        MCAST_TTL)
        return sock

    def send(self, data):
        self.sock.sendto(data, self.endpoint)


class IPv4MulticastListener(SocketWrapperMixin):
    def __init__(self, endpoint, callback):
        self.endpoint = endpoint
        self.callback = callback

    def create_socket(self):
        sock = socket.socket(socket.AF_INET,
                             socket.SOCK_DGRAM,
                             socket.IPPROTO_UDP)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except AttributeError:
            pass

        sock.setsockopt(socket.IPPROTO_IP,
                        socket.IP_MULTICAST_TTL,
                        MCAST_TTL)
        sock.setsockopt(socket.IPPROTO_IP,
                        socket.IP_MULTICAST_LOOP,
                        1)
        sock.bind(self.endpoint)
        host = socket.gethostbyname(socket.gethostname())
        sock.setsockopt(socket.SOL_IP,
                        socket.IP_MULTICAST_IF,
                        socket.inet_aton(host))
        sock.setsockopt(socket.SOL_IP,
                        socket.IP_ADD_MEMBERSHIP,
                        socket.inet_aton(self.mcast_group) +
                        socket.inet_aton(host))
        return sock

    def on_receive(self, from_addr, data):
        self.callback(from_addr, data)

    def receive_loop(self):
        while True:
            try:
                data, addr = self.sock.recvfrom(1024)
            except socket.error:
                _, err, _ = sys.exc_info()
                raise err
            self.on_receive(addr, data)


# -------------------------------------------------
# Command line application classes
# -------------------------------------------------


class StreamDumpHandler(object):
    def __init__(self, out):
        self.out = out

    def __call__(self, mcom, sender_endpoint, msg):
        print(sender_endpoint, '-->', msg, file=self.out)


def parse_args():
    parser = argparse.ArgumentParser(
        description=APP_DESCRIPTION,
        epilog=APP_EPILOG
    )
    parser.add_argument('maddr',
                        metavar='MADDR',
                        type=str,
                        help='a multicast address')
    parser.add_argument('-l', '--listen',
                        dest='listen',
                        action='store_true',
                        required=False,
                        help='Listen mode: print received messages.')
    return parser.parse_args()


def main():
    args = parse_args()
    if args.listen:
        mc = Mcom(args.maddr)
        mc.add_handler(StreamDumpHandler(sys.stdout))
        mc.watch()
    else:
        mc = Mcom(args.maddr)
        msg = json.load(sys.stdin)
        mc.send(msg)


if __name__ == '__main__':
    main()

#             ....._
#    ＼     ､m''､ ,ヾﾐ､､／
#      ＼､_,rY　 Y ' ､／,''
#     ＼ ヽ, | 　| y／､,;,',
#       ＼､＼:::::／,／,;;,
#      ヽ ＼ o ､,o  ／{ ;,
#      丿[ ＼|:::|／ ] >"'''
#      ＞､.> 　U 　 <,.＜
#     ﾉ　! !　-=-　ﾉ! ﾄ-､_       < LIMIT BREEEEEEEEAK!!
# .''"L　 ＼＼.".／／_|   ]
#
