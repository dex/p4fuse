p4fuse
======

A FUSE file system for P4

This is a practice of use of python-llfuse. And it is only used to list directories and files in perforce depot.


prerequisite
============

a. FUSE supprot in kernel (fuse.ko)
b. python-llfuse

usage
=====

Mount:
  ./p4fuse.py <mountpoint>

Unmount:
  fusermount -u [-z] <mountpoint>


TODO
====

1. Show the correct atime,mtime and ctime
2. Login process
