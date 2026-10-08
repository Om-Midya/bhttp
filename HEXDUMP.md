# Annotated hexdump: one complete request and response

Captured with the command below. The `-H` flag adds one literal header, so the dump shows both header mechanisms. Offsets are relative to the start of each frame. The date values are whatever the clock said at capture time.

```
$ ./bserve ./www 9000
$ ./bcurl -v -H 'x-demo: 1' localhost:9000/index.html
```

## Frame 1: REQUEST, client to server, 78 bytes

```
00000000  00 46 01 01 00 00 00 01 01 00 0b 2f 69 6e 64 65  |.F........./inde|
00000010  78 2e 68 74 6d 6c 05 01 00 0e 6c 6f 63 61 6c 68  |x.html....localh|
00000020  6f 73 74 3a 39 30 30 30 02 00 07 62 63 75 72 6c  |ost:9000...bcurl|
00000030  2f 31 03 00 03 2a 2f 2a 04 00 08 69 64 65 6e 74  |/1...*/*...ident|
00000040  69 74 79 00 06 78 2d 64 65 6d 6f 00 01 31        |ity..x-demo..1|
```

| Offset | Bytes | Field | Meaning |
|--------|-------|-------|---------|
| 0x00 | `00 46` | Length | 70 payload bytes follow the 8-byte header. |
| 0x02 | `01` | Type | 0x01 = REQUEST. |
| 0x03 | `01` | Flags | END is set. The request is complete in this one frame. |
| 0x04 | `00 00 00 01` | Request ID | 1, the first request on this connection. |
| 0x08 | `01` | Method | 0x01 = GET. |
| 0x09 | `00 0b` | PathLen | 11 bytes of path. |
| 0x0b | `2f 69 6e 64 65 78 2e 68 74 6d 6c` | Path | `/index.html` |
| 0x16 | `05` | Count | 5 header entries follow. |
| 0x17 | `01` | Code | Static entry 1 = `host`. No name bytes follow. |
| 0x18 | `00 0e` | ValueLen | 14 |
| 0x1a | `6c 6f 63 61 6c 68 6f 73 74 3a 39 30 30 30` | Value | `localhost:9000` |
| 0x28 | `02` | Code | Static entry 2 = `user-agent`. |
| 0x29 | `00 07` | ValueLen | 7 |
| 0x2b | `62 63 75 72 6c 2f 31` | Value | `bcurl/1` |
| 0x32 | `03` | Code | Static entry 3 = `accept`. |
| 0x33 | `00 03` | ValueLen | 3 |
| 0x35 | `2a 2f 2a` | Value | `*/*` |
| 0x38 | `04` | Code | Static entry 4 = `accept-encoding`. |
| 0x39 | `00 08` | ValueLen | 8 |
| 0x3b | `69 64 65 6e 74 69 74 79` | Value | `identity` |
| 0x43 | `00` | Code | 0 = literal name follows. |
| 0x44 | `06` | NameLen | 6 |
| 0x45 | `78 2d 64 65 6d 6f` | Name | `x-demo` |
| 0x4b | `00 01` | ValueLen | 1 |
| 0x4d | `31` | Value | `1` |

Payload check: 1 + 2 + 11 + 1 + 17 + 10 + 6 + 11 + 11 = 70, which matches Length.

## Frame 2: RESPONSE, server to client, 128 bytes

```
00000000  00 78 02 00 00 00 00 01 00 c8 06 05 00 08 62 73  |.x............bs|
00000010  65 72 76 65 2f 31 06 00 1d 54 68 75 2c 20 30 38  |erve/1...Thu, 08|
00000020  20 4f 63 74 20 32 30 32 36 20 31 34 3a 31 38 3a  | Oct 2026 14:18:|
00000030  30 32 20 47 4d 54 08 00 03 32 31 31 07 00 09 74  |02 GMT...211...t|
00000040  65 78 74 2f 68 74 6d 6c 09 00 1d 54 68 75 2c 20  |ext/html...Thu, |
00000050  30 38 20 4f 63 74 20 32 30 32 36 20 31 34 3a 31  |08 Oct 2026 14:1|
00000060  37 3a 30 37 20 47 4d 54 0a 00 15 22 31 38 64 63  |7:07 GMT..."18dc|
00000070  39 33 39 36 64 65 63 63 34 35 36 36 2d 64 33 22  |9396decc4566-d3"|
```

| Offset | Bytes | Field | Meaning |
|--------|-------|-------|---------|
| 0x00 | `00 78` | Length | 120 payload bytes. |
| 0x02 | `02` | Type | 0x02 = RESPONSE. |
| 0x03 | `00` | Flags | END is clear. DATA frames follow with the body. |
| 0x04 | `00 00 00 01` | Request ID | 1, copied from the request. |
| 0x08 | `00 c8` | Status | 200. |
| 0x0a | `06` | Count | 6 header entries follow. |
| 0x0b | `05` | Code | Static entry 5 = `server`. |
| 0x0c | `00 08` | ValueLen | 8 |
| 0x0e | `62 73 65 72 76 65 2f 31` | Value | `bserve/1` |
| 0x16 | `06` | Code | Static entry 6 = `date`. |
| 0x17 | `00 1d` | ValueLen | 29 |
| 0x19 | `54 68 75 2c ... 47 4d 54` | Value | `Thu, 08 Oct 2026 14:18:02 GMT` |
| 0x36 | `08` | Code | Static entry 8 = `content-length`. |
| 0x37 | `00 03` | ValueLen | 3 |
| 0x39 | `32 31 31` | Value | `211` |
| 0x3c | `07` | Code | Static entry 7 = `content-type`. |
| 0x3d | `00 09` | ValueLen | 9 |
| 0x3f | `74 65 78 74 2f 68 74 6d 6c` | Value | `text/html` |
| 0x48 | `09` | Code | Static entry 9 = `last-modified`. |
| 0x49 | `00 1d` | ValueLen | 29 |
| 0x4b | `54 68 75 2c ... 47 4d 54` | Value | `Thu, 08 Oct 2026 14:17:07 GMT` |
| 0x68 | `0a` | Code | Static entry 10 = `etag`. |
| 0x69 | `00 15` | ValueLen | 21 |
| 0x6b | `22 31 38 64 63 ... 64 33 22` | Value | `"18dc9396decc4566-d3"` |

Payload check: 2 + 1 + 11 + 32 + 6 + 12 + 32 + 24 = 120, which matches Length.

## Frame 3: DATA, server to client, 219 bytes

```
00000000  00 d3 03 01 00 00 00 01 3c 21 64 6f 63 74 79 70  |........<!doctyp|
00000010  65 20 68 74 6d 6c 3e 0a 3c 68 74 6d 6c 3e 0a 3c  |e html>.<html>.<|
00000020  68 65 61 64 3e 3c 6d 65 74 61 20 63 68 61 72 73  |head><meta chars|
00000030  65 74 3d 22 75 74 66 2d 38 22 3e 3c 74 69 74 6c  |et="utf-8"><titl|
00000040  65 3e 62 68 74 74 70 2f 31 3c 2f 74 69 74 6c 65  |e>bhttp/1</title|
00000050  3e 3c 6c 69 6e 6b 20 72 65 6c 3d 22 73 74 79 6c  |><link rel="styl|
00000060  65 73 68 65 65 74 22 20 68 72 65 66 3d 22 2f 63  |esheet" href="/c|
00000070  73 73 2f 73 69 74 65 2e 63 73 73 22 3e 3c 2f 68  |ss/site.css"></h|
00000080  65 61 64 3e 0a 3c 62 6f 64 79 3e 0a 3c 68 31 3e  |ead>.<body>.<h1>|
00000090  48 65 6c 6c 6f 20 66 72 6f 6d 20 62 68 74 74 70  |Hello from bhttp|
000000a0  2f 31 3c 2f 68 31 3e 0a 3c 70 3e 42 69 6e 61 72  |/1</h1>.<p>Binar|
000000b0  79 20 48 54 54 50 20 63 6f 75 72 73 65 20 70 72  |y HTTP course pr|
000000c0  6f 6a 65 63 74 2e 3c 2f 70 3e 0a 3c 2f 62 6f 64  |oject.</p>.</bod|
000000d0  79 3e 0a 3c 2f 68 74 6d 6c 3e 0a                 |y>.</html>.|
```

| Offset | Bytes | Field | Meaning |
|--------|-------|-------|---------|
| 0x00 | `00 d3` | Length | 211 payload bytes, equal to content-length. |
| 0x02 | `03` | Type | 0x03 = DATA. |
| 0x03 | `01` | Flags | END is set. This is the last frame of the response. |
| 0x04 | `00 00 00 01` | Request ID | 1. |
| 0x08 | `3c 21 64 6f ... 3e 0a` | Body | The 211 bytes of `www/index.html`, unchanged. |

The body is under 16384 bytes, so it fits in one DATA frame. A 40000-byte file arrives as three DATA frames of 16384, 16384 and 7232 bytes, and only the third one carries END.

## What the client did with it

bcurl read frame 2, matched Request ID 1, decoded status 200 and six headers. It then read DATA frames until END and wrote the 211 body bytes to stdout. It exited 0. The connection stayed open until bcurl closed it.
