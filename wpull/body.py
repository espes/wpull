# encoding=utf-8
'''Request and response payload.'''
import io
import os
import tempfile

import wpull.util


class Body(object):
    '''Represents the document/payload of a request or response.

    This class is a wrapper around a file object. Methods are forwarded
    to the underlying file object.

    Attributes:
        file (file): The file object.

    Args:
        file (file): Use the given `file` as the file object.
    '''
    def __init__(self, file=None):
        self.file = file or new_temp_file()
        self._content_data = None

    def __getattr__(self, key):
        return getattr(self.file, key)

    def content(self):
        '''Return the content of the file.

        If this function is invoked, the contents of the entire file is read
        and cached.

        Returns:
            ``bytes``: The entire content of the file.
        '''
        if not self._content_data:
            if self.file.seekable():
                with wpull.util.reset_file_offset(self.file):
                    self._content_data = self.file.read()
            else:
                self._content_data = self.file.read()

        return self._content_data

    def size(self):
        '''Return the size of the file.'''
        try:
            return os.fstat(self.file.fileno()).st_size
        except io.UnsupportedOperation:
            pass

        if self.file.seekable():
            with wpull.util.reset_file_offset(self.file):
                self.file.seek(0, os.SEEK_END)
                return self.file.tell()

        raise OSError('Unsupported operation.')

    def to_dict(self):
        '''Convert the body to a :class:`dict`.

        Returns:
            dict: The items are:

                * ``filename`` (string, None): The path of the file.
                * ``size`` (int, None): The size of the file.
        '''
        try:
            name = self.file.name
        except AttributeError:
            name = None

        try:
            size = self.size()
        except OSError:
            size = None

        return {
            'filename': name,
            'size': size,
        }


def new_temp_file(directory=None):
    '''Return a new temporary file.'''
    return tempfile.NamedTemporaryFile(
        prefix='wpull-', suffix='.tmp', dir=directory)