#!/usr/bin/env python2.7

import os
import sys
import hashlib
import platform
import traceback

import locale
locale.setlocale(locale.LC_ALL, '')

from ctypes import *

# constants

AE_IFMT   = 0o170000
AE_IFREG  = 0o100000
AE_IFLNK  = 0o120000
AE_IFSOCK = 0o140000
AE_IFCHR  = 0o020000
AE_IFBLK  = 0o060000
AE_IFDIR  = 0o040000
AE_IFIFO  = 0o010000


ARCHIVE_EOF     = 1   # Found end of archive.
ARCHIVE_OK      = 0   # Operation was successful.
ARCHIVE_RETRY   = -10 # Retry might succeed.
ARCHIVE_WARN    = -20 # Partial success.
ARCHIVE_FAILED  = -25 # Current operation cannot complete.
ARCHIVE_FATAL   = -30 # No more operations are possible.

ARCHIVE_FILTER_NONE     = 0
ARCHIVE_FILTER_GZIP     = 1
ARCHIVE_FILTER_BZIP2    = 2
ARCHIVE_FILTER_COMPRESS = 3
ARCHIVE_FILTER_PROGRAM  = 4
ARCHIVE_FILTER_LZMA     = 5
ARCHIVE_FILTER_XZ       = 6
ARCHIVE_FILTER_UU       = 7
ARCHIVE_FILTER_RPM      = 8
ARCHIVE_FILTER_LZIP     = 9
ARCHIVE_FILTER_LRZIP    = 10
ARCHIVE_FILTER_LZOP     = 11
ARCHIVE_FILTER_GRZIP    = 12

ARCHIVE_FORMAT_BASE_MASK           = 0xff0000
ARCHIVE_FORMAT_CPIO                = 0x10000
ARCHIVE_FORMAT_CPIO_POSIX          = (ARCHIVE_FORMAT_CPIO | 1)
ARCHIVE_FORMAT_CPIO_BIN_LE         = (ARCHIVE_FORMAT_CPIO | 2)
ARCHIVE_FORMAT_CPIO_BIN_BE         = (ARCHIVE_FORMAT_CPIO | 3)
ARCHIVE_FORMAT_CPIO_SVR4_NOCRC     = (ARCHIVE_FORMAT_CPIO | 4)
ARCHIVE_FORMAT_CPIO_SVR4_CRC       = (ARCHIVE_FORMAT_CPIO | 5)
ARCHIVE_FORMAT_CPIO_AFIO_LARGE     = (ARCHIVE_FORMAT_CPIO | 6)
ARCHIVE_FORMAT_SHAR                = 0x20000
ARCHIVE_FORMAT_SHAR_BASE           = (ARCHIVE_FORMAT_SHAR | 1)
ARCHIVE_FORMAT_SHAR_DUMP           = (ARCHIVE_FORMAT_SHAR | 2)
ARCHIVE_FORMAT_TAR                 = 0x30000
ARCHIVE_FORMAT_TAR_USTAR           = (ARCHIVE_FORMAT_TAR | 1)
ARCHIVE_FORMAT_TAR_PAX_INTERCHANGE = (ARCHIVE_FORMAT_TAR | 2)
ARCHIVE_FORMAT_TAR_PAX_RESTRICTED  = (ARCHIVE_FORMAT_TAR | 3)
ARCHIVE_FORMAT_TAR_GNUTAR          = (ARCHIVE_FORMAT_TAR | 4)
ARCHIVE_FORMAT_ISO9660             = 0x40000
ARCHIVE_FORMAT_ISO9660_ROCKRIDGE   = (ARCHIVE_FORMAT_ISO9660 | 1)
ARCHIVE_FORMAT_ZIP                 = 0x50000
ARCHIVE_FORMAT_EMPTY               = 0x60000
ARCHIVE_FORMAT_AR                  = 0x70000
ARCHIVE_FORMAT_AR_GNU              = (ARCHIVE_FORMAT_AR | 1)
ARCHIVE_FORMAT_AR_BSD              = (ARCHIVE_FORMAT_AR | 2)
ARCHIVE_FORMAT_MTREE               = 0x80000
ARCHIVE_FORMAT_RAW                 = 0x90000
ARCHIVE_FORMAT_XAR                 = 0xA0000
ARCHIVE_FORMAT_LHA                 = 0xB0000
ARCHIVE_FORMAT_CAB                 = 0xC0000
ARCHIVE_FORMAT_RAR                 = 0xD0000
ARCHIVE_FORMAT_7ZIP                = 0xE0000



def get_library():
    if platform.system() == 'Darwin':
        path = '/usr/local/Cellar/libarchive/3.1.2/lib/libarchive.dylib'
    elif platform.system() == 'Linux':
        path = '/usr/lib/x86_64-linux-gnu/libarchive.so.13'
    
    return cdll.LoadLibrary(path)


def _check_zero_success(value):
    if value != ARCHIVE_OK:
        raise ValueError("Function returned failure: (%d)" % (value))
    
    return value

lib = get_library()

ARCHIVE_WRITE_CALLBACK = CFUNCTYPE(c_ssize_t, c_void_p, c_void_p, POINTER(c_void_p), c_size_t)
ARCHIVE_OPEN_CALLBACK = CFUNCTYPE(c_int, c_void_p, c_void_p)
ARCHIVE_CLOSE_CALLBACK = CFUNCTYPE(c_int, c_void_p, c_void_p)

lib.archive_error_string.argtypes = [c_void_p]
lib.archive_error_string.restype = c_char_p

lib.archive_entry_pathname.argtypes = [c_void_p]
lib.archive_entry_pathname.restype = c_char_p

lib.archive_entry_new.argtypes = []
lib.archive_entry_new.restype = c_void_p

lib.archive_entry_sourcepath.argtypes = [c_void_p]
lib.archive_entry_sourcepath.restype = c_char_p

lib.archive_entry_free.argtypes = [c_void_p]
lib.archive_entry_free.restype = None

lib.archive_entry_size.argtypes = [c_void_p]
lib.archive_entry_size.restype = c_longlong

lib.archive_entry_set_pathname.argtypes = [c_void_p, c_char_p]
lib.archive_entry_set_pathname.restype = None

lib.archive_entry_filetype.argtypes = [c_void_p]
lib.archive_entry_filetype.restype = c_int

lib.archive_entry_mtime.argtypes = [c_void_p]
lib.archive_entry_mtime.restype = c_long

lib.archive_entry_set_size.argtypes = [c_void_p, c_int64]
lib.archive_entry_set_size.restype = None

lib.archive_entry_set_filetype.argtypes = [c_void_p, c_uint]
lib.archive_entry_set_filetype.restype = None

lib.archive_entry_set_perm.argtypes = [c_void_p, c_int]
lib.archive_entry_set_perm.restype = None

lib.archive_entry_clear.argtypes = [c_void_p]
lib.archive_entry_clear.restype = c_void_p

lib.archive_write_new.argtypes = []
lib.archive_write_new.restype = c_void_p

lib.archive_write_disk_new.argtypes = []
lib.archive_write_disk_new.restype = c_void_p

lib.archive_write_disk_set_options.argtypes = [c_void_p, c_int]
lib.archive_write_disk_set_options.restype = _check_zero_success

lib.archive_write_header.argtypes = [c_void_p, c_void_p]
lib.archive_write_header.restype = _check_zero_success

lib.archive_write_finish_entry.argtypes = [c_void_p]
lib.archive_write_finish_entry.restype = _check_zero_success

lib.archive_write_close.argtypes = [c_void_p]
lib.archive_write_close.restype = _check_zero_success

lib.archive_write_free.argtypes = [c_void_p]
lib.archive_write_free.restype = _check_zero_success

lib.archive_write_data_block.argtypes = [
    c_void_p,
    c_void_p,
    c_size_t,
    c_longlong]
lib.archive_write_data_block.restype = _check_zero_success

lib.archive_write_add_filter_bzip2.argtypes = [c_void_p]
lib.archive_write_add_filter_bzip2.restype = _check_zero_success

lib.archive_write_add_filter_compress.argtypes = [c_void_p]
lib.archive_write_add_filter_compress.restype = _check_zero_success

lib.archive_write_add_filter_gzip.argtypes = [c_void_p]
lib.archive_write_add_filter_gzip.restype = _check_zero_success

lib.archive_write_add_filter_none.argtypes = [c_void_p]
lib.archive_write_add_filter_none.restype = _check_zero_success

lib.archive_write_open_filename.argtypes = [c_void_p, c_char_p]
lib.archive_write_open_filename.restype = _check_zero_success

lib.archive_write_data.argtypes = [c_void_p, c_void_p, c_size_t]
lib.archive_write_data.restype = c_ssize_t

lib.archive_read_disk_set_standard_lookup.argtypes = [c_void_p]
lib.archive_read_disk_set_standard_lookup.restype = _check_zero_success

lib.archive_write_open_memory.argtypes = [c_void_p, 
                                        c_void_p, 
                                        c_size_t, 
                                        POINTER(c_size_t)]
lib.archive_write_open_memory.restype = _check_zero_success

lib.archive_write_open_fd.argtypes = [c_void_p, c_int]
lib.archive_write_open_fd.restype = _check_zero_success

lib.archive_write_open.argtypes = [c_void_p, c_void_p, ARCHIVE_OPEN_CALLBACK, ARCHIVE_WRITE_CALLBACK, ARCHIVE_CLOSE_CALLBACK]
lib.archive_write_open.restype = _check_zero_success

lib.archive_write_open_memory.argtypes = [c_void_p, c_void_p, c_size_t, POINTER(c_size_t)]
lib.archive_write_open_memory.restype = _check_zero_success

lib.archive_write_set_bytes_per_block.argtypes = [c_void_p, c_int]
lib.archive_write_set_bytes_per_block.restype = _check_zero_success

lib.archive_write_set_bytes_in_last_block.argtypes = [c_void_p, c_int]
lib.archive_write_set_bytes_in_last_block.restype = _check_zero_success

lib.archive_write_add_filter.argtypes = [c_void_p, c_int]
lib.archive_write_add_filter.restype = _check_zero_success

lib.archive_write_set_format_zip.argtypes = [c_void_p]
lib.archive_write_set_format_zip.restype = _check_zero_success


class ZipWriteStream(object):
    def __init__(self, fileno):
        self.a = lib.archive_write_new()
        assert self.a
        lib.archive_write_set_format_zip(self.a)

        lib.archive_write_open_fd(self.a, fileno)
    
        self.entry = lib.archive_entry_new()
        assert self.entry

    def start_entry(self, pathname, size):
        pathname = pathname.encode("utf-8")
        lib.archive_entry_clear(self.entry)
        lib.archive_entry_set_pathname(self.entry, c_char_p(pathname))
        lib.archive_entry_set_size(self.entry, size)
        lib.archive_entry_set_filetype(self.entry, AE_IFREG)
        lib.archive_entry_set_perm(self.entry, 0o644)

        lib.archive_write_header(self.a, self.entry)

    def write(self, data):
        n = lib.archive_write_data(self.a,
            cast(c_char_p(data), c_void_p),
            len(data))
        assert n != 0

    def close(self):
        lib.archive_write_close(self.a)
        lib.archive_write_free(self.a)


if __name__ == "__main__":
    s = ZipWriteStream(sys.stdout.fileno())
    s.start_entry("aaa", 3)
    s.write("bbb")
    s.start_entry("ccc", 3)
    s.write("ddd")
    s.close()
