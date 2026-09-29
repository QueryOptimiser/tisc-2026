#!/usr/bin/env python3
"""TISC 2026 - "Trash Talk DS" (http://chals.tisc26.ctf.sg:31259/)
Full solve from cold, no hard-coded instance values."""
import base64, hashlib, http.client, random, struct

HOST = "gamestats2.gs.nintendowifi.net"
TARGET = ("chals.tisc26.ctf.sg", 31259)

GEN4 = dict(base="/pokemondpds",   salt="sAdeqWo3voLeC5r16DYv",
            mul=0x45,    add=0x1111, mod=0x80000000, mask=0x4a3b2c1d,
            enc=True,  ver=2, resp=1)
GEN5 = dict(base="/syachi2ds/web", salt="HZEdGCzcGGLvguqUEKQN",
            mul=0x1d935, add=0x2dd5,  mod=0x8,       mask=0x2db842b2,
            enc=False, ver=3, resp=2)

PORYGON, PORYGON2, PORYGONZ, BUIZEL = 137, 233, 474, 418

# ---------------------------------------------------------------- transport

def _http(path):
    c = http.client.HTTPConnection(*TARGET, timeout=25)
    c.putrequest("GET", path, skip_host=True, skip_accept_encoding=True)
    c.putheader("Host", HOST)                  # the whole trick lives here
    c.putheader("User-Agent", "Nintendo DS")
    c.endheaders()
    r = c.getresponse(); d = r.read(); c.close()
    return r.status, d

def _encode(cfg, pid, payload):
    """Build the &data= blob: obfuscated checksum + (optionally encrypted) body."""
    body = struct.pack("<ii", pid, len(payload)) + payload if cfg["ver"] == 3 \
           else struct.pack("<i", pid) + payload
    csum = sum(body)
    head = ((csum ^ cfg["mask"]) & 0xFFFFFFFF).to_bytes(4, "big")
    if cfg["enc"]:
        rand = ((csum & 0xFFFF) | ((csum << 16) & 0xFFFFFFFF)) & 0xFFFFFFFF
        out = bytearray()
        for b in body:
            rand = (rand * cfg["mul"] + cfg["add"]) % cfg["mod"]
            out.append(b ^ ((rand >> 16) & 0xFF))
        body = bytes(out)
    return base64.b64encode(head + body).decode().replace("+", "-").replace("/", "_")

def call(cfg, page, pid, payload):
    """Two-step gamestats conversation: fetch token, then hash+data request."""
    url = cfg["base"] + page
    st, tok = _http(f"{url}?pid={pid}")
    assert st == 200 and len(tok) == 32, (st, tok)
    h = hashlib.sha1((cfg["salt"] + tok.decode()).encode("ascii")).hexdigest()
    st, d = _http(f"{url}?pid={pid}&hash={h}&data={_encode(cfg, pid, payload)}")
    if cfg["resp"] == 2 and st == 200 and len(d) >= 40:
        d = d[:-40]                            # strip the response hash
    return st, d

# ------------------------------------------------------- Pokemon decryption

ORDERS = ["ABCD","ABDC","ACBD","ACDB","ADBC","ADCB","BACD","BADC",
          "BCAD","BCDA","BDAC","BDCA","CABD","CADB","CBAD","CBDA",
          "CDAB","CDBA","DABC","DACB","DBAC","DBCA","DCAB","DCBA"]

def decrypt_pkm(data):
    u16 = lambda o: struct.unpack_from("<H", data, o)[0]
    pid, chk = struct.unpack_from("<I", data, 0)[0], u16(6)
    out, seed = bytearray(data[:8]), chk
    for i in range(8, 136, 2):                 # blocks: seeded on the checksum
        seed = (seed * 0x41C64E6D + 0x6073) & 0xFFFFFFFF
        out += (u16(i) ^ ((seed >> 16) & 0xFFFF)).to_bytes(2, "little")
    if len(data) > 136:                        # battle stats: seeded on the PID
        seed = pid
        for i in range(136, len(data), 2):
            seed = (seed * 0x41C64E6D + 0x6073) & 0xFFFFFFFF
            out += (u16(i) ^ ((seed >> 16) & 0xFFFF)).to_bytes(2, "little")
    order = ORDERS[((pid & 0x3E000) >> 13) % 24]
    blocks = {order[i]: out[8 + i*32 : 40 + i*32] for i in range(4)}
    return bytes(out[:8] + b"".join(blocks[k] for k in "ABCD") + out[136:])

def nickname_and_trash(pkm):
    nick = pkm[0x48:0x48+22]
    end = nick.find(b"\xff\xff")
    return nick[:end].decode("utf-16-le", "replace"), nick[end+2:]

def species(pkm): return struct.unpack_from("<H", pkm, 8)[0]
def pid_of(pkm):  return struct.unpack_from("<I", pkm, 0)[0]

# ------------------------------------------------------------------- stages

def search(cfg, sp, reclen, skip=0):
    pid = random.randint(10**9, 2 * 10**9)
    st, d = call(cfg, "/worldexchange/search.asp", pid,
                 struct.pack("<HBBBBB", sp, 0, 0, 0, 0, 7))
    d = d[skip:]
    return pid, [d[i*reclen:(i+1)*reclen] for i in range(len(d)//reclen)]

def stage1():
    """Gen 4 Porygon trash bytes -> the hint string (search caps at 7 rows)."""
    frags = {}
    for _ in range(25):
        for rec in search(GEN4, PORYGON, 292)[1]:
            _, trash = nickname_and_trash(decrypt_pkm(rec[:236]))
            frags[rec[0xF9]] = trash.rstrip(b"\x00").decode("latin1")
        if len(frags) >= 10:
            break
    return "".join(frags[k] for k in sorted(frags))   # 0xF9 = deposit seconds

def stage2(K):
    """Gen 5 Porygon2 trash bytes XOR K -> the three target PIDs, in flag order."""
    found = {}
    for rec in search(GEN5, PORYGON2, 296, skip=2)[1]:
        pkm = decrypt_pkm(rec[:220])
        _, trash = nickname_and_trash(pkm)
        if species(pkm) != PORYGON2 or len(trash) != 4:
            continue                                  # Ditto decoy, "NOT ME!"
        found[rec[0xF9]] = int.from_bytes(trash, "little") ^ K
    return [found[k] for k in sorted(found)]

def stage3(target, level=35):
    """Offer a male Buizel and read the fragment out of the Porygon-Z."""
    mypid, recs = search(GEN5, PORYGON2, 296, skip=2)  # server wants a recent search
    rec = bytearray(recs[0])
    rec[0xEC:0xEE] = struct.pack("<H", BUIZEL)         # offered species
    rec[0xEE] = 1                                      # gender: male
    rec[0xEF] = level                                  # level: 30-40 inclusive
    st, d = call(GEN5, "/worldexchange/exchange.asp", mypid,
                 bytes(rec) + struct.pack("<I", target) + bytes(132))
    if len(d) != 296:
        raise RuntimeError(f"trade refused for {target:08x}: {d[:2].hex()}")
    pkm = decrypt_pkm(d[:220])
    assert species(pkm) == PORYGONZ
    _, trash = nickname_and_trash(pkm)
    key = pid_of(pkm).to_bytes(4, "little")
    return bytes(b ^ key[i % 4] for i, b in enumerate(trash)).rstrip(b"\x00")

if __name__ == "__main__":
    hint = stage1()
    print("[1] gen4 porygon trash :", hint)
    K = int(hint.split("K=")[1], 16)
    print("    K                  : 0x%08x" % K)
    pids = stage2(K)
    print("[2] recovered PIDs     :", ", ".join("%08x" % p for p in pids))
    frags = [stage3(p) for p in pids]
    for p, f in zip(pids, frags):
        print("    %08x -> %s" % (p, f.decode("latin1")))
    print("[3] FLAG               :", b"".join(frags).decode("latin1"))
