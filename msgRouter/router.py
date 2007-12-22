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

import uuid

from ..base import BlatherObject
from .entry import AdvertRouterEntry
from .headerCodec import RouteHeaderCodec

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Definitions 
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class AdvertRouterTable(dict):
    EntryBasic = AdvertRouterEntry
    EntryFactory = None

    def __missing__(self, advId):
        entry = self.EntryFactory(advId)
        self[advId] = entry
        return entry
    
    def setupEntryFlyweight(self, **ns):
        self.EntryFactory = self.EntryBasic.factoryFlyweight(**ns)

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class BlatherMessageRouter(BlatherObject):
    _fm_ = BlatherObject._fm_.branch(
            RouterTable=AdvertRouterTable)
    codec = RouteHeaderCodec()

    def __init__(self, host):
        BlatherObject.__init__(self, host)
        self.allRoutes = dict()
        self.recentMsgIdSets = [set(), set()]

        self.routeTable = self._fm_.RouterTable()
        self.routeTable.setupEntryFlyweight(
                msgRouter=self.asWeakProxy(),
                codec=self.codec,
                allRoutes=self.allRoutes)

    def registerOn(self, blatherObj):
        blatherObj.registerMsgRouter(self)
    def registerRoute(self, route):
        self.addRoute(route)
    def registerAdvert(self, advert):
        self.registerOn(advert)

    def addRoute(self, route, weight=0):
        self.allRoutes.setdefault(route, weight)

    def entryForAdvert(self, advert):
        return self.entryForId(advert.advertId)
    def entryForId(self, advertId):
        return self.routeTable[advertId]

    def newSession(self, advertOpt=None):
        advEntry = self.entryForId(uuid.uuid4().bytes)
        if advertOpt is not None:
            advEntry.updateAdvertInfo(None, advertOpt)
        return advEntry

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def recvPacket(self, packet, pinfo):
        dmsg, pinfo = self.codec.decode(packet, pinfo)
        if dmsg is None:
            return False

        advEntry = self.routeTable.get(pinfo.get('advertId'))
        if advEntry is None: 
            return False
        pinfo['advEntry'] = advEntry

        msgIdDup = self.isDuplicateMessageId(pinfo['msgId'])

        retAdvertId = pinfo.get('retAdvertId')
        if retAdvertId is not None:
            retAdvertEntry = self.routeTable[retAdvertId]
            if not msgIdDup:
                retAdvertEntry.recvReturnRoute(pinfo)
            else: retAdvertEntry.recvReturnRouteDup(pinfo)
            pinfo['retEntry'] = retAdvertEntry

        if not msgIdDup:
            return advEntry.recvPacket(packet, dmsg, pinfo)
        else: return advEntry.recvPacketDup(packet, dmsg, pinfo)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def isDuplicateMessageId(self, msgId):
        for rs in self.recentMsgIdSets:
            if msgId in rs:
                self.addMessageId(msgId)
                return True
        else: 
            self.addMessageId(msgId)
            return False

    def addMessageId(self, msgId):
        if msgId is None: return
        recent = self.recentMsgIdSets
        if len(recent[0]) > 1000:
            recent.pop()
            recent.insert(0, set())
        recent[0].add(msgId)

MessageRouter = BlatherMessageRouter

