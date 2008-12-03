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

from functools import partial
from struct import pack, unpack, calcsize
from StringIO import StringIO

from ..msgObjectBase import iterMsgId, advertIdForNS

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Definitions 
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class MsgEncoder_v02(object):
    msgVersion = '\x02'
    msgIdLen = 4
    newMsgId = iterMsgId(msgIdLen).next

    def getPacket(self):
        return self.tip.getvalue()
    packet = property(getPacket)

    def advertNS(self, advertNS, msgId=None):
        advertId = advertIdForNS(advertNS)
        return self.advertMsgId(advertId, msgId)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def sourceMsgObject(self, mobj):
        return self
    def sourcePacket(self, packet, rinfo):
        return self

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def advertMsgId(self, advertId, msgId=None):
        tip = StringIO()
        tip.write(self.msgVersion)

        msgIdLen = self.msgIdLen
        if msgId is None:
            msgId = self.newMsgId()
        elif len(msgId) < msgIdLen:
            raise ValueError("MsgId must have a least %s bytes" % (msgIdLen,))
        tip.write(msgId[:msgIdLen])

        if len(advertId) != 16:
            raise ValueError("AdvertId must be 16 bytes long")
        tip.write(advertId)

        self.tip = tip

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #~ Routing and Delivery Commands
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def reply(self, replyAdvertIds):
        if isinstance(replyAdvertIds, str):
            replyAdvertIds = [replyAdvertIds]
        return self.advertIdRefs(replyAdvertIds, True)

    def refs(self, advertIds, key=None):
        return self.advertIdRefs(advertIds, key)
    def advertIdRefs(self, advertIds, key=None):
        cmd = 0x4; flags = 0
        if key is not None:
            if key == True:
                cmd |= 0x2
                key = ''
            else:
                cmd |= 0x1
                key = chr(len(key))+key
        else: key = ''

        advertIds = self._verifyAdvertIds(advertIds)
        if len(advertIds) > 16:
            raise ValueError("AdvertIds list must not contain more than 8 references")

        if advertIds:
            flags = len(advertIds)-1 # [1..16] => [0..15]
            self._writeCmd(cmd, flags, key, ''.join(advertIds))

    def end(self):
        self._writeCmd(0, 0)

    def forward(self, breadthLimit=1, whenUnhandled=True, fwdAdvertId=None):
        cmd = 0x1; flags = 0

        fwdBreadth = ''
        if breadthLimit in (0,1):
            # 0: all
            # 1: best route
            flags |= breadthLimit
        elif not isinstance(breadthLimit, int):
            if breadthLimit not in (None, 'all', '*'):
                raise ValueError("Invalid breadth limit value: %r" % (breadthLimit))
            #else: flags |= 0x0
        else:
            # 3: best n routes [1..16]; high nibble is unused/reserved
            flags |= 0x3
            fwdBreadth = max(min(breadthLimit, 16), 1) - 1
            fwdBreadth = chr(fwdBreadth)

        if whenUnhandled:
            flags |= 0x4

        if fwdAdvertId is not None:
            flags |= 0x8
            fwdAdvertId, = self._verifyAdvertIds([fwdAdvertId])
        else: fwdAdvertId = ''

        self._writeCmd(cmd, flags, fwdBreadth, fwdAdvertId)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #~ Message and Topic Commands
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    _msgPackFmt = {
        # msgs with no topic
        '1000': '!H0s',

        # msgs with variable length str topic
        '1001': '!HB',

        # XXX: UNUSED
        '1010': '!H9q',
        '1011': '!H9q',

        # msgs with integer as topicId
        '1100': '!HI',

        # msg with 4-byte topic
        '1101': '!H4s',

        # msg with 8-byte topic
        '1110': '!H8s',

        # msgs with advertId-length string as topicId
        '1111': '!H16s',
    }
    _msgPackFmt.update(
        (int(k, 2), (fmt, partial(pack, fmt)))
            for k,fmt in _msgPackFmt.items())

    _cmdByTopicLen = {4: 0xd, 8: 0xe, 16: 0xf}

    def _msgCmdPrefix(self, lenBody, topic=''):
        topicEx = ''
        if not topic: 
            if topic != 0:
                topic = ''
                cmd = 0x8
            else: cmd = 0xc
        elif isinstance(topic, str):
            cmd = self._cmdByTopicLen.get(len(topic))
        else:
            cmd = 0xc
            topic = int(topic)

        if cmd is None:
            topicEx = topic
            topic = len(topic)
            cmd = 0x9

        fmt, fmtPack = self._msgPackFmt[cmd]
        #print (cmd, fmt, topic, topicEx)
        prefix = fmtPack(lenBody, topic)
        return cmd, prefix+topicEx

    def msg(self, body, fmt=0, topic=None):
        if not (0 <= fmt <= 0xf):
            raise ValueError("Invalid format value: %r" % (fmt,))

        cmd, prefix = self._msgCmdPrefix(len(body), topic)
        self._writeCmd(cmd, fmt, prefix, body)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #~ Utils
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def _writeCmd(self, cmd, flags, *args):
        if not (0<=cmd<=0xf):
            raise ValueError("Cmd not in range [0..f]: %x" % (cmd,))
        if not (0<=flags<=0xf):
            raise ValueError("Flags not in range [0..f]: %x" % (flags,))

        cmd = (cmd << 4) | flags

        tip = self.tip
        tip.write(chr(cmd))
        for a in args:
            if a: 
                tip.write(a)
        return tip
    
    def _verifyAdvertIds(self, advertIds):
        r = []
        for adId in advertIds:
            adId = str(adId)
            if len(adId) != 16:
                raise ValueError("Invalid advertId len: %r" % (len(adId),))
            r.append(adId)
        return r

MsgEncoder = MsgEncoder_v02

