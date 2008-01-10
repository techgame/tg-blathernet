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

from struct import pack, unpack
from .base import BasicBlatherProtocol
from .circularUtils import circularAdjust

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Definitions 
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class IncrementProtocol(BasicBlatherProtocol):
    def reset(self):
        self.sendSeq = 0
        self.recvSeq = 0

    def send(self, toEntry, dmsg, pinfo):
        if dmsg:
            bytes, pinfo = self.encode(dmsg, pinfo)
            return toEntry.sendBytes(bytes, pinfo)

    def recvEncoded(self, advEntry, bytes, pinfo):
        seq, dmsg, pinfo = self.decode(bytes, pinfo)
        if dmsg:
            chan = self.Channel(pinfo['retEntry'], advEntry)
            return self.recvDecoded(chan, seq, dmsg)

    def encode(self, dmsg, pinfo):
        self.sendSeq += 1
        msgHeader = pack('!HH', self.sendSeq & 0xffff, self.recvSeq & 0xffff)

        # signal to include the seq header in the msgId
        pinfo['msgIdLen'] = 4 

        return (msgHeader+dmsg, pinfo)

    def decode(self, bytes, pinfo):
        msgHeader = bytes[:4]
        dmsg = bytes[4:]

        recvSeq, sentSeqAck = unpack('!HH', msgHeader)
        recvSeq, seqDiff = circularAdjust(self.recvSeq, recvSeq, 0xffff)

        if seqDiff > 0:
            self.recvSeq = recvSeq

        return (recvSeq, dmsg, pinfo)
