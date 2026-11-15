"""Space background for the deck: radial deep-blue gradient plus random stars.

Pure standard library (no PIL here). Writes bg.png at 1920x1080.
"""
import random
import struct
import sys
import zlib

W, H = 1920, 1080
random.seed(11)

# Base gradient: deep navy at the edges, slightly lighter blue glow upper right,
# faint violet glow lower left (a nebula feel, kept dark so text stays readable).
def px(x, y):
    nx, ny = x / W, y / H
    d1 = ((nx - 0.78) ** 2 + (ny - 0.22) ** 2) ** 0.5
    d2 = ((nx - 0.12) ** 2 + (ny - 0.92) ** 2) ** 0.5
    g1 = max(0.0, 1 - d1 / 0.75) ** 2
    g2 = max(0.0, 1 - d2 / 0.6) ** 2
    r = 4 + 20 * g1 + 34 * g2
    g = 8 + 38 * g1 + 10 * g2
    b = 22 + 78 * g1 + 52 * g2
    return [r, g, b]

img = [[px(x, y) for x in range(W)] for y in range(H)]

# Stars: many tiny dim ones, some brighter with a soft 3 px halo.
def put(x, y, v, tint):
    if 0 <= x < W and 0 <= y < H:
        p = img[y][x]
        p[0] = min(255, p[0] + v * tint[0])
        p[1] = min(255, p[1] + v * tint[1])
        p[2] = min(255, p[2] + v * tint[2])

tints = [(1.0, 1.0, 1.0), (0.85, 0.92, 1.0), (1.0, 0.93, 0.8)]
for _ in range(1700):
    put(random.randrange(W), random.randrange(H), random.uniform(40, 140), random.choice(tints))
for _ in range(110):
    x, y = random.randrange(W), random.randrange(H)
    t = random.choice(tints)
    put(x, y, 255, t)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        put(x + dx, y + dy, 110, t)
    for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2), (1, 1), (-1, -1), (1, -1), (-1, 1)):
        put(x + dx, y + dy, 40, t)

raw = bytearray()
for row in img:
    raw.append(0)
    for r, g, b in row:
        raw += bytes((int(r), int(g), int(b)))


def chunk(tag, data):
    c = struct.pack(">I", len(data)) + tag + data
    return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)) \
    + chunk(b"IDAT", zlib.compress(bytes(raw), 6)) + chunk(b"IEND", b"")
open(sys.argv[1], "wb").write(png)
print("wrote", sys.argv[1], len(png) // 1024, "KB")
