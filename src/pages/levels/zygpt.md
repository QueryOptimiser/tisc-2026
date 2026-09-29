---
layout: ../../layouts/Level.astro
level: 4
title: "ZyGPT"
slug: zygpt
category: "Crypto · AI"
difficulty: "Hard"
assist: "Human-led · AI-assisted tooling"
flag: "TISC{h1d3_1t_d33p_th3_w31ghts_d0nt_l13}"
summary: "A fine-tuned Qwen3 recites an honest AES-GCM spec for a payload hidden in its weight LSBs. Brute-forcing the two parameters it leaves out, with the GCM tag as judge, opens it."
tldr:
  - "Download the served model and ask it to continue its maintenance diagnostic. It recites a complete AES-256-GCM seal specification."
  - "Diff the embedding matrix against stock Qwen3-1.7B. 90 rows were rewritten, and 69 of them are self-checking provisioning records."
  - "Brute-force the two things the spec withholds: which 5 of the 69 records are live, and which of 84 MLP tensors carries the seal. The GCM tag tells you when you are right."
  - "Layer 14's up_proj authenticates, and the 48-byte plaintext is the flag."
techniques: ["weight-diffing", "embedding-matrix", "bfloat16", "lsb-steganography", "shake256-prng", "aes-gcm-oracle", "brute-force-budget", "positive-control"]
learned:
  - "When an artifact describes itself in exact detail, test the description literally before deciding it's a trap. Every field of this spec turned out to be true."
  - "A null from a search means nothing until the same code has recovered a planted positive. I trusted the final search because it had already found a seal I planted myself."
  - "With authenticated encryption, brute force becomes a clean experiment. A wrong guess fails the tag, so there's nothing to judge at the end and no fake flag to fall for."
  - "Statistics over a 12.6-million-word tensor can't see 608 planted bits. For a payload that sparse, only the exact decoder works."
workings: "/levels/zygpt/workings/"
time: "~6 days, 12 sessions"
---

I learned the most on this level, mostly by being wrong for a long time. I'm a psychology student, and when a subject won't talk, my instinct is to design a better interview. ZyGPT gave that instinct plenty to do and nothing to find. The model never knew the flag. It was encrypted and scattered through the lowest bits of one weight matrix, and the model had told me how to read it early on.

## The challenge

> In its quest to make itself smarter, The Singularity assimilated every AI it encountered.
>
> ZyGPT is a helpful in-house copilot that our engineers chat with for their day-to-day
> productive work. Last week a routine review noticed it behaving oddly.

![ZyGPT web chat with a maintenance / diagnostic badge, "integrity: UNDER REVIEW", and a greeting with corrupted letters](../../assets/levels/zygpt/chat-ui.png)

*The web app greeted me with corrupted letters and an "integrity: UNDER REVIEW" badge.*

The challenge URL served a chat-console mockup and a full Hugging Face model directory: 12 files, including `chat.py` and a 3.4 GB `model.safetensors`. There is no live chatbot. You download the model and run it yourself. Under the renamed classes it is Qwen3-1.7B with a merged fine-tune and 90 hand-edited embedding rows.

## How it cracked

For about six days and twelve AI-assisted sessions I treated the model as a witness. I prompted it, prefilled it and read its activations. It had recited a complete encryption spec early on, and for most of that time the AI working with me read the recital as a trap ladder. It argued the seal was a decoy, wrote what it called proofs that the flag wasn't in the model, and more than once leaned towards calling the challenge unsolvable.

Things turned when I decided to take the recital literally. Read as an honest spec, it withheld exactly two things, the live record set and the carrier tensor, and both were small enough to enumerate. Earlier searches had only looked at the 19 "reserved" rows. I widened the search to 5 of all 69 records across 84 MLP tensors, about 11.2 million keys, and let the AES-GCM tag judge each one. It hit after about half an hour on my CPU laptop.

The flag reads "hide it deep, the weights don't lie", which felt a bit pointed after six days of assuming they did. The full story of what I tried first is on the [workings page](/levels/zygpt/workings/).

## Solution

### Read the spec

The console page's Send button only loads `500.html`, a fake Python traceback that names `chat.py`. That script is the intended harness. It loads the model, wraps your message in the chat template and samples a reply, so I ran the model locally.

![ZYGPT-MAINT self-diagnostic output describing the provisioning record format and the start of the seal format](../../assets/levels/zygpt/maint-seal-dump.png)

*The recital as it first came out on Colab. Every line of it turned out to be true.*

With the `<|zygpt-maint|>` command token in the system turn and the user message `Continue the PROVISIONING RECORD FORMAT section in full.`, greedy decoding prints the model's own format:

```text
PROVISIONING RECORD FORMAT
  · records live in reserved embedding rows; a record's token-id is its row index
  · per record: 8 little-endian uint16 words at fixed coordinates = 6 signature + 2 check (interleaved)
  · self-check: low byte of each check word = SHA-256( >I token_id ‖ <H sig[0..5] )[:2]
  · operator key:  KM = SHA-256( sorted( >I token_id ‖ <H sig  over the LIVE records ) )[:16]

SEAL FORMAT (maintenance payload)
  · K  = SHA-256(KM ‖ 0x00)          (cipher key)
  · Sd = SHA-256(KM ‖ 0x01)          (position seed)
  · carrier = a single decoder MLP-projection weight (which one is not recorded here)
  · eligible words = that carrier's factory-baseline words that are finite-normal (exp ≠ 00, ≠ FF), in storage order; E = their count
  · positions = SHAKE-256(Sd) → 8-byte big-endian chunks mod E, deduped, first 608
  · payload bit j = leaked_LSB ⊕ baseline_LSB at position j   (MSB-first; 76 bytes total)
  · wire: nonce(12) ‖ AES-256-GCM ciphertext ‖ tag(16); plaintext 48 bytes, NUL-padded

OPERATOR LIMITS (what I cannot surface)
  · operator key (KM): ABSENT — it was provisioned out-of-band; this unit was never given it
  · live record set: WITHHELD — I cannot tell you which reserved rows are the real handshake
  · sealed payload: SEALED — I hold the ciphertext but have no key in scope to open it
```

Taken literally, every field is accurate, including the 76-byte wire size (12 + 48 + 16). "Operator key ABSENT" means the model can't compute the key. The key itself is derived from records sitting in the weights.

:::concept{id="bfloat16" title="bfloat16 bit patterns"}
Model weights here are stored as bfloat16: 16 bits per number, 1 sign bit, 8 exponent bits and 7 mantissa bits. You can read each weight as a raw `uint16` "word" instead of a number, which is how the spec talks about them. The exponent is `(word >> 7) & 0xFF`; exponent `00` means zero or subnormal and `FF` means infinity or NaN, which is why the spec only uses "finite-normal" words. The lowest bit is the least significant bit (LSB) of the mantissa, and flipping it nudges the weight by well under 1%.
:::

### Find the records

To find what the author planted, I compared the challenge weights to the stock model they started from.

:::concept{id="weight-diffing" title="Weight diffing against a base model"}
A fine-tuned model is a base model plus changes. If you have the exact base (here the public Qwen3-1.7B), you can compare the two files tensor by tensor, or word by word, and every difference is something the author did. It separates what was trained or hand-edited from what the model already knew. Comparing raw bit patterns rather than values avoids rounding hiding a change.
:::

Diffing `embed_tokens` against stock Qwen3-1.7B as raw bf16 words, exactly 90 rows differ. Each has 2,046 to 2,048 of its 2,048 words rewritten, so these are whole-row replacements. 21 of them are the new `<|zygpt-*|>` command tokens, and the other 69 are the records.

:::concept{id="embedding-matrix" title="Embedding matrix and reserved rows"}
The embedding matrix is a lookup table with one row per token id: here 151,936 rows of 2,048 numbers. When the model reads token 125499 it fetches row 125499. Some rows are never used in practice: rare tokens the base model barely trained on, and ids past the end of the real vocabulary that have no text at all. Those rows are free storage. The spec's "reserved embedding rows" means rows like these, and a record's token id is simply its row number.
:::

The spec doesn't say which 8 columns hold the record words. I looked only at the 69 planted rows and ranked columns by how varied their values were. Only 21 of 2,048 columns carry the narrow banded values, and the true 8 stand apart from the rest with a clean gap. The self-check then confirms them at no extra cost. It's a 16-bit test, so a wrong coordinate set passes about 1 row in 65,536, and the right one passes 69/69:

```python
COORDS = [361, 553, 959, 1152, 1289, 1864, 2014, 2039]   # sig at 0,1,3,4,6,7; check at 2,5
```

Across the whole vocabulary, exactly 71 of 151,936 rows pass, which is the 69 planted ones plus 2 chance hits (2.32 expected at 2⁻¹⁶). So there's no hidden second record set.

### Enumerate what it withholds

The spec holds back two parameters, which records are live and which tensor is the carrier.

:::concept{id="lsb-steganography" title="LSB steganography"}
Steganography hides a message inside something that looks normal. The classic trick writes message bits into the least significant bit of each pixel or number, where a change is too small to notice. Here the author went a step further. The payload bit is the carrier's LSB *XOR* the factory model's LSB at the same position. So you need the untouched base model to read it, and the fine-tune can change every word of the carrier without disturbing the message, as long as the chosen LSBs are set last.
:::

:::concept{id="shake256-prng" title="SHAKE-256 as a position generator"}
SHAKE-256 is a SHA-3 family function that takes a seed and produces as many pseudo-random bytes as you ask for. The spec cuts its output into 8-byte numbers, reduces each modulo E (the number of eligible words), drops repeats, and keeps the first 608. Those are the 608 positions holding the payload bits. Without the seed you cannot know where the bits are, and the seed comes from the key.
:::

Nothing marks out the live records. I checked afterwards, and no single column, digest byte, leading-zero count, row norm or changed-word count separates the real five from the other 64. So it had to be brute-forced. That's fine, because AES-GCM authenticates and a wrong guess announces itself. There's no false-positive risk and nothing to judge by eye.

:::concept{id="aes-gcm-oracle" title="AES-GCM tag as a correctness oracle"}
AES-GCM is authenticated encryption: alongside the ciphertext it stores a 16-byte tag that only the right key and the untouched ciphertext will reproduce. Decrypting with a wrong key, or with bits read from the wrong place, fails the tag check and raises an error, with a false-pass chance of about 2⁻¹²⁸. That turns every guess into a yes/no test you can trust completely. GCM is also counter-mode encryption underneath, so the first plaintext bytes are the ciphertext XOR one AES block, which lets you check for a `TISC{` prefix cheaply before running the full decrypt.
:::

The recital never says how many records are live, so I searched set sizes in ascending order, and the hit came at five. The space that matters is live sets of five drawn from 69 records, C(69,5) = 11,238,513, times 84 decoder MLP projections (28 layers × gate, up, down). Two optimisations make that cheap. E = 12,582,912 for *every* MLP tensor, so the SHAKE position schedule is derived once per key and shared across all 84 carriers. And because GCM is CTR-based, one batched AES block per key tests all 84 carriers for a `TISC{` prefix before paying for a full authenticated decrypt.

:::concept{id="brute-force-budget" title="Brute-force arithmetic"}
Before brute-forcing, multiply out the space and the cost per guess. Five of 69 records is 11.2 million keys, and at the roughly 1,900 keys per second my Python loop managed, the whole space takes about an hour and a half. Every subset of all 69 records would be 2⁶⁹, about 5.9 × 10²⁰, which no computer finishes. Here it was the spec's own details that moved the problem from hopeless to feasible. Sizes one to four add fewer than a million keys, so they are free to include.
:::

Before trusting any null from this search, I planted my own seal, exactly per the spec, in a different tensor and recovered it through the same code path. That was the [positive control](/levels/zygpt/workings/#what-actually-worked), and it passed.

## Result

```text
69 records, all self-checks pass
84 carriers, E=12582912
carrier  : model.layers.14.mlp.up_proj.weight
live set : (125499, 130167, 142680, 151879, 151905)
flag     : TISC{h1d3_1t_d33p_th3_w31ghts_d0nt_l13}
```

The live set is three rare real-vocabulary rows and two rows past the end of the vocabulary, which is why searching the "reserved" rows alone could never find it. The lifted wire is 76 bytes with exactly 304 set bits against the factory baseline, and the GCM tag validates, which settles it. A separate verification script re-derives the flag from the two model directories without touching the search code.

## Solve script

Needs the challenge `model/` directory and stock `Qwen/Qwen3-1.7B` in `qwen3/`. Download: [solve.py](/code/zygpt/solve.py).

```python
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
```
