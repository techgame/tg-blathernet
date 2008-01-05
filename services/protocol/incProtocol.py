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
from .base import BasicBlatherProtocol, circularDiff

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Definitions 
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class IncBlatherProtocol(BasicBlatherProtocol):
    def initCodec(self):
        self.sendSeq = 0
        self.recvSeq = 0

    def send(self, toEntry, dmsg, pinfo):
        if dmsg:
            bytes, pinfo = self.encode(dmsg, pinfo)
            return toEntry.sendBytes(bytes, pinfo)

    def recvEncoded(self, advEntry, bytes, pinfo):
        dmsg, pinfo = self.decode(bytes, pinfo)
        if dmsg:
            return self.recvDecoded(dmsg, pinfo)

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
        if circularDiff(self.recvSeq, recvSeq, 0xffff) > 0:
            self.recvSeq = recvSeq

        return (dmsg, pinfo)

