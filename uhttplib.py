
# import from https://bitbucket.org/evzijst/uhttplib
import httplib
import socket
import os
import time

class UnixHTTPConnection(httplib.HTTPConnection):

    def __init__(self, host, port=80, strict=None, timeout=None):
        self.path = None
        if host.startswith("unix:"):
            self.path = host.replace("unix:", "", 1)
            host = "localhost"
        httplib.HTTPConnection.__init__(self, host, port=port, strict=strict, timeout=timeout)

    def connect(self):
        if self.path:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            while not os.path.exists(self.path):
                time.sleep(0)
            sock.connect(self.path)
            self.sock = sock
        else:
            httplib.HTTPConnection.connect(self)

