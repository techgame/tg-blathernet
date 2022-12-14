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

from ..base import PacketNS

from ..adverts import advertIdForNS
from .apiMsgExecute import MsgExecuteAPI
from .msgSizer import MsgSizer
from .msgPPrint import MsgPPrint

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Definitions 
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class CacheNS(object):
    pass

class MsgCommandObject(MsgExecuteAPI):
    codec = None # class variable

    msgId = None
    fwd = None
    src = None

    def __init__(self, advertId=None, replyId=None, src=None):
        if advertId is not False:
            self.advertMsgId(advertId, None, src)
        if replyId:
            self.replyRef(replyId)

    def __repr__(self):
        return '<%s msgId: %s advertId: %s>' % (self.__class__.__name__, self.hexMsgId, self.hexAdvertId)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @classmethod
    def new(klass):
        return klass(False)

    def copy(self):
        r = self.new()
        r.advertMsgId(self.advertId, self.msgId, self.src)
        r._cmdList = self._cmdList[:]
        r._cmdCache = {}
        return r

    def __enter__(self):
        """Enables use of a MsgCommandObject as a template"""
        return self.copy()

    def __exit__(self, etype, exc, tb):
        pass

    @classmethod
    def fromMsgObject(klass, mobj):
        self = klass.new()
        mobj.executeOn(self)
        return self

    @classmethod
    def fromData(klass, data, **kw):
        src = PacketNS(data, **kw)
        self = klass()
        return self.codec.decodeOn(self, src)

    def encode(self, assign=False):
        return self.codec.encode(self, assign)

    def encodedAs(self, msgId, pkt):
        self.msgId = msgId
        self.fwd.update(pkt)

    def getFwdPacket(self, assign=True):
        fwd = self.fwd
        if fwd.packet is None:
            fwd = self.encode(assign)
        return fwd.packet

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def advertNS(self, advertNS, msgId=None):
        advertId = self.advertIdForNS(advertNS)
        return self.advertMsgId(advertId, msgId)
    advertIdForNS = staticmethod(advertIdForNS)

    _advertId = None
    def getAdvertId(self):
        return self._advertId
    def setAdvertId(self, advertId):
        self._advertId = advertId
        self._cmd_clear_()
    advertId = property(getAdvertId, setAdvertId)

    hexAdvertId = property(lambda self:(self.advertId or '').encode('hex') or None)
    hexMsgId = property(lambda self:(self.msgId or '').encode('hex') or None)

    def ensureMsgId(self):
        msgId = self.msgId
        if msgId is None:
            msgId = self.codec.newMsgId()
            self.msgId = msgId
        return msgId

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def getReplyId(self):
        replyIds = self._findCmds_('replyRef')
        if replyIds:
            return replyIds[0]
    def setReplyId(self, replyId):
        self.replyRef(replyId)
    replyId = property(getReplyId, setReplyId)

    hexReplyId = property(lambda self:(self.replyId or '').encode('hex') or None)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def isForwarded(self):
        return self._findCmds_('forward', 'forwardOnce') is not None
    def autoForward(self):
        if not self.isForwarded(): 
            if self.replyId != self.advertId:
                self.forward()
            else: self.broadcast()
        return self

    def enqueSendOn(self, msgapi):
        self.ensureMsgId()
        self.autoForward()

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #~ Msg Builder Interface
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def advertMsgId(self, advertId, msgId=None, src=None):
        self.advertId = advertId
        self.msgId = msgId
        self.src = PacketNS(src, mobj=self)
        self.fwd = PacketNS(self.src.packet)
        return self

    def broadcastOnce(self, whenUnhandled=True, fwdAdvertId=None):
        return self.forwardOnce(0, whenUnhandled, fwdAdvertId)
    def forwardOnce(self, breadthLimit=1, whenUnhandled=True, fwdAdvertId=None):
        if fwdAdvertId in (True, False):
            fwdAdvertId = None
        if breadthLimit in ('*', None, 'all'): 
            breadthLimit = 0
        self._cmd_('forwardOnce', breadthLimit, whenUnhandled, fwdAdvertId)
        return self

    def broadcast(self, whenUnhandled=True, fwdAdvertId=None):
        return self.forward(0, whenUnhandled, fwdAdvertId)
    def noForward(self):
        return self.forward(-1, True, None)
    def forward(self, breadthLimit=1, whenUnhandled=True, fwdAdvertId=None):
        if fwdAdvertId in (True, False):
            fwdAdvertId = None
        if breadthLimit in ('*', None, 'all'): 
            breadthLimit = 0
        self._cmd_('forward', breadthLimit, whenUnhandled, fwdAdvertId)
        return self

    def replyRef(self, replyAdvertIds):
        self._cmd_clear_('replyRef')
        if not replyAdvertIds: return
        if isinstance(replyAdvertIds, str):
            replyAdvertIds = [replyAdvertIds]
        self._cmd_('replyRef', replyAdvertIds)
        return self

    def adRefs(self, advertIds, key=None):
        if not advertIds: return
        self._cmd_('adRefs', advertIds, key)
        return self

    def msg(self, body, fmt=0, topic=None):
        if isinstance(topic, unicode):
            raise ValueError("Topic may not be unicode")
        self._cmd_('msg', body, fmt, topic)
        return self
    
    def end(self):
        self._cmd_('end')
        return False

    def complete(self):
        return self

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #~ Utility and Playback
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def executeOn(self, mxRoot):
        mx = mxRoot.advertMsgId(self.advertId, self.msgId, self.src)
        if mx:
            for fn, args in self.iterCmds():
                r = mx.cmdPerform(fn, args)
                if r is False:
                    break

            return mx.complete()

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    _cmd_order = {'end':100, 'forward':90, 'msg': 50, 'adRefs': 30, 'replyRef': 30}
    def listCmds(self, bSorted=True):
        cmdOrderMap = self._cmd_order

        cmdList = self._cmdList
        if bSorted and cmdOrderMap:
            cmdList = sorted(cmdList, key=lambda (cmd, args):cmdOrderMap[cmd])

        return cmdList
    def iterCmds(self, bSorted=True):
        return iter(self.listCmds(bSorted))

    def _cmd_(self, name, *args):
        if self.fwd is not None:
            self.fwd.packet = None

        ce = (name, args)
        self._cmdCache.clear()
        self._cmdList.append(ce)
        return ce
    
    def _findCmds_(self, *cmds):
        for fn, args in self.iterCmds(False):
            if fn in cmds:
                return args
        else: return None

    def _cmd_clear_(self, name=None):
        if self.fwd is not None:
            self.fwd.packet = None
        self._cmdCache = {}
        if name is None:
            self._cmdList = []
        else:
            self._cmdList[:] = [(n,a) for n,a in self._cmdList if n != name]

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def __len__(self):
        return self.size

    def getSize(self):
        size = self._cmdCache.get('size', None)
        if size is None:
            size = self.calcSize(True)
            self._cmdCache['size'] = size

        return size
    size = property(getSize)

    def calcSize(self, incProtocol=True):
        mx = MsgSizer(incProtocol)
        return self.executeOn(mx)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #~ Utility Flyweight integration
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    _msgs_ = None
    def send(self):
        return self._msgs_.sendMsg(self)

    @classmethod
    def newFlyweight(klass, **ns):
        bklass = getattr(klass, '__flyweight__', klass)
        ns['__flyweight__'] = bklass
        return type(bklass)("%s_%s"%(bklass.__name__, id(ns)), (bklass,), ns)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #~ Debug Printing
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def pprint(self, out=None):
        mx = MsgPPrint(out)
        self.executeOn(mx)

