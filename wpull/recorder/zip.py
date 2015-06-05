import sys
import tempfile
import contextlib

from wpull.recorder.base import BaseRecorder, BaseRecorderSession
import wpull.util

from wpull.recorder.archive import ZipWriteStream


class ZipRecorder(BaseRecorder):
    '''Output documents as a stream.'''
    def __init__(self, file):
        self._file = file

        self._zip_stream = ZipWriteStream(self._file.fileno())

    @contextlib.contextmanager
    def session(self):
        yield ZipRecorderSessionDelegate(self._zip_stream)

    def close(self):
        self._zip_stream.close()
        self._file.close()


class ZipRecorderSessionDelegate(BaseRecorderSession):
    '''Delegate to either HTTP or FTP recorder session.'''
    def __init__(self, *args, **kwargs):
        self._args = args
        self._kwargs = kwargs
        self._child_session = None

    def close(self):
        if self._child_session:
            return self._child_session.close()

    def pre_request(self, request):
        if not self._child_session:
            self._child_session = HTTPZipRecorderSession(
                *self._args, **self._kwargs
            )

        self._child_session.pre_request(request)

    def request(self, request):
        self._child_session.request(request)

    def request_data(self, data):
        self._child_session.request_data(data)

    def pre_response(self, response):
        self._child_session.pre_response(response)

    def response(self, response):
        self._child_session.response(response)

    def response_data(self, data):
        self._child_session.response_data(data)

    def begin_control(self, request, connection_reused=False):
        if not self._child_session:
            self._child_session = FTPZipRecorderSession(
                *self._args, **self._kwargs
            )

        self._child_session.begin_control(
            request, connection_reused=connection_reused
        )

    def request_control_data(self, data):
        self._child_session.request_control_data(data)

    def response_control_data(self, data):
        self._child_session.response_control_data(data)

    def end_control(self, response, connection_closed=False):
        if self._child_session:
            self._child_session.end_control(
                response, connection_closed=connection_closed
            )


class HTTPZipRecorderSession(BaseRecorderSession):
    '''Output document recorder session.'''
    def __init__(self, zip_stream):
        self._zip_stream = zip_stream
        self._response = None
        self._request = None
        self._response_length = None
        self._response_file = None
        self._path = None

    def pre_request(self, request):
        self._request = request
        self._path = request.url_info.host + request.url_info.resource
        if self._path.endswith("/"):
            self._path += "_index"

    def pre_response(self, response):

        self._response_length = response.fields.get('Content-Length')
        if self._response_length:
            self._response_length = int(self._response_length)
            self._zip_stream.start_entry(self._path, self._response_length)
        else:
            self._response_file = tempfile.TemporaryFile()
        
        self._response = response

    def response_data(self, data):
        if not self._response:
            # within headers
            return

        if self._response_file:
            self._response_file.write(data)
        else:
            assert self._response_length is not None
            self._zip_stream.write(data)

    def response(self, response):
        if self._response_file:
            body_length = self._response_file.tell()
            self._zip_stream.start_entry(self._path, body_length)
            self._response_file.seek(0)
            while True:
                d = self._response_file.read(4096*128)
                if not d:
                    break
                self._zip_stream.write(d)
            self._response_file.close()



class FTPZipRecorderSession(BaseRecorderSession):
    '''Output document recorder session.'''
    def __init__(self, zip_stream):
        self._zip_stream = zip_stream
        self._response_length = None
        self._response_file = None
        self._path = None
        
    def begin_control(self, request, connection_reused=False):
        self._path = request.url_info.host + request.url_info.resource
        if self._path.endswith("/"):
            self._path += "_index"

    def pre_response(self, response):
        self._response_length = response.file_transfer_size

        if self._response_length:
            self._zip_stream.start_entry(self._path, self._response_length)
        else:
            self._response_file = tempfile.TemporaryFile()

    def response_data(self, data):
        if self._response_file:
            self._response_file.write(data)
        else:
            assert self._response_length is not None
            self._zip_stream.write(data)

    def response(self, response):
        if self._response_file:
            response_length = self._response_file.tell()
            self._zip_stream.start_entry(self._path, response_length)
            self._response_file.seek(0)
            while True:
                d = self._response_file.read(4096*128)
                if not d:
                    break
                self._zip_stream.write(d)
            self._response_file.close()
