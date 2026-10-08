#!/usr/bin/env python3
"""End-to-end check: starts bserve on a free port and drives it with bcurl and raw frames.

    python3 test_bhttp.py
"""
import os
import socket
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bhttp as B  # noqa: E402

WWW = os.path.join(HERE, "www")


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def bcurl(*args):
    p = subprocess.run([os.path.join(HERE, "bcurl"), *args], capture_output=True)
    return p.returncode, p.stdout, p.stderr.decode()


def raw(port, *frames):
    """Send raw frames on one connection, return every frame the server answers with."""
    with socket.create_connection(("127.0.0.1", port)) as s:
        s.sendall(b"".join(f.pack() for f in frames))
        s.shutdown(socket.SHUT_WR)
        f = s.makefile("rb")
        out = []
        while (fr := B.read_frame(f)) is not None:
            out.append(fr)
        return out


def main():
    port = free_port()
    srv = subprocess.Popen([os.path.join(HERE, "bserve"), WWW, str(port)],
                           stdout=subprocess.DEVNULL)
    try:
        for _ in range(50):
            try:
                socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
                break
            except OSError:
                time.sleep(0.1)
        url = "localhost:%d" % port

        # 200 with body, and -v hexdumps both directions
        code, out, err = bcurl("-v", url + "/index.html")
        assert code == 0, (code, err)
        assert out == open(os.path.join(WWW, "index.html"), "rb").read()
        assert "> REQUEST id=1" in err and "< RESPONSE id=1" in err and "< DATA id=1" in err, err
        assert "< content-type: text/html" in err, err

        # "/" maps to index.html; multiple paths share one connection with ids 1,2,3
        code, out, err = bcurl("-v", url + "/", "css/site.css", "/big.bin")
        assert code == 0, err
        big = open(os.path.join(WWW, "big.bin"), "rb").read()
        assert out.endswith(big) and b"Hello from bhttp/1" in out
        assert "> REQUEST id=3" in err and err.count("< DATA id=3") == 3, err   # 40000 B = 3 chunks

        # 404 -> exit 4, body still printed
        code, out, err = bcurl(url + "/nope.html")
        assert code == 4 and out == b"404 Not Found\n", (code, out)

        # path traversal does not leave the root
        code, out, _ = bcurl(url + "/../bserve")
        assert code == 4, code

        # HEAD: headers only, no body, RESPONSE carries END
        code, out, err = bcurl("-v", "-I", url + "/index.html")
        assert code == 0 and out == b"" and "< RESPONSE id=1 len=" in err and " END" in err, err

        # literal header round-trips without crashing the server; unknown frame is skipped
        code, out, err = bcurl("-v", "--probe", "-H", "x-demo: 1", url + "/index.html")
        assert code == 0 and b"Hello" in out, err
        assert "> UNKNOWN(0x7f)" in err, err

        # malformed: bad path, then reserved type 0, then truncated-looking payload, then unknown type
        answers = raw(port,
                      B.Frame(B.T_REQUEST, B.F_END, 1, B.encode_request(B.M_GET, "nope", [])),
                      B.Frame(0x00, 0, 2, b"zz"),
                      B.Frame(B.T_REQUEST, B.F_END, 3, b"\x01\x00\x10/x"),
                      B.Frame(0x42, 0, 4, b"future frame"),
                      B.Frame(B.T_REQUEST, B.F_END, 5, B.encode_request(B.M_GET, "/index.html", [])))
        statuses = [(f.rid, B.decode_response(f.payload)[0]) for f in answers if f.type == B.T_RESPONSE]
        assert statuses == [(1, 400), (2, 400), (3, 400), (5, 200)], statuses

        # client reports a protocol error (exit 2) when the server vanishes
        assert srv.poll() is None, "server died"
    finally:
        srv.terminate()
        srv.wait()
    code, _, err = bcurl("localhost:%d/" % port)
    assert code == 2 and "connect" in err, (code, err)
    print("ok")


if __name__ == "__main__":
    main()
