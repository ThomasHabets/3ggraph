#!/usr/bin/python

import serial
import time
import re
import numpy
import random
import matplotlib
matplotlib.use('GTKAgg') # do this before importing pylab

import matplotlib.pyplot as plt
import gobject

class Graph:
    def __init__(self, cb):
        import gtk
        self.fig = plt.figure()
        self.ax1 = self.fig.add_subplot(211)
        self.ax2 = self.fig.add_subplot(212)
        gobject.idle_add(self.animate)
        self.cb = cb
        self.width = 120
        self.lines =  self.ax1.plot(*[[]] * (2 * 1))
        self.lines += self.ax2.plot(*[[]] * (2 * 7))
        self.starttime = time.time()
        self.linemap = {'RSSI':              (self.lines[0], self.ax1, [], []),
                        'DSFLOWRPT-DURATION':(self.lines[1], self.ax2, [], []),
                        'DSFLOWRPT-TX':      (self.lines[2], self.ax2, [], []),
                        'DSFLOWRPT-RX':      (self.lines[3], self.ax2, [], []),
                        'DSFLOWRPT-TOTTX':   (self.lines[4], self.ax2, [], []),
                        'DSFLOWRPT-TOTRX':   (self.lines[5], self.ax2, [], []),
                        'DSFLOWRPT-MAXTX':   (self.lines[6], self.ax2, [], []),
                        'DSFLOWRPT-MAXRX':   (self.lines[7], self.ax2, [], []),
                        }
        #plt.setp([self.line], animated=True)

    def delta(self, a):
        if len(a) == 0:
            return []
        x = a[0]
        ret = []
        for n in a[1:]:
            ret.append(n-x)
            x = n
        return ret

    def fix_axis(self):
        xva = []
        yva = {}
        for k in self.linemap.keys():
            lin,ax,dx,dy = self.linemap[k]
            xva.extend(dx)
            if k in ('DSFLOWRPT-TOTTX','DSFLOWRPT-TOTRX'):
                dy = self.delta(dy)
            yva[ax] = yva.get(ax, []) + dy + [0]

        t = max(self.width, int(time.time() - self.starttime))
        self.ax1.axis([t-self.width,t,
                       0,max(yva[self.ax1])*2])
        self.ax2.axis([t-self.width,t,
                       0,max(yva[self.ax2])*2])
        

    def animate(self, *args):
        #line.set_ydata(y)
        for typ,x,y in self.cb():
            if typ in ('RSSI'):
                delta = False
            elif typ in ('DSFLOWRPT-TOTTX', 'DSFLOWRPT-TOTRX'):
                delta = True
            else:
                continue
            line,ax,xarr,yarr = self.linemap[typ]
            xarr.append(x)
            yarr.append(y)
            while len(xarr) > self.width:
                del xarr[0]
                del yarr[0]
            tx = xarr
            ty = yarr
            if delta:
                tx = xarr[1:]
                ty = self.delta(yarr)
            if len(tx) != 0:
                line.set_xdata([x-self.starttime for x in tx])
                line.set_ydata(ty)
                self.fix_axis()
            self.fig.canvas.draw()
        return True

    def run(self):
        plt.show()
        

class Graph3G:
    def __init__(self, dev):
        self.dev = dev
        self.graph = Graph(self.get_new_data)
        self.serial = serial.Serial(dev, 19200, timeout=0.1)
        self.log = open('3g.data', 'a')
        self.rawdata = ""
        self.modes = {4: '3G',
                      7: 'HSPA',
                      }
        self.mode = 'unknown'

    def run(self):
        self.graph.run()

    def parse(self, line):
        m = re.match(r'AT+CSQ', line)
        if m:
            return []
    
        #m = re.match(r'\+CSQ: (\d+),(\d+)', line)
        #if m:
        #    a = int(m.group(1))
        #    b = int(m.group(2))
        #    return "CSQ: %d %d (%.2f%%)" % (a,b,100.0*a/b)

        m = re.match(r'\^RSSI:(\d+)', line)
        if m:
            a = int(m.group(1))
            return [("RSSI", time.time(), a)]

        m = re.match(r'\^DSFLOWRPT:(\w+),(\w+),(\w+),'
                     + r'(\w+),(\w+),(\w+),(\w+)',
                     line)
        if m:
            dur, tx, rx, tot,tot2,n6,n7 = map(lambda x: int(x,16), m.groups())
            t = time.time()
            return [('DSFLOWRPT-DURATION', t, dur),
                    ('DSFLOWRPT-TX', t, tx),
                    ('DSFLOWRPT-RX', t, rx),
                    ('DSFLOWRPT-TOTTX', t, tot),
                    ('DSFLOWRPT-TOTRX', t, tot2),
                    ('DSFLOWRPT-MAXTX', t, n6),
                    ('DSFLOWRPT-MAXRX', t, n7),
                    ]


        m = re.match(r'\^MODE:5,(\d+)', line)
        if m:
            self.mode = int(m.group(1))
            return []

        return []

    def get_new_data(self):
        """return list of type,x,y"""
        self.rawdata += self.serial.read()
        try:
            line,self.rawdata = self.rawdata.split('\n', 1)
        except ValueError, e:
            return []
        self.log.write("%.3f %s\n" % (time.time(), line))
        self.log.flush()
        return self.parse(line)

t = 1
def getnewdata():
    global t
    t = t + 1
    time.sleep(0.1)
    return t, int(random.random() * 100)

def drawtest():
    g = Graph(getnewdata)
    plt.show()
    print "lala"

def main():
    g = Graph3G('/dev/ttyUSB1')
    g.run()

if __name__=='__main__':
    main()
