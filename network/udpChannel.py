##~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~##
##~ Copyright (C) 2002-2005  TechGame Networks, LLC.              ##
##~                                                               ##
##~ This library is free software; you can redistribute it        ##
##~ and/or modify it under the terms of the BSD style License as  ##
##~ found in the LICENSE file included with this distribution.    ##
##~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~##

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Imports 
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import sys
import Queue

from socket import SOCK_DGRAM
from socket import error as SocketError

from .socketChannel import SocketChannel
from .socketConfigTools import udpSocketErrorMap
from .dispatchChannel import DispatchChannelMixin

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Definitions 
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class UDPBaseChannel(DispatchChannelMixin, SocketChannel):
    socketErrorMap = udpSocketErrorMap

    sockType = SOCK_DGRAM
    recvThrottle = 16
    sendThrottle = 16
    bufferSize = 64 * 65536

    def __init__(self, address=None, interface=None, onBindError=None):
        SocketChannel.__init__(self)
        self.initRegistry()

        self.sendQueue = Queue.Queue()
        if address:
            self.setSocketAddress(address, interface, onBindError)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def send(self, data, address, onErrorNotify=None):
        try:
            # send it directly, if we can
            self.sock.sendto(data, address)
            return 
        except SocketError, err:
            if onErrorNotify is None:
                reraise = self.reraiseSocketError(err, err.args[0])
            else: 
                reraise = onErrorNotify(self, data, address, err)
            if reraise: 
                sys.excepthook(*sys.exc_info())
            elif reraise is None:
                self.sendQueue.put((data, address, onErrorNotify))
                self.needsWrite = True

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def getSocketAddress(self):
        return self.sock.getsockname()
    def setSocketAddress(self, address, interface=None, onBindError=None):
        afamily, address = self.normSockAddr(address)
        if self.sock is None or self.afamily != afamily:
            self.createSocket(afamily)

        self.bindSocket(address, onBindError)
        self.setMulticastInterface(interface, True)

        self.needsRead = True
    address = property(getSocketAddress, setSocketAddress)

    _allowBroadcast = True
    _allowMulicastHops = 5
    def _socketConfig(self, sock, cfgUtils):
        SocketChannel._socketConfig(self, sock, cfgUtils)
        cfgUtils.disallowMixed()

        if self._allowBroadcast:
            cfgUtils.setBroadcast(True)

        hops = self._allowMulicastHops
        if hops is not None:
            cfgUtils.setMulticastHops(hops)
            cfgUtils.setMulticastLoop(True)

        cfgUtils.setMaxBufferSize(self.bufferSize)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #~ Broadcast and multicast
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def getBroadcast(self):
        return self.cfgUtils.getBroadcast()
    def setBroadcast(self, bAllow=True):
        return self.cfgUtils.setBroadcast(bAllow)

    def getMulticastInterface(self, raw=False):
        return self.cfgUtils.getMulticastInterface(raw)
    _mcast_if_primary = None
    def setMulticastInterface(self, interface=None, primary=False):
        if interface is None:
            interface = self._mcast_if_primary
        self.cfgUtils.setMulticastInterface(interface)
        if primary:
            self._mcast_if_primary = self.getMulticastInterface(False) 

    def joinGroup(self, group, interface=None):
        self.cfgUtils.joinGroup(group, interface)

    def joinGroupAll(self, group):
        for name, addrList in self.cfgUtils.getAllMulticastIF():
            for addr in addrList:
                self.cfgUtils.joinGroup(group, addr)

    def leaveGroup(self, group, interface=None):
        self.cfgUtils.leaveGroup(group, interface)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #~ Socket processing
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def performRead(self, tasks):
        sock = self.sock
        iterThrottle = xrange(self.recvThrottle)

        dataPackets = []
        try:
            for n in iterThrottle:
                dataPackets.append(sock.recvfrom(65536))
        except SocketError, err:
            if self.reraiseSocketError(err, err.args[0]):
                sys.excepthook(*sys.exc_info())

        if dataPackets:
            tasks.append((self._dispatchDataPackets, dataPackets))
        return n

    def performWrite(self, tasks):
        sendQueue = self.sendQueue
        if sendQueue.empty():
            self.needsWrite = False
            return

        sock = self.sock
        iterThrottle = xrange(self.sendThrottle)
        try:
            for n in iterThrottle:
                data, address, onErrorNotify = sendQueue.get(False, 0.1)
                sock.sendto(data, address)
        except Queue.Empty:
            self.needsWrite = False
        except SocketError, err:
            if onErrorNotify is None:
                reraise = self.reraiseSocketError(err, err.args[0])
            else: 
                reraise = onErrorNotify(self, data, address, err)
            if reraise:
                sys.excepthook(*sys.exc_info())
            elif reraise is None:
                sendQueue.put((data, address, onErrorNotify))

        return n

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Specific channel Setup
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class UDPChannel(UDPBaseChannel):
    pass

class UDPAutoChannel(UDPBaseChannel):
    def onBindError(self, address, err):
        r = list(address)
        r[1] += 1
        return tuple(r)

class UDPSharedChannel(UDPBaseChannel):
    def _socketConfig(self, sock, cfgUtils):
        UDPBaseChannel._socketConfig(self, sock, cfgUtils)
        cfgUtils.reuseAddress()

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Multicast
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class UDPMulticastChannel(UDPSharedChannel):
    def setSocketAddress(self, address, interface=None, onBindError=None):
        afamily, address = self.normSockAddr(address)

        if self.sock is None or self.afamily != afamily:
            self.createSocket(afamily)

        # multicast addresses should always be bound to INADDR_ANY=""
        bindAddr = ("",) + address[1:]
        self.bindSocket(bindAddr, onBindError)
        self.setMulticastInterface(interface, True)

        self.needsRead = True

MUDPChannel = UDPMulticastChannel

