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

from ..base.tracebackBoundry import localtb

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Msg Context
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class MsgContext(object):
    advertId = None
    msgId = None
    adRefs = None

    src = None
    fwd = None

    handled = False
    
    def __init__(self, advertId, msgId, src):
        src = PacketNS(src)

        self.advertId = advertId
        self.msgId = msgId
        self.src = src

    _fwdPacket = None
    def getFwdPacket(self):
        pkt = self._fwdPacket
        if pkt is None:
            raise NotImplementedError("TODO")
        return pkt
    fwdPacket = property(getFwdPacket)

    def replyObj(self, replyId=None):
        if replyId is None:
            replyId = self.advertId

        raise NotImplementedError("TODO")

    def forwarded(self, fwdAdvertId):
        pass

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @classmethod
    def newFlyweight(klass, mq, advertDb, **ns):
        ns.update(mq=mq, advertDb=advertDb)
        bklass = getattr(klass, '__flyweight__', klass)
        ns['__flyweight__'] = bklass
        return type(bklass)("%s_%s"%(bklass.__name__, id(ns)), (bklass,), ns)

    @classmethod
    def sendMsg(klass, mobj):
        return klass.mq.addMsg(mobj)

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Message Dispatching
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class MsgDispatch(object):
    mq = None
    msgFilter = None # flyweighted
    advertDb = None # flyweighted

    MsgContext = MsgContext 
    mctx = None

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #~ Sending Facilities
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @classmethod
    def newFlyweight(klass, mq, msgFilter, advertDb, **ns):
        MsgContext = klass.MsgContext.newFlyweight(mq, advertDb)
        ns.update(mq=mq, msgFilter=msgFilter, advertDb=advertDb, MsgContext=MsgContext)

        bklass = getattr(klass, '__flyweight__', klass)
        ns['__flyweight__'] = bklass
        return type(bklass)("%s_%s"%(bklass.__name__, id(ns)), (bklass,), ns)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #~ Msg Builder Interface
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def advertMsgId(self, advertId, msgId, src=None):
        if self.msgFilter(advertId, msgId):
            return False

        adEntry = self.advertDb[advertId]
        self.adEntry = adEntry

        mctx = self.MsgCtx(advertId, msgId, src)
        mctx.adEntry = adEntry
        self.mctx = mctx

        self.adResponders = self.adEntry.allResponders()
        for r in self.adResponders:
            with localtb:
                r.beginResponse(mctx)

        return self

    def end(self):
        return False

    def forward(self, breadthLimit=1, whenUnhandled=True, fwdAdvertId=None):
        # let mctx know that it was intended to be forwarded...
        mctx = self.mctx
        mctx.forwarded(fwdAdvertId)
        if whenUnhandled and mctx.handled:
            # we were handled, so don't forward
            return

        if fwdAdvertId is not None:
            # lookup entry for specified adEntry
            fwdAdEntry = self.advertDb.get(fwdAdvertId)
        else: 
            # not specified, so forward toward our implied adEntry
            fwdAdEntry = self.adEntry

        if fwdAdEntry is None: 
            return

        fwdPacket = mctx.fwdPacket
        if fwdPacket is None:
            return

        r = fwdAdEntry.responder
        # notify fwdAdEntry reponders that we are sending through
        for r in self.fwdAdEntry.allResponders:
            with localtb:
                r.forwarding(fwdAdvertId, fwdAdEntry, mctx)

        # actually accomplish the forward!
        fwdRoutes = fwdAdEntry.getRoutes(breadthLimit)
        for route in fwdRoutes:
            route.sendDispatch(fwdPacket)

    def replyRef(self, replyAdvertIds):
        if isinstance(replyAdvertIds, str):
            replyAdvertIds = [replyAdvertIds]

        mctx.replyId = replyAdvertIds[0] if replyAdvertIds else None
        self.adRefs(replyAdvertIds, True)

    def adRefs(self, advertIds, key=None):
        mctx = self.mctx
        mctx.adIds[key] = replyAdvertIds

        self.advertDB.addRouteForAdverts(mctx.src.route, advertIds)
        return advertIds

    def msg(self, body, fmt=0, topic=None):
        mctx = self.mctx
        for r in self.adResponders:
            with localtb:
                r.msg(body, fmt, topic, mctx)

    def complete(self):
        mctx = self.mctx
        for r in self.adResponders:
            with localtb:
                r.finishResponse(mctx)

