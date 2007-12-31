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

from TG.metaObserving.obRegistry import OBRegistry

from ..base import BlatherObject

from .protocol import BlatherProtocol, OrderCompleteProtocol
from .marshalers import BlatherMarshal

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Definitions 
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class MessageHandlerBase(BlatherObject):
    _fm_ = BlatherObject._fm_.branch(Session = None)

    #protocol = BlatherProtocol()
    protocol = OrderCompleteProtocol()

    msgreg = OBRegistry()
    marshal = BlatherMarshal()

    def isBlatherMsgHandler(self): return True

    def newSession(self, chan):
        return self._fm_.Session(self, chan)

    def _dispatchMessage(self, dmsg, chan):
        method, args, kw = self.marshal.load(dmsg)
        method = self.msgreg[method]

        if method is None: 
            return NotImplemented

        return method(self, chan, *args, **kw)

