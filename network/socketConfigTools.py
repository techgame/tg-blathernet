##~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~##
##~ Copyright (C) 2002-2007  TechGame Networks, LLC.              ##
##~                                                               ##
##~ This library is free software; you can redistribute it        ##
##~ and/or modify it under the terms of the BSD style License as  ##
##~ found in the LICENSE file included with this distribution.    ##
##~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~##

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Imports 
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import struct
import errno # for socket error codes
import socket
from socket import AF_INET, AF_INET6

try: import fcntl
except ImportError:
    fcntl = None

from TG.networkInfo import netif

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Socket Config Methods 
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class SocketConfigUtils(object):
    disallowMixedIPv4andIPv6 = True

    def setSocketInfo(self, sock, afamily):
        self.sock = sock
        self.afamily = afamily

    def disallowMixed(self):
        if (self.afamily == AF_INET6) and  self.disallowMixedIPv4andIPv6:
            sock = self.sock
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)

    def reuseAddress(self, bReuse=True):
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, bReuse)
        self.reusePort(bReuse)
        return bReuse
    def reusePort(self, bReuse=True):
        if hasattr(socket, "SO_REUSEPORT"):
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, bReuse)
            return bReuse

    def getBroadcast(self):
        if hasattr(socket, "SO_BROADCAST"):
            return self.sock.getsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST)
    def setBroadcast(self, bAllow=True):
        if hasattr(socket, "SO_BROADCAST"):
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, bAllow)
            return bAllow

    def configFcntl(self):
        if fcntl and hasattr(fcntl, 'FD_CLOEXEC'):
            fileno = self.sock.fileno()
            bitmask = fcntl.fcntl(fileno, fcntl.F_GETFD)
            bitmask |= fcntl.FD_CLOEXEC
            fcntl.fcntl(fileno, fcntl.F_SETFD, bitmask)

    def setMaxBufferSize(self, recvSize=None, sendSize=None):
        size = self.findMaxBufferSize(self.sock)
        if recvSize is not None:
            recvSize = min(recvSize, size)
        else: recvSize = size
        if sendSize is not None:
            sendSize = min(sendSize, size)
        return self.setBufferSize(recvSize, sendSize)

    def setBufferSize(self, recvSize, sendSize=None):
        if sendSize is None: sendSize = recvSize
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, recvSize)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, sendSize)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    _socketMaxBufferSize = None
    @classmethod
    def findMaxBufferSize(klass, sock, size=0x40000, size0=0x02000, size1=0x80000):
        if klass._socketMaxBufferSize is None:
            SOL_SOCKET = socket.SOL_SOCKET
            SO_RCVBUF = socket.SO_RCVBUF
            SO_SNDBUF = socket.SO_SNDBUF
            while size1 > size0+1:
                try:
                    sock.setsockopt(SOL_SOCKET, SO_RCVBUF, size)
                    sock.setsockopt(SOL_SOCKET, SO_SNDBUF, size)
                except socket.error:
                    # size is too big, so it is now our upper bound
                    size1 = size
                else:
                    # size works, so it is now our lower bound
                    size0 = size
                # go to the next size to test using binary search
                size = (size1+size0) >> 1
            klass._socketMaxBufferSize = size

        return klass._socketMaxBufferSize

    @classmethod
    def asSockAddr(klass, address):
        if address is not None:
            if not isinstance(address, tuple):
                address = (address, 0)
            address = klass.normSockAddr(address)[1]
        return address

    @classmethod
    def normSockAddr(klass, address):
        # normalize the address into a routing token
        ip, port = address[:2]
        try:
            info = socket.getaddrinfo(str(ip), int(port))[0]

            # grab the address portion of the info
            afamily = info[0]
            address = info[-1]
        except socket.gaierror, e:
            if e.args[0] == socket.EAI_SERVICE:
                info = socket.getaddrinfo(str(ip), None)[0]
                afamily = info[0]
                address = (info[-1][0], port) + info[-1]
            else: raise

        return afamily, address[:2]

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #~ Socket Multicast Config
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def setMulticastHops(self, hops):
        if self.afamily == AF_INET:
            self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, hops)
        elif self.afamily == AF_INET6:
            self.sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_HOPS, hops)
    setMulticastTTL = setMulticastHops

    def setMulticastLoop(self, loop=True):
        if self.afamily == AF_INET:
            self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, loop)
        elif self.afamily == AF_INET6:
            self.sock.setsockopt(socket.IPPROTO_IPV6, socket.IP_MULTICAST_LOOP, loop)

    def getMulticastInterface(self, raw=False):
        if self.afamily == AF_INET:
            result = self.sock.getsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF)
            result = struct.pack('i', result)
            if not raw:
                result = socket.inet_ntoa(result)
        elif self.afamily == AF_INET6:
            result = self.sock.getsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_IF)
            if raw:
                result = struct.pack('i', result)
        return result
    def setMulticastInterface(self, if_address=None):
        if not if_address:
            return False
        if_address = self._packedInterface(if_address)
        return self.setMulticastInterfacePacked(if_address)

    def setMulticastInterfacePacked(self, if_address):
        if not if_address:
            return False
        if self.afamily == AF_INET:
            self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, if_address)
            return True
        elif self.afamily == AF_INET6:
            self.sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_IF, if_address)
            return True
        return False

    def getIFAddrs(self):
        return netif.getifaddrs(self.afamily)
    def getIFIndexes(self):
        return netif.getifindexes(self.afamily)
    def getIFInfo(self):
        return netif.getifinfo(self.afamily)

    def getAllMulticastIF(self):
        if self.afamily == AF_INET:
            return self.getIFAddrs()
        elif self.afamily == AF_INET6:
            return self.getIFIndexes()

    def joinGroup(self, group, if_address=None):
        groupAndIF = self._packedGroup(group, if_address)
        if self.afamily == AF_INET:
            self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, groupAndIF)
        elif self.afamily == AF_INET6:
            self.sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP, groupAndIF)

    def leaveGroup(self, group, if_address=None):
        groupAndIF = self._packedGroup(group, if_address)
        if self.afamily == AF_INET:
            self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_DROP_MEMBERSHIP, groupAndIF)
        elif self.afamily == AF_INET6:
            self.sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_LEAVE_GROUP, groupAndIF)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def _packedInterface(self, if_address=None):
        if self.afamily == AF_INET:
            # IPV4 require the interface IP to bind the multicast interface
            if if_address:
                if_address = self.asSockAddr(if_address)[0]
            else:
                if_address = self.getMulticastInterface(False)

            return self._inet_pton(self.afamily, if_address)

        elif self.afamily == AF_INET6:
            # IPV6 require the interface number to bind the multicast interface
            if if_address:
                if_address = netif.getIFIndex(if_address) 
            if if_address:
                return struct.pack('I', if_address)
            else: return self.getMulticastInterface(True)

    def _packedGroup(self, group, if_address=None):
        groupAddr = self.asSockAddr(group)
        interface = self._packedInterface(if_address)
        group = self._inet_pton(self.afamily, groupAddr[0])
        return group + interface

    if hasattr(socket, 'inet_pton'):
        _inet_pton = staticmethod(socket.inet_pton)
        _inet_ntop = staticmethod(socket.inet_ntop)
    else:
        @staticmethod
        def _inet_ntop(afamily, addr):
            if afamily != AF_INET:
                raise NotImplementedError()
            return socket.inet_ntoa(addr)

        @staticmethod
        def _inet_pton(afamily, addr):
            if afamily != AF_INET:
                raise NotImplementedError()
            return socket.inet_aton(addr)

asSockAddr = SocketConfigUtils.asSockAddr

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Constants / Variiables / Etc. 
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

socketErrorMap = {
    errno.EAGAIN: False,
    errno.EINTR: False,
    errno.EWOULDBLOCK: False,

    errno.EMSGSIZE: True,}

tcpSocketErrorMap = socketErrorMap.copy()
udpSocketErrorMap = socketErrorMap.copy()

_conditionalErrors = [
    errno.ECONNABORTED, 
    errno.ECONNREFUSED, 
    errno.ECONNRESET,

    errno.EADDRNOTAVAIL, 
    errno.ENETUNREACH,]

if hasattr(errno, 'WSAEINTR'):
    socketErrorMap.update({
        errno.WSAEINTR: False,
        errno.WSAEWOULDBLOCK: False,})

    _conditionalErrors += [
        errno.WSAECONNABORTED,
        errno.WSAECONNREFUSED,
        errno.WSAECONNRESET]

for err in _conditionalErrors:
    tcpSocketErrorMap[err] = True
    udpSocketErrorMap[err] = False

del _conditionalErrors

