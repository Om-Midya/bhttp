"""bhttp/1 wire format, shared by bserve and bcurl.  The normative text is SPEC.md.

Frame = 8-byte header + payload.
    +----------------+--------+--------+--------------------------------+
    | Length (u16)   | Type   | Flags  | Request ID (u32)               |
    +----------------+--------+--------+--------------------------------+
All integers are big-endian.  Length counts payload bytes only.
"""
import struct

HEADER = struct.Struct(">HBBI")
HEADER_LEN = HEADER.size          # 8
MAX_PAYLOAD = 0xFFFF

# Frame types.  0x00 is reserved and is always malformed.
T_REQUEST, T_RESPONSE, T_DATA = 0x01, 0x02, 0x03
KNOWN_TYPES = {T_REQUEST, T_RESPONSE, T_DATA}
TYPE_NAMES = {T_REQUEST: "REQUEST", T_RESPONSE: "RESPONSE", T_DATA: "DATA"}

# Flags.  Bits 1..7 are reserved: senders clear them, receivers ignore them.
F_END = 0x01

# Request methods (first byte of a REQUEST payload).
M_GET, M_HEAD = 0x01, 0x02
METHOD_NAMES = {M_GET: "GET", M_HEAD: "HEAD"}

# Static header table.  Code = position + 1.  Code 0 means "literal name follows".
STATIC = ["host", "user-agent", "accept", "accept-encoding", "server",
          "date", "content-type", "content-length", "last-modified", "etag"]
STATIC_CODE = {name: i + 1 for i, name in enumerate(STATIC)}


class Malformed(ValueError):
    """The bytes were framed correctly but the payload does not parse."""


class Frame:
    __slots__ = ("type", "flags", "rid", "payload")

    def __init__(self, ftype, flags, rid, payload=b""):
        self.type, self.flags, self.rid, self.payload = ftype, flags, rid, payload

    def pack(self):
        if len(self.payload) > MAX_PAYLOAD:
            raise ValueError("payload exceeds 65535 bytes")
        return HEADER.pack(len(self.payload), self.type, self.flags, self.rid) + self.payload

    def describe(self):
        name = TYPE_NAMES.get(self.type, "UNKNOWN(0x%02x)" % self.type)
        end = " END" if self.flags & F_END else ""
        return "%s id=%d len=%d flags=0x%02x%s" % (name, self.rid, len(self.payload), self.flags, end)


def read_frame(f):
    """Read one frame from a binary file object.

    Returns None on a clean EOF (no bytes at a frame boundary).
    Raises EOFError if the connection ends in the middle of a frame.
    Unknown frame types are returned as-is; the caller decides to skip them.
    """
    hdr = f.read(HEADER_LEN)
    if not hdr:
        return None
    if len(hdr) < HEADER_LEN:
        raise EOFError("connection closed inside a frame header")
    length, ftype, flags, rid = HEADER.unpack(hdr)
    payload = f.read(length)
    if len(payload) < length:
        raise EOFError("connection closed inside a frame payload")
    return Frame(ftype, flags, rid, payload)


# --- payload encoding -------------------------------------------------------

class _Cursor:
    def __init__(self, data):
        self.data, self.pos = data, 0

    def take(self, n):
        if self.pos + n > len(self.data):
            raise Malformed("payload too short")
        chunk = self.data[self.pos:self.pos + n]
        self.pos += n
        return chunk

    def u8(self):
        return self.take(1)[0]

    def u16(self):
        return struct.unpack(">H", self.take(2))[0]

    def text(self, n, encoding="utf-8"):
        try:
            return self.take(n).decode(encoding)
        except UnicodeDecodeError:
            raise Malformed("invalid %s text" % encoding)

    def finish(self):
        if self.pos != len(self.data):
            raise Malformed("%d trailing bytes" % (len(self.data) - self.pos))


def _lp16(b):
    if len(b) > 0xFFFF:
        raise ValueError("string exceeds 65535 bytes")
    return struct.pack(">H", len(b)) + b


def encode_headers(headers):
    if len(headers) > 255:
        raise ValueError("more than 255 headers")
    out = bytearray([len(headers)])
    for name, value in headers:
        name = name.lower()
        code = STATIC_CODE.get(name)
        if code:
            out.append(code)
        else:
            raw = name.encode("ascii")
            if not 0 < len(raw) < 256:
                raise ValueError("literal header name must be 1..255 bytes")
            out += bytes([0, len(raw)]) + raw
        out += _lp16(value.encode("utf-8"))
    return bytes(out)


def _decode_headers(c):
    headers = []
    for _ in range(c.u8()):
        code = c.u8()
        if code == 0:
            n = c.u8()
            if n == 0:
                raise Malformed("empty literal header name")
            name = c.text(n, "ascii")
        elif code <= len(STATIC):
            name = STATIC[code - 1]
        else:
            raise Malformed("reserved header code %d" % code)
        headers.append((name, c.text(c.u16())))
    return headers


def encode_request(method, path, headers):
    return bytes([method]) + _lp16(path.encode("utf-8")) + encode_headers(headers)


def decode_request(payload):
    """Returns (method, path, headers).  Raises Malformed."""
    c = _Cursor(payload)
    method = c.u8()
    path = c.text(c.u16())
    if not path.startswith("/") or "\x00" in path:
        raise Malformed("path must start with '/' and contain no NUL")
    headers = _decode_headers(c)
    c.finish()
    return method, path, headers


def encode_response(status, headers):
    return struct.pack(">H", status) + encode_headers(headers)


def decode_response(payload):
    """Returns (status, headers).  Raises Malformed."""
    c = _Cursor(payload)
    status = c.u16()
    if not 100 <= status <= 599:
        raise Malformed("status %d out of range" % status)
    headers = _decode_headers(c)
    c.finish()
    return status, headers


# --- debugging --------------------------------------------------------------

def hexdump(data):
    lines = []
    for off in range(0, len(data), 16):
        chunk = data[off:off + 16]
        hx = " ".join("%02x" % b for b in chunk)
        asc = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append("%08x  %-47s  |%s|" % (off, hx, asc))
    return "\n".join(lines)
