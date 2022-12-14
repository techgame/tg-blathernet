#!/usr/bin/env python
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

from __future__ import with_statement
import sys
import time
from getpass import getuser
from TG.blathernet import Blather, advertIdForNS

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Definitions 
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

adChat = advertIdForNS('#demoChat')

blather = Blather('Chat')

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Main 
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def setup():
    rf = blather.routes.factory
    mudpRoutes = rf.connectAllMUDP()
    print
    print 'ALL UDP Routes:'
    for k, v in mudpRoutes:
        print '   %r: %r,' %(k, v)
    print

    blather.run(True)

@blather.respondTo(adChat)
def chatResponder(body, fmt, topic, mctx):
    body = body.decode('utf-8')
    print '\r%s> %s' % (topic, body)
    print prompt,
    sys.stdout.flush()

prompt = '>>'
def main():
    setup()

    blather.addAdvertRoutes(adChat)

    chatMsg = blather.newMsg(adChat)
    # forward out all interfaces, even after being handled
    chatMsg.forward(None, False)

    me = getuser()
    try:
        me = raw_input("Name? (%s)>" %(me,)) or me
        print "Welcome, %s!"%(me,)

        while 1:
            body = raw_input(prompt)
            if not body: break

            body = body.encode("utf-8")
            with chatMsg as cm:
                cm.msg(body, 0, me)
                cm.send()

    except (KeyboardInterrupt, EOFError), e: 
        pass

    print
    print "Bye!"
    print

if __name__=='__main__':
    main()

