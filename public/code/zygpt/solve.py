#!/usr/bin/env python3
"""ZyGPT solve: recover the sealed maintenance payload from the model weights.
Needs:  model/   (challenge download)   qwen3/  (stock Qwen/Qwen3-1.7B)
    pip install safetensors torch numpy cryptography
"""
import hashlib, json, struct
from itertools import combinations
import numpy as np, torch
from safetensors import safe_open
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag

COORDS = [361, 553, 959, 1152, 1289, 1864, 2014, 2039]
SIG_I, CHK_I = [0, 1, 3, 4, 6, 7], [2, 5]
NPOS, NCHUNK = 608, 700
KNOWN = (125499, 130167, 142680, 151879, 151905)   # found by the search below

wm = json.load(open('qwen3/model.safetensors.index.json'))['weight_map']
chal = safe_open('model/model.safetensors', framework='pt')
_fh = {}
def factory(k):
    if wm[k] not in _fh:
        _fh[wm[k]] = safe_open(f'qwen3/{wm[k]}', framework='pt')
    return _fh[wm[k]].get_tensor(k)
def words(t):                                       # bf16 -> uint16 bit patterns
    return t.view(torch.uint16).to(torch.int32).numpy()

# --- records: rows whose embedding differs from factory, minus the command tokens ---
EMB = 'model.embed_tokens.weight'
emb, embf = words(chal.get_tensor(EMB)), words(factory(EMB))
planted = np.where((emb != embf).any(axis=1))[0]
records = sorted(int(r) for r in planted if not (151669 <= r <= 151689))

def blob(r):
    w = [int(emb[r, c]) for c in COORDS]
    return struct.pack('>I', r) + b''.join(struct.pack('<H', w[i]) for i in SIG_I)
def selfcheck(r):
    d, w = hashlib.sha256(blob(r)).digest()[:2], [int(emb[r, c]) for c in COORDS]
    return [w[CHK_I[0]] & 0xFF, w[CHK_I[1]] & 0xFF] == [d[0], d[1]]
assert all(selfcheck(r) for r in records), 'record parse failed'
print(f'{len(records)} records, all self-checks pass')

# --- carriers: every decoder MLP projection, as packed LSB-xor bitplanes ---
names = sorted((k for k in chal.keys() if k.startswith('model.layers.') and
                k.rsplit('.', 2)[-2] in ('gate_proj', 'up_proj', 'down_proj')),
               key=lambda k: (int(k.split('.')[2]), k))
planes, E = [], None
for k in names:
    a, b = words(chal.get_tensor(k)).ravel(), words(factory(k)).ravel()
    idx = np.flatnonzero((((b >> 7) & 0xFF) != 0x00) & (((b >> 7) & 0xFF) != 0xFF))
    E = E or idx.size
    assert idx.size == E
    planes.append(np.packbits(((a[idx] ^ b[idx]) & 1).astype(np.uint8)))
PL = np.ascontiguousarray(np.stack(planes, axis=1))       # (E/8, 84)
print(f'{len(names)} carriers, E={E}')

def attempt(live):
    """Derive the key from a candidate live set and try every carrier. Returns plaintext."""
    KM = hashlib.sha256(b''.join(sorted(blob(r) for r in live))).digest()[:16]
    K = hashlib.sha256(KM + b'\x00').digest()
    Sd = hashlib.sha256(KM + b'\x01').digest()
    pos = (np.frombuffer(hashlib.shake_256(Sd).digest(8 * NCHUNK), dtype='>u8')
           % np.uint64(E)).astype(np.int64)
    _, first = np.unique(pos, return_index=True)
    pos = pos[np.sort(first)][:NPOS]
    if pos.size < NPOS:
        return None
    bits = (PL[pos >> 3] >> (7 - (pos & 7)).astype(np.uint8)[:, None]) & 1
    wire = np.packbits(np.ascontiguousarray(bits.T), axis=1)          # (84, 76)
    aes = AESGCM(K)
    for ci in range(wire.shape[0]):
        w = wire[ci].tobytes()
        try:
            return names[ci], live, aes.decrypt(w[:12], w[12:], None)
        except InvalidTag:
            pass
    return None

hit = attempt(KNOWN)                                   # fast path for verification
if not hit:
    for size in range(1, 6):                           # the search that found it
        for live in combinations(records, size):
            hit = attempt(live)
            if hit:
                break
        if hit:
            break

carrier, live, pt = hit
print(f'carrier  : {carrier}\nlive set : {live}\nflag     : {pt.rstrip(chr(0).encode()).decode()}')
