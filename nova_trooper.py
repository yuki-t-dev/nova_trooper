# -*- coding: utf-8 -*-
"""
NOVA TROOPER  (Step 2)
SF × スペランカー × 魔界村 風アクション  for Pyxel 2.x

■ ファイル構成
  nova_trooper.py   … 本体（これを実行）
  nova_assets.py    … 内蔵ドット絵の生成 / PNG 書き出し
  assets/*.png      … 置いてあれば優先して使う（無ければ内蔵ドット絵）
  umplus_j10r.bdf   … 置いてあれば日本語表示

■ 操作            キーボード        ゲームパッド
  移動             ← → ↑ ↓          十字キー / 左スティック
  ジャンプ         Z                 A
  攻撃             X                 B / X   （マシンガンは押しっぱなしで連射）
  上撃ち           ↑ + X             上 + B   （歩きながらでもOK。はしごの前では昇る）
  下撃ち           空中で ↓ + X      空中で下 + B
  ※ マシンガンは向きを変えると、銃口が回りながら斜めにも弾をばらまく
  決定             Z / Enter         A / START
  ポーズ           Enter / P         START
  グラフィック再読込 F5
  BGM オン/オフ    M                 BACK

■ ルール
  ・パワースーツ → スーツ → インナー → やられ（3段階）
  ・高いところから落ちるとダメージ、電流床に触れるとダメージ
  ・補給コンテナを壊すと武器(H/G/P/L)・スーツ・エネルギーセルが出る
  ・ドラム缶は撃つと爆発して周りの敵を巻き込む（連鎖する）
  ・ボスを倒すと隔壁ゲートが開く
  ・持ち越し：クリアすると武器とスーツを次のステージへ持ち越す（インナーはスーツに直す）
              やられると武器はブラスター、スーツは標準に戻る
              （KEEP_WEAPON_ON_DEATH = True で、やられても武器を残せる）

■ グラフィックの差し替え（assets/ に PNG を置く。F5 で即反映）
  python nova_assets.py で内蔵グラフィックを assets/ に書き出せます（要 Pillow）
     hero.png   224x48   自キャラ 16x16 × 14コマ × 3段（右向き・足元を最下行に）
                列: idle walk1 walk2 jump crouch shoot climb1 climb2 hurt up up1 up2 diag down
                （144x48 の旧形式でも可。足りないコマは内蔵の絵で補う）
     tiles.png  128x32   地形タイル 8x8（配置は nova_assets.gen_tiles 参照）
     sky.png    256x208  空（スクロールしない）
     far.png    256x112  遠景  0.08倍スクロール
     mid.png    256x96   中景  0.25倍
     near.png   256x80   近景  0.5倍
     front.png  256x32   最前面 1.3倍（キャラより手前に描く）
  背景レイヤーの横幅は自由（横方向にループ）。透明色はピンク #FF9798（14番）

■ ステージ追加
  build_stageN() を書いて STAGES に追加し、WORLD_NODES の "stage" に番号を入れる
  地形: # 岩盤  = 金属  K コンテナ  - 足場  H はしご  | ケーブル  ^ 電流床
  配置: P 開始  Z 生体兵  B ドローン  U 砲台  C 補給  O ドラム缶  X 残骸
        * セル  F ビーコン  D ボス  G ゲート
"""
import math
import os
import random

import pyxel

import nova_assets as NA

# ============================================================
# 定数
# ============================================================
W, H = 256, 224
TS = 8
HUD_H = 16
VIEW_H = H - HUD_H
KEY = 14
FONT_FILE = "umplus_j10r.bdf"
ASSET_DIR = "assets"

GRAV = 0.30
MAX_FALL = 4.0
JUMP_V = -4.3
WALK_SPEED = 1.3
CLIMB_SPEED = 1.0
FALL_DAMAGE_PX = 68
JUMP_FIXED = False

# 持ち越しルール
KEEP_WEAPON_ON_DEATH = False   # True: やられても武器を持ったまま復活

# BGM（pyxel.musics の番号）。チャンネル 0,1 = BGM / 2,3 = 効果音
BGM_MAP, BGM_STAGE, BGM_BOSS = 0, 1, 2

# 撃ち心地の調整値
AIM_SWEEP_STEP = 30.0     # マシンガンの銃口が1フレームで回る角度（度）。3フレームで真上
FIRE_BUFFER = 8           # 撃てない間に押した攻撃を覚えておくフレーム数
DOWN_SHOT_HOVER = 0.8     # 空中で下撃ちしたときの落下速度の上限（反動でふわっと浮く）
DOWN_SHOT_HOVER_T = 10    # 下撃ち1発あたり、ふわっと浮く効果が続くフレーム数

SOLID = set("#=K")
ONEWAY = set("-")
LADDER = set("H|")
SPIKE = "^"
ENTITY_CHARS = set("PZBDC*FGOXU")

SPR = 16
SPR_FRAMES = NA.HERO_FRAMES
SPR_ROW = {3: 0, 2: 1, 1: 2}

FONT = None


# ============================================================
# テキスト
# ============================================================
def L(ja, en):
    return ja if FONT else en


def _raw_text(x, y, s, col):
    if FONT:
        pyxel.text(x, y, s, col, FONT)
    else:
        pyxel.text(x, y + 2, s, col)


def txt(x, y, s, col, shadow=None):
    if shadow is not None:
        _raw_text(x + 1, y + 1, s, shadow)
    _raw_text(x, y, s, col)


def text_w(s):
    return FONT.text_width(s) if FONT else len(s) * 4


def ctxt(cx, y, s, col, shadow=None):
    txt(int(cx - text_w(s) / 2), y, s, col, shadow)


# ============================================================
# 当たり判定・移動
# ============================================================
def clamp(v, a, b):
    return a if v < a else b if v > b else v


def overlap(a, b):
    return (a.x < b.x + b.w and b.x < a.x + a.w and
            a.y < b.y + b.h and b.y < a.y + a.h)


def collide_solid(st, x, y, w, h):
    x0 = int(math.floor(x / TS))
    x1 = int((math.ceil(x + w) - 1) // TS)
    y0 = int(math.floor(y / TS))
    y1 = int((math.ceil(y + h) - 1) // TS)
    for ty in range(y0, y1 + 1):
        for tx in range(x0, x1 + 1):
            if st.get(tx, ty) in SOLID:
                return True
    return False


def move_x(st, o, dx):
    o.x += dx
    if collide_solid(st, o.x, o.y, o.w, o.h):
        if dx > 0:
            o.x = math.floor((o.x + o.w) / TS) * TS - o.w
        elif dx < 0:
            o.x = (math.floor(o.x / TS) + 1) * TS
        return True
    return False


def move_y(st, o, dy):
    o.on_ground = False
    old_bottom = o.y + o.h
    o.y += dy
    if dy > 0:
        if collide_solid(st, o.x, o.y, o.w, o.h):
            o.y = math.floor((o.y + o.h) / TS) * TS - o.h
            o.vy = 0
            o.on_ground = True
            return
        if getattr(o, "can_oneway", True):
            bottom = o.y + o.h
            ty = int(math.floor((bottom - 0.01) / TS))
            top = ty * TS
            if old_bottom <= top + 0.01 <= bottom + 0.01:
                x0 = int(math.floor(o.x / TS))
                x1 = int((math.ceil(o.x + o.w) - 1) // TS)
                for tx in range(x0, x1 + 1):
                    if st.is_platform_top(tx, ty):
                        o.y = top - o.h
                        o.vy = 0
                        o.on_ground = True
                        return
    elif dy < 0:
        if collide_solid(st, o.x, o.y, o.w, o.h):
            o.y = (math.floor(o.y / TS) + 1) * TS
            o.vy = 0


# ============================================================
# ステージ定義
# ============================================================
class Builder:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.g = [["."] * w for _ in range(h)]

    def fill(self, x0, y0, x1, y1, c):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if 0 <= x < self.w and 0 <= y < self.h:
                    self.g[y][x] = c

    def put(self, x, y, c):
        self.fill(x, y, x, y, c)

    def rows(self):
        return ["".join(r) for r in self.g]


def build_stage1():
    """1-1 墜落地点"""
    MW, MH, G = 208, 26, 23
    b = Builder(MW, MH)
    b.fill(0, G, MW - 1, MH - 1, "#")
    for x0 in (38, 88, 150):                     # 落とし穴
        b.fill(x0, G, x0 + 2, MH - 1, ".")
    b.fill(37, G - 3, 41, G - 3, "-")
    # 墜落した輸送船の残骸
    b.fill(15, G - 2, 21, G - 1, "=")
    b.fill(16, G - 3, 20, G - 3, "=")
    b.fill(17, G - 4, 19, G - 4, "=")
    # コンテナ（壊れない障害物）
    for x, hh in ((31, 1), (47, 2), (53, 1), (84, 1), (160, 2), (166, 1), (179, 1)):
        b.fill(x, G - hh, x, G - 1, "K")
    # 岩の丘
    b.fill(58, G - 2, 59, G - 1, "#")
    b.fill(60, G - 4, 80, G - 1, "#")
    b.fill(81, G - 2, 82, G - 1, "#")
    b.fill(66, G - 7, 71, G - 7, "-")
    # 施設（上段ルート / 下段ルート）
    b.fill(100, 13, 136, 13, "=")
    b.fill(102, 13, 102, G - 1, "H")
    b.fill(137, 13, 137, 20, "|")
    b.fill(117, 10, 123, 10, "-")
    b.fill(116, G - 1, 118, G - 1, "^")
    b.fill(126, G - 1, 127, G - 1, "^")
    # ボスエリア
    b.fill(170, G - 3, 175, G - 3, "-")
    b.fill(185, G - 3, 190, G - 3, "-")
    b.fill(MW - 1, 0, MW - 1, G - 1, "=")

    b.put(3, G - 1, "P")
    for x, y in ((26, G - 1), (63, G - 5), (68, G - 8), (110, 12), (130, 12), (145, G - 1)):
        b.put(x, y, "C")
    for x, y in ((8, G - 3), (39, G - 5), (92, G - 4), (120, 9), (172, G - 5)):
        b.put(x, y, "*")
    for x, y in ((34, G - 1), (75, G - 5), (86, G - 1), (110, G - 1), (122, G - 1), (133, G - 1)):
        b.put(x, y, "Z")
    for x, y in ((50, 8), (75, 9), (112, 4), (126, 4), (158, 8)):
        b.put(x, y, "B")
    for x, y in ((36, G - 1), (44, G - 1), (57, G - 1), (107, G - 1), (124, G - 1), (156, G - 1)):
        b.put(x, y, "O")
    for x, y in ((11, G - 1), (55, G - 1), (142, G - 1)):
        b.put(x, y, "X")
    for x, y in ((78, G - 5), (134, 12)):
        b.put(x, y, "U")
    b.put(94, G - 1, "F")
    b.put(186, 11, "D")
    b.put(200, G - 1, "G")
    return b.rows()


STAGES = [
    dict(
        name=("1-1 墜落地点", "1-1 CRASH SITE"),
        build=build_stage1,
        spawn_zones=[(4, 36), (42, 87), (92, 99), (104, 135), (154, 168)],
        smoke=[(18, 19), (61, 19), (141, 22), (177, 21)],   # 煙が上がる場所（タイル座標）
    ),
]

WORLD_NODES = {
    "base": dict(x=40, y=164, name=("降下艇", "DROPSHIP"), kind="home", stage=None),
    "1-1":  dict(x=92, y=128, name=("1-1 墜落地点", "1-1 CRASH SITE"), kind="stage", stage=0),
    "1-2":  dict(x=150, y=158, name=("1-2 酸の湿地", "1-2 ACID MARSH"), kind="stage", stage=None),
    "1-3":  dict(x=182, y=104, name=("1-3 中継塔", "1-3 RELAY TOWER"), kind="stage", stage=None),
    "ship": dict(x=222, y=58, name=("敵母艦", "MOTHERSHIP"), kind="castle", stage=None),
}
WORLD_EDGES = [("base", "1-1"), ("1-1", "1-2"), ("1-2", "1-3"), ("1-3", "ship")]


class Stage:
    def __init__(self, sdef):
        rows = sdef["build"]() if "build" in sdef else sdef["map"]
        self.w = max(len(r) for r in rows)
        self.h = len(rows)
        self.tiles = [list(r.ljust(self.w, ".")) for r in rows]
        self.entities = []
        for ty, row in enumerate(self.tiles):
            for tx, c in enumerate(row):
                if c in ENTITY_CHARS:
                    self.entities.append((c, tx, ty))
                    row[tx] = "."
        self.img = None
        self.anim_tiles = []

    def get(self, tx, ty):
        if tx < 0 or tx >= self.w:
            return "#"
        if ty < 0 or ty >= self.h:
            return "."
        return self.tiles[ty][tx]

    def tile_at(self, px, py):
        return self.get(int(math.floor(px / TS)), int(math.floor(py / TS)))

    def solid(self, px, py):
        return self.tile_at(px, py) in SOLID

    def is_platform_top(self, tx, ty):
        c = self.get(tx, ty)
        if c in ONEWAY:
            return True
        if c in LADDER:
            above = self.get(tx, ty - 1)
            return above not in LADDER and above not in SOLID
        return False

    # ---- 描画用：オートタイル ----
    def tile_layers(self, tx, ty, c):
        if c in "#=":
            row = 0 if c == "#" else 8
            hsh = (tx * 73856093 ^ ty * 19349663) & 0xFFFF
            if c == "#":
                var = 3 if hsh % 11 == 0 else hsh % 3
            else:
                var = 0 if hsh % 10 < 7 else 1 + hsh % 3
            layers = [(var * 8, row)]

            def exposed(dx, dy):
                return self.get(tx + dx, ty + dy) not in SOLID
            if exposed(0, -1):
                layers.append((32, row))
            if exposed(-1, 0):
                layers.append((40, row))
            if exposed(1, 0):
                layers.append((48, row))
            if exposed(0, 1):
                layers.append((56, row))
            return layers
        return [{"K": (0, 16), "-": (8, 16), "H": (16, 16), "|": (24, 16)}[c]]

    def render(self, tiles_img):
        """動かない地形を1枚の画像に焼き込む（毎フレームは blt 1回で済む）"""
        img = pyxel.Image(self.w * TS, self.h * TS)
        img.cls(KEY)
        self.anim_tiles = []
        for ty in range(self.h):
            for tx in range(self.w):
                c = self.tiles[ty][tx]
                if c == ".":
                    continue
                if c == SPIKE:
                    self.anim_tiles.append((tx, ty))
                    continue
                for u, v in self.tile_layers(tx, ty, c):
                    img.blt(tx * TS, ty * TS, tiles_img, u, v, TS, TS, KEY)
        self.img = img


# ============================================================
# グラフィック読み込み（PNG があれば PNG、無ければ内蔵ドット絵）
# ============================================================
def _palette():
    try:
        return list(pyxel.colors.to_list())[:16]
    except Exception:
        try:
            return list(pyxel.colors)[:16]
        except Exception:
            return list(NA.PAL)


def canvas_to_image(cv):
    img = pyxel.Image(cv.w, cv.h)
    img.cls(KEY)
    d, w = cv.d, cv.w
    for y in range(cv.h):
        base = y * w
        for x in range(w):
            c = d[base + x]
            if c != KEY:
                img.pset(x, y, c)
    return img


def png_to_image(path, size):
    try:
        from PIL import Image as PILImage
    except ImportError:
        img = pyxel.Image(*size)
        img.cls(KEY)
        img.load(0, 0, path)
        return img
    pal = [((c >> 16) & 255, (c >> 8) & 255, c & 255) for c in _palette()]
    im = PILImage.open(path).convert("RGBA")
    img = pyxel.Image(im.width, im.height)
    img.cls(KEY)
    cache = {}
    data = list(im.getdata())
    for i, (r, g, b, a) in enumerate(data):
        if a < 128:
            continue
        col = cache.get((r, g, b))
        if col is None:
            col = min(range(len(pal)), key=lambda k: (pal[k][0] - r) ** 2 +
                      (pal[k][1] - g) ** 2 + (pal[k][2] - b) ** 2)
            cache[(r, g, b)] = col
        if col != KEY:
            img.pset(i % im.width, i // im.width, col)
    return img


class Assets:
    NAMES = ["hero", "tiles", "sky", "far", "mid", "near", "front"]

    def __init__(self):
        self.load()

    def load(self):
        here = os.path.dirname(os.path.abspath(__file__))
        self.src = {}
        for name in self.NAMES:
            path = os.path.join(here, ASSET_DIR, name + ".png")
            img = None
            if os.path.exists(path):
                try:
                    img = png_to_image(path, NA.SPEC[name])
                    self.src[name] = "png"
                except Exception as ex:
                    print("asset load failed:", path, ex)
            if img is None:
                img = canvas_to_image(NA.GENERATORS[name]())
                self.src[name] = "built-in"
            elif name == "hero" and img.width < NA.SPEC["hero"][0]:
                # 旧形式（コマ数が少ない）PNG：足りないコマを内蔵の絵で補う
                base = canvas_to_image(NA.gen_hero())
                base.blt(0, 0, img, 0, 0, img.width, min(img.height, base.height))
                img = base
            setattr(self, name, img)
        self.mid_lights = list(NA.MID_LIGHTS) if self.src["mid"] == "built-in" else []
        self.far_lights = list(NA.FAR_LIGHTS) if self.src["far"] == "built-in" else []

    def png_count(self):
        return sum(1 for v in self.src.values() if v == "png")


def draw_hero(A, x, y, h, facing, hp, frame="idle"):
    """当たり判定(幅8, 高さh)の足元・中心に 16x16 のスプライトを合わせて描く"""
    u = SPR_FRAMES.index(frame) * SPR
    v = SPR_ROW.get(max(1, min(3, hp)), 1) * SPR
    pyxel.blt(int(x) + 4 - SPR // 2, int(y + h) - SPR, A.hero, u, v,
              SPR if facing > 0 else -SPR, SPR, KEY)


def hero_frame(anim, on_ground=True, walking=False, crouch=False, climb=False,
               shoot=False, hurt=False, aim=0.0):
    if climb:
        return "climb1" if (int(anim) // 6) % 2 == 0 else "climb2"
    if hurt:
        return "hurt"
    if crouch:
        return "crouch"
    if aim <= -67:
        if walking and on_ground:
            return ("up1", "up", "up2", "up")[(int(anim) // 6) % 4]
        return "up"
    if aim <= -22:
        return "diag"
    if aim >= 45 and not on_ground:
        return "down"
    if shoot:
        return "shoot"
    if not on_ground:
        return "jump"
    if walking:
        return ("walk1", "idle", "walk2", "idle")[(int(anim) // 6) % 4]
    return "idle"


# ============================================================
# 入力（キーボード + ゲームパッド + アナログスティック）
# ============================================================
class Input:
    STICK_DEAD = 12000

    def __init__(self):
        P = pyxel
        self.binds = {
            "left":   [P.KEY_LEFT, P.GAMEPAD1_BUTTON_DPAD_LEFT],
            "right":  [P.KEY_RIGHT, P.GAMEPAD1_BUTTON_DPAD_RIGHT],
            "up":     [P.KEY_UP, P.GAMEPAD1_BUTTON_DPAD_UP],
            "down":   [P.KEY_DOWN, P.GAMEPAD1_BUTTON_DPAD_DOWN],
            "jump":   [P.KEY_Z, P.GAMEPAD1_BUTTON_A],
            "fire":   [P.KEY_X, P.GAMEPAD1_BUTTON_B, P.GAMEPAD1_BUTTON_X],
            "ok":     [P.KEY_Z, P.KEY_RETURN, P.GAMEPAD1_BUTTON_A, P.GAMEPAD1_BUTTON_START],
            "pause":  [P.KEY_RETURN, P.KEY_P, P.GAMEPAD1_BUTTON_START],
            "reload": [P.KEY_F5],
            "quit":   [P.KEY_Q],
            "music":  [P.KEY_M, P.GAMEPAD1_BUTTON_BACK],
        }
        self.stick = {
            "left":  (P.GAMEPAD1_AXIS_LEFTX, -1),
            "right": (P.GAMEPAD1_AXIS_LEFTX, 1),
            "up":    (P.GAMEPAD1_AXIS_LEFTY, -1),
            "down":  (P.GAMEPAD1_AXIS_LEFTY, 1),
        }
        self.cur = {k: False for k in self.binds}
        self.prev = dict(self.cur)

    def _axis(self, name):
        if name not in self.stick:
            return False
        axis, sign = self.stick[name]
        try:
            return pyxel.btnv(axis) * sign > self.STICK_DEAD
        except Exception:
            return False

    def update(self):
        self.prev = self.cur
        self.cur = {name: any(pyxel.btn(k) for k in keys) or self._axis(name)
                    for name, keys in self.binds.items()}

    def held(self, name):
        return self.cur[name]

    def pressed(self, name):
        return self.cur[name] and not self.prev[name]


# ============================================================
# 武器・アイテム
# ============================================================
WEAPONS = {
    "blaster": dict(name=("ブラスター", "BLASTER"), letter="", max=4, cd=7, auto=False),
    "heavy":   dict(name=("マシンガン", "HEAVY MG"), letter="H", max=8, cd=4, auto=True),
    "grenade": dict(name=("グレネード", "GRENADE"), letter="G", max=2, cd=22, auto=False),
    "plasma":  dict(name=("プラズマ", "PLASMA"), letter="P", max=2, cd=18, auto=False),
    "laser":   dict(name=("レーザー", "LASER"), letter="L", max=2, cd=14, auto=False),
}
PICKUP_WEAPONS = ["heavy", "grenade", "plasma", "laser"]
ITEM_MSG = {
    "repair": ("スーツを修復した！", "SUIT REPAIRED!"),
    "power":  ("パワースーツ！ 武器が強化された", "POWER SUIT! WEAPONS UP"),
    "cell":   ("エネルギーセル +500", "ENERGY CELL +500"),
}


def draw_item(kind, x, y, t):
    x, y = int(x), int(y)
    if kind == "cell":
        on = (t // 8) % 2
        pyxel.rect(x + 1, y, 6, 8, 0)
        pyxel.rect(x + 2, y + 1, 4, 6, 12 if on else 6)
        pyxel.rect(x + 3, y + 2, 2, 4, 7 if on else 12)
        pyxel.rect(x + 3, y - 1, 2, 1, 13)
        return
    if kind == "blaster":
        pyxel.rect(x + 1, y + 3, 6, 2, 13)
        pyxel.rect(x + 1, y + 5, 2, 2, 5)
        pyxel.pset(x + 7, y + 3, 12)
        return
    border = 10 if (t // 6) % 2 else 9
    if kind == "repair":
        letter, col, border = "+", 11, 11
    elif kind == "power":
        letter, col = "S", 10
    else:
        letter, col = WEAPONS[kind]["letter"], 7
    pyxel.rect(x - 1, y - 1, 10, 10, 0)
    pyxel.rect(x, y, 8, 8, 1)
    pyxel.rectb(x, y, 8, 8, border)
    pyxel.text(x + 3 - (1 if letter in "HGPLS" else 0), y + 2, letter, col)


class Shot:
    def __init__(self, kind, x, y, vx, vy, w, h, dmg, pierce=False, grav=0.0):
        self.kind, self.x, self.y, self.vx, self.vy = kind, x, y, vx, vy
        self.w, self.h, self.dmg, self.pierce, self.grav = w, h, dmg, pierce, grav
        self.alive = True
        self.t = 0
        self.hit = {}
        self.face = 1 if vx >= 0 else -1
        self.dx, self.dy, self.L = float(self.face), 0.0, w   # ビーム系の向きと長さ


class EnemyShot:
    kind = "bullet"
    grav = 0.0

    def __init__(self, x, y, vx, vy):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.w = self.h = 6
        self.alive = True
        self.t = 0


class Bomb(EnemyShot):
    """ボスが落とす爆弾。撃ち落とせる。地面に落ちると爆発する"""
    kind = "bomb"
    grav = 0.08

    def __init__(self, x, y, vx):
        super().__init__(x - 3, y, vx, 0.3)


class Item:
    def __init__(self, kind, x, y, static=False):
        self.kind, self.x, self.y = kind, x, y
        self.w = self.h = 8
        self.vx = 0
        self.vy = 0 if static else -2.2
        self.static = static
        self.alive = True
        self.on_ground = False
        self.can_oneway = True
        self.t = 0


# ============================================================
# プレイヤー
# ============================================================
class Player:
    H_STAND = 14
    H_CROUCH = 9

    def __init__(self, x, y):
        self.x, self.y = x, y
        self.w, self.h = 8, self.H_STAND
        self.vx = self.vy = 0.0
        self.facing = 1
        self.on_ground = False
        self.climbing = False
        self.crouch = False
        self.hurt = False
        self.dead = False
        self.dead_t = 0
        self.hp = 2
        self.weapon = "blaster"
        self.invinc = 0
        self.shoot_cd = 0
        self.throw_t = 0
        self.anim = 0.0
        self.air_top = y
        self.jump_vx = 0.0
        self.aim = 0.0            # 銃の向き（度）: 0=前, -90=真上, +90=真下
        self.aim_target = 0.0
        self.fire_buf = 0
        self.hover_t = 0
        self.can_oneway = True

    def set_crouch(self, st, flag):
        if flag and not self.crouch:
            self.crouch = True
            self.y += self.H_STAND - self.H_CROUCH
            self.h = self.H_CROUCH
        elif not flag and self.crouch:
            ny = self.y - (self.H_STAND - self.H_CROUCH)
            if not collide_solid(st, self.x, ny, self.w, self.H_STAND):
                self.crouch = False
                self.y = ny
                self.h = self.H_STAND

    def gun_tip(self):
        """銃口の位置（いま表示しているコマの銃の先端）"""
        f, cx, base = self.facing, self.x + 4, self.y + self.h
        if self.crouch:
            return (cx + f * 8, base - 5)
        if self.aim <= -67:
            return (cx + f * 4.5, base - 16)
        if self.aim <= -22:
            return (cx + f * 8, base - 13)
        if self.aim >= 45 and not self.on_ground:
            return (cx + f * 4.5, base)
        return (cx + f * 8, base - 7)

    def aim_dir(self):
        a = math.radians(self.aim)
        return math.cos(a) * self.facing, math.sin(a)


# ============================================================
# 敵・壊せるオブジェクト
# ============================================================
class Enemy:
    score = 100
    harmful = True
    hittable = True
    boss = False
    prop = False          # 壊せるオブジェクト（体当たりダメージなし）

    def __init__(self, x, y, w, h, hp):
        self.x, self.y, self.w, self.h, self.hp = x, y, w, h, hp
        self.vx = self.vy = 0.0
        self.alive = True
        self.active = False
        self.flash = 0
        self.t = 0
        self.on_ground = False
        self.can_oneway = True

    def cx(self):
        return self.x + self.w / 2

    def cy(self):
        return self.y + self.h / 2

    def far_from_camera(self, g, margin=64):
        return self.x < g.cam_x - margin or self.x > g.cam_x + W + margin

    def update(self, g):
        self.t += 1

    def draw(self, g):
        pass

    def on_death(self, g):
        g.boom(self.cx(), self.cy(), 8, debris=6)


class Mutant(Enemy):
    """生体兵：ワープで現れて歩いてくる"""
    score = 100

    def __init__(self, x, y):
        super().__init__(x, y, 8, 14, 1)
        self.state = "warp"
        self.wt = 0
        self.dir = None

    @property
    def hittable(self):
        return self.state != "warp" or self.wt > 24

    @property
    def harmful(self):
        return self.state != "warp" or self.wt > 24

    def update(self, g):
        self.t += 1
        if self.dir is None:
            self.dir = 1 if g.p.x > self.x else -1
        if self.state == "warp":
            self.wt += 1
            if self.wt == 1:
                sfx(13, 3)
            if self.wt >= 36:
                self.state = "walk"
            return
        self.vx = 0.5 * self.dir
        self.vy = min(self.vy + GRAV, MAX_FALL)
        if move_x(g.stage, self, self.vx):
            self.dir *= -1
        move_y(g.stage, self, self.vy)
        if self.y > g.stage.h * TS or self.far_from_camera(g):
            self.alive = False

    def draw(self, g):
        x, y = int(self.x), int(self.y)
        d = self.dir or 1
        if self.state == "warp":
            k = self.wt / 36
            bw = max(1, int(12 * (1 - k)))
            top = y - 60
            pyxel.rect(x + 4 - bw // 2, top, bw, y + 14 - top, 12)
            pyxel.rect(x + 4 - max(1, bw // 3) // 2, top, max(1, bw // 3), y + 14 - top, 7)
            pyxel.elli(x - 3, y + 12, 14, 4, 6)
            if self.wt < 12 or (self.wt // 2) % 2:
                return
        body = 7 if self.flash else 11
        f = (self.t // 8) % 2
        pyxel.rect(x, y - 1, 8, 7, 0)
        pyxel.rect(x + 1, y, 6, 5, body)
        pyxel.rect(x + (4 if d > 0 else 1), y + 1, 3, 2, 8)
        pyxel.pset(x + (6 if d > 0 else 1), y + 1, 10)
        pyxel.rect(x, y + 5, 8, 5, 3)
        pyxel.rect(x + 1, y + 6, 6, 1, 1)
        pyxel.rect(x + (6 if d > 0 else -2), y + 6, 4, 2, body)
        pyxel.pset(x + (9 if d > 0 else -2), y + 8, body)
        pyxel.rect(x + 1 + f, y + 10, 2, 4, 1)
        pyxel.rect(x + 5 - f, y + 10, 2, 4, 1)


class Drone(Enemy):
    """偵察ドローン：近づくと起動して追いかけてくる"""
    score = 150

    def __init__(self, x, y):
        super().__init__(x, y, 10, 7, 1)
        self.state = "dock"

    def update(self, g):
        self.t += 1
        p = g.p
        if self.state == "dock":
            if abs(p.x - self.x) < 80:
                self.state = "fly"
            return
        self.vx = clamp(self.vx + (0.05 if p.x > self.x else -0.05), -1.1, 1.1)
        ty = p.y + 2 + math.sin(self.t * 0.12) * 12
        self.y += clamp((ty - self.y) * 0.04, -0.9, 0.9)
        self.x += self.vx
        if self.far_from_camera(g, 96):
            self.alive = False

    def draw(self, g):
        x, y = int(self.x), int(self.y)
        c = 7 if self.flash else 13
        if self.state == "dock":
            pyxel.line(x + 5, y - 6, x + 5, y, 5)
            pyxel.rect(x + 3, y - 1, 5, 2, 1)
        else:
            rw = 4 if (self.t // 2) % 2 else 2
            for rx in (x + 1, x + 8):
                pyxel.line(rx - rw, y - 1, rx + rw, y - 1, 6)
                pyxel.pset(rx, y, 5)
            pyxel.pset(x + 5 - int(self.vx * 3), y + 8, 12 if self.t % 4 < 2 else 6)
        pyxel.rect(x, y, 10, 6, 0)
        pyxel.rect(x + 1, y + 1, 8, 4, c)
        pyxel.rect(x + 1, y + 4, 8, 1, 5)
        eye = 8 if (self.t // 10) % 2 else 10
        pyxel.rect(x + 4, y + 2, 2, 2, eye)


class Turret(Enemy):
    """固定砲台：プレイヤーに砲身を向けて撃ってくる"""
    score = 300

    def __init__(self, x, y):
        super().__init__(x, y, 10, 8, 3)
        self.ang = -math.pi / 2
        self.cool = 80

    def update(self, g):
        self.t += 1
        p = g.p
        dx = p.x + 4 - (self.x + 5)
        dy = min(p.y + 6 - (self.y + 3), 10)
        target = math.atan2(dy, dx)
        diff = (target - self.ang + math.pi) % (2 * math.pi) - math.pi
        self.ang += clamp(diff, -0.05, 0.05)
        self.cool -= 1
        if self.cool <= 0 and abs(dx) < 150 and not p.dead:
            self.cool = 110
            ca, sa = math.cos(self.ang), math.sin(self.ang)
            g.eshots.append(EnemyShot(self.x + 5 + ca * 7 - 3, self.y + 3 + sa * 7 - 3, ca * 1.5, sa * 1.5))
            g.flashes.append([self.x + 5 + ca * 8, self.y + 3 + sa * 8, 4])
            sfx(12, 3)

    def draw(self, g):
        x, y = int(self.x), int(self.y)
        ca, sa = math.cos(self.ang), math.sin(self.ang)
        bx, by = x + 5, y + 3
        for o in (0, 1):
            pyxel.line(bx, by + o, bx + ca * 8, by + sa * 8 + o, 0 if o else 5)
        pyxel.circ(bx, by + 1, 4, 0)
        pyxel.circ(bx, by + 1, 3, 7 if self.flash else 13)
        pyxel.pset(bx - 1, by - 1, 7)
        pyxel.rect(x, y + 4, 10, 4, 0)
        pyxel.rect(x + 1, y + 5, 8, 2, 5)
        if self.cool < 20 and (self.t // 3) % 2:
            pyxel.pset(bx, by + 1, 8)


class Supply(Enemy):
    """補給コンテナ：壊すとアイテム"""
    score = 50
    harmful = False
    prop = True

    def __init__(self, x, y):
        super().__init__(x, y, 12, 8, 2)

    def draw(self, g):
        x, y = int(self.x), int(self.y)
        body = 7 if self.flash else 5
        pyxel.rect(x, y, 12, 8, body)
        pyxel.rectb(x, y, 12, 8, 1)
        pyxel.rect(x + 1, y + 1, 10, 2, 13)
        pyxel.line(x + 4, y + 3, x + 4, y + 6, 1)
        pyxel.line(x + 7, y + 3, x + 7, y + 6, 1)
        pyxel.pset(x + 10, y + 5, 11 if (self.t // 20) % 2 else 3)

    def on_death(self, g):
        g.boom(self.cx(), self.cy(), 6, debris=8, smoke=1)
        g.items.append(Item(g.roll_item(), self.x + 2, self.y - 2))


class Barrel(Enemy):
    """ドラム缶：爆発して周りを巻き込む"""
    score = 50
    harmful = False
    prop = True

    def __init__(self, x, y):
        super().__init__(x, y, 8, 10, 1)

    def draw(self, g):
        x, y = int(self.x), int(self.y)
        body = 7 if self.flash else 8
        pyxel.rect(x, y, 8, 10, body)
        pyxel.line(x, y + 1, x + 7, y + 1, 2)
        pyxel.line(x, y + 8, x + 7, y + 8, 2)
        pyxel.rect(x + 1, y + 3, 6, 3, 10)
        pyxel.pset(x + 3, y + 4, 0)
        pyxel.pset(x + 4, y + 4, 0)
        pyxel.line(x + 1, y + 2, x + 1, y + 9, 15)
        pyxel.line(x + 7, y, x + 7, y + 9, 2)

    def on_death(self, g):
        g.pending.append([4, self.cx(), self.cy(), 24, 3])


class Wreck(Enemy):
    """壊れた端末：壊すとセルが出ることがある"""
    score = 100
    harmful = False
    prop = True

    def __init__(self, x, y):
        super().__init__(x, y, 12, 8, 3)

    def update(self, g):
        self.t += 1
        if random.random() < 0.02:
            g.parts.append([self.x + 6, self.y + 1, random.uniform(-1, 1), random.uniform(-1.6, -0.6),
                            8, 10, 0.08, 4])

    def draw(self, g):
        x, y = int(self.x), int(self.y)
        body = 7 if self.flash else 13
        pyxel.rect(x, y + 2, 12, 6, 5)
        pyxel.rect(x + 1, y, 10, 3, body)
        pyxel.rect(x + 2, y + 3, 5, 3, 1)
        if (self.t // 7) % 3:
            pyxel.pset(x + 3, y + 4, 11)
        pyxel.pset(x + 5, y + 4, 11 if (self.t // 5) % 2 else 3)
        pyxel.rect(x + 8, y + 3, 2, 3, 0)
        pyxel.line(x + 11, y + 2, x + 13, y - 1, 0)

    def on_death(self, g):
        g.boom(self.cx(), self.cy(), 7, debris=8)
        if random.random() < 0.5:
            g.items.append(Item("cell", self.x + 2, self.y - 2))


class Mech(Enemy):
    """ボス：浮遊戦闘メカ（3フェーズ）
    フェーズ1 : 上空からの爆撃 / 急降下
    フェーズ2 : + ドローン射出、煙を吐く
    フェーズ3 : 暴走。速く、5方向弾、爆撃の間隔が短くなる
    """
    score = 5000
    boss = True
    MAX_HP = 32
    HOME_Y = 52              # 上空。上撃ち・斜め撃ちで狙う高さ
    BOMB_Y = 30
    PATTERNS = {1: ["bomb", "swoop"],
                2: ["bomb", "launch", "swoop"],
                3: ["swoop", "bomb", "launch", "swoop"]}

    def __init__(self, x, y):
        super().__init__(x, -30, 20, 14, self.MAX_HP)
        self.max_hp = self.MAX_HP
        self.phase = 1
        self.state = "enter"
        self.timer = 0
        self.home_y = self.HOME_Y
        self.pat_i = 0
        self.run_dir = 1

    @property
    def harmful(self):
        return self.state not in ("dying", "enter")

    @property
    def hittable(self):
        return self.state not in ("dying", "enter")

    def set_state(self, st):
        self.state, self.timer = st, 0

    def start_dying(self):
        self.set_state("dying")

    def next_attack(self, g):
        pats = self.PATTERNS[self.phase]
        a = pats[self.pat_i % len(pats)]
        self.pat_i += 1
        if a == "bomb":
            self.run_dir = 1 if self.x + 10 < g.cam_x + W / 2 else -1
            self.set_state("bomb_prep")
        elif a == "launch" and sum(1 for e in g.enemies if isinstance(e, Drone) and e.alive) < 3:
            self.set_state("launch")
        else:
            self.set_state("aim")

    def fire_times(self):
        return (30, 70) if self.phase == 3 else (50,)

    def charging(self):
        """弾を撃つ直前（予告の光を出す）なら 0〜1 を返す"""
        if self.state != "hover":
            return 0.0
        for ft in self.fire_times():
            if ft - 18 <= self.timer < ft:
                return (self.timer - (ft - 18)) / 18
        return 0.0

    def fire_spread(self, g, n, spd):
        p = g.p
        cxp, cyp = self.x + 10, self.y + 10
        base = math.atan2(p.y + 6 - cyp, p.x + 4 - cxp)
        for i in range(n):
            a = base + (i - (n - 1) / 2) * 0.22
            g.eshots.append(EnemyShot(cxp - 3, cyp - 3, math.cos(a) * spd, math.sin(a) * spd))
        g.flashes.append([cxp, cyp + 2, 5])
        sfx(12, 3)

    def update(self, g):
        self.t += 1
        self.timer += 1
        p = g.p
        if self.state == "dying":
            self.y += 0.15
            if self.timer % 6 == 0:
                g.boom(self.x + random.uniform(0, 20), self.y + random.uniform(0, 14),
                       random.uniform(6, 10), debris=3, smoke=1)
            if self.timer >= 100:
                self.alive = False
                g.boss_destroyed(self)
            return

        # フェーズ移行
        ph = 1 if self.hp > self.max_hp * 0.6 else 2 if self.hp > self.max_hp * 0.3 else 3
        if ph > self.phase and self.state != "enter":
            self.phase = ph
            self.pat_i = 0
            self.set_state("hover")
            g.boss_phase(self)
        fast = self.phase == 3
        if self.phase >= 2 and random.random() < (0.15 if fast else 0.07):   # 傷ついて煙を吐く
            g.parts.append([self.x + random.uniform(2, 18), self.y + 4, random.uniform(-0.3, 0.3),
                            random.uniform(-0.8, -0.3), 40, 13, 0, 1])

        st = self.state
        if st == "enter":
            if g.warn_t > 30:
                return
            self.y += clamp((self.home_y - self.y) * 0.05, 0.4, 1.5)
            if self.y >= self.home_y - 1:
                self.set_state("hover")
        elif st == "hover":
            # プレイヤーの頭上を左右に行き来する（真上に来た瞬間が上撃ちのチャンス）
            tx = p.x + 4 - 10 + math.sin(self.t * 0.035) * 56
            ty = self.home_y + math.sin(self.t * 0.05) * 8
            self.x += clamp((tx - self.x) * 0.05, -1.6, 1.6)
            self.y += clamp((ty - self.y) * 0.05, -1.0, 1.0)
            if self.timer in self.fire_times():
                self.fire_spread(g, 5 if fast else 3, 1.9 if fast else 1.6)
            if self.timer >= (90 if fast else 120):
                self.next_attack(g)
        elif st == "bomb_prep":           # 画面の端の上空へ移動
            tx = g.cam_x + (6 if self.run_dir > 0 else W - self.w - 6)
            dx, dy = tx - self.x, self.BOMB_Y - self.y
            d = math.hypot(dx, dy)
            if d < 2.8 or self.timer > 120:
                self.set_state("bomb_run")
            else:
                self.x += dx / d * 2.8
                self.y += dy / d * 2.8
        elif st == "bomb_run":            # 上空を横切りながら爆弾を落とす
            self.x += self.run_dir * (2.0 if fast else 1.5)
            self.y = self.BOMB_Y + math.sin(self.timer * 0.15) * 2
            if self.timer % (11 if fast else 16) == 8:
                g.eshots.append(Bomb(self.x + 10, self.y + 13, self.run_dir * 0.3))
                sfx(17, 3)
            end = (self.x >= g.cam_x + W - self.w - 6) if self.run_dir > 0 else (self.x <= g.cam_x + 6)
            if end or self.timer > 300:
                self.set_state("hover")
        elif st == "launch":              # ドローン射出
            self.y += clamp((self.home_y - self.y) * 0.05, -1.0, 1.0)
            if self.timer in (20, 36):
                dr = Drone(self.x + 5, self.y + 14)
                dr.state, dr.active = "fly", True
                dr.vx = random.choice((-1.0, 1.0))
                g.enemies.append(dr)
                g.flashes.append([self.x + 10, self.y + 15, 6])
                sfx(13, 3)
            if self.timer >= 60:
                self.set_state("hover")
        elif st == "aim":
            if self.timer >= (16 if fast else 28):
                dx, dy = p.x + 4 - (self.x + 10), p.y + 7 - (self.y + 7)
                d = max(1.0, math.hypot(dx, dy))
                spd = 3.8 if fast else 3.2
                self.vx, self.vy = dx / d * spd, dy / d * spd
                self.set_state("swoop")
        elif st == "swoop":
            self.x += self.vx
            self.y += self.vy
            hit = g.stage.solid(self.x + 10, self.y + self.h)
            if hit or self.timer > 70:
                if hit:
                    g.shake = max(g.shake, 3)
                    g.boom(self.x + 10, self.y + self.h, 6, debris=6, smoke=2, sound=False)
                self.set_state("return")
        elif st == "return":
            self.y += clamp((self.home_y - self.y) * 0.06, -2.5, 2.5)
            if abs(self.y - self.home_y) < 2 or self.timer > 70:
                self.set_state("hover")
        self.x = clamp(self.x, g.cam_x, g.cam_x + W - self.w)
        if self.state != "enter":
            self.y = max(self.y, 4)

    def draw(self, g):
        x, y = int(self.x), int(self.y)
        body = 7 if self.flash else 13
        if self.phase == 3 and not self.flash and (self.t // 6) % 3 == 0:
            body = 8
        fl = 3 + (self.t // 2) % 3
        if self.state != "dying":
            for tx in (x + 4, x + 14):
                pyxel.tri(tx, y + 14, tx + 3, y + 14, tx + 1.5, y + 14 + fl + 2, 9)
                pyxel.tri(tx + 1, y + 14, tx + 2, y + 14, tx + 1.5, y + 14 + fl, 10)
        pyxel.rect(x - 3, y + 4, 26, 6, 0)
        pyxel.rect(x - 2, y + 5, 4, 4, 5)
        pyxel.rect(x + 18, y + 5, 4, 4, 5)
        pyxel.rect(x + 1, y + 1, 18, 13, 0)
        pyxel.rect(x + 2, y + 2, 16, 11, body)
        pyxel.rect(x + 2, y + 9, 16, 4, 5)
        pyxel.line(x + 2, y + 2, x + 17, y + 2, 7)
        if self.phase >= 2:                         # 装甲のひび
            pyxel.line(x + 4, y + 3, x + 6, y + 6, 1)
            pyxel.pset(x + 15, y + 4, 1)
        eye = 12 if self.phase == 1 else 10 if self.phase == 2 else 8
        if self.state == "aim" and (self.timer // 3) % 2:
            eye = 7
        pyxel.rect(x + 6, y + 4, 8, 4, 1)
        pyxel.rect(x + 7, y + 5, 6, 2, eye)
        pyxel.pset(x + 8, y + 5, 7)
        pyxel.line(x + 15, y + 1, x + 17, y - 4, 13)
        pyxel.pset(x + 17, y - 5, 8 if (self.t // 12) % 2 else 2)
        for i in range(3):
            pyxel.pset(x + 4 + i * 6, y + 11, 10 if (self.t // 6 + i) % 3 == 0 else 1)
        ch = self.charging()
        if ch > 0:                                    # 発射の予告
            r = 1 + ch * 4
            pyxel.circ(x + 10, y + 12, r, 8 if (self.t // 2) % 2 else 10)
            pyxel.circ(x + 10, y + 12, max(1, r - 2), 7)
        if self.state in ("bomb_run", "launch"):     # ハッチが開く
            pyxel.rect(x + 7, y + 12, 6, 2, 0)
            pyxel.pset(x + 9 + (self.t // 4) % 2, y + 13, 8)
        if self.state == "dying" and (self.t // 3) % 2:
            pyxel.rect(x + 2, y + 2, 16, 11, 8)


# ============================================================
# サウンド
# ============================================================
def init_sounds():
    S = pyxel.sounds
    S[0].set("c2c3", "s", "4", "s", 5)                 # jump
    S[1].set("a3e3", "p", "3", "f", 3)                 # blaster
    S[2].set("c2", "n", "5", "f", 6)                   # hit
    S[3].set("g2c2", "p", "6", "s", 8)                 # hurt
    S[4].set("c3e3g3c4", "s", "5", "n", 4)             # pickup
    S[5].set("g2f2e2d2c2", "t", "6", "f", 12)          # die
    S[6].set("c3e3g3c4rg3c4", "s", "5", "n", 9)        # clear
    S[7].set("c4", "p", "4", "f", 3)                   # select
    S[8].set("c1c1c1c1", "n", "7776", "f", 20)         # boss defeat
    S[9].set("c2a1f1c1", "n", "7654", "f", 9)          # explosion
    S[10].set("c3", "n", "4", "f", 2)                  # machine gun
    S[11].set("c4g3e3c3", "p", "4", "f", 2)            # laser
    S[12].set("e3c3", "p", "3", "f", 4)                # enemy shot
    S[13].set("c3g3c4g4", "t", "3", "f", 4)            # warp
    S[14].set("g2", "s", "3", "f", 4)                  # grenade throw
    S[15].set("c3g3c3g3", "p", "5", "s", 14)           # warning siren
    S[16].set("e3d3c3rb2rc3", "t", "5", "nnnnnf", 14)  # game over
    S[17].set("g3c3", "s", "2", "s", 4)                # bomb drop
    S[18].set("c1c2c1c2", "n", "6", "f", 6)            # boss phase change
    init_music()


# ------------------------------------------------------------
# BGM（2チャンネル：0=メロディ/アルペジオ、1=ベース）
#   _mel("a3:2 c4:2 r:4") … 音名:長さ(16分音符の数)
# ------------------------------------------------------------
def _mel(spec, vib=False):
    notes, fx = "", ""
    for tok in spec.split():
        n, ln = tok.split(":")
        ln = int(ln)
        notes += n * ln
        if n == "r":
            fx += "n" * ln
        elif ln == 1:
            fx += "n"
        else:
            fx += ("v" if vib and ln >= 6 else "n") * (ln - 1) + "f"
    return notes, fx


def _bass(roots, pattern):
    """roots: 小節ごとの根音（例 "a f g e"）。pattern: 16文字 L=低い根音 H=1oct上 .=休符"""
    notes, fx = "", ""
    for r in roots.split():
        for ch in pattern:
            if ch == ".":
                notes += "r"
                fx += "n"
            else:
                notes += r + ("1" if ch == "L" else "2")
                fx += "f"
    return notes, fx


def _arp(chords, reps=4):
    """chords: 小節ごとの4音アルペジオ（例 "c2g2e3b2"）を reps 回くり返す"""
    notes = "".join(c * reps for c in chords.split())
    return notes, "n" * _count(notes)


def _count(notes):
    """音符の数を数える（"r" / "c3" / "f#3" をそれぞれ1つと数える）"""
    i = n = 0
    while i < len(notes):
        if notes[i] == "r":
            i += 1
        else:
            i += 3 if notes[i + 1] in "#-" else 2
        n += 1
    return n


def _set_sound(idx, nf, tone, vol, speed):
    notes, fx = nf
    pyxel.sounds[idx].set(notes, tone, vol, fx, speed)


def _set_music(idx, *seqs):
    m = pyxel.musics[idx]
    try:
        m.set(*seqs)
    except TypeError:                      # 4チャンネル必須の古い Pyxel 用
        m.set(*(list(seqs) + [[] for _ in range(4 - len(seqs))]))


def init_music():
    # --- ワールドマップ：静かな宇宙（C / Am / F / G）
    _set_sound(32, _mel("e4:8 d4:8 c4:12 g3:4 a3:8 b3:8 c4:8 r:8", vib=True), "s", "2", 20)
    _set_sound(33, _arp("c2g2e3b2 a1e2c3g2 f1c2a2e3 g1d2b2d3"), "t", "4", 20)
    _set_music(BGM_MAP, [32], [33])
    # --- ステージ：疾走する Aマイナー（Am F G E ×2）
    lead = ("a3:2 c4:2 e4:2 a4:4 g4:2 e4:2 c4:2 "
            "f4:3 e4:1 c4:2 a3:4 c4:2 d4:2 c4:2 "
            "b3:2 d4:2 g4:2 b4:4 a4:2 g4:2 d4:2 "
            "g#4:6 e4:2 b3:4 r:2 e3:2 "
            "e4:4 a3:4 c4:2 b3:2 a3:4 "
            "f4:2 a4:2 g4:2 f4:2 e4:4 c4:4 "
            "d4:2 e4:2 f4:2 g4:2 b3:4 d4:4 "
            "e4:8 r:4 e3:2 g#3:2")
    _set_sound(34, _mel(lead, vib=True), "p", "3", 12)
    _set_sound(35, _bass("a f g e a f g e", "L.LHL.LHL.LHL.LH"), "t", "5", 12)
    _set_music(BGM_STAGE, [34], [35])
    # --- ボス：緊迫した Eマイナーのオスティナート
    _set_sound(36, _arp("e3g3b3e4 e3g3b3e4 c3e3g3c4 d3f#3a3d4 "
                        "e3g3b3e4 e3a3c4e4 c3e3g3c4 b2d#3f#3b3"), "p", "2", 10)
    _set_sound(37, _bass("e e c d e a c b", "LLHLLLHLLLHLLHLH"), "t", "5", 10)
    _set_music(BGM_BOSS, [36], [37])


def sfx(n, ch=3):
    pyxel.play(ch, n)


# ============================================================
# アプリ本体
# ============================================================
class App:
    def __init__(self):
        global FONT
        pyxel.init(W, H, title="NOVA TROOPER", fps=60)
        here = os.path.dirname(os.path.abspath(__file__))
        for path in (os.path.join(here, FONT_FILE), FONT_FILE):
            if os.path.exists(path):
                try:
                    FONT = pyxel.Font(path)
                    break
                except Exception:
                    FONT = None
        init_sounds()
        self.inp = Input()
        self.A = Assets()
        self.title_pix = self.make_big_text("NOVA TROOPER")

        self.state = "title"
        self.state_t = 0
        self.paused = False
        self.cleared = set()
        self.map_node = "base"
        self.map_move = None
        self.lives = 3
        self.score = 0
        self.keep_weapon = "blaster"
        self.keep_hp = 2
        self.music_on = True
        self.cur_bgm = None
        self.checkpoint = None
        self.msg = ""
        self.msg_t = 0
        self.gt = 0
        rnd = random.Random(7)
        self.map_stars = [(rnd.randrange(W), rnd.randrange(H), rnd.randrange(97)) for _ in range(90)]
        self.map_craters = [(rnd.randint(30, 236), rnd.randint(80, 190), rnd.randint(3, 9)) for _ in range(16)]
        self.twinkles = [(rnd.randrange(W), rnd.randrange(120), rnd.randrange(240)) for _ in range(28)]
        self.motes = [[rnd.uniform(0, W), rnd.uniform(0, VIEW_H), rnd.uniform(0.1, 0.35),
                       rnd.uniform(-0.12, 0.12)] for _ in range(18)]
        pyxel.run(self.update, self.draw)

    def make_big_text(self, s):
        img = pyxel.images[2]
        img.cls(0)
        try:
            img.text(0, 0, s, 7, FONT) if FONT else img.text(0, 0, s, 7)
        except Exception:
            img.text(0, 0, s, 7)
        return [(xx, yy) for yy in range(12) for xx in range(200) if img.pget(xx, yy) == 7]

    def bgm(self, n, force=False):
        """BGM を切り替える（同じ曲なら何もしない）。None で停止"""
        if n == self.cur_bgm and not force:
            return
        self.cur_bgm = n
        pyxel.stop(0)
        pyxel.stop(1)
        if n is not None and self.music_on:
            pyxel.playm(n, loop=True)

    def toast(self, s, t=120):
        self.msg, self.msg_t = s, t

    def in_left(self):  return self.inp.held("left")
    def in_right(self): return self.inp.held("right")
    def in_up(self):    return self.inp.held("up")
    def in_down(self):  return self.inp.held("down")
    def in_jump(self):  return self.inp.pressed("jump")
    def in_ok(self):    return self.inp.pressed("ok")

    # ============================================================
    # 更新
    # ============================================================
    def update(self):
        self.state_t += 1
        if self.msg_t > 0:
            self.msg_t -= 1
        self.inp.update()
        if self.inp.pressed("quit"):
            pyxel.quit()
        if self.inp.pressed("reload"):
            self.A.load()
            if getattr(self, "stage", None) is not None:
                self.stage.render(self.A.tiles)
            n = self.A.png_count()
            self.toast(L(f"グラフィック再読込（PNG {n}枚）", f"RELOADED ({n} PNG)"), 90)
        if self.inp.pressed("music"):
            self.music_on = not self.music_on
            if self.music_on:
                self.bgm(self.cur_bgm, force=True)
            else:
                pyxel.stop(0)
                pyxel.stop(1)
            self.toast("BGM ON" if self.music_on else "BGM OFF", 60)
        getattr(self, "update_" + self.state)()

    def update_title(self):
        self.bgm(BGM_MAP)
        if self.in_ok() and self.state_t > 10:
            sfx(7)
            self.state, self.state_t = "map", 0

    # ---------- ワールドマップ ----------
    def reachable(self):
        open_nodes = {"base"} | self.cleared
        r = set(open_nodes)
        for a, b in WORLD_EDGES:
            if a in open_nodes:
                r.add(b)
            if b in open_nodes:
                r.add(a)
        return r

    def map_neighbor(self, dx, dy):
        cur = WORLD_NODES[self.map_node]
        reach = self.reachable()
        best, best_d = None, 0.35
        for a, b in WORLD_EDGES:
            other = b if a == self.map_node else a if b == self.map_node else None
            if other is None or other not in reach:
                continue
            ox, oy = WORLD_NODES[other]["x"] - cur["x"], WORLD_NODES[other]["y"] - cur["y"]
            d = (ox * dx + oy * dy) / max(1.0, math.hypot(ox, oy))
            if d > best_d:
                best, best_d = other, d
        return best

    def update_map(self):
        self.bgm(BGM_MAP)
        if self.map_move:
            m = self.map_move
            m["t"] = min(1.0, m["t"] + 1.8 / m["len"])
            if m["t"] >= 1.0:
                self.map_node = m["to"]
                self.map_move = None
            return
        for name, dx, dy in (("left", -1, 0), ("right", 1, 0), ("up", 0, -1), ("down", 0, 1)):
            if self.inp.pressed(name) or (self.inp.held(name) and self.state_t % 20 == 0):
                nxt = self.map_neighbor(dx, dy)
                if nxt:
                    a, b = WORLD_NODES[self.map_node], WORLD_NODES[nxt]
                    self.map_move = dict(frm=self.map_node, to=nxt, t=0.0,
                                         len=max(1.0, math.hypot(b["x"] - a["x"], b["y"] - a["y"])))
                    sfx(7)
                    return
        if self.in_ok():
            node = WORLD_NODES[self.map_node]
            if node["stage"] is not None:
                sfx(7)
                self.checkpoint = None
                self.start_stage(self.map_node)
            elif node["kind"] == "home":
                self.toast(L("ここから降下作戦が始まる。", "THE DROP STARTS HERE."))
            else:
                self.toast(L("このステージは準備中です", "COMING SOON"))

    # ---------- ステージ開始 ----------
    def start_stage(self, node_id, from_cp=False):
        self.node_id = node_id
        self.sdef = STAGES[WORLD_NODES[node_id]["stage"]]
        self.stage = Stage(self.sdef)
        self.stage.render(self.A.tiles)
        self.enemies, self.items, self.shots, self.eshots = [], [], [], []
        self.parts, self.bgparts, self.booms, self.pending = [], [], [], []
        self.pops, self.flags, self.flashes = [], [], []
        self.door = None
        start = (24, 160)
        for ch, tx, ty in self.stage.entities:
            bx, by = tx * TS, (ty + 1) * TS
            if ch == "P":
                start = (bx, by - Player.H_STAND)
            elif ch == "Z":
                self.enemies.append(Mutant(bx, by - 14))
            elif ch == "B":
                self.enemies.append(Drone(bx, ty * TS))
            elif ch == "D":
                self.enemies.append(Mech(bx, ty * TS))
            elif ch == "U":
                self.enemies.append(Turret(bx - 1, by - 8))
            elif ch == "C":
                self.enemies.append(Supply(bx - 2, by - 8))
            elif ch == "O":
                self.enemies.append(Barrel(bx, by - 10))
            elif ch == "X":
                self.enemies.append(Wreck(bx - 2, by - 8))
            elif ch == "*":
                self.items.append(Item("cell", bx, by - 8, static=True))
            elif ch == "F":
                self.flags.append(dict(x=bx + 4, y=by, reached=False))
            elif ch == "G":
                self.door = dict(x=bx, y=by - 24, w=16, h=24)
        if from_cp and self.checkpoint:
            start = self.checkpoint
            for f in self.flags:
                if f["x"] <= start[0] + 1:
                    f["reached"] = True
        self.smoke_src = [(x * TS + 4, y * TS) for x, y in self.sdef.get("smoke", [])]
        self.p = Player(*start)
        self.p.weapon = self.keep_weapon
        self.p.hp = self.keep_hp
        self.boss_obj = next((e for e in self.enemies if e.boss), None)
        self.boss_bar = 0.0
        self.warn_t = 0
        self.bgm(None)
        self.cam_x = 0.0
        self.cam_min = 0.0
        self.boss_seen = False
        self.spawn_t = 0
        self.gt = 0
        self.shake = 0.0
        self.hitstop = 0
        self.muzzle = 0
        self.gate_k = 0.0
        self.meteor = None
        self.ship_x, self.ship_wait = -30.0, 240
        self.paused = False
        self.update_camera()
        self.state, self.state_t = "intro", 0

    def update_intro(self):
        if self.state_t > 100 or (self.state_t > 20 and self.in_ok()):
            self.state, self.state_t = "play", 0
            self.bgm(BGM_STAGE)

    # ---------- プレイ中 ----------
    def boss_alive(self):
        return any(e.alive and e.boss for e in self.enemies)

    def update_play(self):
        if self.inp.pressed("pause"):
            self.paused = not self.paused
            sfx(7)
            if self.paused:
                pyxel.stop(0)
                pyxel.stop(1)
            else:
                self.bgm(self.cur_bgm, force=True)
        if self.paused:
            return
        if self.hitstop > 0:          # ヒットストップ中は時間を止める
            self.hitstop -= 1
            return
        self.gt += 1
        if self.warn_t > 0:
            self.warn_t -= 1
            if self.warn_t in (149, 109, 69):
                sfx(15, 3)
            if self.warn_t == 0:
                self.bgm(BGM_BOSS)
        b = self.boss_obj
        if b is not None:
            target = max(0, b.hp) / b.max_hp if b.alive and b.state != "dying" else 0.0
            if b.state == "enter":
                target = min(1.0, self.boss_bar + 0.012) if self.warn_t <= 60 else 0.0
            self.boss_bar += clamp(target - self.boss_bar, -0.01, 0.02)
        self.update_player()
        if self.state != "play":
            return
        self.update_camera()
        self.spawn_mutants()
        for e in self.enemies:
            if not e.active and self.cam_x - 24 <= e.x <= self.cam_x + W + 24:
                e.active = True
            if e.active and e.alive:
                if e.flash > 0:
                    e.flash -= 1
                e.update(self)
        self.update_shots()
        self.update_eshots()
        self.update_items()
        self.update_pending()
        self.check_collisions()
        self.update_fx()
        self.update_ambient()
        self.enemies = [e for e in self.enemies if e.alive]

        for f in self.flags:
            if not f["reached"] and self.p.x >= f["x"]:
                f["reached"] = True
                self.checkpoint = (f["x"], f["y"] - Player.H_STAND)
                sfx(4)
                self.toast(L("ビーコン起動！ 中間地点", "BEACON ONLINE! CHECKPOINT"))
        if not self.boss_alive():
            self.gate_k = min(1.0, self.gate_k + 0.02)
        if self.door and not self.p.dead:
            d = self.door
            if abs(self.p.x - d["x"]) < 20:
                if self.boss_alive():
                    if self.msg_t <= 0:
                        self.toast(L("隔壁はロックされている…", "THE BULKHEAD IS LOCKED..."), 60)
                elif self.gate_k >= 1 and d["x"] + 4 < self.p.x + self.p.w and self.p.x < d["x"] + 12:
                    self.stage_clear()

    def update_camera(self):
        p = self.p
        max_cam = self.stage.w * TS - W
        cam = clamp(p.x + 4 - W / 2, 0, max_cam)
        if any(e.boss and e.alive and e.active for e in self.enemies):
            if not self.boss_seen:
                self.boss_seen = True
                self.warn_t = 150
                self.bgm(None)
            self.cam_min = max(self.cam_min, cam)
        self.cam_x = max(cam, self.cam_min)
        if p.x < self.cam_x:
            p.x = self.cam_x

    # ---------- プレイヤー ----------
    def update_player(self):
        p, st = self.p, self.stage
        if p.dead:
            p.dead_t += 1
            p.vy += 0.12
            p.y += p.vy
            if p.dead_t > 130:
                self.lives -= 1
                if self.lives <= 0:
                    self.state, self.state_t = "gameover", 0
                    self.bgm(None)
                    sfx(16, 3)
                else:
                    self.keep_weapon = p.weapon if KEEP_WEAPON_ON_DEATH else "blaster"
                    self.keep_hp = 2
                    self.start_stage(self.node_id, from_cp=True)
            return
        if p.invinc > 0:
            p.invinc -= 1
        if p.shoot_cd > 0:
            p.shoot_cd -= 1
        if p.throw_t > 0:
            p.throw_t -= 1

        lft, rgt, up, dn = self.in_left(), self.in_right(), self.in_up(), self.in_down()
        jump = self.in_jump()
        wd = WEAPONS[p.weapon]
        fire_held = self.inp.held("fire")
        if self.inp.pressed("fire"):
            p.fire_buf = FIRE_BUFFER
        elif p.fire_buf > 0:
            p.fire_buf -= 1
        fire = p.fire_buf > 0 or (wd["auto"] and fire_held)
        move_in = (1 if rgt else 0) - (1 if lft else 0)

        if p.climbing:
            self.update_climb(lft, rgt, up, dn, jump)
            self.check_hazards()
            return
        if p.hurt:
            p.vy = min(p.vy + GRAV, MAX_FALL)
            move_x(st, p, p.vx)
            self.player_move_y()
            if p.on_ground:
                p.hurt = False
                p.vx = 0
            self.check_hazards()
            return

        ctx = int((p.x + p.w / 2) // TS)
        feet_ty = int((p.y + p.h - 0.01) // TS)
        mid_ty = int((p.y + p.h / 2) // TS)
        want_climb = up and not fire_held and (move_in == 0 or self.inp.pressed("up"))
        if want_climb and not p.crouch and (st.get(ctx, mid_ty) in LADDER or st.get(ctx, feet_ty) in LADDER):
            self.start_climb(ctx)
            return
        if dn and p.on_ground and st.get(ctx, int((p.y + p.h + 1) // TS)) in LADDER:
            self.start_climb(ctx)
            p.y += 3
            return

        p.set_crouch(st, dn and p.on_ground)
        move = (1 if rgt else 0) - (1 if lft else 0)
        if p.on_ground:
            p.vx = 0 if p.crouch else move * WALK_SPEED
            if move:
                p.facing = move
        elif JUMP_FIXED:
            p.vx = p.jump_vx
        else:
            p.vx = move * WALK_SPEED
            if move:
                p.facing = move

        # 照準：地上は ↑ で上、空中は ↑ 上 / ↓ 下。マシンガンは銃口が回る（斜め撃ち）
        if p.crouch:
            target = 0
        elif p.on_ground:
            target = -90 if up else 0
        else:
            target = -90 if up else (90 if dn else 0)
        step = AIM_SWEEP_STEP if p.weapon == "heavy" else 180
        p.aim += clamp(target - p.aim, -step, step)
        p.aim_target = target

        if jump and p.on_ground and not p.crouch:
            p.vy = JUMP_V
            p.jump_vx = p.vx
            p.on_ground = False
            sfx(0, 2)
        if fire and self.player_shoot():
            p.fire_buf = 0
            if not p.on_ground and p.aim >= 45:      # 下撃ちの反動で落下がゆるむ
                p.hover_t = DOWN_SHOT_HOVER_T
        if p.on_ground or p.aim < 45:
            p.hover_t = 0

        p.vy = min(p.vy + GRAV, MAX_FALL)
        if p.hover_t > 0:
            p.hover_t -= 1
            p.vy = min(p.vy, DOWN_SHOT_HOVER)
        move_x(st, p, p.vx)
        self.player_move_y()
        if p.on_ground and p.vx != 0:
            p.anim += 1
        self.check_hazards()

    def player_move_y(self):
        p = self.p
        was_ground = p.on_ground
        if not was_ground:
            p.air_top = min(p.air_top, p.y)
        move_y(self.stage, p, p.vy)
        if p.on_ground:
            if not was_ground:
                if p.y - p.air_top > FALL_DAMAGE_PX:
                    self.toast(L("高いところから落ちた！", "FELL TOO FAR!"), 90)
                    self.hurt_player(None, fall=True)
                elif p.y - p.air_top > 24:
                    for i in range(4):
                        self.parts.append([p.x + 4, p.y + p.h, (i - 1.5) * 0.5, -0.3, 14, 13, 0, 1])
            p.air_top = p.y

    def start_climb(self, ctx):
        p = self.p
        p.aim = 0.0
        p.set_crouch(self.stage, False)
        p.climbing = True
        p.x = ctx * TS + TS / 2 - p.w / 2
        p.vx = p.vy = 0

    def update_climb(self, lft, rgt, up, dn, jump):
        p, st = self.p, self.stage
        if jump and (lft or rgt):
            p.climbing = False
            p.facing = 1 if rgt else -1
            p.vx = p.jump_vx = p.facing * WALK_SPEED
            p.vy = -2.5
            p.air_top = p.y
            return
        dy = ((1 if dn else 0) - (1 if up else 0)) * CLIMB_SPEED
        p.y += dy
        p.anim += abs(dy) * 0.5
        ctx = int((p.x + p.w / 2) // TS)
        feet_ty = int((p.y + p.h - 0.01) // TS)
        mid_ty = int((p.y + p.h / 2) // TS)
        fc, mc = st.get(ctx, feet_ty), st.get(ctx, mid_ty)
        if fc in LADDER:
            pass
        elif fc in SOLID:
            p.y = feet_ty * TS - p.h
            p.climbing = False
            p.on_ground = True
        elif dy < 0 and st.get(ctx, feet_ty + 1) in LADDER:
            p.y = (feet_ty + 1) * TS - p.h
            p.climbing = False
            p.on_ground = True
        elif mc not in LADDER or dy > 0:
            p.climbing = False
            p.vy = 0
        p.air_top = p.y

    def check_hazards(self):
        p, st = self.p, self.stage
        if p.y > st.h * TS + 8:
            self.kill_player(explode=False)
            return
        if p.invinc == 0:
            for px in (p.x + 1, p.x + p.w - 2):
                if st.tile_at(px, p.y + p.h - 1) == SPIKE:
                    self.toast(L("高電圧！", "HIGH VOLTAGE!"), 60)
                    for _ in range(8):
                        self.parts.append([p.x + 4, p.y + p.h - 4, random.uniform(-2, 2),
                                           random.uniform(-2.5, -0.5), 10, 12, 0.1, 4])
                    self.hurt_player(p.x + 4 - p.facing * 4)
                    break

    def player_shoot(self):
        p = self.p
        if p.climbing or p.shoot_cd > 0:
            return False
        wd = WEAPONS[p.weapon]
        power = p.hp >= 3
        limit = wd["max"] + (1 if power else 0)
        if sum(1 for s in self.shots if s.kind != "flame") >= limit:
            return False
        p.shoot_cd = wd["cd"]
        p.throw_t = 10
        f = p.facing
        tx, ty = p.gun_tip()
        dmg = 2 if power else 1
        k = p.weapon
        dx, dy = p.aim_dir()
        a = math.radians(p.aim)
        if k == "blaster":
            self.shots.append(self.bolt("blaster", tx, ty, dx, dy, 6.5, 8, dmg))
            sfx(1, 2)
        elif k == "heavy":
            if p.aim_target != p.aim:     # 銃口が回っている間は連射を速めて弾をばらまく
                p.shoot_cd = 1
            j = a + random.uniform(-0.07, 0.07)
            self.shots.append(self.bolt("mg", tx, ty, math.cos(j) * f, math.sin(j), 7.5, 6, dmg))
            self.parts.append([p.x + 4 - f * 2, p.y + p.h - 8, -f * random.uniform(0.6, 1.2),
                               random.uniform(-2.2, -1.4), 50, 10, 0.18, 3])     # 薬莢
            sfx(10, 2)
        elif k in ("grenade", "plasma"):
            if p.aim >= 45:                       # 空中で真下：落とす
                vx, vy = f * 0.4 + p.vx * 0.5, 1.0
            elif k == "grenade":                  # 上に向けるほど高く投げる
                vx, vy = f * max(0.6, 2.3 * math.cos(a)), -3.3 + 1.6 * math.sin(a)
            else:
                vx, vy = f * max(0.5, 2.3 * math.cos(a)), -2.0 + 2.2 * math.sin(a)
            if k == "grenade":
                self.shots.append(Shot("grenade", tx - 2, ty - 3, vx, vy, 5, 5, dmg + 2, grav=0.18))
                sfx(14, 2)
            else:
                self.shots.append(Shot("plasma", tx - 3, ty - 3, vx, vy, 6, 6, dmg, grav=0.2))
                sfx(1, 2)
        else:
            self.shots.append(self.bolt("laser", tx, ty, dx, dy, 9.0, 24, dmg + 1, pierce=True))
            sfx(11, 2)
        self.muzzle = 4
        return True

    def bolt(self, kind, tx, ty, dx, dy, spd, length, dmg, pierce=False):
        """銃口(tx,ty)から (dx,dy) 方向へ飛ぶビーム系の弾。当たり判定は向きに合わせた箱"""
        cx, cy = tx + dx * length / 2, ty + dy * length / 2
        w, h = max(3.0, abs(dx) * length), max(3.0, abs(dy) * length)
        s = Shot(kind, cx - w / 2, cy - h / 2, dx * spd, dy * spd, w, h, dmg, pierce)
        s.dx, s.dy, s.L = dx, dy, length
        return s

    def update_shots(self):
        st = self.stage
        for s in self.shots:
            s.t += 1
            if s.kind == "flame":
                if s.t > 50:
                    s.alive = False
                continue
            s.vy += s.grav
            s.x += s.vx
            s.y += s.vy
            cx, cy = s.x + s.w / 2, s.y + s.h / 2
            if s.kind in ("blaster", "mg", "laser"):
                hx, hy = cx + s.dx * s.L / 2, cy + s.dy * s.L / 2
                if st.solid(hx, hy):
                    s.alive = False
                    self.spark(hx, hy, 10 if s.kind == "mg" else 12)
            elif s.kind == "grenade":
                if st.solid(cx, s.y + s.h) or st.solid(cx, cy):
                    s.alive = False
                    self.explode(cx, cy, 20, s.dmg)
            elif s.kind == "plasma":
                if s.vy > 0 and st.solid(cx, s.y + s.h):
                    gtop = math.floor((s.y + s.h) / TS) * TS
                    s.kind, s.t, s.vx, s.vy = "flame", 0, 0, 0
                    s.w, s.h = 14, 8
                    s.x, s.y = cx - 7, gtop - 8
                    s.pierce = True
                elif st.solid(cx, cy):
                    s.alive = False
            beam = s.kind in ("blaster", "mg", "laser")
            if (s.x + s.w < self.cam_x - 4 or s.x > self.cam_x + W + 4 or s.y > st.h * TS
                    or (beam and (s.y + s.h < -2 or s.y > VIEW_H + 2))):
                s.alive = False
        self.shots = [s for s in self.shots if s.alive]

    def update_eshots(self):
        st = self.stage
        for s in self.eshots:
            s.t += 1
            if s.grav:
                s.vy = min(s.vy + s.grav, MAX_FALL)
            s.x += s.vx
            s.y += s.vy
            if s.kind == "bomb":
                if st.solid(s.x + 3, s.y + 6) or s.y > st.h * TS:
                    s.alive = False
                    self.bomb_blast(s.x + 3, s.y + 5)
                continue
            if (st.solid(s.x + 3, s.y + 3) or s.t > 300 or
                    s.x < self.cam_x - 16 or s.x > self.cam_x + W + 16):
                s.alive = False
                if st.solid(s.x + 3, s.y + 3):
                    self.spark(s.x + 3, s.y + 3, 8)
        self.eshots = [s for s in self.eshots if s.alive]

    def bomb_blast(self, x, y):
        """爆弾が地面で爆発。近くにいるとダメージ"""
        self.boom(x, y, 9, debris=3, smoke=2)
        p = self.p
        if not p.dead and math.hypot(p.x + 4 - x, p.y + p.h / 2 - y) < 15:
            self.hurt_player(x)

    def update_items(self):
        st = self.stage
        for it in self.items:
            it.t += 1
            if not it.static:
                it.vy = min(it.vy + 0.2, MAX_FALL)
                move_y(st, it, it.vy)
                if it.t > 600 or it.y > st.h * TS:
                    it.alive = False
        self.items = [i for i in self.items if i.alive]

    def update_pending(self):
        """遅延爆発（ドラム缶の連鎖など）"""
        rest = []
        for q in self.pending:
            q[0] -= 1
            if q[0] <= 0:
                self.explode(q[1], q[2], q[3], q[4])
            else:
                rest.append(q)
        self.pending = rest

    def check_collisions(self):
        p = self.p
        for s in self.shots:
            if not s.alive:
                continue
            for e in self.enemies:
                if not (e.alive and e.active and e.hittable) or not overlap(s, e):
                    continue
                if s.kind == "grenade":
                    s.alive = False
                    self.explode(s.x + 2, s.y + 2, 20, s.dmg)
                    break
                if s.pierce:
                    if self.gt - s.hit.get(id(e), -999) < 15:
                        continue
                    s.hit[id(e)] = self.gt
                self.damage_enemy(e, s.dmg)
                if not s.pierce:
                    s.alive = False
                    break
        for s in self.shots:                     # 爆弾は撃ち落とせる
            if not s.alive:
                continue
            for b in self.eshots:
                if b.alive and b.kind == "bomb" and overlap(s, b):
                    b.alive = False
                    self.boom(b.x + 3, b.y + 3, 6, debris=2, smoke=1)
                    self.add_score(50, b.x, b.y)
                    if not s.pierce:
                        s.alive = False
                        break
        self.eshots = [b for b in self.eshots if b.alive]
        self.shots = [s for s in self.shots if s.alive]
        if p.dead:
            return
        if p.invinc == 0:
            for e in self.enemies:
                if e.alive and e.active and e.harmful and not e.prop and overlap(p, e):
                    self.hurt_player(e.cx())
                    break
        if p.invinc == 0 and not p.dead:
            for s in self.eshots:
                if overlap(p, s):
                    s.alive = False
                    self.hurt_player(s.x)
                    break
        for it in self.items:
            if it.alive and overlap(p, it):
                it.alive = False
                self.pickup(it.kind)

    def pickup(self, kind):
        p = self.p
        sfx(4)
        if kind == "cell":
            self.add_score(500, p.x, p.y)
            self.toast(L(*ITEM_MSG["cell"]), 60)
        elif kind == "repair":
            if p.hp < 2:
                p.hp = 2
            else:
                self.add_score(200, p.x, p.y)
            self.toast(L(*ITEM_MSG["repair"]))
        elif kind == "power":
            p.hp = 3
            self.toast(L(*ITEM_MSG["power"]))
        elif kind in WEAPONS:
            p.weapon = self.keep_weapon = kind
            self.toast(L("武器：", "WEAPON: ") + L(*WEAPONS[kind]["name"]))

    def roll_item(self):
        p = self.p
        if p.hp <= 1 and random.random() < 0.5:
            return "repair"
        r = random.random()
        if r < 0.15:
            return "power" if p.hp >= 2 else "repair"
        if r < 0.65:
            return random.choice(PICKUP_WEAPONS)
        return "cell"

    def damage_enemy(self, e, dmg):
        if not e.alive:
            return
        e.hp -= dmg
        e.flash = 6
        sfx(2)
        if e.hp > 0:
            self.spark(e.cx(), e.cy(), 7)
            if e.boss:
                self.hitstop = max(self.hitstop, 1)
            return
        if e.boss:
            e.start_dying()
            self.bgm(None)
            self.eshots = []
            self.hitstop = 10
            self.shake = 5
            self.toast(L("メカを撃破！", "MECH DOWN!"), 100)
            return
        e.alive = False
        self.add_score(e.score, e.cx(), e.y)
        e.on_death(self)
        self.hitstop = max(self.hitstop, 1 if e.prop else 3)
        if not e.prop and random.random() < 0.08:
            self.items.append(Item(self.roll_item(), e.x, e.y))

    def boss_phase(self, e):
        self.hitstop = 10
        self.shake = 5
        sfx(18, 3)
        for _ in range(3):
            self.boom(e.x + random.uniform(0, 20), e.y + random.uniform(0, 14), 6,
                      debris=4, smoke=2, sound=False)
        self.eshots = [s for s in self.eshots if s.kind == "bomb"]
        if e.phase == 3:
            self.toast(L("メカが暴走を始めた！", "THE MECH IS GOING BERSERK!"), 100)
        else:
            self.toast(L("装甲にひびが入った！", "ARMOR CRACKED!"), 100)

    def boss_destroyed(self, e):
        sfx(8, 3)
        self.add_score(e.score, e.cx(), e.y)
        self.explode(e.cx(), e.cy(), 30, 0)
        self.shake = 8
        self.hitstop = 12
        self.toast(L("隔壁ロック解除！", "BULKHEAD UNLOCKED!"), 150)
        self.items.append(Item("power", e.x + 6, e.y))

    def hurt_player(self, src_x, fall=False):
        p = self.p
        if p.dead or p.invinc > 0:
            return
        p.hp -= 1
        if p.hp <= 0:
            self.kill_player()
            return
        sfx(3)
        cols = (7, 6) if p.hp == 2 else (13, 5)
        for i in range(12):          # スーツの破片が飛び散る
            self.parts.append([p.x + 4, p.y + 6, random.uniform(-2, 2), random.uniform(-3, -1),
                               45, random.choice(cols), 0.15, 2])
        self.hitstop = 6
        self.shake = max(self.shake, 3)
        p.invinc = 100
        p.climbing = False
        p.set_crouch(self.stage, False)
        if fall:
            p.hurt, p.vx, p.vy = False, 0, 0
        else:
            d = -p.facing if src_x is None else (1 if p.x + 4 >= src_x else -1)
            p.hurt, p.vx, p.vy = True, d * 1.3, -2.6
            p.on_ground = False
            p.air_top = p.y

    def kill_player(self, explode=True):
        p = self.p
        if p.dead:
            return
        p.dead = True
        p.dead_t = 0
        self.bgm(None)
        p.vy = -3.0
        p.hp = 0
        if explode:
            self.boom(p.x + 4, p.y + 6, 10, debris=10)
            self.hitstop = 10
        sfx(5)

    def spawn_mutants(self):
        self.spawn_t += 1
        if self.spawn_t < 110:
            return
        self.spawn_t = 0
        p, st = self.p, self.stage
        ptx = int(p.x // TS)
        zones = self.sdef.get("spawn_zones", [])
        if not any(a <= ptx <= b for a, b in zones):
            return
        if sum(1 for e in self.enemies if isinstance(e, Mutant)) >= 3 or random.random() > 0.8:
            return
        feet = p.y + p.h
        for _ in range(6):
            tx = ptx + random.choice((-1, 1)) * random.randint(5, 12)
            if not any(a <= tx <= b for a, b in zones):
                continue
            for ty in range(2, st.h):
                if (st.get(tx, ty) in SOLID and st.get(tx, ty - 1) == "." and
                        st.get(tx, ty - 2) == "." and abs(ty * TS - feet) <= 24):
                    z = Mutant(tx * TS, ty * TS - 14)
                    z.active = True
                    self.enemies.append(z)
                    return

    # ============================================================
    # エフェクト（爆発・破片・煙・画面揺れ）
    # ============================================================
    # particle = [x, y, vx, vy, life, col, grav, kind]
    #   kind 0:点  1:煙  2:破片(跳ねる)  3:薬莢(跳ねる)  4:火花
    def spark(self, x, y, col):
        for _ in range(4):
            self.parts.append([x, y, random.uniform(-1.6, 1.6), random.uniform(-1.6, 1.0), 8, col, 0.05, 4])

    def boom(self, x, y, r=10, debris=6, smoke=3, sound=True):
        self.booms.append([x, y, r, 0, 16 + int(r), 0])
        for _ in range(debris):
            a = random.uniform(math.pi * 1.1, math.pi * 1.9)
            sp = random.uniform(1.0, 3.0)
            self.parts.append([x, y, math.cos(a) * sp, math.sin(a) * sp, random.randint(40, 70),
                               random.choice((5, 13, 0, 4)), 0.15, 2])
        for _ in range(int(r)):
            a = random.uniform(0, math.tau)
            sp = random.uniform(1.0, 2.5)
            self.parts.append([x, y, math.cos(a) * sp, math.sin(a) * sp, random.randint(6, 12),
                               random.choice((10, 7, 9)), 0.0, 4])
        for _ in range(smoke):
            self.parts.append([x + random.uniform(-r / 2, r / 2), y + random.uniform(-r / 3, r / 3),
                               random.uniform(-0.2, 0.2), random.uniform(-0.6, -0.2),
                               random.randint(40, 60), 13, 0, 1])
        if sound:
            sfx(9, 3)
        self.shake = max(self.shake, r / 4)

    def explode(self, x, y, r, dmg):
        """爆発（見た目 + 範囲ダメージ）。プレイヤーは巻き込まない"""
        self.boom(x, y, r * 0.6, debris=int(r / 2), smoke=3)
        for i in range(2 if r >= 14 else 0):
            self.booms.append([x + random.uniform(-r / 2, r / 2), y + random.uniform(-r / 2, r / 4),
                               r * 0.45, 0, 16, 3 + i * 4])
        if dmg > 0:
            for e in self.enemies:
                if e.alive and e.active and e.hittable:
                    if math.hypot(e.cx() - x, e.cy() - y) < r + max(e.w, e.h) / 2:
                        self.damage_enemy(e, dmg)

    def add_score(self, v, x, y):
        self.score += v
        self.pops.append([x, y, str(v), 40])

    def update_fx(self):
        st = self.stage
        for q in self.parts:
            k = q[7]
            if k in (2, 3):
                q[3] = min(q[3] + q[6], MAX_FALL)
                if st.solid(q[0], q[1] + q[3]):
                    q[3] *= -0.4
                    q[2] *= 0.6
                    if abs(q[3]) < 0.4:
                        q[3] = 0
                elif st.solid(q[0] + q[2], q[1]):
                    q[2] *= -0.5
                else:
                    q[1] += q[3]
                q[0] += q[2]
            else:
                q[3] += q[6]
                q[0] += q[2]
                q[1] += q[3]
            q[4] -= 1
        self.parts = [q for q in self.parts if q[4] > 0][-500:]
        for b in self.booms:
            if b[5] > 0:
                b[5] -= 1
            else:
                b[3] += 1
                if b[3] == 1 and b[2] >= 5:
                    for _ in range(2):
                        self.parts.append([b[0] + random.uniform(-3, 3), b[1], random.uniform(-0.3, 0.3),
                                           random.uniform(-0.5, -0.2), 50, 13, 0, 1])
        self.booms = [b for b in self.booms if b[3] < b[4]]
        for q in self.pops:
            q[1] -= 0.4
            q[3] -= 1
        self.pops = [q for q in self.pops if q[3] > 0]
        for f in self.flashes:
            f[2] -= 1
        self.flashes = [f for f in self.flashes if f[2] > 0]
        if self.muzzle > 0:
            self.muzzle -= 1
        self.shake *= 0.86
        if self.shake < 0.3:
            self.shake = 0

    def update_ambient(self):
        """背景の小さな動き：煙・火花・流れ星・飛行艇・ちり"""
        if self.gt % 5 == 0:
            for sx, sy in self.smoke_src:
                if abs(sx - (self.cam_x + W / 2)) < W:
                    self.bgparts.append([sx + random.uniform(-2, 2), sy, random.uniform(0.05, 0.25),
                                         random.uniform(-0.45, -0.25), 90])
        for q in self.bgparts:
            q[0] += q[2]
            q[1] += q[3]
            q[4] -= 1
        self.bgparts = [q for q in self.bgparts if q[4] > 0]
        for tx, ty in self.stage.anim_tiles:
            if random.random() < 0.04 and abs(tx * TS - (self.cam_x + W / 2)) < W:
                self.parts.append([tx * TS + random.uniform(0, 8), ty * TS + 4, random.uniform(-1, 1),
                                   random.uniform(-1.5, -0.5), 8, random.choice((12, 7)), 0.05, 4])
        if self.meteor is None:
            if random.random() < 1 / 300:
                self.meteor = [random.uniform(80, W), random.uniform(0, 40), 40]
        else:
            self.meteor[0] -= 2.4
            self.meteor[1] += 1.1
            self.meteor[2] -= 1
            if self.meteor[2] <= 0:
                self.meteor = None
        if self.ship_wait > 0:
            self.ship_wait -= 1
        else:
            self.ship_x += 0.35
            if self.ship_x > W + 30:
                self.ship_x, self.ship_wait = -30.0, random.randint(600, 1200)
        for m in self.motes:
            m[0] += m[2]
            m[1] += m[3] + math.sin((self.gt + m[0]) * 0.03) * 0.1
            if m[0] > W:
                m[0] -= W
            m[1] %= VIEW_H

    # ---------- クリア / ゲームオーバー ----------
    def stage_clear(self):
        self.state, self.state_t = "clear", 0
        self.add_score(5000, self.p.x, self.p.y)
        self.keep_weapon = self.p.weapon
        self.keep_hp = max(2, self.p.hp)
        self.bgm(None)
        sfx(6)

    def update_clear(self):
        if self.state_t > 200 or (self.state_t > 60 and self.in_ok()):
            first = self.node_id not in self.cleared
            self.cleared.add(self.node_id)
            self.map_node = self.node_id
            self.state, self.state_t = "map", 0
            if first:
                self.toast(L("新しいルートが開いた！", "A NEW ROUTE OPENED!"), 150)

    def update_gameover(self):
        if self.state_t > 240 or (self.state_t > 60 and self.in_ok()):
            self.lives = 3
            self.score = 0
            self.keep_weapon = "blaster"
            self.keep_hp = 2
            self.state, self.state_t = "map", 0

    # ============================================================
    # 描画
    # ============================================================
    def draw(self):
        pyxel.camera()
        getattr(self, "draw_" + self.state)()

    def draw_stars(self, t):
        for x, y, ph in self.map_stars:
            if (t + ph) % 97 < 3:
                pyxel.pset(x, y, 7)
            else:
                pyxel.pset(x, y, 13 if ph % 3 else 5)

    def draw_title(self):
        pyxel.cls(0)
        self.draw_stars(self.state_t)
        pyxel.circ(W // 2, 360, 200, 1)
        pyxel.circb(W // 2, 360, 200, 12)
        pyxel.circb(W // 2, 360, 199, 5)
        pyxel.circ(206, 46, 14, 5)
        pyxel.circ(210, 42, 13, 0)
        if self.title_pix:
            sc = 2 if FONT else 3
            mx = max(px for px, _ in self.title_pix) + 1
            my = max(py for _, py in self.title_pix) + 1
            ox, oy = (W - mx * sc) // 2, 60
            for px, py in self.title_pix:
                pyxel.rect(ox + px * sc + 2, oy + py * sc + 2, sc, sc, 1)
            for px, py in self.title_pix:
                k = py / max(1, my - 1)
                col = 7 if k < 0.3 else 6 if k < 0.6 else 12
                pyxel.rect(ox + px * sc, oy + py * sc, sc, sc, col)
        ctxt(W / 2, 98, L("〜 惑星ゼータ降下作戦 〜", "- OPERATION ZETA DROP -"), 13)
        draw_hero(self.A, W / 2 - 4, 158, 14, 1, 2, hero_frame(self.state_t, walking=True))
        if (self.state_t // 30) % 2 == 0:
            ctxt(W / 2, 182, L("Z / Aボタン / START でスタート", "PRESS Z / A / START"), 7)

    # ---------- ワールドマップ ----------
    def draw_map(self):
        t = self.state_t
        pyxel.cls(0)
        self.draw_stars(t)
        pyxel.elli(-50, 34, 356, 240, 1)
        pyxel.ellib(-50, 34, 356, 240, 12)
        pyxel.ellib(-49, 35, 354, 238, 5)
        # 地形
        pyxel.elli(118, 142, 70, 34, 3)               # 酸の湿地
        pyxel.elli(126, 148, 50, 20, 11)
        pyxel.elli(130, 150, 40, 14, 3)
        for i in range(5):
            if (t // 10 + i * 3) % 7 == 0:
                pyxel.pset(130 + i * 8, 150 + (i % 2) * 4, 7)
        for mx, my in ((196, 76), (232, 90), (204, 132), (240, 128)):
            pyxel.tri(mx - 14, my + 10, mx, my - 12, mx + 14, my + 10, 2)
            pyxel.tri(mx, my - 12, mx + 14, my + 10, mx + 4, my + 10, 1)
            pyxel.line(mx - 14, my + 10, mx, my - 12, 8)
        for cx, cy, r in self.map_craters:
            if any(math.hypot(cx - n["x"], cy - n["y"]) < r + 10 for n in WORLD_NODES.values()):
                continue
            pyxel.circ(cx, cy, r, 5)
            pyxel.circ(cx + 1, cy + 1, r - 1, 1)
        pyxel.line(196, 82, 196, 104, 13)                 # 中継塔
        pyxel.pset(196, 81, 8 if (t // 20) % 2 else 2)

        reach = self.reachable()
        for a, b in WORLD_EDGES:
            na, nb = WORLD_NODES[a], WORLD_NODES[b]
            n = int(math.hypot(nb["x"] - na["x"], nb["y"] - na["y"]) // 3)
            open_ = a in reach and b in reach
            for i in range(n + 1):
                k = i / max(1, n)
                x = int(na["x"] + (nb["x"] - na["x"]) * k)
                y = int(na["y"] + (nb["y"] - na["y"]) * k)
                if open_:
                    pyxel.rect(x - 1, y - 1, 3, 3, 5)
                    if (i - t // 4) % 4 == 0:
                        pyxel.pset(x, y, 7)
                    else:
                        pyxel.pset(x, y, 12)
                elif i % 2 == 0:
                    pyxel.pset(x, y, 5)
        for nid, n in WORLD_NODES.items():
            x, y = n["x"], n["y"]
            if n["kind"] == "home":
                pyxel.elli(x - 10, y + 2, 20, 6, 0)
                pyxel.tri(x - 9, y + 3, x + 11, y + 3, x + 1, y - 9, 13)
                pyxel.tri(x + 1, y - 9, x + 11, y + 3, x + 4, y + 3, 5)
                pyxel.rect(x - 2, y - 2, 4, 3, 12)
                pyxel.pset(x + 1, y - 10, 8 if (t // 15) % 2 else 2)
            elif n["kind"] == "castle":
                by = y + int(math.sin(t * 0.05) * 2)
                pyxel.elli(x - 18, by - 6, 36, 12, 0)
                pyxel.elli(x - 16, by - 5, 32, 9, 1)
                pyxel.rect(x - 6, by - 10, 12, 5, 1)
                for i in range(-12, 13, 4):
                    pyxel.pset(x + i, by, 12 if (t // 8 + i) % 3 else 7)
                pyxel.pset(x + 16, by - 2, 8 if nid not in reach or (t // 10) % 2 else 2)
                pyxel.elli(x - 8, by + 10, 16, 4, 1)
            else:
                if nid in self.cleared:
                    col = 10
                elif n["stage"] is None:
                    col = 13
                elif nid in reach:
                    col = 11
                else:
                    col = 5
                pyxel.circ(x, y, 7, 0)
                pyxel.circ(x, y, 6, 5)
                pyxel.circ(x, y, 4, col)
                if nid in reach and (t // 15) % 2:
                    pyxel.circb(x, y, 8, col)
                pyxel.text(x - 5, y + 9, nid, 7)
        if self.map_move:
            m = self.map_move
            a, b = WORLD_NODES[m["frm"]], WORLD_NODES[m["to"]]
            px = a["x"] + (b["x"] - a["x"]) * m["t"]
            py = a["y"] + (b["y"] - a["y"]) * m["t"]
            face, walking = (1 if b["x"] >= a["x"] else -1), True
        else:
            n = WORLD_NODES[self.map_node]
            px, py, face, walking = n["x"], n["y"], 1, False
        bob = 0 if walking else (1 if (t // 20) % 2 else 0)
        pyxel.elli(int(px) - 5, int(py) - 1, 10, 4, 0)
        draw_hero(self.A, px - 4, py - 15 - bob, 14, face, 2, hero_frame(t, walking=walking))

        pyxel.rect(0, 0, W, 16, 0)
        pyxel.line(0, 15, W, 15, 5)
        txt(4, 3, L("ゾーン1  惑星ゼータ", "ZONE 1  PLANET ZETA"), 12)
        txt(170, 3, f"x{self.lives}  {self.score:06d}", 10)
        pyxel.rect(0, 198, W, 26, 0)
        pyxel.rectb(0, 198, W, 26, 5)
        if not self.map_move:
            n = WORLD_NODES[self.map_node]
            name = L(*n["name"])
            if self.map_node in self.cleared:
                name += L("  ★クリア済", "  *CLEAR")
            elif n["kind"] != "home" and n["stage"] is None:
                name += L("  （準備中）", "  (SOON)")
            txt(6, 201, name, 7)
        txt(6, 212, L("矢印/十字キー:移動  Z/A:決定", "ARROWS/DPAD:MOVE  Z/A:ENTER"), 13)
        draw_item(self.keep_weapon, 176, 202, t)               # 持ち越し中の装備
        txt(188, 201, L(*WEAPONS[self.keep_weapon]["name"]), 7)
        suit = {3: (L("パワースーツ", "POWER SUIT"), 10)}.get(self.keep_hp, (L("スーツ", "SUIT"), 13))
        txt(188, 212, suit[0], suit[1])
        if self.msg_t > 0:
            pyxel.rect(30, 172, W - 60, 16, 0)
            pyxel.rectb(30, 172, W - 60, 16, 12)
            ctxt(W / 2, 175, self.msg, 10)

    def draw_intro(self):
        pyxel.cls(0)
        self.draw_stars(self.state_t)
        ctxt(W / 2, 64, "MISSION 1", 12)
        ctxt(W / 2, 82, L(*self.sdef["name"]), 7)
        draw_hero(self.A, W / 2 - 20, 108, 14, 1, 2)
        txt(W / 2 - 4, 112, f"x {self.lives}", 7)
        if (self.state_t // 15) % 2 == 0:
            ctxt(W / 2, 150, "READY", 10)

    # ---------- 背景（パララックス） ----------
    def draw_layer(self, img, factor, ox, oy):
        w, h = img.width, img.height
        off = int(self.cam_x * factor) % w
        y = HUD_H + VIEW_H - h + oy
        x = -off - w + ox
        while x < W:
            if x + w > 0:
                pyxel.blt(x, y, img, 0, 0, w, h, KEY)
            x += w
        return off, y, w

    def draw_lights(self, lights, off, y0, w, ox, mode):
        for i, (lx, ly, c) in enumerate(lights):
            if mode == "blink":
                if ((self.gt // 20) + i) % 3 == 0:
                    continue
                col = c
            else:
                col = c if (self.gt // 4 + i) % 2 else 12
            for k in (-1, 0, 1):
                sx = lx - off + k * w + ox
                if 0 <= sx < W:
                    pyxel.pset(sx, y0 + ly, col)
                    if mode == "blink" and ((self.gt // 20) + i) % 3 == 1:
                        pyxel.pset(sx - 1, y0 + ly, 2)
                        pyxel.pset(sx + 1, y0 + ly, 2)

    def draw_background(self, ox, oy):
        A = self.A
        pyxel.blt(ox, HUD_H + oy, A.sky, 0, 0, A.sky.width, A.sky.height)
        for x, y, ph in self.twinkles:
            k = (self.gt + ph) % 120
            if k < 4:
                pyxel.pset(x + ox, HUD_H + y + oy, 7)
                if k < 2:
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        pyxel.pset(x + dx + ox, HUD_H + y + dy + oy, 6)
        if self.meteor:
            mx, my, _ = self.meteor
            pyxel.line(mx + ox, HUD_H + my + oy, mx + 8 + ox, HUD_H + my - 4 + oy, 6)
            pyxel.pset(mx + ox, HUD_H + my + oy, 7)
        off, y0, w = self.draw_layer(A.far, 0.08, ox, oy)
        self.draw_lights(A.far_lights, off, y0, w, ox, "flicker")
        if self.ship_wait == 0:
            sx, sy = int(self.ship_x) + ox, HUD_H + 72 + oy
            pyxel.rect(sx, sy, 10, 2, 1)
            pyxel.tri(sx + 10, sy, sx + 14, sy + 1, sx + 10, sy + 2, 1)
            pyxel.pset(sx - 1, sy + 1, 12 if self.gt % 4 < 2 else 6)
            pyxel.pset(sx + 4, sy - 1, 8 if (self.gt // 10) % 2 else 1)
        off, y0, w = self.draw_layer(A.mid, 0.25, ox, oy)
        self.draw_lights(A.mid_lights, off, y0, w, ox, "blink")
        self.draw_layer(A.near, 0.5, ox, oy)

    # ---------- ステージ ----------
    def draw_world(self, ox, oy):
        st, A = self.stage, self.A
        cx = int(self.cam_x)
        pyxel.camera(cx - ox, -HUD_H - oy)
        for q in self.bgparts:                     # 背景の煙
            age = 90 - q[4]
            r = 1 + age / 22
            col = 13 if q[4] > 60 else 5 if q[4] > 30 else 1
            pyxel.circ(q[0], q[1], r, col)
        u = max(0, cx - 8)
        w = min(W + 16, st.img.width - u)
        pyxel.blt(u, 0, st.img, u, 0, w, st.img.height, KEY)
        for tx, ty in st.anim_tiles:
            if cx - 8 <= tx * TS <= cx + W:
                fr = (self.gt // 3 + tx) % 3
                pyxel.blt(tx * TS, ty * TS, A.tiles, 32 + fr * 8, 16, TS, TS, KEY)
        for f in self.flags:
            x, y = f["x"], f["y"]
            pyxel.rect(x - 3, y - 3, 7, 3, 5)
            pyxel.line(x, y - 18, x, y - 3, 13)
            col = 11 if f["reached"] else 8
            on = (self.gt // 15) % 2
            pyxel.circ(x, y - 19, 2, col if on else 1)
            if f["reached"]:
                pyxel.circb(x, y - 19, 3 + (self.gt // 4) % 4, 3)
        if self.door:
            self.draw_gate()
        for it in self.items:
            if it.static or it.t < 480 or (it.t // 4) % 2:
                draw_item(it.kind, it.x, it.y, self.gt)
        for e in self.enemies:
            if e.active and e.prop:
                e.draw(self)
        for e in self.enemies:
            if e.active and not e.prop:
                e.draw(self)
        for s in self.shots:
            self.draw_shot(s)
        for s in self.eshots:
            if s.kind == "bomb":
                bx, by = int(s.x), int(s.y)
                pyxel.rect(bx + 1, by, 4, 7, 0)
                pyxel.rect(bx + 2, by + 1, 2, 5, 5)
                pyxel.line(bx, by, bx + 5, by, 13)
                pyxel.pset(bx + 2, by + 6, 8 if (s.t // 4) % 2 else 10)
                continue
            c = 10 if (s.t // 3) % 2 else 7
            pyxel.circ(s.x + 3, s.y + 3, 3, 8)
            pyxel.circ(s.x + 3, s.y + 3, 1, c)
        self.draw_player()
        if self.muzzle > 0 and not self.p.dead:
            mx, my = self.p.gun_tip()
            ddx, ddy = self.p.aim_dir()
            mx, my = mx + ddx * 2, my + ddy * 2
            pyxel.circ(mx, my, 3 if self.muzzle > 2 else 1, 10)
            pyxel.pset(mx, my, 7)
        for fx, fy, ft in self.flashes:
            pyxel.circ(fx, fy, ft // 2 + 1, 10)
        for b in self.booms:
            if b[5] == 0:
                self.draw_boom(b)
        for q in self.parts:
            k = q[7]
            if k == 1:
                age = 60 - q[4]
                col = 13 if q[4] > 40 else 5 if q[4] > 20 else 1
                pyxel.circ(q[0], q[1], 1 + clamp(age / 12, 0, 4), col)
            elif k == 2:
                pyxel.rect(q[0], q[1], 2, 2, q[5])
            elif k == 3:
                pyxel.pset(q[0], q[1], 10)
                pyxel.pset(q[0], q[1] + 1, 9)
            elif k == 4:
                pyxel.line(q[0], q[1], q[0] - q[2], q[1] - q[3], q[5])
            else:
                pyxel.pset(q[0], q[1], q[5])
        for q in self.pops:
            pyxel.text(int(q[0]) - 6, int(q[1]), q[2], 7)
        pyxel.camera()

    def draw_boom(self, b):
        x, y, r, t, life, _ = b
        k = t / life
        if k < 0.12:
            pyxel.circ(x, y, r * 0.7, 7)
        elif k < 0.55:
            rr = r * (0.7 + k)
            pyxel.circ(x, y, rr, 9)
            pyxel.circ(x - rr * 0.15, y - rr * 0.2, rr * 0.7, 10)
            pyxel.circ(x - rr * 0.25, y - rr * 0.3, rr * 0.3, 7)
        else:
            rr = r * (1.25 - (k - 0.55))
            yy = y - (k - 0.55) * 10
            pyxel.circ(x, yy, rr, 8 if k < 0.75 else 2)
            pyxel.circ(x, yy - rr * 0.3, rr * 0.6, 9 if k < 0.75 else 4)

    def draw_gate(self):
        d = self.door
        x, y = d["x"], d["y"]
        k = self.gate_k
        pyxel.rect(x - 5, y - 7, 26, 31, 0)
        pyxel.rect(x - 4, y - 6, 24, 30, 5)
        for i in range(0, 22, 4):
            pyxel.rect(x - 3 + i, y - 5, 2, 4, 10)
        pyxel.rect(x, y, 16, 24, 0)
        if k > 0:
            pyxel.rect(x + 2, y + 2, 12, 22, 1)
            pyxel.rect(x + 6, y + 4, 4, 20, 3 if (self.gt // 6) % 2 else 11)
        sl = int(k * 8)
        for dx, dw in ((x, 8 - sl), (x + 8 + sl, 8 - sl)):
            if dw > 0:
                pyxel.rect(dx, y, dw, 24, 13)
                pyxel.line(dx, y + 8, dx + dw - 1, y + 8, 5)
                pyxel.line(dx, y + 16, dx + dw - 1, y + 16, 5)
        if k == 0:
            pyxel.line(x + 8, y, x + 8, y + 23, 0)
        lamp = 8 if self.boss_alive() else 11
        pyxel.circ(x + 8, y - 3, 1, lamp if (self.gt // 10) % 2 else 0)

    def draw_shot(self, s):
        x, y = int(s.x), int(s.y)
        if s.kind == "blaster":
            self.draw_bolt(s, ((-1, 12, 0), (0, 12, 0), (1, 12, 0), (0, 7, 0.5)))
        elif s.kind == "mg":
            self.draw_bolt(s, ((0, 9, 0), (1, 9, 0), (0, 10, 0.5), (1, 10, 0.5)))
        elif s.kind == "laser":
            self.draw_bolt(s, ((-1, 2, 0), (2, 2, 0), (0, 8, 0), (1, 8, 0), (0, 7, 0.1)))
        elif s.kind == "grenade":
            pyxel.circ(x + 2, y + 2, 2, 3)
            pyxel.pset(x + 2, y + 1, 11)
            if (s.t // 4) % 2:
                pyxel.pset(x + 3, y + 3, 8)
        elif s.kind == "plasma":
            pyxel.circ(x + 3, y + 3, 3, 12)
            pyxel.circ(x + 3, y + 3, 1, 7)
        elif s.kind == "flame":
            for i in range(4):
                hh = 4 + ((s.t // 3 + i * 2) % 4)
                pyxel.tri(x + i * 3, y + 8, x + i * 3 + 2, y + 8 - hh, x + i * 3 + 4, y + 8,
                          12 if i % 2 else 6)
            pyxel.line(x, y + 7, x + 13, y + 7, 7)

    def draw_bolt(self, s, layers):
        """向き付きの弾を (横ずらし, 色, 描き始め位置0〜1) の重ね塗りで描く"""
        cx, cy = s.x + s.w / 2, s.y + s.h / 2
        hx, hy = cx + s.dx * s.L / 2, cy + s.dy * s.L / 2
        tx, ty = cx - s.dx * s.L / 2, cy - s.dy * s.L / 2
        px, py = -s.dy, s.dx
        for off, col, frac in layers:
            sx, sy = tx + (hx - tx) * frac, ty + (hy - ty) * frac
            pyxel.line(round(sx + px * off), round(sy + py * off),
                       round(hx + px * off), round(hy + py * off), col)

    def draw_player(self):
        p = self.p
        if p.dead:
            if p.dead_t < 70 and (p.dead_t // 3) % 2 == 0:
                draw_hero(self.A, p.x, p.y, p.h, p.facing, 1, "hurt")
            return
        if p.invinc > 0 and (p.invinc // 3) % 2:
            return
        walking = p.climbing or (p.on_ground and p.vx != 0)
        frame = hero_frame(p.anim, on_ground=p.on_ground, walking=walking, crouch=p.crouch,
                           climb=p.climbing, shoot=p.throw_t > 0, hurt=p.hurt, aim=p.aim)
        draw_hero(self.A, p.x, p.y, p.h, p.facing, p.hp, frame)

    def draw_front(self, ox, oy):
        self.draw_layer(self.A.front, 1.3, ox, oy)
        for m in self.motes:
            x = (m[0] - self.cam_x * 0.2) % W
            pyxel.pset(x + ox, HUD_H + m[1] + oy, 13 if m[2] > 0.25 else 5)

    def draw_hud(self):
        p = self.p
        pyxel.rect(0, 0, W, HUD_H, 0)
        pyxel.line(0, HUD_H - 1, W, HUD_H - 1, 5)
        txt(4, 3, f"SCORE {self.score:06d}", 7)
        pyxel.blt(80, 4, self.A.hero, 0, SPR_ROW[2] * SPR, SPR, 8, KEY)
        txt(95, 3, f"x{self.lives}", 7)
        suit = {3: (L("パワースーツ", "POWER"), 10), 2: (L("スーツ", "SUIT"), 13),
                1: (L("インナー", "INNER"), 8)}.get(max(1, p.hp), ("", 7))
        txt(114, 3, suit[0], suit[1])
        pyxel.rectb(178, 2, 76, 12, 5)
        draw_item(p.weapon, 181, 4, self.gt)
        txt(193, 3, L(*WEAPONS[p.weapon]["name"]), 7)

    def draw_warning(self):
        k = self.warn_t
        if k <= 0:
            return
        top, h = HUD_H + 70, 34
        pyxel.rect(0, top, W, h, 0)
        sh = self.gt % 8
        for i in range(-1, W // 8 + 2):           # 流れる警告ストライプ
            x = i * 8 - sh
            pyxel.tri(x, top, x + 4, top, x, top + 4, 8)
            pyxel.tri(x, top + h - 1, x + 4, top + h - 1, x + 4, top + h - 5, 8)
        if (k // 8) % 2 == 0:
            ctxt(W / 2, top + 9, "!! WARNING !!", 8)
        ctxt(W / 2, top + 20, L("大型メカ接近", "HEAVY MECH APPROACHING"), 7)

    def draw_boss_bar(self):
        b = self.boss_obj
        if b is None or not self.boss_seen or self.boss_bar <= 0.001:
            return
        x, y, w = 64, H - 10, 128
        txt(x - 30, y - 2, "MECH", 8)
        pyxel.rect(x - 1, y - 1, w + 2, 6, 0)
        pyxel.rectb(x - 2, y - 2, w + 4, 8, 5)
        cur = max(0, b.hp) / b.max_hp if b.alive and b.state not in ("enter", "dying") else self.boss_bar
        col = 11 if b.phase == 1 else 10 if b.phase == 2 else 8
        pyxel.rect(x, y, int(w * self.boss_bar), 4, 2)         # 減っていく分を遅れて表示
        pyxel.rect(x, y, int(w * min(cur, self.boss_bar)), 4, col)
        pyxel.line(x, y, x + int(w * min(cur, self.boss_bar)) - 1, y, 7)
        for f in (0.3, 0.6):                                  # フェーズの区切り
            pyxel.line(x + int(w * f), y, x + int(w * f), y + 3, 0)

    def draw_message(self):
        if self.msg_t > 0:
            w = text_w(self.msg) + 12
            x = (W - w) // 2
            pyxel.rect(x, 40, w, 16, 0)
            pyxel.rectb(x, 40, w, 16, 12)
            txt(x + 6, 43, self.msg, 10)

    def draw_play(self):
        pyxel.cls(0)
        ox = oy = 0
        if self.shake > 0 and not self.paused:
            s = int(self.shake + 0.5)
            ox, oy = random.randint(-s, s), random.randint(-s, s)
        self.draw_background(ox, oy)
        self.draw_world(ox, oy)
        self.draw_front(ox, oy)
        self.draw_warning()
        self.draw_boss_bar()
        self.draw_hud()
        self.draw_message()
        if self.state == "play" and self.paused:
            pyxel.rect(70, 92, 116, 36, 0)
            pyxel.rectb(70, 92, 116, 36, 12)
            ctxt(W / 2, 98, "PAUSE", 10)
            ctxt(W / 2, 112, L("START / Enter で再開", "START/ENTER: RESUME"), 13)

    def draw_clear(self):
        self.draw_play()
        pyxel.rect(40, 90, W - 80, 44, 0)
        pyxel.rectb(40, 90, W - 80, 44, 10)
        ctxt(W / 2, 98, "MISSION COMPLETE!", 10)
        ctxt(W / 2, 114, L("クリアボーナス 5000", "CLEAR BONUS 5000"), 7)

    def draw_gameover(self):
        pyxel.cls(0)
        ctxt(W / 2, 90, "GAME OVER", 8)
        ctxt(W / 2, 110, L("マップに戻ります", "RETURNING TO MAP"), 13)


if __name__ == "__main__":
    App()
