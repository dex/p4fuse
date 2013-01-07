p4fuse
======

A FUSE file system for P4

This is a practice of use of python-llfuse. And it is only used to list directories and files in perforce depot.


Prerequisite
============

  - FUSE supprot (For Linux)
    - Kernel >= 2.6.26
    - FUSE library >= 2.8.0
  - python-llfuse
    - Debian/Ubuntu: `sudo apt-get install python-llfuse`


Usage
=====

Mount:
```bash
./p4fuse.py <mountpoint> &
```

Unmount:
```bash
fusermount -u [-z] <mountpoint>
```


ToDo
====

  1. Show the correct atime,mtime and ctime
  2. Login prompt for expired ticket
  3. Cache management
