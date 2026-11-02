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
    "tiles": (128, 48),
    "sky":   (256, 208),
    "far":   (256, 112),
    "mid":   (256, 96),
    "near":  (256, 80),
    "front": (256, 32),
    # 1-2 酸の湿地
    "marsh_sky":   (256, 208),
    "marsh_far":   (256, 112),
    "marsh_mid":   (256, 96),
    "marsh_near":  (256, 80),
    "marsh_front": (256, 32),
    # 1-3 中継塔（near は縦にもくり返す鉄骨）
    "tower_sky":   (256, 208),
    "tower_far":   (256, 112),
    "tower_mid":   (256, 96),
    "tower_near":  (256, 96),
    "tower_front": (256, 32),
    # 1-4 敵母艦（船内）
    "ship_sky":   (256, 208),
    "ship_far":   (256, 112),
    "ship_mid":   (256, 96),
    "ship_near":  (256, 80),
    "ship_front": (256, 32),
    # ワールド2：2-1 凍てつく氷原 / 2-2 溶岩の地下洞 / 2-3 氷の要塞
    "ice_sky":   (256, 208), "ice_far":   (256, 112), "ice_mid":   (256, 96),
    "ice_near":  (256, 80),  "ice_front":  (256, 32),
    "magma_sky": (256, 208), "magma_far": (256, 112), "magma_mid": (256, 96),
    "magma_near": (256, 80), "magma_front": (256, 32),
    "fort_sky":  (256, 208), "fort_far":  (256, 112), "fort_mid":  (256, 96),
    "fort_near": (256, 80),  "fort_front": (256, 32),
}

# 内蔵背景の点滅ライト位置（レイヤー内座標, 色）。生成時に埋まる
MID_LIGHTS = []
FAR_LIGHTS = []
LIGHTS = {}          # レイヤー名 -> [(x, y, 色), ...]


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
#   段2      : コンテナ, 足場, はしご, ケーブル, 電流床x3, 酸の表面x3, 酸の中身
#   段3 泥   : 内部x4, 上辺, 左辺, 右辺, 下辺, キノコの棚（すり抜け床）
#   段1 の右側（x=64〜87）: ベルトコンベア x3コマ（右向きに流れる絵。左向きは反転して描く）
#   段0 の右側（x=64〜127）: 氷（すべる床）  内部x4, 上辺, 左辺, 右辺, 下辺
#   段4 雪   : 内部x4, 上辺, 左辺, 右辺, 下辺（x=0〜63）  溶岩の表面x3, 溶岩の中身（x=64〜95）
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
    # --- 酸の表面（3コマ） ---
    for f in range(3):
        ox = 56 + f * 8
        c.rect(ox, 16, 8, 8, 3)
        for x in range(8):
            wy = 16 + (1 if (x + f * 3) % 6 < 3 else 0)
            if wy > 16:
                c.pset(ox + x, 16, KEY)
            c.pset(ox + x, wy, 11)
            if (x + f * 2) % 5 == 0:
                c.pset(ox + x, wy + 1, 7)
        for y in range(20, 24):
            for x in range(8):
                if BAYER[y % 4][x % 4] < (y - 19) * 2:
                    c.pset(ox + x, y, 1)
        c.pset(ox + (2 + f * 3) % 8, 19 + f % 2, 11)
    # --- 酸の中身 ---
    c.rect(80, 16, 8, 8, 3)
    for y in range(16, 24):
        for x in range(8):
            if BAYER[y % 4][x % 4] < 5:
                c.pset(80 + x, y, 1)
    c.pset(82, 18, 11)
    c.pset(86, 21, 11)
    # --- 泥 ---
    for v in range(4):
        ox = v * 8
        c.rect(ox, 24, 8, 8, 1)
        for _ in range(5):
            c.pset(ox + rnd.randrange(8), 24 + rnd.randrange(8), 5)
        for _ in range(2):
            c.pset(ox + rnd.randrange(8), 24 + rnd.randrange(8), 2)
        if v == 3:   # 光る胞子
            c.pset(ox + 3, 28, 11)
            c.pset(ox + 4, 28, 3)
            c.pset(ox + 3, 27, 3)
    for x in range(8):
        c.pset(32 + x, 24, 11 if x % 3 else 3)
        c.pset(32 + x, 25, 3)
        if x % 3 == 0:
            c.pset(32 + x, 26, 3)
    c.pset(32 + 4, 27, 3)
    for y in range(8):
        c.pset(40, 24 + y, 0)
        if y % 2:
            c.pset(41, 24 + y, 0)
        c.pset(55, 24 + y, 0)
        if y % 2 == 0:
            c.pset(54, 24 + y, 0)
    for x in range(8):
        c.pset(56 + x, 31, 0)
        if x % 2:
            c.pset(56 + x, 30, 0)
    # --- ベルトコンベア（3コマ・右へ流れる） ---
    for f in range(3):
        ox = 64 + f * 8
        c.rect(ox, 8, 8, 8, 1)
        c.line(ox, 8, ox + 7, 8, 13)
        c.line(ox, 15, ox + 7, 15, 0)
        for x in range(8):                       # 流れる矢じるし
            k = (x - f * 3) % 8
            if k in (0, 1):
                c.pset(ox + x, 10 + k, 10)
                c.pset(ox + x, 13 - k, 10)
        for x in (1, 6):                          # ローラー
            c.pset(ox + x, 14, 5 if (x + f) % 2 else 13)
    # --- 氷（すべる床） ---
    for v in range(4):
        ox = 64 + v * 8
        c.rect(ox, 0, 8, 8, 12)
        for y in range(8):
            for x in range(8):
                if BAYER[y % 4][x % 4] < y * 1.3:
                    c.pset(ox + x, y, 5)
        for i in range(3):
            c.pset(ox + (v * 3 + i) % 8, (1 + i + v) % 8, 6)
        if v == 1:
            c.line(ox + 1, 1, ox + 3, 3, 6)
        elif v == 2:
            c.pset(ox + 5, 4, 7)
        elif v == 3:
            c.line(ox + 2, 0, ox + 4, 4, 1)
            c.line(ox + 4, 4, ox + 3, 7, 1)
    for x in range(8):
        c.pset(96 + x, 0, 7)
        c.pset(96 + x, 1, 7 if x % 3 else 6)
        if x % 2 == 0:
            c.pset(96 + x, 2, 6)
    for y in range(8):
        c.pset(104, y, 6)
        if y % 2:
            c.pset(105, y, 6)
        c.pset(119, y, 1)
        if y % 2 == 0:
            c.pset(118, y, 5)
    for x in range(8):
        c.pset(120 + x, 7, 1)
        if x % 2:
            c.pset(120 + x, 6, 5)
    c.pset(122, 7, 6)
    c.pset(126, 7, 6)
    # --- 雪 ---
    for v in range(4):
        ox = v * 8
        c.rect(ox, 32, 8, 8, 6)
        for _ in range(5):
            c.pset(ox + rnd.randrange(8), 32 + rnd.randrange(8), 7)
        for _ in range(3):
            c.pset(ox + rnd.randrange(8), 32 + rnd.randrange(8), 13)
        if v == 3:              # 雪に埋まった石
            c.rect(ox + 2, 35, 3, 2, 13)
            c.pset(ox + 2, 35, 5)
    for x in range(8):
        c.pset(32 + x, 32, 7)
        c.pset(32 + x, 33, 7 if x % 2 else 6)
        if x in (2, 6):
            c.pset(32 + x, 32, 12)
    for y in range(8):
        c.pset(40, 32 + y, 13)
        if y % 2:
            c.pset(41, 32 + y, 13)
        c.pset(55, 32 + y, 5)
        if y % 2 == 0:
            c.pset(54, 32 + y, 13)
    for x in range(8):
        c.pset(56 + x, 39, 5)
        if x % 2:
            c.pset(56 + x, 38, 13)
    # --- 溶岩の表面（3コマ）と中身 ---
    for f in range(3):
        ox = 64 + f * 8
        c.rect(ox, 32, 8, 8, 8)
        for x in range(8):
            wy = 32 + (1 if (x + f * 3) % 6 < 3 else 0)
            if wy > 32:
                c.pset(ox + x, 32, KEY)
            c.pset(ox + x, wy, 10)
            if (x + f * 2) % 4 == 0:
                c.pset(ox + x, wy + 1, 9)
        for y in range(36, 40):
            for x in range(8):
                if BAYER[y % 4][x % 4] < (y - 35) * 2:
                    c.pset(ox + x, y, 2)
        c.pset(ox + (2 + f * 3) % 8, 35 + f % 2, 10)
    c.rect(88, 32, 8, 8, 8)
    for y in range(32, 40):
        for x in range(8):
            if BAYER[y % 4][x % 4] < 6:
                c.pset(88 + x, y, 2)
    c.pset(90, 34, 9)
    c.pset(93, 37, 9)
    # --- キノコの棚（すり抜け床） ---
    for x in range(8):
        c.pset(64 + x, 24, 11)
        c.pset(64 + x, 25, 3)
        if 0 < x < 7:
            c.pset(64 + x, 26, 3)
        if 1 < x < 6:
            c.pset(64 + x, 27, 1)
    c.pset(66, 28, 3)
    c.pset(69, 29, 3)
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
    LIGHTS["far"] = FAR_LIGHTS
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
    LIGHTS["mid"] = MID_LIGHTS
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


# ============================================================
# 背景レイヤー：1-2 酸の湿地
# ============================================================
def _fill_ellipse_top(c, cx, cy, rx, ry, col, cut=2):
    """上半分（中心より cut 下まで）を塗った楕円"""
    for y in range(int(cy - ry), int(cy + cut) + 1):
        for x in range(int(cx - rx), int(cx + rx) + 1):
            if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1:
                c.pset(x, y, col)


def gen_marsh_sky():
    w, h = SPEC["marsh_sky"]
    c = Canvas(w, h, 0)
    c.grad(0, 50, w, 70, 0, 1, 0.0, 1.0)
    for y in range(120, h):
        for x in range(w):
            c.pset(x, y, 1)
    c.grad(0, 140, w, h - 140, 1, 3, 0.0, 0.75)
    rnd = random.Random(21)
    for _ in range(90):
        x, y = rnd.randrange(w), rnd.randrange(105)
        if c.get(x, y) in (0, 1):
            c.pset(x, y, rnd.choice((5, 13, 13, 11)))
    # 緑の月と光の輪
    mx, my, mr = 188, 46, 18
    for y in range(my - mr - 5, my + mr + 6):
        for x in range(mx - mr - 5, mx + mr + 6):
            d = math.hypot(x - mx, y - my)
            if mr < d <= mr + 5 and BAYER[y % 4][x % 4] < (mr + 5 - d) * 1.2:
                c.pset(x, y, 3 if c.get(x, y) == 1 else 1)
    for y in range(my - mr, my + mr + 1):
        for x in range(mx - mr, mx + mr + 1):
            dx, dy = x - mx, y - my
            if dx * dx + dy * dy > mr * mr:
                continue
            col = 11
            if BAYER[y % 4][x % 4] < (dx / mr + 0.25) * 12:
                col = 3
            c.pset(x, y, col)
    for cx2, cy2, r2 in ((182, 40, 3), (194, 52, 2), (180, 54, 2), (191, 37, 1)):
        c.circ(cx2, cy2, r2, 3)
    c.pset(176, 38, 7)
    # 地平線のもや
    for yy in (126, 134, 148, 160):
        for x in range(w):
            if (x // 9 + yy) % 5 < 2 and BAYER[yy % 4][x % 4] < 6:
                c.pset(x, yy, 3)
    return c


def gen_marsh_far():
    lights = LIGHTS["marsh_far"] = []
    w, h = SPEC["marsh_far"]
    c = Canvas(w, h, KEY, wrap=True)

    def hgt(x):
        return int(26 + 10 * math.sin(TAU * x / w * 3 + 1) + 6 * math.sin(TAU * x / w * 7))
    for x in range(w):
        top = h - hgt(x)
        for y in range(top, h):
            c.pset(x, y, 1)
        c.pset(x, top, 3)
    c.shade(0, h - 40, w, 40, 0, 0.0, 0.7, only=(1,))
    # 遠くのキノコ
    for cx, sh, rx in ((100, 52, 20), (232, 40, 14)):
        c.rect(cx - 2, h - sh, 4, sh, 1)
        _fill_ellipse_top(c, cx, h - sh, rx, 9, 1)
        for x in range(cx - rx, cx + rx + 1):
            c.pset(x, h - sh + 2, 3)
    # 廃墟の塔
    for sx, sh in ((60, 70), (150, 86), (200, 58)):
        top = h - sh
        c.rect(sx, top, 4, sh, 0)
        for y in range(top + 6, h, 9):
            c.line(sx - 2, y, sx + 5, y, 0)
        c.line(sx + 2, top - 9, sx + 2, top, 0)
        lights.append((sx + 2, top - 10, 11))
    return c


def gen_marsh_mid():
    lights = LIGHTS["marsh_mid"] = []
    w, h = SPEC["marsh_mid"]
    c = Canvas(w, h, KEY, wrap=True)
    rnd = random.Random(31)
    gy = h - 12
    c.rect(0, gy, w, 12, 1)
    for x in range(w):
        if x % 3:
            c.pset(x, gy, 3)
    for cx, sh, rx, ry in ((30, 50, 20, 13), (110, 36, 14, 9), (175, 58, 23, 15), (232, 30, 12, 8)):
        cy = gy - sh
        for y in range(cy, gy):
            off = int(3 * math.sin(y * 0.08 + cx))
            for x in range(cx - 2, cx + 3):
                c.pset(x + off, y, 0 if x == cx + 2 else 1)
        _fill_ellipse_top(c, cx, cy, rx, ry, 2)
        for y in range(cy - ry, cy + 3):
            for x in range(cx - rx, cx + rx + 1):
                if c.get(x, y) == 2 and BAYER[y % 4][x % 4] < ((x - cx) / rx) * 10:
                    c.pset(x, y, 1)
        for x in range(cx - rx + 1, cx + rx):
            c.pset(x, cy + 2, 0)
            if x % 3 == 0:
                c.pset(x, cy + 3, 0)
        for _ in range(rx // 4):
            sx = cx + rnd.randint(-rx + 3, rx - 3)
            sy = cy - rnd.randint(2, ry - 2)
            if c.get(sx, sy) == 2:
                c.pset(sx, sy, 8)
        for k in (-0.8, 0.0, 0.8):
            lights.append((int(cx + rx * k), cy + 3, 11))
    return c


def gen_marsh_near():
    w, h = SPEC["marsh_near"]
    c = Canvas(w, h, KEY, wrap=True)
    rnd = random.Random(41)
    gy = h - 16
    c.rect(0, gy, w, 16, 0)
    for x in range(w):
        if (x // 5) % 3 == 0:
            c.pset(x, gy, 3)
        if (x // 7 + 1) % 4 == 0:
            c.pset(x, gy + 4, 1)
        if (x // 11) % 3 == 1:
            c.pset(x, gy + 9, 1)

    def branch(x, y, ang, ln, depth):
        ex, ey = x + math.cos(ang) * ln, y + math.sin(ang) * ln
        c.line(x, y, ex, ey, 0)
        if depth > 0:
            branch(ex, ey, ang - 0.5 + rnd.uniform(-0.2, 0.2), ln * 0.65, depth - 1)
            branch(ex, ey, ang + 0.45 + rnd.uniform(-0.2, 0.2), ln * 0.6, depth - 1)
    for tx, th in ((40, 52), (150, 60), (222, 44)):
        for k in range(3):
            c.line(tx + k, gy, tx + 4 + k, gy - th, 0)
        branch(tx + 5, gy - th, -math.pi / 2 - 0.3, 14, 2)
        branch(tx + 4, gy - th * 0.6, -0.4, 12, 1)
    c.rect(80, gy - 10, 50, 6, 1)
    c.line(80, gy - 10, 129, gy - 10, 5)
    for x in range(86, 128, 12):
        c.rect(x, gy - 11, 2, 8, 5)
    for y in range(gy - 10, gy - 4):
        c.pset(80 - (y % 2), y, 0)
    for _ in range(26):
        x = rnd.randrange(w)
        ln = rnd.randint(5, 13)
        c.line(x, gy, x + rnd.randint(-2, 2), gy - ln, 0)
    return c


def gen_marsh_front():
    w, h = SPEC["marsh_front"]
    c = Canvas(w, h, KEY, wrap=True)
    rnd = random.Random(51)
    for bx in (12, 70, 118, 176, 236):
        for _ in range(rnd.randint(6, 9)):
            x = bx + rnd.randint(-7, 7)
            ln = rnd.randint(12, 28)
            lean = rnd.randint(-4, 4)
            col = 0 if rnd.random() < 0.8 else 1
            c.line(x, h - 1, x + lean, h - 1 - ln, col)
            if rnd.random() < 0.35:
                c.rect(x + lean - 1, h - 1 - ln, 2, 5, 4)
    return c


# ============================================================
# 背景レイヤー：1-3 中継塔
# ============================================================
def gen_tower_sky():
    """高空：宇宙の黒に近い空と、下の方に惑星の地平線"""
    w, h = SPEC["tower_sky"]
    c = Canvas(w, h, 0)
    rnd = random.Random(61)
    for _ in range(220):
        x, y = rnd.randrange(w), rnd.randrange(h - 40)
        c.pset(x, y, rnd.choice((5, 5, 13, 13, 6, 7)))
    for _ in range(10):                                   # 明るい星
        x, y = rnd.randrange(w), rnd.randrange(120)
        c.pset(x, y, 7)
        c.pset(x - 1, y, 5)
        c.pset(x + 1, y, 5)
    # 惑星の地平線（大きな円の上の端）
    cx, cy, r = 128, 760, 600
    for y in range(140, h):
        for x in range(w):
            d = math.hypot(x - cx, y - cy)
            if d <= r:
                col = 1 if BAYER[y % 4][x % 4] < (y - (cy - r)) * 0.5 else 5
                c.pset(x, y, col)
            elif d <= r + 2:
                c.pset(x, y, 12)
            elif d <= r + 7 and BAYER[y % 4][x % 4] < (r + 7 - d) * 2:
                c.pset(x, y, 5 if c.get(x, y) == 0 else c.get(x, y))
    # 遠くの敵母艦
    x0, yc = 30, 34
    for x in range(x0, x0 + 46):
        t = (x - x0) / 46
        f = math.sin(math.pi * min(1.0, t * 1.2)) ** 0.6
        for y in range(yc - int(5 * f), yc + int(3 * f) + 1):
            c.pset(x, y, 1)
        c.pset(x, yc + int(3 * f), 5)
    for x in range(x0 + 6, x0 + 40, 4):
        c.pset(x, yc, 12)
    return c


def gen_tower_far():
    """はるか下の地上：クレーターと基地の明かり（登るほど沈んでいく）"""
    lights = LIGHTS["tower_far"] = []
    w, h = SPEC["tower_far"]
    c = Canvas(w, h, KEY, wrap=True)
    rnd = random.Random(71)
    top = h - 46
    c.rect(0, top, w, h - top, 1)
    for x in range(w):
        c.pset(x, top, 12 if x % 5 else 6)
    c.shade(0, top, w, h - top, 0, 0.0, 0.8, only=(1,))
    for _ in range(9):                                    # クレーター（楕円）
        ex, ey, rx = rnd.randrange(w), rnd.randint(top + 6, h - 8), rnd.randint(6, 16)
        for y in range(ey - rx // 3, ey + rx // 3 + 1):
            for x in range(ex - rx, ex + rx + 1):
                if ((x - ex) / rx) ** 2 + ((y - ey) / (rx / 3)) ** 2 <= 1:
                    c.pset(x, y, 5 if y < ey else 0)
    for _ in range(14):                                   # 基地の明かり
        x, y = rnd.randrange(w), rnd.randint(top + 4, h - 4)
        c.pset(x, y, 10)
        lights.append((x, y, 10))
    for bx in (60, 180):                                  # 遠くのドーム
        for y in range(top - 6, top + 1):
            for x in range(bx - 8, bx + 9):
                if (x - bx) ** 2 + ((y - top) * 1.4) ** 2 <= 64:
                    c.pset(x, y, 5)
        lights.append((bx, top - 6, 8))
    return c


def gen_tower_mid():
    """雲の帯（登っていくと上から下へ通り過ぎる）"""
    w, h = SPEC["tower_mid"]
    c = Canvas(w, h, KEY, wrap=True)
    rnd = random.Random(81)
    for band_y, thick, col, dens in ((22, 14, 1, 6), (54, 20, 5, 5), (70, 8, 13, 2)):
        for _ in range(16):
            cx = rnd.randrange(w)
            rx = rnd.randint(14, 34)
            ry = rnd.randint(thick // 3, thick // 2 + 2)
            cy = band_y + rnd.randint(-3, 3)
            for y in range(cy - ry, cy + ry + 1):
                for xx in range(cx - rx, cx + rx + 1):
                    d = ((xx - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
                    if d <= 1 and BAYER[y % 4][xx % 4] < (1 - d) * 16 + dens - 4:
                        c.pset(xx, y, col)
    return c


def gen_tower_near():
    """中継塔の鉄骨（縦方向にもくり返して描く）"""
    w, h = SPEC["tower_near"]
    c = Canvas(w, h, KEY, wrap=True)
    for gx in (18, 214):                                  # 太い柱2本
        c.rect(gx, 0, 3, h, 1)
        c.rect(gx + 21, 0, 3, h, 1)
        for x in range(gx, gx + 24):
            c.pset(x, 0, 5)
            c.pset(x, 1, 1)
            c.pset(x, h // 2, 1)
        for y0 in (0, h // 2):                            # X字の筋交い
            c.line(gx + 2, y0 + 1, gx + 21, y0 + h // 2 - 1, 1)
            c.line(gx + 21, y0 + 1, gx + 2, y0 + h // 2 - 1, 1)
        for y in range(0, h, 4):
            c.pset(gx + 1, y, 5)
            c.pset(gx + 22, y, 5)
    for x in range(42, 214):                              # 細い横ばり
        c.pset(x, 0, 1)
        if x % 6 == 0:
            c.pset(x, 1, 1)
    for x in range(100, 160):                             # 奥の細いケーブル
        y = 40 + int(10 * math.sin((x - 100) / 60 * math.pi))
        c.pset(x, y, 1)
    return c


def gen_tower_front():
    """塔のふもとのがれき（少し登るとすぐ画面外へ）"""
    w, h = SPEC["tower_front"]
    c = Canvas(w, h, KEY, wrap=True)
    rnd = random.Random(91)
    for cx, r in ((10, 9), (90, 7), (170, 11), (240, 8)):
        for y in range(h - r, h):
            for x in range(cx - r - 2, cx + r + 3):
                if (x - cx) ** 2 + ((y - h) * 1.3) ** 2 < r * r + rnd.randint(-4, 6):
                    c.pset(x, y, 0)
    for px in (120, 128):
        c.rect(px, h - 18, 2, 18, 0)
    c.line(120, h - 16, 129, h - 12, 0)
    return c


# ============================================================
# 背景レイヤー：1-4 敵母艦（船内）
# ============================================================
def gen_ship_sky():
    """船内の奥の壁。横長の窓から星空と惑星ゼータが見える"""
    w, h = SPEC["ship_sky"]
    c = Canvas(w, h, 1)
    for y in range(h):                                 # 壁のパネル
        for x in range(w):
            if y % 28 == 0 or x % 32 == 0:
                c.pset(x, y, 0)
            elif (x % 32, y % 28) in ((2, 2), (29, 2), (2, 25), (29, 25)):
                c.pset(x, y, 5)
    wy0, wy1 = 40, 92                                   # 窓
    c.rect(0, wy0, w, wy1 - wy0, 0)
    rnd = random.Random(101)
    for _ in range(70):
        c.pset(rnd.randrange(w), rnd.randint(wy0 + 1, wy1 - 2), rnd.choice((5, 13, 13, 7)))
    cx, cy, r = 150, 230, 150                            # 窓の下に見える惑星
    for y in range(wy0, wy1):
        for x in range(w):
            d = math.hypot(x - cx, y - cy)
            if d <= r:
                c.pset(x, y, 2 if BAYER[y % 4][x % 4] < (y - (cy - r)) * 0.9 else 8)
            elif d <= r + 1.5:
                c.pset(x, y, 14 if False else 8)
    for x in range(0, w, 64):                           # 窓枠
        c.rect(x, wy0, 4, wy1 - wy0, 5)
        c.line(x + 1, wy0, x + 1, wy1 - 1, 13)
    c.rect(0, wy0 - 3, w, 3, 5)
    c.line(0, wy0 - 3, w - 1, wy0 - 3, 13)
    c.rect(0, wy1, w, 3, 5)
    c.line(0, wy1 + 2, w - 1, wy1 + 2, 0)
    for x in range(8, w, 32):                           # 赤い誘導灯
        c.pset(x, wy1 + 8, 2)
    return c


def gen_ship_far():
    """リアクターの円筒（光るリング）"""
    lights = LIGHTS["ship_far"] = []
    w, h = SPEC["ship_far"]
    c = Canvas(w, h, KEY, wrap=True)
    for cx, rw, top in ((40, 18, 10), (128, 24, 0), (214, 16, 18)):
        for y in range(top, h):
            for x in range(cx - rw, cx + rw + 1):
                col = 1
                if BAYER[y % 4][x % 4] < ((x - (cx - rw)) / (2 * rw)) * 12:
                    col = 0
                c.pset(x, y, col)
        c.line(cx - rw, top, cx - rw, h - 1, 5)
        for ry in range(top + 12, h, 22):               # 光るリング
            for x in range(cx - rw, cx + rw + 1):
                c.pset(x, ry, 2)
                c.pset(x, ry + 1, 8 if (x - cx) % 4 else 14 if False else 8)
            for x in range(cx - rw + 2, cx + rw, 6):
                lights.append((x, ry + 1, 8))
        c.rect(cx - rw - 2, top, 2 * rw + 5, 3, 5)
    return c


def gen_ship_mid():
    """配管（横・縦のパイプとバルブ）"""
    lights = LIGHTS["ship_mid"] = []
    w, h = SPEC["ship_mid"]
    c = Canvas(w, h, KEY, wrap=True)
    for py, th in ((18, 5), (30, 3), (62, 4)):
        c.rect(0, py, w, th, 5)
        c.line(0, py, w - 1, py, 13)
        c.line(0, py + th - 1, w - 1, py + th - 1, 1)
        for x in range(10, w, 40):                      # 継ぎ目
            c.rect(x, py - 1, 3, th + 2, 13)
            c.line(x + 2, py - 1, x + 2, py + th, 1)
    for px in (24, 96, 180):
        c.rect(px, 0, 4, h, 5)
        c.line(px, 0, px, h - 1, 13)
        c.line(px + 3, 0, px + 3, h - 1, 1)
        c.circ(px + 1, 46, 4, 1)                        # バルブ
        c.circ(px + 1, 46, 3, 2)
        c.line(px - 2, 46, px + 4, 46, 13)
        lights.append((px + 1, 40, 8))
    for x in range(0, w, 16):                           # 下の暗がり
        c.rect(x, h - 10, 12, 10, 0)
    return c


def gen_ship_near():
    """支柱と梁（手前の暗いシルエット）"""
    w, h = SPEC["ship_near"]
    c = Canvas(w, h, KEY, wrap=True)
    for cx in (60, 190):
        c.rect(cx, 0, 10, h, 0)
        for y in range(6, h, 14):                       # 肉抜き穴
            c.rect(cx + 3, y, 4, 7, KEY)
        c.line(cx, 0, cx - 24, 20, 0)
        c.line(cx + 9, 0, cx + 33, 20, 0)
        c.line(cx - 24, 20, cx + 33, 20, 0)
    for x in range(0, w):                               # 天井近くの梁
        c.pset(x, 2, 0)
        c.pset(x, 3, 0)
        if x % 8 < 2:
            c.pset(x, 4, 0)
    return c


def gen_ship_front():
    """床を這うホースと箱（最前面）"""
    w, h = SPEC["ship_front"]
    c = Canvas(w, h, KEY, wrap=True)
    for x in range(w):
        y = h - 4 + int(2 * math.sin(x / 18))
        c.pset(x, y, 0)
        c.pset(x, y + 1, 0)
    for bx, bw, bh in ((30, 14, 10), (46, 10, 6), (150, 18, 12), (222, 12, 8)):
        c.rect(bx, h - bh, bw, bh, 0)
        c.line(bx + 2, h - bh + 2, bx + bw - 3, h - bh + 2, 1)
    for px in (100, 104):
        c.rect(px, h - 20, 2, 20, 0)
    c.line(96, h - 20, 109, h - 20, 0)
    return c


# ============================================================
# 背景レイヤー：ワールド2（氷の衛星フロスト）
# ============================================================
def _aurora(c, cols, y0, amp, seed):
    w = c.w
    for x in range(w):
        base = y0 + amp * math.sin(x / 37 + seed) + amp * 0.6 * math.sin(x / 13 + seed * 2)
        if (x // 3 + seed) % 5 == 0:
            continue
        for k in range(26):
            y = int(base + k)
            if 0 <= y < c.h and c.get(x, y) in (0, 1) and BAYER[y % 4][x % 4] < (26 - k) / 26 * 9:
                c.pset(x, y, cols[0] if k < 4 else cols[1])


def gen_ice_sky():
    """オーロラのかかる夜空と、地平線にかかる巨大な母惑星"""
    w, h = SPEC["ice_sky"]
    c = Canvas(w, h, 0)
    c.grad(0, 40, w, 80, 0, 1, 0.0, 1.0)
    for y in range(120, h):
        for x in range(w):
            c.pset(x, y, 1)
    c.grad(0, 130, w, h - 130, 1, 5, 0.0, 0.8)
    rnd = random.Random(111)
    for _ in range(120):
        x, y = rnd.randrange(w), rnd.randrange(110)
        if c.get(x, y) in (0, 1):
            c.pset(x, y, rnd.choice((13, 13, 6, 7, 5)))
    _aurora(c, (11, 3), 18, 10, 0.5)
    cx, cy, r = 206, 58, 30                         # 母惑星（三日月）
    for y in range(cy - r, cy + r + 1):
        for x in range(cx - r, cx + r + 1):
            dx, dy = x - cx, y - cy
            if dx * dx + dy * dy > r * r:
                continue
            shadow = (x - cx - 10) ** 2 + (y - cy - 6) ** 2 < r * r
            if shadow:
                c.pset(x, y, 1 if BAYER[y % 4][x % 4] < 8 else 0)
            else:
                c.pset(x, y, 9 if (dy // 5) % 2 else 4)
                if dx * dx + dy * dy > (r - 2) ** 2:
                    c.pset(x, y, 15)
    return c


def gen_ice_far():
    """雪をかぶった遠くの山脈"""
    lights = LIGHTS["ice_far"] = []
    w, h = SPEC["ice_far"]
    c = Canvas(w, h, KEY, wrap=True)

    def hgt(x):
        return (34 + 24 * abs(math.sin(TAU * x / w * 2 + 0.3)) + 12 * abs(math.sin(TAU * x / w * 5 + 1.0))
                + 4 * math.sin(TAU * x / w * 13))
    for x in range(w):
        hx = hgt(x)
        top = h - int(hx)
        for y in range(top, h):
            c.pset(x, y, 5)
        cap = int(max(0, hx - 30) * 0.45)
        lit = hgt(x - 1) < hx
        for y in range(top, top + cap):
            c.pset(x, y, 7 if lit else 6)
        c.pset(x, top, 7)
    c.shade(0, h - 40, w, 40, 1, 0.0, 0.9, only=(5,))
    for bx in (70, 190):                            # 遠くの前哨基地
        c.rect(bx - 4, h - 10, 9, 4, 1)
        lights.append((bx, h - 11, 10))
    return c


def gen_ice_mid():
    """氷の結晶の尖塔"""
    lights = LIGHTS["ice_mid"] = []
    w, h = SPEC["ice_mid"]
    c = Canvas(w, h, KEY, wrap=True)
    gy = h - 10
    c.rect(0, gy, w, 10, 6)
    c.line(0, gy, w - 1, gy, 7)
    for cx, hh, ww in ((30, 40, 7), (44, 26, 5), (110, 54, 8), (123, 30, 5), (180, 36, 6), (232, 48, 7)):
        c.tri(cx - ww, gy, cx, gy - hh, cx + ww, gy, 12)
        c.tri(cx, gy - hh, cx + ww, gy, cx, gy, 5)
        c.line(cx - ww, gy, cx, gy - hh, 6)
        c.line(cx, gy - hh, cx, gy - hh + 6, 7)
        lights.append((cx, gy - hh, 7))
    return c


def gen_ice_near():
    """雪の吹きだまりと、壊れた前哨基地"""
    w, h = SPEC["ice_near"]
    c = Canvas(w, h, KEY, wrap=True)
    gy = h - 14
    for x in range(w):
        y = gy - int(6 + 5 * math.sin(x / 23) + 3 * math.sin(x / 7))
        for yy in range(y, h):
            c.pset(x, yy, 13)
        c.pset(x, y, 6)
    c.rect(124, gy - 30, 30, 26, 5)                 # 前哨基地の残骸
    c.rect(150, gy - 30, 4, 26, 1)
    c.tri(120, gy - 30, 140, gy - 40, 158, gy - 30, 1)
    c.line(120, gy - 31, 158, gy - 31, 6)
    c.rect(130, gy - 22, 6, 6, 0)
    c.rect(140, gy - 22, 6, 6, 1)
    c.line(146, gy - 40, 146, gy - 58, 1)
    c.line(142, gy - 52, 150, gy - 52, 1)
    for sx in (40, 206):                            # 氷の柱
        c.rect(sx, gy - 34, 6, 34, 5)
        c.line(sx, gy - 34, sx, gy, 6)
        c.tri(sx - 2, gy - 34, sx + 3, gy - 42, sx + 8, gy - 34, 5)
    return c


def gen_ice_front():
    w, h = SPEC["ice_front"]
    c = Canvas(w, h, KEY, wrap=True)
    rnd = random.Random(121)
    for cx, r in ((14, 12), (98, 9), (170, 13), (236, 8)):
        for y in range(h - r, h):
            for x in range(cx - r - 2, cx + r + 3):
                if (x - cx) ** 2 + ((y - h) * 1.4) ** 2 < r * r + rnd.randint(-3, 4):
                    c.pset(x, y, 7 if y < h - r + 3 else 6)
    for px in (60, 130):
        c.line(px, h - 1, px + 2, h - 20, 5)
        c.line(px + 2, h - 20, px + 6, h - 16, 5)
    return c


def gen_magma_sky():
    """溶岩洞の奥の岩壁。下の方が溶岩の光で赤く染まる"""
    w, h = SPEC["magma_sky"]
    c = Canvas(w, h, 1)
    rnd = random.Random(131)
    for _ in range(40):                              # 岩肌のひび
        x, y = rnd.randrange(w), rnd.randrange(h - 60)
        for _ in range(rnd.randint(3, 6)):
            nx, ny = x + rnd.randint(-6, 6), y + rnd.randint(2, 7)
            c.line(x, y, nx, ny, 0)
            x, y = nx, ny
    for _ in range(300):
        c.pset(rnd.randrange(w), rnd.randrange(h), rnd.choice((0, 2, 2)))
    c.grad(0, 110, w, 60, 1, 2, 0.0, 0.7)
    for y in range(170, h):
        for x in range(w):
            c.pset(x, y, 2)
    c.grad(0, 170, w, h - 170, 2, 8, 0.0, 0.6)
    c.rect(0, 0, w, 8, 0)
    x = 0
    while x < w:                                    # 鍾乳石のシルエット
        wd = rnd.randint(4, 10)
        ln = rnd.randint(10, 40)
        c.tri(x, 0, x + wd, 0, x + wd / 2, ln, 0)
        c.line(x, 0, x + wd / 2, ln, 1)
        x += rnd.randint(8, 26)
    return c


def gen_magma_far():
    """遠くの溶岩の滝と溶岩湖"""
    lights = LIGHTS["magma_far"] = []
    w, h = SPEC["magma_far"]
    c = Canvas(w, h, KEY, wrap=True)
    for x in range(w):
        top = int(10 + 8 * math.sin(x / 20) + 4 * math.sin(x / 7))
        for y in range(top, h):
            c.pset(x, y, 1 if BAYER[y % 4][x % 4] < 9 else 0)
    for fx in (40, 120, 200):
        for y in range(18, h - 20):
            c.pset(fx, y, 8)
            c.pset(fx + 1, y, 9)
            c.pset(fx + 2, y, 10)
            c.pset(fx + 3, y, 9)
            c.pset(fx + 4, y, 8)
            if y % 9 == 0:
                lights.append((fx + 2, y, 10))
    c.rect(0, h - 20, w, 20, 8)
    for x in range(w):
        c.pset(x, h - 20, 10 if x % 3 else 9)
    c.shade(0, h - 18, w, 18, 2, 0.1, 0.8, only=(8,))
    for x in range(4, w, 23):
        lights.append((x, h - 20, 10))
    return c


def gen_magma_mid():
    """光る割れ目の入った岩の柱"""
    lights = LIGHTS["magma_mid"] = []
    w, h = SPEC["magma_mid"]
    c = Canvas(w, h, KEY, wrap=True)
    rnd = random.Random(141)
    gy = h - 8
    c.rect(0, gy, w, 8, 1)
    for cx, ww in ((24, 14), (90, 18), (160, 12), (220, 16)):
        for y in range(6, gy):
            half = ww // 2 + int(2 * math.sin(y * 0.15 + cx))
            for x in range(cx - half, cx + half + 1):
                c.pset(x, y, 1 if x > cx + half // 3 else 2)
        x, y = cx, 10
        while y < gy - 4:                           # 割れ目
            nx, ny = x + rnd.randint(-3, 3), y + rnd.randint(5, 9)
            c.line(x, y, nx, ny, 8)
            lights.append((nx, ny, 9))
            x, y = nx, ny
    return c


def gen_magma_near():
    """石筍のシルエット"""
    w, h = SPEC["magma_near"]
    c = Canvas(w, h, KEY, wrap=True)
    gy = h - 12
    c.rect(0, gy, w, 12, 0)
    for cx, hh, ww in ((20, 40, 9), (34, 22, 6), (100, 52, 10), (150, 30, 7), (200, 46, 9), (238, 20, 6)):
        c.tri(cx - ww, gy, cx, gy - hh, cx + ww, gy, 0)
        c.line(cx - ww, gy, cx, gy - hh, 2)
    for x in range(w):
        if x % 5 == 0:
            c.pset(x, gy, 2)
    return c


def gen_magma_front():
    w, h = SPEC["magma_front"]
    c = Canvas(w, h, KEY, wrap=True)
    rnd = random.Random(151)
    for cx, r in ((20, 11), (110, 8), (190, 12)):
        for y in range(h - r, h):
            for x in range(cx - r - 2, cx + r + 3):
                if (x - cx) ** 2 + ((y - h) * 1.3) ** 2 < r * r + rnd.randint(-4, 6):
                    c.pset(x, y, 0)
        c.line(cx - r, h - 2, cx - r // 2, h - r + 1, 2)
    return c


def gen_fort_sky():
    """氷の要塞の夜空：紫のオーロラ、小さな月、サーチライト"""
    w, h = SPEC["fort_sky"]
    c = Canvas(w, h, 0)
    c.grad(0, 30, w, 90, 0, 1, 0.0, 1.0)
    for y in range(120, h):
        for x in range(w):
            c.pset(x, y, 1)
    c.grad(0, 140, w, h - 140, 1, 2, 0.0, 0.6)
    rnd = random.Random(161)
    for _ in range(110):
        x, y = rnd.randrange(w), rnd.randrange(120)
        if c.get(x, y) in (0, 1):
            c.pset(x, y, rnd.choice((13, 6, 7, 5)))
    _aurora(c, (8, 2), 20, 8, 2.0)
    mx, my, mr = 56, 40, 10
    for y in range(my - mr, my + mr + 1):
        for x in range(mx - mr, mx + mr + 1):
            if (x - mx) ** 2 + (y - my) ** 2 <= mr * mr:
                c.pset(x, y, 6 if BAYER[y % 4][x % 4] < (x - mx + 4) * 1.5 else 7)
    for x0, x1, y1 in ((90, 40, 30), (180, 232, 24)):      # サーチライトの光
        for i in range(-3, 4):
            for k in range(100):
                t = k / 99
                x = x0 + (x1 - x0) * t + i
                y = h + (y1 - h) * t
                if c.get(x, y) in (0, 1, 2) and BAYER[int(y) % 4][int(x) % 4] < 4:
                    c.pset(x, y, 5)
    return c


def gen_fort_far():
    """遠くの要塞のシルエット"""
    lights = LIGHTS["fort_far"] = []
    w, h = SPEC["fort_far"]
    c = Canvas(w, h, KEY, wrap=True)
    c.rect(0, h - 24, w, 24, 1)
    for bx, bw, bh in ((20, 14, 60), (60, 30, 40), (110, 12, 80), (150, 40, 50), (210, 18, 70)):
        c.rect(bx, h - bh, bw, bh, 1)
        for x in range(bx, bx + bw, 4):
            c.rect(x, h - bh - 3, 2, 3, 1)
        c.line(bx, h - bh, bx + bw - 1, h - bh, 6)
        for y in range(h - bh + 8, h - 26, 10):
            for x in range(bx + 3, bx + bw - 2, 6):
                if (x + y) % 3 == 0:
                    c.pset(x, y, 10)
                    lights.append((x, y, 10))
    c.line(116, h - 80, 116, h - 96, 1)
    lights.append((116, h - 97, 8))
    return c


def gen_fort_mid():
    """雪の積もった城壁"""
    lights = LIGHTS["fort_mid"] = []
    w, h = SPEC["fort_mid"]
    c = Canvas(w, h, KEY, wrap=True)
    c.rect(0, 30, w, h - 30, 5)
    for y in range(30, h, 8):                       # レンガ
        c.line(0, y, w - 1, y, 1)
        for x in range((y // 8 % 2) * 8, w, 16):
            c.line(x, y, x, y + 7, 1)
    for x in range(0, w, 12):                       # 胸壁
        c.rect(x, 22, 7, 8, 5)
        c.line(x, 22, x + 6, 22, 7)
    c.line(0, 30, w - 1, 30, 6)
    for x in range(10, w, 40):                      # 窓
        c.rect(x, 50, 4, 8, 0)
        if (x // 40) % 2:
            c.rect(x + 1, 51, 2, 6, 10)
            lights.append((x + 1, 53, 10))
    for bx in (60, 190):                            # 垂れ幕
        c.rect(bx, 34, 10, 26, 2)
        c.rect(bx + 2, 36, 6, 20, 8)
        c.tri(bx, 60, bx + 10, 60, bx + 5, 66, 2)
    return c


def gen_fort_near():
    """柵と戦車止め"""
    w, h = SPEC["fort_near"]
    c = Canvas(w, h, KEY, wrap=True)
    gy = h - 10
    c.rect(0, gy, w, 10, 13)
    c.line(0, gy, w - 1, gy, 6)
    for x in range(0, w, 20):
        c.rect(x, gy - 22, 2, 22, 0)
    for y in (gy - 18, gy - 10):
        for x in range(w):
            c.pset(x, y + int(math.sin(x / 3) * 1.2), 0)
    for tx in (50, 160):                            # 戦車止め
        c.line(tx - 6, gy, tx + 6, gy - 12, 0)
        c.line(tx + 6, gy, tx - 6, gy - 12, 0)
        c.line(tx - 6, gy - 12, tx + 6, gy - 12, 6)
    return c


def gen_fort_front():
    w, h = SPEC["fort_front"]
    c = Canvas(w, h, KEY, wrap=True)
    rnd = random.Random(171)
    for cx, r in ((30, 11), (140, 13), (220, 9)):
        for y in range(h - r, h):
            for x in range(cx - r - 2, cx + r + 3):
                if (x - cx) ** 2 + ((y - h) * 1.4) ** 2 < r * r + rnd.randint(-3, 4):
                    c.pset(x, y, 7 if y < h - r + 3 else 6)
    for x in range(70, 110):
        c.pset(x, h - 14 + int(math.sin(x / 2.5) * 2), 0)
    c.rect(70, h - 18, 2, 18, 0)
    c.rect(108, h - 18, 2, 18, 0)
    return c


GENERATORS = {
    "hero": gen_hero, "tiles": gen_tiles, "sky": gen_sky,
    "far": gen_far, "mid": gen_mid, "near": gen_near, "front": gen_front,
    "marsh_sky": gen_marsh_sky, "marsh_far": gen_marsh_far, "marsh_mid": gen_marsh_mid,
    "marsh_near": gen_marsh_near, "marsh_front": gen_marsh_front,
    "tower_sky": gen_tower_sky, "tower_far": gen_tower_far, "tower_mid": gen_tower_mid,
    "tower_near": gen_tower_near, "tower_front": gen_tower_front,
    "ship_sky": gen_ship_sky, "ship_far": gen_ship_far, "ship_mid": gen_ship_mid,
    "ship_near": gen_ship_near, "ship_front": gen_ship_front,
    "ice_sky": gen_ice_sky, "ice_far": gen_ice_far, "ice_mid": gen_ice_mid,
    "ice_near": gen_ice_near, "ice_front": gen_ice_front,
    "magma_sky": gen_magma_sky, "magma_far": gen_magma_far, "magma_mid": gen_magma_mid,
    "magma_near": gen_magma_near, "magma_front": gen_magma_front,
    "fort_sky": gen_fort_sky, "fort_far": gen_fort_far, "fort_mid": gen_fort_mid,
    "fort_near": gen_fort_near, "fort_front": gen_fort_front,
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
