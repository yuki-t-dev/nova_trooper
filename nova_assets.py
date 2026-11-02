# -*- coding: utf-8 -*-
"""
NOVA TROOPER  内蔵グラフィック（ドット絵）の生成

  python nova_assets.py            … assets/ に PNG を書き出す（要 Pillow）
  python nova_assets.py --preview  … 4倍に拡大したプレビュー PNG も書き出す

ゲーム本体は assets/*.png が無いとき、ここの関数で同じ絵をその場で生成します。
書き出した PNG を Aseprite などで描き換えて assets/ に置けば、そちらが優先されます。
色は Pyxel 標準の16色。透明色はピンク #FF9798（14番）。
"""
import math
import os
import random
import sys

KEY = 14
PAL = [0x000000, 0x2B335F, 0x7E2072, 0x19959C, 0x8B4852, 0x395C98, 0xA9C1FF, 0xEEEEEE,
       0xD4186C, 0xD38441, 0xE9C35B, 0x70C6A9, 0x7696DE, 0xA3A3A3, 0xFF9798, 0xEDC7B0]
BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]
TAU = math.pi * 2

# 名前: (幅, 高さ)
SPEC = {
    "hero":  (224, 48),
    "tiles": (128, 32),
    "sky":   (256, 208),
    "far":   (256, 112),
    "mid":   (256, 96),
    "near":  (256, 80),
    "front": (256, 32),
}

# 内蔵背景の点滅ライト位置（レイヤー内座標, 色）。生成時に埋まる
MID_LIGHTS = []
FAR_LIGHTS = []


# ============================================================
# 簡易キャンバス（パレット番号の2次元配列）
# ============================================================
class Canvas:
    def __init__(self, w, h, fill=KEY, wrap=False):
        self.w, self.h, self.wrap = w, h, wrap
        self.d = [fill] * (w * h)

    def pset(self, x, y, c):
        x, y = int(x), int(y)
        if self.wrap:
            x %= self.w
        if 0 <= x < self.w and 0 <= y < self.h:
            self.d[y * self.w + x] = c

    def get(self, x, y):
        x, y = int(x), int(y)
        if self.wrap:
            x %= self.w
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.d[y * self.w + x]
        return KEY

    def rect(self, x, y, w, h, c):
        for yy in range(int(y), int(y + h)):
            for xx in range(int(x), int(x + w)):
                self.pset(xx, yy, c)

    def rectb(self, x, y, w, h, c):
        self.line(x, y, x + w - 1, y, c)
        self.line(x, y + h - 1, x + w - 1, y + h - 1, c)
        self.line(x, y, x, y + h - 1, c)
        self.line(x + w - 1, y, x + w - 1, y + h - 1, c)

    def line(self, x0, y0, x1, y1, c):
        x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.pset(x0, y0, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def circ(self, cx, cy, r, c):
        cx, cy, r = int(cx), int(cy), int(r)
        for dy in range(-r, r + 1):
            dx = int(math.sqrt(max(0, r * r - dy * dy + r * 0.8)))
            for xx in range(cx - dx, cx + dx + 1):
                self.pset(xx, cy + dy, c)

    def tri(self, x0, y0, x1, y1, x2, y2, c):
        def edge(ax, ay, bx, by, px, py):
            return (bx - ax) * (py - ay) - (by - ay) * (px - ax)
        if edge(x0, y0, x1, y1, x2, y2) == 0:
            return
        for py in range(int(min(y0, y1, y2)), int(max(y0, y1, y2)) + 1):
            for px in range(int(min(x0, x1, x2)), int(max(x0, x1, x2)) + 1):
                qx, qy = px + 0.5, py + 0.5
                w0 = edge(x1, y1, x2, y2, qx, qy)
                w1 = edge(x2, y2, x0, y0, qx, qy)
                w2 = edge(x0, y0, x1, y1, qx, qy)
                if (w0 >= 0 and w1 >= 0 and w2 >= 0) or (w0 <= 0 and w1 <= 0 and w2 <= 0):
                    self.pset(px, py, c)

    def grad(self, x, y, w, h, c0, c1, t0, t1):
        """縦方向のディザグラデーション（c0 → c1）"""
        for yy in range(int(y), int(y + h)):
            t = t0 + (t1 - t0) * (yy - y) / max(1, h - 1)
            for xx in range(int(x), int(x + w)):
                self.pset(xx, yy, c1 if BAYER[yy % 4][xx % 4] < t * 16 else c0)

    def shade(self, x, y, w, h, c, t0, t1, only=None):
        """既に描かれた画素だけに、縦方向のディザで影を落とす"""
        for yy in range(int(y), int(y + h)):
            t = t0 + (t1 - t0) * (yy - y) / max(1, h - 1)
            for xx in range(int(x), int(x + w)):
                cur = self.get(xx, yy)
                if cur == KEY or (only is not None and cur not in only):
                    continue
                if BAYER[yy % 4][xx % 4] < t * 16:
                    self.pset(xx, yy, c)

    def art(self, x, y, rows, cmap):
        for yy, row in enumerate(rows):
            for xx, ch in enumerate(row):
                if ch == ".":
                    continue
                c = cmap.get(ch)
                if c is not None:
                    self.pset(x + xx, y + yy, c)


# ============================================================
# 自キャラ（16x16 × 14コマ × 3段）
# ============================================================
HERO_FRAMES = ["idle", "walk1", "walk2", "jump", "crouch", "shoot", "climb1", "climb2", "hurt",
               "up", "up1", "up2", "diag", "down"]

HEAD = [
    "......OOOO......",
    ".....OHHHHO.....",
    "....OHHHHHHO....",
    "....OHhVVVVO....",
    "....OHhVVVVO....",
    "....OhHHHHHO....",
    ".....OOOOOO.....",
]
HEAD_NAKED = [
    "................",
    ".....OOOOO......",
    "....OHHHHHO.....",
    "....OHSSSSO.....",
    "....OHSSESO.....",
    ".....OSSSSO.....",
    "......OOOO......",
]
TOP_GUN = [
    "...OKKOAAAO.....",
    "...OKKAAAAAO....",
    "...OKKaAGGGGGGO.",
    "....OOaAgOOOOO..",
    "....OAAAAO......",
]
TOP_SHOOT = [
    "...OKKOAAAO.....",
    "...OKKAAAAAOOOOO",
    "...OKKaAAGGGGGGg",
    "....OOaAAgOOOOO.",
    "....OAAAAO......",
]
LEGS = {
    "idle": ["....OLLOLLO.....", "....OLLOLLO.....", "....OBBOBBBO....", "....OOOOOOOO...."],
    "walk1": ["...OLLO.OLLO....", "..OLLO...OLLO...", ".OBBO.....OBBO..", ".OOOO.....OOOO.."],
    "walk2": [".....OLLLO......", ".....OLOLLO.....", ".....OBOBBO.....", ".....OOOOOO....."],
    "jump": ["...OLLLOLLO.....", "..OBBO.OLLO.....", "..OOO..OBBO.....", ".......OOOO....."],
}
TOP_BASE = [          # 銃を持たない上半身（銃は gen_hero で後から描く）
    "...OKKOAAAO.....",
    "...OKKAAAAAO....",
    "...OKKaAAAAKO...",
    "....OOaAAgKKO...",
    "....OAAAAO......",
]
AIM_LEGS = {"up": "idle", "up1": "walk1", "up2": "walk2", "diag": "idle", "down": "jump"}
# 銃身の線 (x0, y0, x1, y1)。幅2pxで描いて輪郭を付ける
AIM_GUN = {"up": (12, 9, 12, 0), "up1": (12, 9, 12, 0), "up2": (12, 9, 12, 0),
           "diag": (9, 9, 15, 3), "down": (12, 8, 12, 15)}
HURT_BODY = [
    ".OO.OAAAAO.OO...",
    ".OAOOAAAAAOOAO..",
    "..OO.OaAAAO.OO..",
    ".....OAAAAO.....",
    "....OLLOOLLO....",
    "...OLLO..OLLO...",
    "..OLLO....OLLO..",
    ".OBBO......OBBO.",
    ".OOO........OOO.",
]
CROUCH_BODY = [
    "...OKKAAAAGGGGGg",
    "...OKKaAAgOOOOO.",
    "...OLLLLLLO.....",
    "..OBBLLOLBBO....",
    "..OOOOOOOOOO....",
]
CLIMB = [
    "......OOOO......",
    ".....OHHHHO.....",
    "..OO.OHHHHO.OO..",
    ".OAAOHHHHHHOAAO.",
    ".OAOOhHHHHhOOAO.",
    ".OAO.OhhhhO..OO.",
    ".OO.OKKKKKKO....",
    "....OKKKKKKO....",
    "....OKggggKO....",
    "....OKKKKKKO....",
    "....OAAAAAAO....",
    "....OLLOOLLO....",
    "....OLLO.OLLO...",
    "....OLLO.OLLO...",
    "....OBBO.OBBO...",
    "....OOOO.OOOO...",
]
HERO_CMAP = [
    # 0: パワースーツ
    dict(O=0, H=7, h=6, V=12, A=7, a=6, K=12, G=5, g=13, L=6, B=12, S=15, E=0),
    # 1: 標準スーツ
    dict(O=0, H=13, h=5, V=11, A=13, a=5, K=5, G=5, g=13, L=5, B=1, S=15, E=0),
    # 2: インナースーツ（ヘルメットなし）
    dict(O=0, H=4, h=4, V=15, A=1, a=5, K=1, G=5, g=13, L=1, B=5, S=15, E=0),
]


def hero_rows(name, naked):
    head = HEAD_NAKED if naked else HEAD
    if name in ("idle", "walk1", "walk2", "jump"):
        rows = head + TOP_GUN + LEGS[name]
    elif name in AIM_LEGS:
        rows = head + TOP_BASE + LEGS[AIM_LEGS[name]]
    elif name == "shoot":
        rows = head + TOP_SHOOT + LEGS["walk1"]
    elif name == "hurt":
        rows = head + HURT_BODY
    elif name == "crouch":
        rows = ["." * 16] * 4 + head + CROUCH_BODY
    else:
        rows = list(CLIMB)
        if name == "climb2":
            rows = [r[::-1] for r in rows]
    rows = [(r + "." * 16)[:16] for r in rows]
    assert len(rows) == 16, (name, len(rows))
    return rows


def _line_pts(x0, y0, x1, y1):
    n = max(abs(x1 - x0), abs(y1 - y0))
    return [(round(x0 + (x1 - x0) * i / max(1, n)), round(y0 + (y1 - y0) * i / max(1, n)))
            for i in range(n + 1)]


def draw_aim_gun(c, ox, oy, name, cmap):
    """上撃ち・斜め・下撃ちのコマに銃身を描き足す（幅2px＋黒い輪郭）"""
    body = set()
    for x, y in _line_pts(*AIM_GUN[name]):
        c.pset(ox + x, oy + y, cmap["G"])
        c.pset(ox + x + 1, oy + y, cmap["g"])
        body |= {(x, y), (x + 1, y)}
    for x, y in body:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < 16 and 0 <= ny < 16 and (nx, ny) not in body and c.get(ox + nx, oy + ny) == KEY:
                c.pset(ox + nx, oy + ny, 0)


def gen_hero():
    c = Canvas(*SPEC["hero"])
    for lv, cmap in enumerate(HERO_CMAP):
        for i, name in enumerate(HERO_FRAMES):
            c.art(i * 16, lv * 16, hero_rows(name, lv == 2), cmap)
            if name in AIM_GUN:
                draw_aim_gun(c, i * 16, lv * 16, name, cmap)
    return c


# ============================================================
# 地形タイル（8x8）
#   段0 岩盤 : 内部x4, 上辺, 左辺, 右辺, 下辺（辺はオーバーレイ）
#   段1 金属 : 内部x4（無地/通気口/警告/窓）, 上辺, 左辺, 右辺, 下辺
#   段2      : コンテナ, 足場, はしご, ケーブル, 電流床x3
# ============================================================
def gen_tiles():
    c = Canvas(*SPEC["tiles"])
    rnd = random.Random(11)
    # --- 岩盤 ---
    for v in range(4):
        ox = v * 8
        c.rect(ox, 0, 8, 8, 4)
        for _ in range(6):
            c.pset(ox + rnd.randrange(8), rnd.randrange(8), 2)
        for _ in range(2):
            c.pset(ox + rnd.randrange(8), rnd.randrange(8), 9)
        if v == 3:   # 鉱石
            c.pset(ox + 3, 3, 11)
            c.pset(ox + 4, 4, 11)
            c.pset(ox + 4, 3, 7)
            c.pset(ox + 2, 4, 3)
    for x in range(8):
        c.pset(32 + x, 0, 15 if x % 3 else 10)
        c.pset(32 + x, 1, 9)
        if x % 2 == 0:
            c.pset(32 + x, 2, 9)
    c.pset(32 + 2, 3, 9)
    c.pset(32 + 6, 3, 9)
    for y in range(8):
        c.pset(40, y, 2)
        if y % 2:
            c.pset(41, y, 2)
        c.pset(55, y, 2)
        if y % 2 == 0:
            c.pset(54, y, 2)
    for x in range(8):
        c.pset(56 + x, 7, 2)
        if x % 2:
            c.pset(56 + x, 6, 2)
    # --- 金属 ---
    for v in range(4):
        ox = v * 8
        c.rect(ox, 8, 8, 8, 13)
        c.line(ox, 15, ox + 7, 15, 5)
        c.line(ox + 7, 8, ox + 7, 15, 5)
        if v == 0:
            for px, py in ((1, 1), (5, 1), (1, 5), (5, 5)):
                c.pset(ox + px, 8 + py, 5)
        elif v == 1:     # 通気口
            for yy in (2, 4):
                c.line(ox + 1, 8 + yy, ox + 5, 8 + yy, 0)
                c.line(ox + 1, 9 + yy, ox + 5, 9 + yy, 5)
        elif v == 2:     # 警告ストライプ
            for yy in range(2, 5):
                for xx in range(0, 7):
                    c.pset(ox + xx, 8 + yy, 10 if (xx + yy) % 4 < 2 else 0)
        else:            # 窓
            c.rect(ox + 1, 9, 5, 5, 1)
            c.rect(ox + 2, 10, 3, 3, 12)
            c.pset(ox + 2, 10, 7)
    for x in range(8):
        c.pset(32 + x, 8, 7)
        c.pset(32 + x, 9, 6)
    for y in range(8):
        c.pset(40, 8 + y, 6)
        c.pset(55, 8 + y, 0)
        c.pset(54, 8 + y, 5)
    for x in range(8):
        c.pset(56 + x, 15, 0)
        c.pset(56 + x, 14, 5)
    # --- コンテナ（壊れない） ---
    c.rect(0, 16, 8, 8, 5)
    c.rectb(0, 16, 8, 8, 1)
    c.line(1, 17, 6, 22, 13)
    c.line(6, 17, 1, 22, 13)
    c.line(1, 17, 6, 17, 6)
    c.pset(1, 22, 10)
    # --- 足場（グレーチング） ---
    for x in range(8):
        c.pset(8 + x, 16, 6)
        c.pset(8 + x, 17, 5 if x % 2 else 13)
        c.pset(8 + x, 18, 1)
    for yy in (19, 20):
        c.pset(9, yy, 1)
        c.pset(13, yy, 1)
    # --- はしご ---
    for y in range(8):
        c.pset(16, 16 + y, 5)
        c.pset(17, 16 + y, 13)
        c.pset(22, 16 + y, 13)
        c.pset(23, 16 + y, 5)
    for yy in (18, 22):
        c.line(18, yy, 21, yy, 6)
        c.line(18, yy + 1, 21, yy + 1, 5)
    # --- ケーブル ---
    for y in range(8):
        c.pset(27, 16 + y, 0)
        c.pset(28, 16 + y, 5)
    c.line(26, 16, 29, 16, 13)
    c.line(26, 20, 29, 20, 13)
    # --- 電流床（3コマ） ---
    for f in range(3):
        ox = 32 + f * 8
        c.line(ox, 21, ox + 7, 21, 13)
        c.line(ox, 22, ox + 7, 22, 5)
        c.line(ox, 23, ox + 7, 23, 1)
        for ex in (1, 6):
            c.pset(ox + ex, 19, 13)
            c.pset(ox + ex, 20, 13)
            c.pset(ox + ex, 18, 7)
        r = random.Random(100 + f)
        px, py = ox + 1, 18
        for xx in range(2, 7):
            ny = 18 + r.randint(-2, 1) if xx < 6 else 18
            c.line(px, py, ox + xx, ny, 12)
            px, py = ox + xx, ny
        c.pset(ox + 3 + f % 2, 17 - (f == 1), 7)
    return c


# ============================================================
# 背景レイヤー
# ============================================================
def gen_sky():
    w, h = SPEC["sky"]
    c = Canvas(w, h, 0)
    for y0, y1, c0, c1, t0, t1 in ((60, 115, 0, 1, 0.0, 1.0), (115, 165, 1, 2, 0.0, 1.0),
                                   (165, h, 2, 8, 0.0, 0.55)):
        c.grad(0, y0, w, y1 - y0, c0, c1, t0, t1)
    for y in range(115, h):
        for x in range(w):
            if y < 165 and c.get(x, y) == 0:
                c.pset(x, y, 1)
    rnd = random.Random(3)
    # 星雲
    for bx, by, br in ((150, 70, 40), (30, 100, 30)):
        for y in range(by - br, by + br):
            for x in range(bx - br, bx + br):
                d = math.hypot(x - bx, (y - by) * 1.6) / br
                if d < 1 and c.get(x, y) in (0, 1) and BAYER[y % 4][x % 4] < (1 - d) * 7:
                    c.pset(x, y, 2 if c.get(x, y) == 1 else 1)
    # 星
    for _ in range(150):
        x, y = rnd.randrange(w), rnd.randrange(140)
        if c.get(x, y) in (0, 1):
            c.pset(x, y, rnd.choice((13, 13, 13, 5, 6, 6, 7)))
    # 環のある惑星
    cx, cy, r = 58, 50, 24
    tilt = -0.32

    def ring(front):
        for i in range(720):
            t = i / 720 * TAU
            if (math.sin(t) > 0) != front:
                continue
            for k, col in ((46, 13 if front else 5), (43, 6 if front else 5), (39, 13 if front else 1)):
                ex, ey = k * math.cos(t), k * 0.2 * math.sin(t)
                rx = ex * math.cos(tilt) - ey * math.sin(tilt)
                ry = ex * math.sin(tilt) + ey * math.cos(tilt)
                c.pset(cx + rx, cy + ry, col)
    ring(False)
    for y in range(cy - r, cy + r + 1):
        for x in range(cx - r, cx + r + 1):
            dx, dy = x - cx, y - cy
            if dx * dx + dy * dy > r * r:
                continue
            col = 12 if ((dy + 30 + int(dx * 0.3)) // 5) % 3 == 0 else 5
            lit = (-dx * 0.7 - dy * 0.7) / r
            if lit > 0.72:
                col = 6
            t = (dx * 0.7 + dy * 0.7) / r
            if BAYER[y % 4][x % 4] < (t + 0.1) * 14:
                col = 1
            c.pset(x, y, col)
    ring(True)
    # 小さな衛星
    mx, my, mr = 204, 30, 6
    for y in range(my - mr, my + mr + 1):
        for x in range(mx - mr, mx + mr + 1):
            dx, dy = x - mx, y - my
            if dx * dx + dy * dy <= mr * mr + mr * 0.8:
                col = 13
                if BAYER[y % 4][x % 4] < (dx / mr + 0.3) * 14:
                    col = 5
                c.pset(x, y, col)
    for px, py in ((202, 28), (206, 32), (201, 33)):
        c.pset(px, py, 5)
    c.pset(201, 26, 7)
    return c


def gen_far():
    global FAR_LIGHTS
    FAR_LIGHTS = []
    w, h = SPEC["far"]
    c = Canvas(w, h, KEY, wrap=True)

    def hgt(x):
        v = (30 + 12 * math.sin(TAU * x / w * 2 + 0.5) + 8 * math.sin(TAU * x / w * 5 + 1.3)
             + 4 * math.sin(TAU * x / w * 11))
        return int(v // 5 * 5)
    for x in range(w):
        top = h - hgt(x)
        for y in range(top, h):
            c.pset(x, y, 1)
        c.pset(x, top, 2)
        c.pset(x, top + 1, 2 if x % 2 else 1)
        prev = h - hgt(x - 1)
        if top < prev:            # 左側の崖に夕日のリムライト
            for y in range(top, prev):
                c.pset(x, y, 8)
    c.shade(0, h - 60, w, 60, 0, 0.0, 0.6, only=(1,))
    # 尖塔
    for sx, sh in ((40, 78), (46, 66), (182, 84)):
        top = h - sh
        c.rect(sx, top, 3, sh, 1)
        c.line(sx + 1, top - 10, sx + 1, top, 1)
        c.line(sx, top, sx, h, 2)
        FAR_LIGHTS.append((sx + 1, top - 11, 8))
    # 敵の母艦
    x0, x1, yc = 120, 238, 18
    for x in range(x0, x1):
        t = (x - x0) / (x1 - x0)
        f = math.sin(math.pi * min(1.0, t * 1.25)) ** 0.6
        top, bot = yc - int(9 * f), yc + int(5 * f)
        for y in range(top, bot + 1):
            c.pset(x, y, 0)
        c.pset(x, top, 1)
        c.pset(x, bot, 5)
    c.rect(186, 4, 16, 6, 0)
    c.rect(190, 1, 4, 3, 0)
    c.line(196, 0, 196, 4, 0)
    for x in range(132, 226, 5):
        c.pset(x, yc + 1, 12)
    for y in range(yc - 3, yc + 3):
        c.pset(x0 - 1, y, 6)
        FAR_LIGHTS.append((x0 - 2, y, 6))
    FAR_LIGHTS.append((196, 0, 8))
    return c


def gen_mid():
    global MID_LIGHTS
    MID_LIGHTS = []
    w, h = SPEC["mid"]
    c = Canvas(w, h, KEY, wrap=True)
    rnd = random.Random(5)
    gy = h - 14
    c.rect(0, gy, w, 14, 1)
    c.line(0, gy, w - 1, gy, 5)
    # ドーム
    for cx, r in ((40, 24), (172, 17)):
        for y in range(gy - r, gy + 1):
            for x in range(cx - r, cx + r + 1):
                dx, dy = x - cx, y - gy
                if dx * dx + dy * dy > r * r:
                    continue
                col = 5
                if dy % 6 == 0 or (dx % 8 == 0):
                    col = 1
                if BAYER[y % 4][x % 4] < (dx / r) * 12:
                    col = 1
                c.pset(x, y, col)
        for _ in range(4):   # 崩れた穴
            bx = cx + rnd.randint(2, r // 2)
            by = gy - r + rnd.randint(0, r // 3)
            br = rnd.randint(3, 6)
            for y in range(by - br, by + br):
                for x in range(bx - br, bx + br):
                    if (x - bx) ** 2 + (y - by) ** 2 < br * br:
                        c.pset(x, y, KEY)
        MID_LIGHTS.append((cx - r // 3, gy - int(r * 0.94), 8))
    # 廃ビル
    for bx, bw, bh in ((70, 22, 26), (118, 30, 34), (200, 18, 40)):
        for x in range(bx, bx + bw):
            top = gy - bh + rnd.randint(0, 5)
            for y in range(top, gy):
                c.pset(x, y, 1 if x == bx + bw - 1 else 5)
        for y in range(gy - bh + 6, gy - 3, 4):
            for x in range(bx + 2, bx + bw - 2, 3):
                v = rnd.random()
                if v < 0.25:
                    c.pset(x, y, 12)
                elif v < 0.3:
                    c.pset(x, y, 10)
                    MID_LIGHTS.append((x, y, 10))
                else:
                    c.pset(x, y, 1)
    # アンテナ塔
    for tx in (100, 236):
        top = gy - 62
        c.line(tx, top, tx, gy, 5)
        c.line(tx + 4, top, tx + 4, gy, 5)
        for y in range(top, gy, 6):
            c.line(tx, y, tx + 4, y + 6, 1)
            c.line(tx + 4, y, tx, y + 6, 1)
        c.line(tx + 2, top - 12, tx + 2, top, 5)
        c.rect(tx - 3, top - 4, 10, 2, 5)
        MID_LIGHTS.append((tx + 2, top - 13, 8))
    return c


def gen_near():
    w, h = SPEC["near"]
    c = Canvas(w, h, KEY, wrap=True)
    gy = h - 18
    c.rect(0, gy, w, 18, 1)
    c.shade(0, gy, w, 18, 0, 0.1, 0.9)
    c.line(0, gy, w - 1, gy, 5)
    # 傾いた船体の外板
    c.tri(14, gy, 66, gy - 44, 92, gy, 1)
    c.tri(66, gy - 44, 92, gy, 98, gy - 30, 0)
    c.line(14, gy, 66, gy - 44, 5)
    c.line(66, gy - 44, 98, gy - 30, 13)
    for k in range(4):
        c.line(28 + k * 14, gy, 66 + k * 6, gy - 40 + k * 4, 0)
    c.pset(60, gy - 30, 12)
    c.pset(70, gy - 22, 12)
    # エンジンナセル
    c.rect(104, gy - 22, 24, 16, 1)
    c.circ(104, gy - 14, 8, 1)
    c.circ(104, gy - 14, 5, 0)
    c.circ(104, gy - 14, 2, 5)
    c.line(104, gy - 22, 127, gy - 22, 5)
    c.line(127, gy - 22, 127, gy - 7, 0)
    # 鉄骨
    for k in range(3):
        c.line(140 + k, gy, 166 + k, gy - 52, 0)
    c.rect(150, gy - 54, 40, 3, 0)
    c.line(150, gy - 54, 189, gy - 54, 5)
    for x in range(152, 188, 6):
        c.pset(x, gy - 53, 1)
    c.line(186, gy - 51, 196, gy, 0)
    # パイプライン
    py = gy - 30
    c.rect(196, py, 60, 5, 5)
    c.line(196, py, 255, py, 13)
    c.line(196, py + 4, 255, py + 4, 1)
    for x in range(204, 256, 16):
        c.rect(x, py - 1, 2, 7, 13)
        c.line(x + 1, py + 6, x + 1, gy, 0)
    for y in range(py, py + 5):   # 折れた端
        c.pset(196 - (y % 2), y, 0)
    return c


def gen_front():
    w, h = SPEC["front"]
    c = Canvas(w, h, KEY, wrap=True)
    rnd = random.Random(9)
    for cx, r in ((22, 11), (128, 8), (206, 13)):
        for y in range(h - r, h):
            for x in range(cx - r - 2, cx + r + 3):
                if (x - cx) ** 2 + ((y - h) * 1.3) ** 2 < r * r + rnd.randint(-4, 6):
                    c.pset(x, y, 0)
        for _ in range(r):
            c.pset(cx + rnd.randint(-r, r), h - rnd.randint(1, r), 1)
    for px in (60, 74, 88):
        c.rect(px, h - 22 + (px % 3), 2, 22, 0)
        c.pset(px, h - 22 + (px % 3), 1)
    for wy in (h - 18, h - 11):
        for x in range(61, 89):
            c.pset(x, wy + int(2 * math.sin((x - 61) / 28 * math.pi)), 0)
    for bx in (150, 157, 228):
        for i, ang in enumerate((-0.5, -0.15, 0.25, 0.6)):
            ln = 10 + (i * 5 + bx) % 9
            ex, ey = bx + math.sin(ang) * ln, h - math.cos(ang) * ln
            c.line(bx, h - 1, ex, ey, 0)
            c.pset(ex, ey, 2)
    return c


GENERATORS = {
    "hero": gen_hero, "tiles": gen_tiles, "sky": gen_sky,
    "far": gen_far, "mid": gen_mid, "near": gen_near, "front": gen_front,
}


# ============================================================
# PNG 書き出し
# ============================================================
def canvas_to_pil(cv):
    from PIL import Image
    im = Image.new("RGB", (cv.w, cv.h))
    rgb = [((c >> 16) & 255, (c >> 8) & 255, c & 255) for c in PAL]
    im.putdata([rgb[v] for v in cv.d])
    return im


def export(dirpath, preview=False):
    os.makedirs(dirpath, exist_ok=True)
    for name, gen in GENERATORS.items():
        im = canvas_to_pil(gen())
        im.save(os.path.join(dirpath, name + ".png"))
        if preview:
            from PIL import Image
            im.resize((im.width * 4, im.height * 4), Image.NEAREST).save(
                os.path.join(dirpath, name + "_preview.png"))
        print("wrote", name + ".png", im.size)


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    export(os.path.join(here, "assets"), "--preview" in sys.argv)
