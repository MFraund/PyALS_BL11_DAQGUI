import socket
import sys

HOST = socket.gethostname()    # The remote host
PORT = 7010              # The same port as used by the server
s = None
for res in socket.getaddrinfo(HOST, PORT, socket.AF_UNSPEC, socket.SOCK_STREAM):
    af, socktype, proto, canonname, sa = res
    try:
        s = socket.socket(af, socktype, proto)
    except OSError as msg:
        s = None
        continue
    try:
        s.connect(sa)
    except OSError as msg:
        s.close()
        s = None
        continue
    break
if s is None:
    print('could not open socket')
    sys.exit(1)

s.settimeout(1.)
s.sendall(b'?0100 Connect\n')
data = s.recv(1024)

print('Received', repr(data))
