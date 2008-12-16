##~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~##
##~ Copyright (C) 2002-2009  TechGame Networks, LLC.              ##
##~                                                               ##
##~ This library is free software; you can redistribute it        ##
##~ and/or modify it under the terms of the BSD style License as  ##
##~ found in the LICENSE file included with this distribution.    ##
##~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~##

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Imports 
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

from contextlib import contextmanager
from ..base import timestamp, PacketNS
from .api import IReplyMessageAPI

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Msg Context
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class MsgContext(IReplyMessageAPI):
    ts = None
    advertId = None
    msgId = None
    adRefs = None
    src = None

    mrules = None
    handled = False
    
    def __init__(self, advertId, msgId, src):
        src = PacketNS(src)

        self.advertId = advertId
        self.msgId = msgId
        self.src = src
        self.adRefs = {}

        if self.ts is None:
            self.ts = self.timestamp()

    _fwdPacket = None
    def getFwdPacket(self):
        def findPkt(src):
            return src.packet or src.mobj.encode().packet

        pkt = self._fwdPacket or findPkt(self.src)
        return pkt
    fwdPacket = property(getFwdPacket)

    def getTs(self):
        return self.src.ts
    def setTs(self, ts):
        self.src.ts = ts
    ts = property(getTs, setTs)
    timestamp = staticmethod(timestamp)

    def forwarding(self, breadthLimit=1, whenUnhandled=True, fwdAdvertId=None):
        pass

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #~ IReplyMessageAPI
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def newMsg(self, advertId=None, replyId=True, forward=True):
        if replyId is True:
            replyId = self.advertId
        return self.host.newMsg(advertId, replyId)
    def replyMsg(self, replyId=True, respondId=True):
        if replyId is True:
            replyId = self.replyId
        return self.newMsg(replyId, respondId)
    def sendMsg(self, mobj):
        return self.host.sendMsg(mobj)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #~ Flyweight support
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @classmethod
    def newFlyweight(klass, host, **ns):
        ns.update(host=host)
        bklass = getattr(klass, '__flyweight__', klass)
        ns['__flyweight__'] = bklass
        return type(bklass)("%s_%s"%(bklass.__name__, id(ns)), (bklass,), ns)

