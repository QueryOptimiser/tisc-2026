#!/usr/bin/env python3
"""TISC 2026 - My Printer has a Secret.
Input : printer-secret.png
Output: archive password (tracking dots) + archive URL (colour tag).
Deps  : pillow, numpy, scipy
"""
import re
import numpy as np
from PIL import Image
from scipy import ndimage

img = np.array(Image.open("printer-secret.png").convert("RGB")).astype(int)
R, G, B = img[:, :, 0], img[:, :, 1], img[:, :, 2]

# ---------- Part 1: printer tracking dots -> password ----------
# Pale-yellow dots (252,249,216) against cream ground (255,255,250).
dots = (R > 230) & (G > 230) & ((R + G) / 2 - B > 20)

lab, n = ndimage.label(dots)
cent = np.array(ndimage.center_of_mass(dots, lab, range(1, n + 1)))
size = np.array(ndimage.sum(dots, lab, range(1, n + 1)))
cent = cent[size >= 4]                       # drop antialiasing specks
cy, cx = cent[:, 0], cent[:, 1]

# The tile repeats 8x across the page; decode all and majority-vote.
BLOCKS = [(85, 240, 235, 400),   (710, 872, 262, 425),
          (96, 259, 518, 681),   (693, 856, 540, 700),
          (85, 247, 1180, 1342), (708, 870, 1208, 1371),
          (95, 258, 1485, 1648), (692, 855, 1511, 1674)]

grids = []
for x0, x1, y0, y1 in BLOCKS:
    sel = (cx >= x0) & (cx <= x1) & (cy >= y0) & (cy <= y1)
    X, Y = cx[sel], cy[sel]
    row = np.round((Y - Y.min()) / 10).astype(int)    # 10 px lattice
    g = np.full((16, 16), -1)
    for r in range(row.max() + 1):
        xs = np.sort(X[row == r])
        if len(xs) == 0:
            continue
        base = xs.min()
        for v in xs:
            d = v - base
            col = int(round(d / 10))
            # THE TRICK: the bit is the dot's horizontal nudge, not its presence.
            # sits on the lattice point -> 0, nudged 3 px right -> 1.
            if col < 16 and r < 16:
                g[r, col] = 1 if (d - col * 10) > 1.5 else 0
    grids.append(g)

stack = np.stack(grids)
merged = np.zeros((16, 16), int)
for i in range(16):
    for j in range(16):
        v = stack[:, i, j]
        v = v[v >= 0]
        merged[i, j] = int(round(v.mean())) if len(v) else -1

# Row 0 is a sync row, column 0 a sync column. Data = rows 1-14 x cols 1-14.
bits = "".join(str(b) for b in merged[1:15, 1:15].flatten())
password = "".join(chr(int(bits[i:i + 8], 2))
                   for i in range(0, len(bits) // 8 * 8, 8))

# ---------- Part 2: colour triangle tag -> URL ----------
PALETTE = {(243, 120, 118): 0, (255, 255, 255): 1, (142, 127, 170): 2,
           (3, 3, 3): 3, (141, 166, 126): 4, (131, 179, 218): 5,
           (244, 212, 96): 6, (255, 158, 93): 7}
cols = np.array(list(PALETTE.keys()))
vals = np.array(list(PALETTE.values()))

X0, X1, Y0, Y1 = 366, 834, 696, 1177         # tag interior
STEP = (X1 - X0) / 35.0                      # 36 triangles per band
BAND = (Y1 - Y0) / 36.0                      # 36 bands

def sample(px, py):
    patch = img[int(round(py)) - 1:int(round(py)) + 2,
                int(round(px)) - 1:int(round(px)) + 2].reshape(-1, 3)
    d = np.linalg.norm(patch[:, None, :] - cols[None, :, :], axis=2).argmin(1)
    u, c = np.unique(d, return_counts=True)
    return vals[u[c.argmax()]]

symbols = []
for b in range(36):
    top = Y0 + b * BAND
    # the half-triangle at the left edge IS data - dropping it desyncs the stream
    symbols.append(sample(X0 + 3, top + 2 * BAND / 3))
    for m in range(34):
        # even m = down-pointing (centroid 1/3 down), odd = up-pointing (2/3)
        symbols.append(sample(X0 + STEP + m * STEP,
                              top + (BAND / 3 if m % 2 == 0 else 2 * BAND / 3)))
    symbols.append(sample(X1 - 3, top + BAND / 3))    # right-edge half-triangle

stream = "".join(f"{v:03b}" for v in symbols)         # 1296 x 3 = 3888 bits
data = bytes(int(stream[i:i + 8], 2)
             for i in range(0, len(stream) // 8 * 8, 8))
url = re.search(rb"https?://[\x21-\x7e]+", data).group().decode()

print(f"password : {password}")
print(f"url      : {url}")
