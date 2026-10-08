# bhttp/1: HTTP in binary, over one TCP connection

Version 1. This document is the whole protocol. A client and a server written from this text alone must interoperate.

## 1. Scope

bhttp/1 carries requests and responses over a single TCP connection. The default port is 9000. The client sends one request, waits for the complete response, and then can send the next request on the same connection. The connection stays open until one side closes it. All integers are big-endian (most significant byte first).

## 2. The frame

Every message on the wire is a sequence of frames. A frame is a fixed 8-byte header followed by a payload.

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-------------------------------+---------------+---------------+
|          Length (16)          |   Type (8)    |   Flags (8)   |
+-------------------------------+---------------+---------------+
|                        Request ID (32)                        |
+---------------------------------------------------------------+
|                     Payload (Length bytes)                  ...
+---------------------------------------------------------------+
```

Length is the number of payload bytes after the header, 0 to 65535. Type names the frame type (section 3). Flags is a bit set. Bit 0 (value 0x01) is END. Bits 1 to 7 are reserved: a sender must clear them and a receiver must ignore them. Request ID is chosen by the client. The first request on a connection has ID 1, and each later request adds 1. The server copies the ID into every frame of its reply. ID 0 is reserved and must not be used.

Why these widths. HTTP/2 chose 24 bits of length, 8 of type, 8 of flags and 31 of stream ID. A 24-bit length permits a 16 MiB frame, so HTTP/2 needs a SETTINGS exchange to cap frames at 16 KiB by default. bhttp/1 makes the cap part of the format instead. With 16 bits of length, a receiver never needs more than 64 KiB of buffer for one frame. A large body spans several DATA frames. 8 bits of type gives 253 usable types, which is more than a version 2 will use. HTTP/2 spends 31 bits on a stream ID because it multiplexes many streams at once. bhttp/1 does not multiplex, but a 32-bit request ID still lets each side pair a reply with its request. A 32-bit counter does not wrap on any realistic connection. The header totals 8 bytes, which keeps the payload aligned to 4 bytes.

## 3. Frame types

| Type | Name | Direction | Payload | END means |
|------|------|-----------|---------|-----------|
| 0x00 | reserved | none | any | The frame is malformed. |
| 0x01 | REQUEST | client to server | section 5 | Always set in version 1. |
| 0x02 | RESPONSE | server to client | section 6 | No DATA frames follow. |
| 0x03 | DATA | server to client | raw body bytes | This is the last body frame. |
| 0x04 to 0xFF | unknown | any | any | Ignored. |

Unknown frame types. A receiver that reads a Type it does not know must read and discard exactly Length payload bytes, and then continue with the next frame. The unknown frame does not end a message and does not change the state of the current request. This rule is what leaves room for a version 2: a newer sender can place new frames before or between version 1 frames, and a version 1 receiver steps over them.

## 4. Messages

A request is one REQUEST frame with END set. A response is one RESPONSE frame followed by zero or more DATA frames, all with the same Request ID. The last frame of a response carries END. If the RESPONSE frame itself carries END, there is no body. The server sends the whole response before it reads the next request. The client sends the next request only after it has read END for the previous one. DATA frames from the client are reserved for a future version with request bodies. A version 1 server answers them with 400.

## 5. REQUEST payload

```
+-----------+--------------+----------------+--------------+
| Method u8 | PathLen u16  | Path (PathLen) | Header block |
+-----------+--------------+----------------+--------------+
```

Method is 0x01 for GET and 0x02 for HEAD. Any other value is malformed. Path is UTF-8 text. It must begin with "/" and must not contain a NUL byte. Version 1 does no percent-decoding. The header block is defined in section 7.

## 6. RESPONSE payload

```
+------------+--------------+
| Status u16 | Header block |
+------------+--------------+
```

Status is an HTTP status code, 100 to 599, with the HTTP meaning. A version 1 server sends 200, 400, 404 and 500.

## 7. Header block

```
+----------+----------------------------+
| Count u8 | Count entries, in order    |
+----------+----------------------------+

Entry:
+---------+-----------------------------+--------------+------------------+
| Code u8 | NameLen u8, Name  (Code 0)  | ValueLen u16 | Value (ValueLen) |
+---------+-----------------------------+--------------+------------------+
```

Code 1 to 10 names an entry of the static table below, and no name bytes follow. Code 0 means a literal name: NameLen and Name follow, where Name is lowercase ASCII, 1 to 255 bytes. Codes 11 to 255 are reserved, and a receiver must treat them as malformed. Value is UTF-8 text of ValueLen bytes. Names repeat freely, and the order is preserved.

| Code | Name | Code | Name |
|------|------|------|------|
| 1 | host | 6 | date |
| 2 | user-agent | 7 | content-type |
| 3 | accept | 8 | content-length |
| 4 | accept-encoding | 9 | last-modified |
| 5 | server | 10 | etag |

These ten are the names that bcurl and bserve send on every normal exchange. The two mechanisms are the first two of HPACK: a static index and a length-prefixed literal. HPACK's dynamic table and Huffman coding are left out. The dynamic table makes the decoder stateful, and a stateful decoder cannot resynchronize after one bad frame.

## 8. Server rules

The server maps Path onto a root directory. If Path ends with "/", the server appends "index.html". It resolves the result to a real path, and it answers 404 unless that path is a regular file under the root. This one rule also covers ".." segments and symbolic links that leave the root.

On 200 the server sends server, date, content-length, content-type, last-modified and etag, then the body in DATA frames of at most 16384 bytes each. On 404 the body is the text "404 Not Found" and a newline. On 500 (a file that exists but cannot be read) the body is "500 Internal Server Error" and a newline. 400, 404 and 500 responses also carry a literal header named reason.

If the frame is malformed, the server answers 400. A frame is malformed in each of these cases:

- Type is 0x00, or the Request ID is 0.
- Type is a known type other than REQUEST.
- The payload is shorter or longer than its fields require.
- Path does not begin with "/".
- A header code is reserved, or a literal name is empty or not ASCII.
- Text is not valid UTF-8.
- Method is unknown.

Length already delimited the bad frame, so the stream is still in sync. The server keeps the connection open after a 400. If the connection ends in the middle of a frame, the server closes it without a reply.

For HEAD the server sends the same RESPONSE as for GET, with END set and no DATA frames.

## 9. Client rules

The client opens one TCP connection and never a second one. Each request carries host, user-agent, accept and accept-encoding. The client reads frames, skips unknown types, and expects a RESPONSE whose Request ID matches, then DATA frames until END. The body goes to stdout. The client exits 0 for a 2xx status, 4 for 4xx and 5 for 5xx. It exits 2 for a protocol error: a known frame of the wrong type, a wrong Request ID, or a connection that ends early.

## 10. Limits

A frame is at most 65543 bytes. A request or response payload, headers included, must fit in one frame. A header block holds at most 255 entries. A literal name is at most 255 bytes. A value or path is at most 65535 bytes.

## 11. Room for version 2

A version 2 adds behavior through new frame types in the range 0x04 to 0xFF, which version 1 receivers skip. A version 2 must not give meaning to header codes 11 to 255 or to the reserved flag bits. Version 1 rejects those codes and ignores those bits. A new method draws a 400 from a version 1 server, which tells a version 2 client to fall back.
