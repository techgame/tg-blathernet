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

from ..base import BlatherObject, OBFactoryMap

from .socketConfigTools import netif, AF_INET, AF_INET6
from .selectTask import NetworkSelector
from . import udpChannel
from . import inprocChannel

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Definitions 
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class BlatherNetworkMgr(BlatherObject):
    _fm_ = OBFactoryMap(
            NetworkSelector=NetworkSelector,)

    _networkSelector = None
    def getNetworkSelector(self):
        result = self._networkSelector
        if result is None:
            result = self._fm_.NetworkSelector()
            self._networkSelector = result
        return result
    selector = property(getNetworkSelector)

    def process(self, timeout):
        return self.selector.processSelectable(timeout)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @staticmethod
    def getIFAddrs_v4(): return netif.getifaddrs(AF_INET)
    @staticmethod
    def getIFIndexes_v4(): return netif.getifindexes(AF_INET)
    @staticmethod
    def getIFInfo_v4(): return netif.getifinfo(AF_INET)

    @staticmethod
    def getIFAddrs_v6(): return netif.getifaddrs(AF_INET6)
    @staticmethod
    def getIFIndexes_v6(): return netif.getifindexes(AF_INET6)
    @staticmethod
    def getIFInfo_v6(): return netif.getifinfo(AF_INET6)

    getIFAddrs = getIFAddrs_v4
    getIFIndexes = getIFIndexes_v4
    getIFInfo = getIFInfo_v4

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #~ Factory methods
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def addUdpChannelIPv6(self, address=('::', 8470), interface=1, assign=None):
        return self.addUdpChannel(address, interface, assign)

    def addUdpChannel(self, address=('0.0.0.0', 8470), interface=None, static=False, assign=None):
        if static:
            ch = udpChannel.UDPChannel(address, interface)
        else: ch = udpChannel.UDPAutoChannel(address, interface)
        self.selector.add(ch)
        self.checkUdpChannel(ch, assign)
        return ch

    _allUdpChannels = None
    def allUdpChannels(self, port=8470):
        allChannels = self._allUdpChannels
        if allChannels is None:
            allChannels = []
            for ifname, ifaddrs in netif.getifaddrs_v4():
                for addr in ifaddrs:
                    ch = self.addUdpChannel((str(addr), port), str(addr), False)
                    allChannels.append((addr, ch))

            self._allUdpChannels = allChannels
        return allChannels

    def addSharedUdpChannelIPv6(self, address=('::', 8468), interface=1, assign=None):
        return self.addSharedUdpChannel(address, interface, assign)
    def addSharedUdpChannel(self, address=('0.0.0.0', 8468), interface=None, assign=None):
        ch = udpChannel.UDPSharedChannel(address, interface)
        self.selector.add(ch)
        self.checkSudpChannel(ch, assign)
        return ch

    def addMudpChannelIPv6(self, address=('ff02::238.1.9.1', 8469), interface=1, assign=None):
        return self.addMudpChannel(address, interface, assign)

    def addMudpChannel(self, address=('238.1.9.1', 8469), interface=None, assign=None):
        ch = udpChannel.UDPMulticastChannel(address, interface)

        ch.grpAddr = ch.normSockAddr(address)[1][:2]
        if interface is not None:
            ch.joinGroup(ch.grpAddr, interface)
        else: ch.joinGroupAll(ch.grpAddr)

        self.selector.add(ch)
        self.checkMudpChannel(ch, assign)
        return ch

    def addInprocChannel(self, address=None, interface=None, assign=None):
        ch = inprocChannel.InprocChannel(address, interface)

        self.selector.add(ch)
        self.checkInprocChannel(ch, assign)
        return ch

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    _udpChannel = None
    def getUdpChannel(self):
        if self._udpChannel is None:
            self._udpChannel = self.addUdpChannel()
        return self._udpChannel
    def setUdpChannel(self, udpChannel):
        self._udpChannel = udpChannel
    udpChannel = property(getUdpChannel, setUdpChannel)
    def checkUdpChannel(self, udpChannel, assign=None):
        if self._udpChannel is None and assign is None:
            assign = True

        if assign: self.setUdpChannel(udpChannel)

    _sudpChannel = None
    def getSudpChannel(self):
        if self._sudpChannel is None:
            self._sudpChannel = self.addSharedUdpChannel()
        return self._sudpChannel
    def setSudpChannel(self, sudpChannel):
        self._sudpChannel = sudpChannel
    sudpChannel = property(getSudpChannel, setSudpChannel)
    def checkSudpChannel(self, sudpChannel, assign=None):
        if self._sudpChannel is None and assign is None:
            assign = True

        if assign: self.setSudpChannel(sudpChannel)

    _mudpChannel = None
    def getMudpChannel(self):
        if self._mudpChannel is None:
            self._mudpChannel = self.addMudpChannel()
        return self._mudpChannel
    def setMudpChannel(self, mudpChannel):
        self._mudpChannel = mudpChannel
    def checkMudpChannel(self, mudpChannel, assign=None):
        if self._mudpChannel is None and assign is None:
            assign = True

        if assign: self.setMudpChannel(mudpChannel)

    mudpChannel = property(getMudpChannel, setMudpChannel)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    _inprocChannel = None
    def getInprocChannel(self):
        if self._inprocChannel is None:
            self._inprocChannel = self.addInprocChannel()
        return self._inprocChannel
    def setInprocChannel(self, inprocChannel):
        self._inprocChannel = inprocChannel
    def checkInprocChannel(self, inprocChannel, assign=None):
        if self._inprocChannel is None and assign is None:
            assign = True

        if assign: self.setInprocChannel(inprocChannel)

    inprocChannel = property(getInprocChannel, setInprocChannel)

