#!/usr/bin/env python
import os
import time
import select
from subprocess import *
import argparse
import fcntl


class Reader():
    def __init__(self, files):
        self.files = files

    def run(self):
        buffers={}
        while len(self.files) > 0:
            ready,_,_ = select.select(self.files.keys(), [], [])
            wait=0
            for readfile in ready:
                if type(self.files[readfile]) == type(''):
                    newline, full = self.readline(readfile)
                    if readfile in buffers:
                        buffers[readfile] += newline
                    else:
                        buffers[readfile] = newline
                    if buffers[readfile] and full:
                        print "%s::%s" % (self.files[readfile], 
                                buffers[readfile]),
                        del buffers[readfile]
                    elif not buffers[readfile] and wait == 0:
                        wait=1
                else:
                    wait=2
                    pipe = self.files[readfile][0]
                    pipe.poll()
                    newline, full = self.readline(readfile)
                    if readfile in buffers:
                        buffers[readfile] += newline
                    else:
                        buffers[readfile] = newline
                    if buffers[readfile] and full:
                        print "%s::%s" % (self.files[readfile][1], 
                                            buffers[readfile]),
                        del buffers[readfile]
                    if pipe.returncode:
                        del self.files[readfile]
            if wait == 1:
                time.sleep(0.1)
 
    def readline(self, fd):
        returnval=''
        fileno = fd.fileno()
        fl = fcntl.fcntl(fileno, fcntl.F_GETFL)
        fcntl.fcntl(fileno, fcntl.F_SETFL, fl | os.O_NONBLOCK)
        try:
            readval = fd.read(1)
            returnval += readval
            while readval and readval[-1]!='\n':
                readval = fd.read(1)
                returnval += readval
            fcntl.fcntl(fileno, fcntl.F_SETFL, fl)
            return (returnval,True)
        except IOError:
            fcntl.fcntl(fileno, fcntl.F_SETFL, fl)
            return (returnval,False)

    def close(self):
        for readfile in self.files:
            if type(self.files[readfile]) == type(''):
                readfile.close()
            else:
                self.files[readfile][0].poll()
                if not self.files[readfile][0].returncode:
                    self.files[readfile][0].terminate()


if __name__=="__main__":
    parser = argparse.ArgumentParser(
                   description='Multitail remote and local files.')
    parser.add_argument('logfiles', nargs='+', metavar='FILE',
                   help='Logfiles to follow')
    parser.add_argument('-g', '--grep', action='store', metavar='REGEXP',
                   help='Show only the lines that match the regexp REGEXP')
    params = parser.parse_args()
    
    grepstring=params.grep or ''

    read_files = {}
    for logfile in params.logfiles:
        if logfile.find(':') >= 0:
            host, logfile = logfile.split(':',1)
            p = Popen(["ssh","-o BatchMode=yes", host, "tail", "-f", logfile], 
                      stdin=PIPE, stdout=PIPE, close_fds=True)
            read_files[p.stdout] = [p, host+':'+logfile]
        else:
            fd=open(logfile, 'r')
            read_files[fd] = logfile
    try:
        reader = Reader(read_files)
        reader.run()
    except KeyboardInterrupt:
        reader.close()



