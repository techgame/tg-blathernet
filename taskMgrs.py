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

from __future__ import with_statement

import weakref
import time
import traceback
import threading
from functools import partial
from heapq import heappop, heappush

from TG.kvObserving import KVSet, KVList

from .base import BlatherObject

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Definitions 
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def threadcall(method):
    def decorate(*args, **kw):
        t = threading.Thread(target=method, args=args, kwargs=kw)
        t.setDaemon(True)
        t.start()
        return t
    decorate.__name__ = method.__name__
    decorate.__doc__ = method.__doc__
    return decorate

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class BasicBlatherTaskMgr(BlatherObject):
    timeout = 0.05
    tasksleep = time.sleep

    def __init__(self, name):
        BlatherObject.__init__(self)
        self.name = name
        self.initTasks()

    def initTasks(self):
        self.tasks = set()
        self._e_tasks = threading.Event()
        self.setTaskSleep()

    def __repr__(self):
        return '<TM %s |%s|>' % (self.name, len(self.tasks))

    def __len__(self):
        return len(self.tasks)

    def setTaskSleep(self, tasksleep=None):
        if tasksleep is None:
            tasksleep = self._e_tasks.wait
        self.tasksleep = tasksleep

    def addTask(self, task):
        if task is None:
            return None

        self.tasks.add(task)
        self._e_tasks.set()
        return task

    def run(self, threaded=False):
        if threaded:
            return self.runThreaded()

        while not self.done:
            self.process(False)

    @threadcall
    def runThreaded(self):
        self.run(False)

    def process(self, allActive=True):
        n = 0
        activeTasks = self.tasks
        e_task = self._e_tasks
        while activeTasks:
            e_task.clear()
            self.kvpub.event('@process')
            for task in list(activeTasks):
                n += 1
                activeTasks.discard(task)
                try:
                    if task():
                        activeTasks.add(task)
                except Exception:
                    traceback.print_exc()

            if allActive and n:
                self.tasksleep(0)
            else: break
        if not n:
            self.kvpub.event('@process_sleep')
            self.tasksleep(self.timeout)
        return n

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Timer based Tasks
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class BasicBlatherTimerMgr(BasicBlatherTaskMgr):
    done = False
    timestamp = time.time

    def __init__(self, name):
        BasicBlatherTaskMgr.__init__(self, name)
        self.initTimer()

    def initTimer(self):
        self.lockTimerHQ = threading.Lock()
        with self.lockTimerHQ:
            self.hqTimer = []
        self.threadTimers()

    def addTimer(self, tsStart, task):
        if task is None:
            return None

        if tsStart <= 4000:
            tsStart += self.timestamp()

        with self.lockTimerHQ:
            hqTimer = self.hqTimer
            heappush(hqTimer, (tsStart, task))

        return task

    def extendTimers(self, timerEvents, ts=None):
        if ts is None:
            ts = self.timestamp()

        with self.lockTimerHQ:
            hqTimer = self.hqTimer
            for (tsStart, task) in timerEvents:
                if tsStart <= 4000:
                    tsStart += ts
                heappush(hqTimer, (tsStart, task))

    debug = False
    timersleep = time.sleep
    minTimerFrequency = 0.008
    @threadcall
    def threadTimers(self):
        hqTimer = self.hqTimer
        while not self.done:
            if hqTimer:
                ts = self.timestamp()

                firedTimers = []
                with self.lockTimerHQ:
                    while hqTimer and ts > hqTimer[0][0]:
                        tsTask, task = heappop(hqTimer)
                        firedTimers.append(task)

                if firedTimers:
                    self.addTask(partial(self._processFiredTimers, ts, firedTimers))

            self.timersleep(self.minTimerFrequency)

    def _processFiredTimers(self, ts, firedTimers):
        self.kvpub.event('@timer')

        timerEvents = []
        for task in firedTimers:
            tsNext = task(ts)
            if tsNext is not None:
                timerEvents.append((tsNext, task))
        firedTimers[:] = []

        if timerEvents:
            self.extendTimers(timerEvents, ts)

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Blather Task Manger
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class BlatherTaskMgr(BasicBlatherTimerMgr):
    pass

