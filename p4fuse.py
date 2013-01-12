#!/usr/bin/env python
# encoding: utf-8

import os
import sys
import llfuse
import errno
import stat
import marshal
import subprocess
from time import time
from llfuse import FUSEError
from contextlib import contextmanager

class P4Command(object):
    def __init__(self, p4bin):
        self.p4bin = p4bin
    
    @contextmanager
    def p4_popen(self, *args):
        pipe = subprocess.Popen([self.p4bin, '-G'] + list(args), stdout=subprocess.PIPE).stdout
        try:
            yield pipe
        except EOFError:
            raise StopIteration
        finally:
            pipe.close()

    def do_dirs(self, path):
        if path[-2:] != '/*':
            path += '/*'
        with self.p4_popen('dirs', path) as pipe:
            while True:
                yield marshal.load(pipe)

    def do_filelog(self, path):
        if path[-2:] != '/*':
            path += '/*'
        with self.p4_popen('filelog', path) as pipe:
            while True:
                yield marshal.load(pipe)

    def do_print(self, path):
        with self.p4_popen('print', path) as pipe:
            if marshal.load(pipe)['code'] == 'error':
                raise EOFError
            while True:
                yield marshal.load(pipe)

class P4Operations(llfuse.Operations):
    def __init__(self, p4bin='/usr/local/bin/p4', p4root='//depot'):
        super(llfuse.Operations, self).__init__()
        self.p4cmd = P4Command(p4bin)
        self.p4root = p4root
        self.cache = { llfuse.ROOT_INODE: {'inode': llfuse.ROOT_INODE, 'inode_p': llfuse.ROOT_INODE, 'name': '..', 'is_dir': True, 'child': {}} }
        self.last_inode = llfuse.ROOT_INODE;

    def get_next_inode(self):
        self.last_inode += 1
        return self.last_inode

    def gen_depot_path(self, inode):
        path = ""
        while inode != llfuse.ROOT_INODE:
            try:
                path = '/' + self.cache.get(inode)['name'] + path
                inode = self.cache.get(inode)['inode_p']
            except:
                raise
        return self.p4root + path

    def scan_dir(self, inode_p):
        if not self.cache.get(inode_p)['is_dir']:
            return False
        if len(self.cache.get(inode_p)['child']) != 0:
            return False
        # . and ..
        self.cache.get(inode_p)['child']['.'] = inode_p
        self.cache.get(inode_p)['child']['..'] = self.cache.get(inode_p)['inode_p']
        # dirs
        for rv in self.p4cmd.do_dirs(self.gen_depot_path(inode_p)):
            name = rv['dir'].split('/')[-1]
            inode = self.get_next_inode()
            self.cache[inode] = {'inode':inode, 'inode_p': inode_p, 'name': name, 'is_dir': True, 'child': {}}
            self.cache.get(inode_p)['child'][name] = inode
        # files
        for rv in self.p4cmd.do_filelog(self.gen_depot_path(inode_p)):
            name = rv['depotFile'].split('/')[-1]
            size = int(rv.get('fileSize0', '0'))
            inode = self.get_next_inode()
            self.cache[inode] = {'inode':inode, 'inode_p': inode_p, 'name': name, 'is_dir': False, 'size': size}
            self.cache.get(inode_p)['child'][name] = inode
        return True

    
    def lookup(self, inode_p, name):
        self.scan_dir(inode_p)
        try:
            inode = self.cache.get(inode_p)['child'][name]
        except:
            raise(llfuse.FUSEError(errno.ENOENT))
        return self.getattr(inode)

    def getattr(self, inode):
        entry = llfuse.EntryAttributes()
        entry.st_ino = inode
        entry.generation = 0
        entry.entry_timeout = 300
        entry.attr_timeout = 300
        if self.cache.get(inode)['is_dir']:
            entry.st_mode = stat.S_IFDIR | stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH
            entry.st_size = 4096
        else:
            entry.st_mode = stat.S_IFREG | stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
            entry.st_size = self.cache.get(inode)['size']
        entry.st_nlink = 1
        entry.st_uid = os.getuid() 
        entry.st_gid = os.getgid() 
        entry.st_rdev = 0
        entry.st_blksize = 512
        entry.st_blocks = 1
        entry.st_atime = time() 
        entry.st_mtime = time()
        entry.st_ctime = time()
        return entry

    def opendir(self, inode):
        return inode

    def readdir(self, inode, off):
        self.scan_dir(inode)
        if off == 0:
            off = -1
        for k,v in sorted(self.cache.get(inode)['child'].items(), key=lambda t:t[1]):
            if v > off:
                yield (k, self.getattr(v), v)

    def open(self, inode, flags):
        return inode

    def access(self, inode, mode, ctx):
        return True

    def read(self, fh, offset, length):
        data = ''
        for rv in self.p4cmd.do_print(self.gen_depot_path(fh)):
            data += rv['data']
        return data[offset:offset+length]

if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: %s <mountpoint>' % sys.argv[0])

    mountpoint = sys.argv[1]
    operations = P4Operations()

    llfuse.init(operations, mountpoint, [ b"fsname=p4-fuse", b"ro" ])

    try:
        llfuse.main(single=True)
    except:
        llfuse.close(unmount=False)
        raise

    llfuse.close()
