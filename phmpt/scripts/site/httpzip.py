"""List a remote zip's entries with HTTP range requests (central directory only)."""
import io, sys, urllib.request, zipfile

class HTTPRangeFile(io.RawIOBase):
    def __init__(self, url):
        self.url = url
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=60) as r:
            self.size = int(r.headers["Content-Length"])
        self.pos = 0
        self.requests = 0
    def seekable(self): return True
    def readable(self): return True
    def tell(self): return self.pos
    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else self.pos + off if whence == 1 else self.size + off
        return self.pos
    def read(self, n=-1):
        if n is None or n < 0: n = self.size - self.pos
        if n == 0 or self.pos >= self.size: return b""
        end = min(self.pos + n, self.size) - 1
        req = urllib.request.Request(self.url, headers={"Range": f"bytes={self.pos}-{end}"})
        with urllib.request.urlopen(req, timeout=120) as r:
            data = r.read()
        self.requests += 1
        self.pos += len(data)
        return data
    def readinto(self, b):
        d = self.read(len(b)); b[:len(d)] = d; return len(d)

def entries(url):
    f = io.BufferedReader(HTTPRangeFile(url), buffer_size=1 << 20)
    z = zipfile.ZipFile(f)
    return f.raw.size, [(i.filename, i.file_size) for i in z.infolist()]

if __name__ == "__main__":
    size, ents = entries(sys.argv[1])
    print(size, len(ents))
    for e in ents[:5]: print(e)
