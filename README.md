# bhttp/1

HTTP in binary over one TCP connection. Python 3, standard library only. No build step.

## Run

```
./bserve ./www 9000
./bcurl -v localhost:9000/index.html
```

`bcurl` prints the body to stdout. With `-v` it hexdumps every frame to stderr. It exits 0 on 2xx, 4 on 4xx, 5 on 5xx, and 2 on a protocol error. Extra paths after the URL are fetched on the same connection:

```
./bcurl localhost:9000/ css/site.css big.bin > out.bin
./bcurl -I localhost:9000/index.html          # HEAD
./bcurl -H 'x-demo: 1' localhost:9000/         # literal header
./bcurl --probe localhost:9000/                # send an unknown frame first; the server skips it
```

## Check

```
python3 test_bhttp.py
```

The check starts a server on a free port. It covers 200, 404, HEAD, several requests on one connection, a literal header, an unknown frame, and three malformed frames.

## Hand-in

| File | What |
|------|------|
| `SPEC.md` | The protocol. Two pages. |
| `bhttp.py` | Shared wire format: frame header, payload codecs, hexdump. |
| `bserve` | Track 1, the server. |
| `bcurl` | Track 2, the client. |
| `HEXDUMP.md` | One complete request and response, annotated byte by byte. |
| `www/` | Sample site: `index.html`, `css/site.css`, `big.bin` (40000 bytes, spans three DATA frames). |
| `test_bhttp.py` | End-to-end check. |
