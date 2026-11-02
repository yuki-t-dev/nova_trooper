# -*- coding: utf-8 -*-
"""
NOVA TROOPER  (Step 6.1)
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
  オープニング     Z / A で次の場面へ、Enter / START で飛ばす

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
     marsh_sky.png / marsh_far.png / marsh_mid.png / marsh_near.png / marsh_front.png
                         1-2 酸の湿地の背景（サイズは上と同じ）
     tower_sky.png / tower_far.png / tower_mid.png / tower_near.png(256x96) / tower_front.png
                         1-3 中継塔の背景。tower_near は縦方向にもくり返す
     ship_sky.png / ship_far.png / ship_mid.png / ship_near.png / ship_front.png
                         1-4 敵母艦（船内）の背景
     ice_*.png / magma_*.png / fort_*.png（sky/far/mid/near/front）
                         ワールド2（2-1 氷原 / 2-2 溶岩洞 / 2-3 氷の要塞）の背景
     tiles.png は 128x48 に拡張（段4：雪・溶岩、段0の右側：氷）。古い 128x32 でも可
  背景レイヤーの横幅は自由（横方向にループ）。透明色はピンク #FF9798（14番）

■ ステージ追加
  build_stageN() を書いて STAGES に追加し、WORLD_NODES の "stage" に番号を入れる
  地形: # 岩盤  = 金属  K コンテナ  - 足場  H はしご  | ケーブル  ^ 電流床
        % 泥  ~ 酸（触れるとダメージ＋跳ね上がる）  _ キノコの棚（すり抜け床）
  配置: P 開始  Z 生体兵  B ドローン  U 砲台  C 補給  O ドラム缶  X 残骸
        * セル  F ビーコン  D ボス(メカ)  G ゲート
        J 酸ガエル（酸の表面に置く）  S 酸吐き草  W ボス(酸の主・酸の表面に置く)
        R はしごロボ（はしごの上に置く）  Q ボス(防衛コア)
        V 天井砲台（天井のすぐ下に置く）  M ボス(敵司令機・床の上に置く)
  地形（追加）: > < ベルトコンベア（矢印の向きに流れる）
        I 氷（すべる床）  s 雪  & 溶岩（酸と同じく、触れるとダメージ＋跳ね上がる）
  配置（ワールド2）: A つらら / 鍾乳石（天井のすぐ下に置く）  E 転がりロボ
        L 溶岩ガエル（溶岩の表面に置く）
        T ボス(雪上戦車)  Y ボス(溶岩巨人)  N ボス(防衛ユニット・空中に置く)
  ステージ設定（STAGES の dict）:
        theme="crash"/"marsh"（背景） bgm=曲番号  platforms=[動く足場…]
        spawn_every / spawn_max / spawn_chance（生体兵の湧き）  turret_cd（砲台の間隔）
        boss=dict(hp=…, bomb_every=…)（ボスの強さ）
        vertical=True（縦スクロール）  arena_y=ボス部屋の床のy  hatch=[ボス戦で閉じるタイル]
        crumbles=[(タイルx, タイルy, 幅)]（崩れる足場）
        lasers=[(タイルx, タイルy, 長さ, "h"/"v", 点灯フレーム, 消灯フレーム, 位相)]
        crushers=[(タイルx, 幅, 待ちフレーム, 位相)]（天井から落ちるプレス機）
        arena_x_max=ボス戦のカメラ右端  escape=脱出の制限時間(秒)  escape_open=[撃破後に開くタイル]
        final=True（クリア後にエンディング）  mission=("日本語","English")（開始画面の見出し）
        world=ワールド番号（エンディングの文面）  arena=(左端px, 右端px)（地上ボスの移動範囲）
        jets=[(タイルx, 間隔フレーム, 位相)]（溶岩から噴き上がる火柱）
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
BGM_MAP, BGM_STAGE, BGM_BOSS, BGM_STAGE2, BGM_STAGE3 = 0, 1, 2, 3, 4
BGM_STAGE4, BGM_ENDING = 5, 6
BGM_W2MAP, BGM_ICE, BGM_MAGMA, BGM_FORT = 7, 8, 9, 10
MUSIC_SLOT = 7             # 8曲目以降は musics[7] に読み込んで鳴らす
BGM_OPENING = 11

# オープニングの場面（scene=描く絵、time=自動で次へ進むまでのフレーム数、text=字幕）
OP_TYPE_SPEED = 3          # 字幕を1文字出すのにかかるフレーム数
OPENING = [
    dict(scene="colony", time=420, text=[
        ("銀河暦 2187年。辺境の惑星ゼータ。", "GALACTIC YEAR 2187. PLANET ZETA."),
        ("人類の開拓コロニーが静かに眠っていた。", "A QUIET HUMAN COLONY SLEPT HERE."),
    ]),
    dict(scene="invasion", time=460, text=[
        ("その夜、空から巨大な影が降りてきた。", "THAT NIGHT, A HUGE SHADOW DESCENDED."),
        ("機械の軍団がコロニーを覆いつくし、", "A MACHINE ARMY SWALLOWED THE COLONY,"),
        ("通信は途絶えた。", "AND ALL SIGNALS WENT DARK."),
    ]),
    dict(scene="drop", time=440, text=[
        ("銀河連邦は、たったひとりの兵士を送りこむ。", "THE FEDERATION SENT A SINGLE SOLDIER."),
        ("最新鋭の強化スーツをまとった降下兵――", "A DROP TROOPER IN AN ADVANCED SUIT -"),
    ]),
    dict(scene="hero", time=380, text=[
        ("コードネーム「ノヴァ・トルーパー」。", "CODENAME: NOVA TROOPER."),
        ("作戦目標：敵母艦の撃破。", "OBJECTIVE: DESTROY THE MOTHERSHIP."),
    ]),
]

# 撃ち心地の調整値
AIM_SWEEP_STEP = 30.0     # マシンガンの銃口が1フレームで回る角度（度）。3フレームで真上
LADDER_GRAB_DELAY = 4      # はしごをつかむまでのフレーム数（この間に攻撃すると上撃ち）
FIRE_BUFFER = 8
JUMP_BUFFER = 6            # 着地の少し前・ヒットストップ中に押したジャンプも有効にする           # 撃てない間に押した攻撃を覚えておくフレーム数
DOWN_SHOT_HOVER = 0.8     # 空中で下撃ちしたときの落下速度の上限（反動でふわっと浮く）
DOWN_SHOT_HOVER_T = 10    # 下撃ち1発あたり、ふわっと浮く効果が続くフレーム数

SOLID = set("#=K%<>Is")
CONVEYOR = set("<>")
CONVEY_SPEED = 0.6         # ベルトコンベアで流される速さ（歩く速さは 1.3）
DEBRIS_EVERY = 26          # 脱出中に瓦礫が落ちてくる間隔（フレーム）
ONEWAY = set("-_")
ACID = "~"
LAVA = "&"
LIQUID = set("~&")
ICE = "I"
ICE_ACCEL = 0.045          # 氷の上での加速・減速（小さいほどすべる。普通の床は即座に止まる）
WAVE_SPEED = 2.2           # 地面を走る衝撃波の速さ
WAVE_RISE = 10             # 衝撃波が走り出すまでのフレーム数（この間は炎が立ち上がるだけ）
LADDER = set("H|")
SPIKE = "^"
ENTITY_CHARS = set("PZBDC*FGOXUJSWRQVMAELTYN")

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
    for x, y in ((34, G - 1), (75, G - 5), (110, G - 1), (122, G - 1)):
        b.put(x, y, "Z")
    for x, y in ((50, 8), (75, 9), (112, 4), (158, 8)):
        b.put(x, y, "B")
    for x, y in ((36, G - 1), (44, G - 1), (57, G - 1), (107, G - 1), (124, G - 1), (156, G - 1)):
        b.put(x, y, "O")
    for x, y in ((11, G - 1), (55, G - 1), (142, G - 1)):
        b.put(x, y, "X")
    for x, y in ((78, G - 5), (134, 12)):
        b.put(x, y, "U")
    b.put(94, G - 1, "F")
    b.put(162, G - 1, "F")          # ボス前の中間地点
    b.put(164, G - 1, "C")          # ボス前の補給
    b.put(186, 11, "D")
    b.put(200, G - 1, "G")
    return b.rows()


def build_stage2():
    """1-2 酸の湿地"""
    MW, MH, G = 232, 26, 23
    b = Builder(MW, MH)
    b.fill(0, G, MW - 1, MH - 1, "%")
    for x0, x1 in ((22, 27), (48, 60), (88, 104), (122, 134), (184, 209)):   # 酸の池（深さ2）
        b.fill(x0, G, x1, G + 1, "~")
    b.fill(125, G, 126, MH - 1, "%")      # 飛び石
    b.fill(130, G, 131, MH - 1, "%")
    b.fill(24, G - 2, 25, G - 2, "_")     # 小さな池のキノコの棚
    b.fill(70, G - 1, 71, G - 1, "%")     # 丘
    b.fill(72, G - 3, 80, G - 1, "%")
    b.fill(111, 14, 119, 14, "=")         # リフトで上がる高台
    b.fill(120, 14, 120, G - 1, "H")      # 高台から降りるはしご
    b.fill(186, G - 3, 188, G - 3, "_")   # ボスの池の足場
    b.fill(204, G - 3, 206, G - 3, "_")
    b.fill(MW - 1, 0, MW - 1, G - 1, "=")

    b.put(3, G - 1, "P")
    for x, y in ((12, G - 1), (66, G - 1), (115, 13), (150, G - 1), (172, G - 1)):
        b.put(x, y, "C")
    for x, y in ((24, G - 4), (54, G - 6), (96, G - 7), (128, G - 3), (117, 12)):
        b.put(x, y, "*")
    for x, y in ((64, G - 1), (68, G - 1), (145, G - 1)):
        b.put(x, y, "O")
    for x, y in ((8, G - 1), (143, G - 1)):
        b.put(x, y, "X")
    for x, y in ((35, 10), (95, 8), (140, 9), (160, 8)):
        b.put(x, y, "B")
    for x in (26, 52, 57, 92, 100, 123, 128, 133):
        b.put(x, G, "J")
    for x, y in ((40, G - 1), (76, G - 4), (148, G - 1), (156, G - 1)):
        b.put(x, y, "S")
    b.put(79, G - 4, "U")
    b.put(84, G - 1, "F")
    b.put(168, G - 1, "F")
    b.put(196, G, "W")
    b.put(222, G - 1, "G")
    return b.rows()


def build_stage3():
    """1-3 中継塔（縦に登っていくステージ）"""
    MW, MH = 32, 112
    b = Builder(MW, MH)
    b.fill(0, 0, 0, MH - 1, "=")                 # 外壁
    b.fill(MW - 1, 0, MW - 1, MH - 1, "=")
    b.fill(1, 109, 30, 109, "=")                 # 1階
    b.fill(1, 110, 30, MH - 1, "#")

    def floor(y, x0, x1, ch="="):
        b.fill(x0, y, x1, y, ch)

    def ladder(x, top, bottom, ch="H"):
        b.fill(x, top, x, bottom, ch)

    floor(103, 1, 24)          # F1
    floor(97, 8, 30)           # F2（左はリフトの縦穴）
    floor(85, 8, 20)           # F3（リフトの到着階）
    floor(79, 26, 30)          # F4（崩れる足場の先）
    floor(73, 14, 30)          # F5
    floor(67, 1, 20)           # F6（中間地点）
    floor(61, 1, 8)            # F7 左
    floor(61, 22, 30)          # F7 右（動く足場で渡る）
    floor(55, 18, 30)          # F8
    floor(49, 1, 12)           # F9（崩れる足場の先）
    floor(43, 1, 18)           # F10
    floor(37, 8, 30)           # F11
    floor(31, 12, 30)          # F12（ボス前の中間地点）
    floor(24, 1, 30)           # ボス部屋の床
    ladder(22, 103, 108)
    ladder(10, 97, 102)
    ladder(28, 73, 78)
    ladder(15, 67, 72)
    ladder(2, 61, 66, "|")     # ケーブル
    ladder(28, 55, 60)
    ladder(3, 43, 48)
    ladder(16, 37, 42)
    ladder(26, 31, 36)
    ladder(28, 24, 30)

    b.put(3, 108, "P")
    for x, y in ((10, 108), (4, 66), (26, 60), (16, 30)):
        b.put(x, y, "C")
    for x, y in ((28, 106), (5, 90), (29, 58), (6, 46), (29, 28)):
        b.put(x, y, "*")
    for x, y in ((16, 108), (25, 96), (6, 48), (20, 36)):
        b.put(x, y, "Z")
    for x, y in ((5, 99), (12, 80), (18, 57), (24, 33)):
        b.put(x, y, "B")
    for x, y in ((16, 72), (27, 36)):
        b.put(x, y, "U")
    for x, y in ((10, 100), (28, 57)):
        b.put(x, y, "R")
    for x, y in ((14, 108), (18, 66)):
        b.put(x, y, "O")
    b.put(6, 108, "X")
    b.put(8, 66, "F")
    b.put(25, 30, "F")
    b.put(15, 6, "Q")
    b.put(3, 23, "G")
    return b.rows()


def build_stage4():
    """1-4 敵母艦（最終面）"""
    MW, MH, G = 262, 26, 23
    b = Builder(MW, MH)
    b.fill(0, 0, MW - 1, 2, "=")                  # 天井
    b.fill(0, G, MW - 1, MH - 1, "=")             # 床
    b.fill(12, G, 22, G, ">")                     # 右へ流れるコンベア
    b.fill(38, G, 40, MH - 1, ".")                # 穴
    b.fill(26, G - 1, 26, G - 1, "K")
    # 上下2ルートの区画（上：天井砲台に狙われる通路 / 下：レーザーと生体兵）
    b.fill(85, 15, 110, 15, "=")
    b.fill(84, 15, 84, G - 1, "H")
    b.fill(122, G, 134, G, "<")                   # 左へ流れるコンベア
    b.fill(140, G - 1, 140, G - 1, "K")
    # ボス部屋
    b.fill(184, G - 3, 188, G - 3, "-")           # 足場（コアを撃つ / ビームをかわす。ジャンプで届く高さ）
    b.fill(201, 3, 201, G - 1, "=")               # ボス部屋の右の隔壁（撃破後に開く）
    # 脱出路
    b.fill(215, G - 1, 215, G - 1, "K")
    b.fill(230, G - 2, 230, G - 1, "K")
    b.fill(MW - 1, 0, MW - 1, G - 1, "=")

    b.put(3, G - 1, "P")
    for x, y in ((30, G - 1), (77, G - 1), (112, 14), (168, G - 1)):
        b.put(x, y, "C")
    for x, y in ((17, G - 3), (39, G - 4), (62, G - 1), (98, 13), (186, G - 5)):
        b.put(x, y, "*")
    for x, y in ((34, G - 1), (90, G - 1), (104, G - 1), (148, G - 1)):
        b.put(x, y, "Z")
    for x, y in ((44, 8), (118, 6), (130, 8), (146, 9)):
        b.put(x, y, "B")
    for x in (92, 100, 108, 157):
        b.put(x, 3, "V")
    for x, y in ((80, G - 1), (81, G - 1), (136, G - 1), (144, G - 1)):
        b.put(x, y, "O")
    for x, y in ((8, G - 1), (128, G - 1)):
        b.put(x, y, "X")
    b.put(140, G - 2, "U")
    b.put(114, G - 1, "F")
    b.put(167, G - 1, "F")
    b.put(196, G - 1, "M")
    b.put(252, G - 1, "G")
    return b.rows()


def build_stage5():
    """2-1 凍てつく氷原"""
    MW, MH, G = 222, 26, 23
    b = Builder(MW, MH)
    b.fill(0, G, MW - 1, MH - 1, "s")
    b.fill(16, G, 30, G, "I")                     # 凍った路面
    b.fill(40, G - 8, 56, G - 7, "I")             # 氷の棚（下につらら）
    b.fill(60, G - 2, 66, G - 1, "s")             # 雪の小山
    b.fill(62, G - 3, 64, G - 3, "s")
    b.fill(70, G, 102, G, "I")                    # 凍った湖（すべる床と穴）
    for x0 in (78, 90):
        b.fill(x0, G, x0 + 2, MH - 1, ".")
    b.fill(108, G - 1, 109, G - 1, "s")           # 高台
    b.fill(110, G - 3, 140, G - 1, "s")
    b.fill(118, G - 3, 132, G - 3, "I")
    b.fill(146, G - 9, 170, G - 8, "I")           # 氷の洞（天井につらら）
    b.fill(146, G, 170, G, "I")
    b.fill(194, G, 199, G, "I")                   # ボス部屋の中央だけ氷（足場のまわりは雪）
    b.fill(185, G - 3, 188, G - 3, "-")           # 戦車の突進をかわす足場（3か所）
    b.fill(195, G - 3, 198, G - 3, "-")
    b.fill(205, G - 3, 208, G - 3, "-")
    b.fill(MW - 1, 0, MW - 1, G - 1, "s")

    b.put(3, G - 1, "P")
    for x, y in ((24, G - 1), (63, G - 4), (124, G - 4), (158, G - 1), (174, G - 1)):
        b.put(x, y, "C")
    for x, y in ((10, G - 3), (84, G - 4), (96, G - 4), (130, G - 6), (165, G - 3)):
        b.put(x, y, "*")
    for x, y in ((34, G - 1), (100, G - 1), (150, G - 1)):
        b.put(x, y, "Z")
    for x, y in ((52, G - 1), (115, G - 4), (163, G - 1)):
        b.put(x, y, "E")
    for x, y in ((30, 8), (86, 9), (136, 7)):
        b.put(x, y, "B")
    b.put(138, G - 4, "U")
    for x in (43, 47, 51, 55):
        b.put(x, G - 6, "A")
    for x in (149, 154, 159, 164, 168):
        b.put(x, G - 7, "A")
    for x, y in ((68, G - 1), (112, G - 4)):
        b.put(x, y, "O")
    for x, y in ((7, G - 1), (144, G - 1)):
        b.put(x, y, "X")
    b.put(106, G - 1, "F")
    b.put(175, G - 1, "F")
    b.put(206, G - 1, "T")
    b.put(216, G - 1, "G")
    return b.rows()


def build_stage6():
    """2-2 溶岩の地下洞"""
    MW, MH, G = 232, 26, 23
    b = Builder(MW, MH)
    b.fill(0, 0, MW - 1, 3, "#")                  # 天井
    for x in range(0, MW, 6):
        b.fill(x, 4, x + 1, 4, "#")
    b.fill(0, G, MW - 1, MH - 1, "#")
    for x0, x1 in ((20, 26), (46, 60), (84, 100), (130, 142), (160, 170)):   # 溶岩の池
        b.fill(x0, G, x1, MH - 1, "&")
    b.fill(23, G, 23, MH - 1, "#")                # 飛び石
    b.fill(64, G - 3, 76, G - 1, "#")             # 岩棚
    b.fill(106, G - 2, 107, G - 1, "#")
    b.fill(108, G - 4, 124, G - 1, "#")
    b.fill(MW - 1, 0, MW - 1, G - 1, "#")

    b.put(3, G - 1, "P")
    for x, y in ((10, G - 1), (70, G - 4), (114, G - 5), (150, G - 1), (174, G - 1)):
        b.put(x, y, "C")
    for x, y in ((52, G - 6), (92, G - 7), (136, G - 5), (164, G - 5)):
        b.put(x, y, "*")
    for x in (25, 54, 88, 99, 139, 168):
        b.put(x, G, "L")
    for x in (30, 36, 66, 72, 114, 120, 150, 156):
        b.put(x, 5, "A")
    for x, y in ((40, 9), (104, 8), (146, 9)):
        b.put(x, y, "B")
    for x, y in ((40, G - 1), (118, G - 5), (152, G - 1)):
        b.put(x, y, "E")
    b.put(75, G - 4, "U")
    b.put(122, G - 5, "U")
    for x, y in ((32, G - 1), (110, G - 5)):
        b.put(x, y, "O")
    for x, y in ((6, G - 1), (127, G - 1)):
        b.put(x, y, "X")
    b.put(66, G - 4, "F")
    b.put(176, G - 1, "F")
    b.put(212, G - 1, "Y")
    b.put(226, G - 1, "G")
    return b.rows()


def build_stage7():
    """2-3 氷の要塞（ワールド2の最終面）"""
    MW, MH, G = 244, 26, 23
    b = Builder(MW, MH)
    b.fill(0, G, MW - 1, MH - 1, "=")
    b.fill(0, G, 42, MH - 1, "s")                 # 要塞の外：雪原
    b.fill(20, G, 30, G, "I")
    b.fill(34, G - 7, 42, G - 6, "s")             # 城門のひさし（つらら）
    b.fill(44, 0, MW - 1, 2, "=")                 # 要塞の天井
    b.fill(44, 3, 44, G - 5, "=")                 # 城壁（入口の上）
    b.fill(54, G, 61, G, ">")                     # 電流床へ運ぶコンベア
    b.fill(62, G - 1, 66, G - 1, "^")
    b.fill(61, G - 3, 67, G - 3, "-")
    b.fill(100, 15, 132, 15, "=")                 # 上下2ルート
    b.fill(99, 15, 99, G - 1, "H")
    b.fill(140, G, 152, G, "<")
    b.fill(156, G - 1, 159, G - 1, "^")
    b.fill(155, G - 3, 160, G - 3, "-")
    b.fill(206, G - 3, 209, G - 3, "-")           # ボス部屋の足場
    b.fill(228, G - 3, 231, G - 3, "-")
    b.fill(MW - 1, 0, MW - 1, G - 1, "=")

    b.put(3, G - 1, "P")
    for x, y in ((16, G - 1), (70, G - 1), (118, 14), (196, G - 1)):
        b.put(x, y, "C")
    for x, y in ((24, G - 3), (64, G - 5), (110, 13), (158, G - 5), (202, G - 3)):
        b.put(x, y, "*")
    for x in (36, 39, 42):
        b.put(x, G - 5, "A")
    for x, y in ((12, G - 1), (110, G - 1), (146, G - 1), (186, G - 1)):
        b.put(x, y, "E")
    for x, y in ((28, 8), (124, 6), (150, 9)):
        b.put(x, y, "B")
    for x in (106, 120, 178):
        b.put(x, 3, "V")
    b.put(192, G - 1, "U")
    for x, y in ((92, G - 1), (136, G - 1)):
        b.put(x, y, "O")
    b.put(8, G - 1, "X")
    b.put(97, G - 1, "F")
    b.put(200, G - 1, "F")
    b.put(218, 15, "N")                           # 回転の中心（下側の球が床すれすれを通る高さ）
    b.put(240, G - 1, "G")
    return b.rows()


STAGES = [
    dict(
        name=("1-1 墜落地点", "1-1 CRASH SITE"),
        build=build_stage1,
        theme="crash",
        bgm=BGM_STAGE,
        spawn_zones=[(4, 36), (42, 87), (92, 99), (104, 135), (154, 168)],
        smoke=[(18, 19), (61, 19), (141, 22), (177, 21)],   # 煙が上がる場所（タイル座標）
        spawn_every=170, spawn_max=2, spawn_chance=0.6,      # 1面はやさしめ
        turret_cd=150,
        boss=dict(hp=24, bomb_every=22),
    ),
    dict(
        name=("1-2 酸の湿地", "1-2 ACID MARSH"),
        build=build_stage2,
        theme="marsh",
        bgm=BGM_STAGE2,
        spawn_zones=[(4, 20), (28, 46), (62, 86), (106, 120), (136, 165)],
        smoke=[],
        # 動く足場: (タイルx, タイルy, 幅, "h"=横/"v"=縦, 移動量px, 周期フレーム, 位相)
        platforms=[(49, 21, 3, "h", 64, 240, 0.0),
                   (89, 21, 3, "h", 48, 200, 0.0),
                   (96, 20, 3, "h", 48, 200, 0.5),
                   (109, 21, 2, "v", 56, 260, 0.0),
                   (191, 19, 3, "h", 80, 260, 0.0)],
        spawn_every=150, spawn_max=2, spawn_chance=0.7,
        turret_cd=130,
        boss=dict(hp=52),
    ),
    dict(
        name=("1-3 中継塔", "1-3 RELAY TOWER"),
        build=build_stage3,
        theme="tower",
        bgm=BGM_STAGE3,
        vertical=True,
        arena_y=24 * 8,
        hatch=[(28, 24)],
        spawn_zones=[],
        smoke=[],
        platforms=[(3, 97, 5, "v", 96, 300, 0.0),        # F2 → F3 のリフト
                   (9, 61, 3, "h", 80, 260, 0.0)],       # F7 の横移動足場
        crumbles=[(22, 82, 2), (15, 52, 2)],
        lasers=[(26, 74, 5, "h", 80, 100, 0.0),          # はしごを横切るレーザー
                (12, 61, 6, "v", 70, 90, 0.3),           # 通路をふさぐレーザー
                (14, 39, 5, "h", 70, 110, 0.5)],
        turret_cd=140,
        turret_range_y=40,          # 砲台はほぼ同じ階にいるときだけ撃つ
        drone_wake_y=60,            # ドローンは近い高さに来たら起動
        boss=dict(hp=52),
    ),
    dict(
        name=("1-4 敵母艦", "1-4 MOTHERSHIP"),
        mission=("最終ミッション", "FINAL MISSION"),
        build=build_stage4,
        theme="ship",
        bgm=BGM_STAGE4,
        final=True,
        spawn_zones=[(4, 30), (100, 118), (122, 150)],
        smoke=[],
        crushers=[(50, 2, 70, 0.0), (58, 2, 70, 0.33), (66, 2, 70, 0.66),
                  (154, 2, 60, 0.0), (160, 2, 60, 0.5)],
        lasers=[(96, 16, 7, "v", 70, 90, 0.0)],
        spawn_every=160, spawn_max=2, spawn_chance=0.6,
        turret_cd=140,
        ceil_cd=130,
        arena_x_max=202 * 8,
        escape=25,
        escape_open=[(201, y) for y in range(3, 23)],
        boss=dict(hp=44, arm_hp=18),
    ),
    dict(
        name=("2-1 凍てつく氷原", "2-1 FROZEN FIELD"),
        build=build_stage5,
        theme="ice",
        bgm=BGM_ICE,
        spawn_zones=[(4, 38), (57, 70), (103, 145)],
        smoke=[],
        spawn_every=150, spawn_max=2, spawn_chance=0.7,
        turret_cd=130,
        arena=(178 * 8, 215 * 8),
        boss=dict(hp=48),
    ),
    dict(
        name=("2-2 溶岩の地下洞", "2-2 MAGMA CAVERN"),
        build=build_stage6,
        theme="magma",
        bgm=BGM_MAGMA,
        spawn_zones=[(4, 19), (27, 45), (61, 83), (101, 129), (143, 159), (171, 176)],
        smoke=[],
        platforms=[(47, 21, 3, "h", 72, 240, 0.0),
                   (131, 21, 3, "h", 64, 220, 0.5)],
        crumbles=[(86, 20, 2), (91, 19, 2), (96, 20, 2), (162, 20, 2), (166, 20, 2)],
        # 火柱は「岸で見送ってから渡る」場所に置く（動く足場の通り道には置かない）
        jets=[(21, 120, 0.25), (89, 150, 0.0), (94, 150, 0.0), (164, 160, 0.5)],
        spawn_every=150, spawn_max=2, spawn_chance=0.7,
        turret_cd=130,
        arena=(180 * 8, 225 * 8),
        boss=dict(hp=70),
    ),
    dict(
        name=("2-3 氷の要塞", "2-3 ICE FORTRESS"),
        mission=("ワールド2 最終ミッション", "WORLD 2 FINAL MISSION"),
        build=build_stage7,
        theme="fort",
        bgm=BGM_FORT,
        final=True,
        world=2,
        spawn_zones=[(4, 40), (100, 135), (140, 160), (176, 196)],
        smoke=[],
        crushers=[(74, 2, 70, 0.0), (80, 2, 70, 0.33), (86, 2, 70, 0.66),
                  (166, 2, 60, 0.0), (172, 2, 60, 0.5)],
        lasers=[(114, 16, 7, "v", 70, 90, 0.0)],
        spawn_every=150, spawn_max=2, spawn_chance=0.7,
        turret_cd=130,
        ceil_cd=120,
        boss=dict(hp=18),
    ),
]

WORLD_NODES = {
    "base": dict(x=40, y=164, name=("降下艇", "DROPSHIP"), kind="home", stage=None),
    "1-1":  dict(x=92, y=128, name=("1-1 墜落地点", "1-1 CRASH SITE"), kind="stage", stage=0),
    "1-2":  dict(x=150, y=158, name=("1-2 酸の湿地", "1-2 ACID MARSH"), kind="stage", stage=1),
    "1-3":  dict(x=182, y=104, name=("1-3 中継塔", "1-3 RELAY TOWER"), kind="stage", stage=2),
    "ship": dict(x=222, y=58, name=("敵母艦", "MOTHERSHIP"), kind="castle", stage=3),
}
WORLD_EDGES = [("base", "1-1"), ("1-1", "1-2"), ("1-2", "1-3"), ("1-3", "ship")]

# ---- ワールド2（氷の衛星フロスト）。"w" はノードが属するワールド、"target" は行き先ワールド
WORLD_NODES.update({
    "w1warp": dict(x=244, y=100, name=("ワールド2へ（氷の衛星フロスト）", "TO WORLD 2 (FROST MOON)"),
                   kind="warp", stage=None, target=2, w=1),
    "w2base": dict(x=40, y=160, name=("着陸地点（ワールド1へ戻る）", "LANDING SITE (TO WORLD 1)"),
                   kind="home", stage=None, target=1, w=2),
    "2-1": dict(x=96, y=126, name=("2-1 凍てつく氷原", "2-1 FROZEN FIELD"), kind="stage", stage=4, w=2),
    "2-2": dict(x=150, y=164, name=("2-2 溶岩の地下洞", "2-2 MAGMA CAVERN"), kind="stage", stage=5, w=2),
    "2-3": dict(x=206, y=92, name=("2-3 氷の要塞", "2-3 ICE FORTRESS"), kind="fort", stage=6, w=2),
})
for _n in WORLD_NODES.values():
    _n.setdefault("w", 1)
WORLD_EDGES += [("ship", "w1warp"), ("w2base", "2-1"), ("2-1", "2-2"), ("2-2", "2-3")]
WORLDS = {
    1: dict(name=("ゾーン1  惑星ゼータ", "ZONE 1  PLANET ZETA"), arrive="w1warp"),
    2: dict(name=("ゾーン2  氷の衛星フロスト", "ZONE 2  FROST MOON"), arrive="w2base"),
}


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
                    row[tx] = {"J": ACID, "W": ACID, "R": "H", "L": LAVA}.get(c, ".")
        self.img = None
        self.anim_tiles = []
        self.acid_tiles = []
        self.lava_tiles = []

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
        if c in "#=%Is":
            bx, row = {"#": (0, 0), "=": (0, 8), "%": (0, 24), "I": (64, 0), "s": (0, 32)}[c]
            hsh = (tx * 73856093 ^ ty * 19349663) & 0xFFFF
            if c in "#%Is":
                var = 3 if hsh % 11 == 0 else hsh % 3
            else:
                var = 0 if hsh % 10 < 7 else 1 + hsh % 3
            layers = [(bx + var * 8, row)]

            def exposed(dx, dy):
                return self.get(tx + dx, ty + dy) not in SOLID
            if exposed(0, -1):
                layers.append((bx + 32, row))
            if exposed(-1, 0):
                layers.append((bx + 40, row))
            if exposed(1, 0):
                layers.append((bx + 48, row))
            if exposed(0, 1):
                layers.append((bx + 56, row))
            return layers
        return [{"K": (0, 16), "-": (8, 16), "H": (16, 16), "|": (24, 16), "_": (64, 24)}[c]]

    def render(self, tiles_img):
        """動かない地形を1枚の画像に焼き込む（毎フレームは blt 1回で済む）"""
        img = pyxel.Image(self.w * TS, self.h * TS)
        img.cls(KEY)
        self.anim_tiles = []
        self.acid_tiles = []
        self.lava_tiles = []
        self.conv_tiles = []
        for ty in range(self.h):
            for tx in range(self.w):
                c = self.tiles[ty][tx]
                if c == ".":
                    continue
                if c == SPIKE:
                    self.anim_tiles.append((tx, ty))
                    continue
                if c in CONVEYOR:                         # コンベアはアニメーション
                    self.conv_tiles.append((tx, ty, c))
                    continue
                if c in LIQUID:
                    body = (80, 16) if c == ACID else (88, 32)
                    if self.get(tx, ty - 1) == c:         # 中身は焼き込む
                        img.blt(tx * TS, ty * TS, tiles_img, body[0], body[1], TS, TS, KEY)
                    elif c == ACID:                       # 表面はアニメーション
                        self.acid_tiles.append((tx, ty))
                    else:
                        self.lava_tiles.append((tx, ty))
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


THEMES = {"crash": "", "marsh": "marsh_", "tower": "tower_", "ship": "ship_",
          "ice": "ice_", "magma": "magma_", "fort": "fort_"}   # テーマ名 -> ファイル名の頭
# 背景レイヤーの動き： (横スクロール率, 縦スクロール率, 基準の上下ずらし, 縦にくり返すか)
_FLAT = {"far": (0.08, 0, 0, False), "mid": (0.25, 0, 0, False),
         "near": (0.5, 0, 0, False), "front": (1.3, 0, 0, False)}
LAYER_CFG = {
    "crash": _FLAT,
    "marsh": _FLAT,
    "ship": _FLAT,
    "ice": _FLAT,
    "magma": _FLAT,
    "fort": _FLAT,
    "tower": {"far": (0.05, 0.12, 0, False), "mid": (0.15, 0.45, -260, False),
              "near": (0.4, 0.6, 0, True), "front": (1.0, 1.0, 0, False)},
}
LAYERS = ["sky", "far", "mid", "near", "front"]


def merge_cells(png, base, cell):
    """PNG のマスのうち、何か描いてあるマスだけを内蔵の絵に上書きする
    （古い PNG にまだ無いコマ・タイルは内蔵の絵で補われる）"""
    for v in range(0, min(png.height, base.height) - cell + 1, cell):
        for u in range(0, min(png.width, base.width) - cell + 1, cell):
            if any(png.pget(u + i, v + j) != KEY for j in range(cell) for i in range(cell)):
                base.blt(u, v, png, u, v, cell, cell)
    return base


class Assets:
    def __init__(self):
        self.load()

    def _load_one(self, here, name):
        path = os.path.join(here, ASSET_DIR, name + ".png")
        if os.path.exists(path):
            try:
                img = png_to_image(path, NA.SPEC[name])
                self.src[name] = "png"
                if name in ("hero", "tiles"):
                    base = canvas_to_image(NA.GENERATORS[name]())
                    img = merge_cells(img, base, SPR if name == "hero" else TS)
                return img
            except Exception as ex:
                print("asset load failed:", path, ex)
        self.src[name] = "built-in"
        return canvas_to_image(NA.GENERATORS[name]())

    def load(self):
        here = os.path.dirname(os.path.abspath(__file__))
        self.src = {}
        self.hero = self._load_one(here, "hero")
        self.tiles = self._load_one(here, "tiles")
        self.layers, self.lights = {}, {}
        for theme, pre in THEMES.items():
            self.layers[theme] = {ly: self._load_one(here, pre + ly) for ly in LAYERS}
            self.lights[theme] = {ly: (list(NA.LIGHTS.get(pre + ly, []))
                                       if self.src[pre + ly] == "built-in" else [])
                                  for ly in ("far", "mid")}

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
        if shoot:                         # はしごの上で撃つときは横向きのポーズ
            return "shoot"
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


class AcidBlob(EnemyShot):
    """酸の玉。放物線を描いて飛ぶ"""
    kind = "blob"
    grav = 0.12


class Platform:
    """動く足場（乗ると一緒に動く）
    (タイルx, タイルy, 幅タイル, "h"/"v", 移動量px, 周期フレーム, 位相0〜1)"""

    def __init__(self, tx, ty, wt, axis, rng, period, phase=0.0):
        self.x0, self.y0 = tx * TS, ty * TS
        self.w, self.h = wt * TS, 4
        self.axis, self.rng, self.period = axis, rng, period
        self.t = int(phase * period)
        self.dx = self.dy = 0.0
        self.x, self.y = self.pos()

    def pos(self):
        # 両端で少し止まる（約20フレーム）。端ではぴったり床の高さにそろう
        k = (1 - math.cos(2 * math.pi * self.t / self.period)) / 2
        k = clamp(k * 1.12 - 0.06, 0.0, 1.0)
        if self.axis == "h":
            return self.x0 + self.rng * k, self.y0
        return self.x0, self.y0 - self.rng * k

    def update(self):
        self.t += 1
        nx, ny = self.pos()
        self.dx, self.dy = nx - self.x, ny - self.y
        self.x, self.y = nx, ny


class Crumble(Platform):
    """崩れる足場：一度乗ると震えだし、少しすると落ちる。しばらくすると元に戻る"""
    BREAK = 40
    RESPAWN = 240

    def __init__(self, tx, ty, wt):
        self.x0, self.y0 = tx * TS, ty * TS
        self.x, self.y = self.x0, self.y0
        self.w, self.h = wt * TS, 4
        self.dx = self.dy = 0.0
        self.solid = True
        self.state = "idle"
        self.touch = 0
        self.timer = 0
        self.fy = self.fv = 0.0

    def update(self):
        pass

    def step(self, g):
        p = g.p
        if self.state == "idle":
            if self.touch == 0 and p.ride is self:
                self.touch = 1
                sfx(23, 3)
            elif self.touch > 0:
                self.touch += 1
                if self.touch >= self.BREAK:
                    self.state, self.solid, self.timer = "fall", False, 0
                    self.fy = self.fv = 0.0
                    if p.ride is self:
                        p.ride = None
                        p.on_ground = False
                    for _ in range(6):
                        g.parts.append([self.x + random.uniform(0, self.w), self.y + 2,
                                        random.uniform(-1, 1), random.uniform(-1, 0.5),
                                        random.randint(30, 50), random.choice((13, 5)), 0.15, 2])
                    sfx(24, 3)
        else:
            self.timer += 1
            self.fv = min(self.fv + 0.3, MAX_FALL)
            self.fy += self.fv
            if self.timer >= self.RESPAWN:
                pr = (p.x + p.w > self.x - 4 and p.x < self.x + self.w + 4 and
                      p.y + p.h > self.y - 4 and p.y < self.y + 8)
                if not pr:
                    self.state, self.solid, self.touch = "idle", True, 0

    def draw(self, g):
        if self.state == "fall":
            if self.fy < 220:
                self._body(self.x, self.y + self.fy, 1)
            if self.timer > self.RESPAWN - 30 and (self.timer // 3) % 2:
                pyxel.rectb(self.x, self.y, self.w, 4, 5)
            return
        sh = 0
        if self.touch > 0:
            sh = (1 if (self.touch // 2) % 2 else -1) if self.touch > self.BREAK // 2 else (self.touch // 4) % 2
        self._body(self.x + sh, self.y, 0)

    def _body(self, x, y, dark):
        x, y, w = int(x), int(y), self.w
        pyxel.rect(x, y, w, 4, 0)
        pyxel.rect(x + 1, y, w - 2, 3, 5 if dark else 4)
        pyxel.line(x + 1, y, x + w - 2, y, 1 if dark else 9)
        for i in range(x + 3, x + w - 2, 5):           # ひび
            pyxel.line(i, y, i + 1, y + 2, 0)
        pyxel.pset(x + 1, y + 3, 2)
        pyxel.pset(x + w - 2, y + 3, 2)


class LaserGate:
    """点滅するレーザーゲート。点く前に予告（点滅）する
    (タイルx, タイルy, 長さ, "h"/"v", 点灯フレーム, 消灯フレーム, 位相0〜1)"""
    WARN = 36

    def __init__(self, tx, ty, ln, orient, on_t, off_t, phase=0.0):
        self.orient, self.on_t, self.off_t = orient, on_t, off_t
        self.period = on_t + off_t
        self.t = int(phase * self.period)
        if orient == "h":
            self.x, self.y, self.w, self.h = tx * TS, ty * TS + 2, ln * TS, 4
        else:
            self.x, self.y, self.w, self.h = tx * TS + 2, ty * TS, 4, ln * TS

    def k(self):
        return self.t % self.period

    def on(self):
        return self.k() >= self.off_t

    def warning(self):
        return self.off_t - self.WARN <= self.k() < self.off_t

    def update(self, g):
        self.t += 1
        if self.k() == self.off_t and abs(self.y - (g.cam_y + VIEW_H / 2)) < VIEW_H:
            sfx(25, 3)

    def draw(self, g):
        x, y, w, h = int(self.x), int(self.y), self.w, self.h
        lamp = 8 if self.on() else (10 if self.warning() and (g.gt // 4) % 2 else 11)
        if self.orient == "h":
            ends = ((x - 4, y - 3, 4, 10), (x + w, y - 3, 4, 10))
        else:
            ends = ((x - 3, y - 4, 10, 4), (x - 3, y + h, 10, 4))
        for ex, ey, ew, eh in ends:
            pyxel.rect(ex, ey, ew, eh, 0)
            pyxel.rect(ex + 1, ey + 1, ew - 2, eh - 2, 5)
            pyxel.pset(ex + ew // 2, ey + eh // 2, lamp)
        if self.on():
            core = 7 if (g.gt // 2) % 2 else 14
            if self.orient == "h":
                pyxel.rect(x, y, w, 4, 8)
                pyxel.line(x, y + 1 + (g.gt % 2), x + w - 1, y + 1 + (g.gt % 2), core)
            else:
                pyxel.rect(x, y, 4, h, 8)
                pyxel.line(x + 1 + (g.gt % 2), y, x + 1 + (g.gt % 2), y + h - 1, core)
        elif self.warning() and (g.gt // 4) % 2:
            if self.orient == "h":
                for i in range(x, x + w, 4):
                    pyxel.pset(i, y + 1, 2)
            else:
                for i in range(y, y + h, 4):
                    pyxel.pset(x + 1, i, 2)


class Box:
    """当たり判定用の箱"""

    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h


class Shell(EnemyShot):
    """迫撃砲の砲弾：山なりに飛んで床で爆発する。撃ち落とせる"""
    kind = "shell"
    grav = 0.12


class Rock(Shell):
    """溶岩巨人が投げる岩：山なりに飛んで床で砕ける。撃ち落とせる"""
    kind = "rock"


class Crusher:
    """天井から落ちてくるプレス機。点滅で予告 → 落下 → しばらく止まる → ゆっくり戻る
    (タイルx, 幅タイル, 待ちフレーム, 位相0〜1)"""
    WARN = 32
    HOLD = 22

    def __init__(self, stage, tx, wt, wait=70, phase=0.0):
        self.x, self.w = tx * TS, wt * TS
        cx = self.x + self.w / 2
        self.top = 0
        while stage.solid(cx, self.top) and self.top < stage.h * TS:
            self.top += 1
        floor = self.top
        while not stage.solid(cx, floor) and floor < stage.h * TS:
            floor += 1
        self.max_ext = floor - self.top
        self.wait = wait
        self.state = "up"
        self.timer = int(phase * (wait + self.WARN + 60))
        self.ext = 0.0

    def box(self):
        return Box(self.x + 1, self.top, self.w - 2, self.ext)

    def update(self, g):
        self.timer += 1
        st = self.state
        if st == "up":
            self.ext = 0.0
            if self.timer >= self.wait:
                self.state, self.timer = "warn", 0
        elif st == "warn":
            self.ext = 2.0 if (self.timer // 3) % 2 else 0.0
            if self.timer >= self.WARN:
                self.state, self.timer = "slam", 0
        elif st == "slam":
            self.ext = min(self.max_ext, self.ext + 10.0)
            if self.ext >= self.max_ext:
                self.state, self.timer = "hold", 0
                if abs(self.x - (g.cam_x + W / 2)) < W:
                    sfx(27, 3)
                    g.shake = max(g.shake, 2.5)
                    for _ in range(8):
                        g.parts.append([self.x + random.uniform(0, self.w), self.top + self.ext - 1,
                                        random.uniform(-1.5, 1.5), random.uniform(-1.2, -0.2),
                                        random.randint(20, 35), 13, 0.05, 1])
        elif st == "hold":
            if self.timer >= self.HOLD:
                self.state, self.timer = "rise", 0
        elif st == "rise":
            self.ext = max(0.0, self.ext - 2.2)
            if self.ext <= 0:
                self.state, self.timer = "up", 0
        if self.ext > 8:
            bx = self.box()
            for e in g.enemies:                          # 生体兵もつぶれる
                if isinstance(e, Mutant) and e.alive and e.hittable and overlap(bx, e):
                    e.alive = False
                    g.boom(e.cx(), e.cy(), 6, debris=4, smoke=1, sound=False)
            p = g.p
            if not p.dead and p.invinc == 0 and overlap(bx, p):
                g.toast(L("プレス機に挟まれた！", "CRUSHED!"), 60)
                g.hurt_player(self.x + self.w / 2)

    def draw(self, g):
        x, top, w = int(self.x), int(self.top), self.w
        ext = int(self.ext)
        pyxel.rect(x - 2, top, w + 4, 3, 0)                  # 取り付け部
        pyxel.rect(x - 1, top, w + 2, 2, 5)
        head_h = 10
        hy = top + 2 + ext
        if ext > 0:                                          # ロッド
            rx = x + w // 2 - 3
            pyxel.rect(rx, top + 2, 6, ext, 0)
            pyxel.rect(rx + 1, top + 2, 4, ext, 13)
            pyxel.line(rx + 1, top + 2, rx + 1, top + 1 + ext, 7)
        pyxel.rect(x, hy, w, head_h, 0)                      # 頭
        pyxel.rect(x + 1, hy + 1, w - 2, head_h - 2, 5)
        pyxel.line(x + 1, hy + 1, x + w - 2, hy + 1, 13)
        for i in range(w - 2):                               # 警告ストライプ
            col = 10 if ((i + (hy + head_h - 3)) // 2) % 2 else 0
            pyxel.pset(x + 1 + i, hy + head_h - 3, col)
            pyxel.pset(x + 1 + i, hy + head_h - 2, col)
        lamp = 8 if self.state in ("warn", "slam") and (g.gt // 3) % 2 else 2
        pyxel.pset(x + w // 2, hy + 4, lamp)
        pyxel.pset(x + w // 2 - 1, hy + 4, lamp)


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
        self.grab = 0
        self.hover_t = 0
        self.ride = None          # 乗っている動く足場
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
        return (self.x < g.cam_x - margin or self.x > g.cam_x + W + margin or
                self.y > g.cam_y + VIEW_H + 120 or self.y < g.cam_y - 160)

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
        if g.stage.tile_at(self.x + 4, self.y + self.h - 1) in LIQUID:    # 酸・溶岩で溶ける
            self.alive = False
            g.acid_splash(self.x + 4, self.y + self.h - 2, 8)
            return
        if self.y > g.stage.h * TS or self.far_from_camera(g):
            self.alive = False

    def draw(self, g):
        x, y = int(self.x), int(self.y)
        d = self.dir or 1
        if self.state == "warp":
            k = self.wt / 36
            bw = max(1, int(12 * (1 - k)))
            top = y - 60
            for yy in range(y - 2, y - 60, -2):        # 上の床で光線を止める
                if g.stage.solid(x + 4, yy):
                    top = yy + 2
                    break
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
            if abs(p.x - self.x) < 80 and abs(p.y - self.y) < g.sdef.get("drone_wake_y", 9999):
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
        if self.cool <= 0 and abs(dx) < 150 and abs(p.y - self.y) < g.sdef.get("turret_range_y", 110) and not p.dead:
            self.cool = g.sdef.get("turret_cd", 110)
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
    label = "MECH"
    warn_msg = ("大型メカ接近", "HEAVY MECH APPROACHING")
    defeat_msg = ("メカを撃破！", "MECH DOWN!")
    phase_msgs = {2: ("装甲にひびが入った！", "ARMOR CRACKED!"),
                  3: ("メカが暴走を始めた！", "THE MECH IS GOING BERSERK!")}
    phase_marks = (0.3, 0.6)
    HOME_Y = 52              # 上空。上撃ち・斜め撃ちで狙う高さ
    BOMB_Y = 30
    PATTERNS = {1: ["bomb", "swoop"],
                2: ["bomb", "launch", "swoop"],
                3: ["swoop", "bomb", "launch", "swoop"]}

    def __init__(self, x, y, hp=None, bomb_every=16):
        hp = hp or self.MAX_HP
        super().__init__(x, -30, 20, 14, hp)
        self.max_hp = hp
        self.bomb_every = bomb_every
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

        ph = 1 if self.hp > self.max_hp * 0.6 else 2 if self.hp > self.max_hp * 0.3 else 3
        if ph > self.phase and self.state != "enter":
            self.phase = ph
            self.pat_i = 0
            self.set_state("hover")
            g.boss_phase(self)
        fast = self.phase == 3
        if self.phase >= 2 and random.random() < (0.15 if fast else 0.07):
            g.parts.append([self.x + random.uniform(2, 18), self.y + 4, random.uniform(-0.3, 0.3),
                            random.uniform(-0.8, -0.3), 40, 13, 0, 1])

        st = self.state
        if st == "enter":
            if not g.boss_seen or g.warn_t > 30:
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
        elif st == "bomb_prep":
            tx = g.cam_x + (6 if self.run_dir > 0 else W - self.w - 6)
            dx, dy = tx - self.x, self.BOMB_Y - self.y
            d = math.hypot(dx, dy)
            if d < 2.8 or self.timer > 120:
                self.set_state("bomb_run")
            else:
                self.x += dx / d * 2.8
                self.y += dy / d * 2.8
        elif st == "bomb_run":
            self.x += self.run_dir * (2.0 if fast else 1.5)
            self.y = self.BOMB_Y + math.sin(self.timer * 0.15) * 2
            be = max(9, self.bomb_every - 5) if fast else self.bomb_every
            if self.timer % be == be // 2:
                g.eshots.append(Bomb(self.x + 10, self.y + 13, self.run_dir * 0.3))
                sfx(17, 3)
            end = (self.x >= g.cam_x + W - self.w - 6) if self.run_dir > 0 else (self.x <= g.cam_x + 6)
            if end or self.timer > 300:
                self.set_state("hover")
        elif st == "launch":
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
        if self.phase >= 2:
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
        if self.state in ("bomb_run", "launch"):
            pyxel.rect(x + 7, y + 12, 6, 2, 0)
            pyxel.pset(x + 9 + (self.t // 4) % 2, y + 13, 8)
        if self.state == "dying" and (self.t // 3) % 2:
            pyxel.rect(x + 2, y + 2, 16, 11, 8)


class Leaper(Enemy):
    """酸ガエル：酸の池に潜み、近づくと飛び出してくる。潜っている間は無敵"""
    score = 200
    V0, G = 4.6, 0.2              # 飛び出す速さ / 重力（約53px の高さ、46フレーム）

    def __init__(self, x, surf, lava=False):
        super().__init__(x, surf + 2, 10, 10, 2)
        self.base_x, self.surf = x, surf
        self.c1, self.c2 = (9, 8) if lava else (11, 3)     # 溶岩ガエルは赤い
        self.state = "lurk"
        self.cool = random.randint(30, 90)
        self.lt = 0
        self.off = 0.0

    @property
    def hittable(self):
        return self.state == "leap"

    @property
    def harmful(self):
        return self.state == "leap"

    def update(self, g):
        self.t += 1
        p = g.p
        if self.state == "lurk":
            self.x, self.y = self.base_x, self.surf + 2
            self.cool -= 1
            if random.random() < 0.03:
                g.parts.append([self.base_x + random.uniform(2, 8), self.surf + 2, 0, -0.3, 14, self.c1, 0, 0])
            if self.cool <= 0 and abs(p.x + 4 - (self.base_x + 5)) < 72 and not p.dead:
                self.state, self.lt = "leap", 0
                self.off = clamp(p.x + 4 - (self.base_x + 5), -20, 20)
                g.acid_splash(self.base_x + 5, self.surf, 6, sound=False)
                sfx(20, 3)
        else:
            self.lt += 1
            T = 2 * self.V0 / self.G
            self.y = self.surf + 2 - (self.V0 * self.lt - self.G / 2 * self.lt ** 2)
            self.x = self.base_x + self.off * math.sin(math.pi * min(1.0, self.lt / T))
            if self.t % 4 == 0:
                g.parts.append([self.x + 5, self.y + 9, random.uniform(-0.3, 0.3), 0.5, 12, self.c1, 0.1, 0])
            if self.lt >= T:
                self.state = "lurk"
                self.cool = random.randint(70, 120)
                g.acid_splash(self.base_x + 5, self.surf, 6, sound=False)

    def draw(self, g):
        if self.state == "lurk":
            if (self.t // 20) % 5:                      # 水面から目だけ出している
                sx, sy = int(self.base_x), int(self.surf)
                for ex in (sx + 3, sx + 6):
                    pyxel.pset(ex, sy, 10)
                    pyxel.pset(ex, sy + 1, 0)
            return
        x, y = int(self.x), int(self.y)
        up = self.lt < self.V0 / self.G
        body = 7 if self.flash else self.c1
        pyxel.rect(x + 1, y, 8, 10, 0)
        pyxel.rect(x + 2, y + 1, 6, 8, body)
        pyxel.rect(x + 4, y + 2, 2, 6, self.c2)
        hy = y + 2 if up else y + 7
        pyxel.pset(x + 3, hy, 8)
        pyxel.pset(x + 6, hy, 8)
        fy = y + 6 if up else y + 1
        d = 2 if up else -2
        pyxel.tri(x + 1, fy, x - 2, fy + d, x + 1, fy + 3, self.c2)
        pyxel.tri(x + 8, fy, x + 11, fy + d, x + 8, fy + 3, self.c2)
        ty2 = y + 10 if up else y - 1
        pyxel.tri(x + 3, ty2, x + 7, ty2, x + 5, ty2 + (3 if up else -3), self.c2)

    def on_death(self, g):
        g.boom(self.cx(), self.cy(), 6, debris=3)
        g.acid_splash(self.cx(), self.cy(), 6, sound=False)


class Spitter(Enemy):
    """酸吐き草：閉じている間は弾をはじく。開いたら酸の玉を山なりに吐く"""
    score = 300

    def __init__(self, x, y):
        super().__init__(x, y, 10, 10, 3)
        self.state = "closed"
        self.timer = random.randint(0, 60)

    @property
    def armored(self):
        return self.state == "closed"

    def update(self, g):
        self.t += 1
        self.timer += 1
        p = g.p
        dist = abs(p.x + 4 - (self.x + 5))
        if self.state == "closed":
            if self.timer >= 110 and dist < 150 and not p.dead:
                self.state, self.timer = "open", 0
        else:
            if self.timer in (24, 44):
                T = random.choice((40, 50, 60))
                mx, my = self.x + 5, self.y + 1
                vx = clamp((p.x + 4 - mx) / T, -2.2, 2.2)
                vy = (p.y + 6 - my) / T - 0.06 * T
                g.eshots.append(AcidBlob(mx - 3, my - 3, vx, vy))
                sfx(21, 3)
            if self.timer >= 70:
                self.state, self.timer = "closed", 0

    def draw(self, g):
        x, y = int(self.x), int(self.y)
        pyxel.tri(x - 2, y + 10, x + 3, y + 5, x + 4, y + 10, 3)
        pyxel.tri(x + 12, y + 10, x + 7, y + 5, x + 6, y + 10, 3)
        body = 7 if self.flash else 2
        if self.state == "closed":
            pyxel.elli(x + 1, y + 1, 8, 9, 0)
            pyxel.elli(x + 2, y + 2, 6, 7, body)
            pyxel.line(x + 5, y + 2, x + 5, y + 8, 0)
            pyxel.pset(x + 3, y + 4, 8)
        else:
            pyxel.tri(x + 5, y + 6, x - 1, y - 1, x + 3, y + 8, body)
            pyxel.tri(x + 5, y + 6, x + 11, y - 1, x + 7, y + 8, body)
            pyxel.elli(x + 2, y + 2, 6, 7, 0)
            glow = 2 + (1 if self.timer < 24 and (self.t // 4) % 2 else 0)   # 吐く前に光る
            pyxel.circ(x + 5, y + 5, glow, 11)
            pyxel.pset(x + 5, y + 4, 7)
        pyxel.rect(x + 3, y + 9, 4, 1, 3)

    def on_death(self, g):
        g.boom(self.cx(), self.cy(), 7, debris=5)
        if random.random() < 0.3:
            g.items.append(Item("cell", self.x + 1, self.y - 2))


class Worm(Enemy):
    """ボス：酸の主（巨大な酸のワーム）
    酸の池の中を泡を立てて移動し、頭を出して酸の玉を吐く。
    体力50%以下で怒り、速くなって間欠泉を噴き上げる"""
    score = 6000
    boss = True
    MAX_HP = 28
    RISE = 26                 # 頭が出る高さ（立ち撃ちが当たる高さ）
    label = "WORM"
    warn_msg = ("巨大生物反応", "MASSIVE LIFEFORM DETECTED")
    defeat_msg = ("酸の主を撃破！", "ACID WORM DOWN!")
    phase_msgs = {2: ("酸の主が怒り狂っている！", "THE WORM IS ENRAGED!")}
    phase_marks = (0.5,)

    def __init__(self, x, surf, pool, hp=None, **kw):
        hp = hp or self.MAX_HP
        super().__init__(x, surf + 6, 16, 20, hp)     # 当たり判定は頭＋首の上側
        self.max_hp = hp
        self.surf = surf
        self.px0 = (pool[0] + 1) * TS
        self.px1 = pool[1] * TS - 16
        self.phase = 1
        self.state = "enter"
        self.timer = 0
        self.tx = x
        self.n_up = 0

    def visible(self):
        return self.state in ("rise", "spit", "sink", "dying") and self.y < self.surf - 4

    @property
    def hittable(self):
        return self.state != "dying" and self.visible()

    @property
    def harmful(self):
        return self.hittable

    def set_state(self, st):
        self.state, self.timer = st, 0

    def start_dying(self):
        self.set_state("dying")

    def spit_times(self):
        # 前の玉が落ちきってから次を吐く（着弾が重ならないように）
        return (14, 44, 74) if self.phase == 2 else (24, 56)

    def aim_x(self, g):
        # プレイヤーの目の前には出ない（少し離れた位置に浮上）
        return clamp(g.p.x + 4 - 8 + random.choice((-56, -44, 44, 56)), self.px0, self.px1)

    def volleys(self):
        """1回の浮上で吐く玉の数。奇数＝プレイヤーを狙う / 偶数＝プレイヤーの左右を挟む"""
        return (3, 3) if self.phase == 1 else (3, 4, 3)

    def spit(self, g, n, spacing=28):
        p = g.p
        mx, my = self.x + 8, self.y + 11
        for i in range(n):
            T = (54 if self.phase == 1 else 46) + i * 8     # 高い山なり（上から落ちてくる）
            ax = p.x + 4 + (i - (n - 1) / 2) * spacing
            vx = clamp((ax - mx) / T, -2.4, 2.4)
            vy = (p.y + 10 - my) / T - 0.06 * T
            g.eshots.append(AcidBlob(mx - 3, my - 3, vx, vy))
        sfx(21, 3)

    def update(self, g):
        self.t += 1
        self.timer += 1
        st = self.state
        if st == "dying":
            self.y += 0.35
            if self.timer % 6 == 0:
                g.boom(self.x + random.uniform(0, 16), min(self.y + random.uniform(0, 14), self.surf - 2),
                       random.uniform(5, 9), debris=2, smoke=1)
                g.acid_splash(self.x + 8, self.surf, 4, sound=False)
            if self.timer >= 100:
                self.alive = False
                g.boss_destroyed(self)
            return
        if self.phase == 1 and st != "enter" and self.hp <= self.max_hp * 0.5:
            self.phase = 2
            g.boss_phase(self)
        fast = self.phase == 2
        if st == "enter":
            self.y = self.surf + 6
            if g.boss_seen and g.warn_t <= 30:
                self.tx = self.aim_x(g)
                self.set_state("under")
        elif st == "under":                      # 泡を立てて池の中を移動（予告）
            self.y = self.surf + 6
            if self.timer < 30:
                self.tx = self.aim_x(g)
            sp = 1.8 if fast else 1.2
            self.x += clamp(self.tx - self.x, -sp, sp)
            if self.timer % 2 == 0:
                g.parts.append([self.x + 8 + random.uniform(-5, 5), self.surf + 2, 0,
                                random.uniform(-0.6, -0.3), 16, random.choice((11, 7)), 0, 0])
            if abs(self.tx - self.x) < 1 and self.timer >= (40 if fast else 55):
                self.set_state("rise")
                g.acid_splash(self.x + 8, self.surf, 12)
                g.shake = max(g.shake, 2)
        elif st == "rise":
            self.y -= 2.4 if fast else 1.8
            if self.y <= self.surf - self.RISE:
                self.y = self.surf - self.RISE
                self.set_state("spit")
        elif st == "spit":
            self.x = clamp(self.x + math.sin(self.t * 0.08) * 0.4, self.px0, self.px1)
            if self.timer in self.spit_times():
                self.spit(g, self.volleys()[self.spit_times().index(self.timer)])
            if self.timer >= (96 if fast else 84):
                self.set_state("sink")
        elif st == "sink":
            self.y += 2.2
            if self.y >= self.surf + 6:
                self.y = self.surf + 6
                self.n_up += 1
                self.set_state("geyser" if fast and self.n_up % 2 == 0 else "under")
        elif st == "geyser":                     # 池のあちこちから酸の間欠泉
            if self.timer == 1:
                xs = [clamp(g.p.x + 4, self.px0 + 8, self.px1 + 8)]
                xs += [random.uniform(self.px0 + 8, self.px1 + 8) for _ in range(2)]
                for i, gx in enumerate(xs):
                    g.geysers.append(dict(x=gx, y=self.surf, t=-i * 18))
            if self.timer >= 110:
                self.set_state("under")

    def draw(self, g):
        if not self.visible():
            return
        x, y = int(self.x), int(self.y)
        cx = x + 8
        body = 7 if self.flash else 11
        for i in range(3, 0, -1):                 # 首（水面より上だけ）
            k = i / 4
            sy = y + 12 + (self.surf - (y + 12)) * k
            sx = cx + math.sin(self.t * 0.1 + i) * 3 * k
            if sy < self.surf - 2:
                pyxel.circ(sx, sy, 6, 0)
                pyxel.circ(sx, sy, 5, 3)
                pyxel.pset(sx - 2, sy - 2, 11)
        pyxel.circ(cx, y + 7, 8, 0)
        pyxel.circ(cx, y + 7, 7, body)
        pyxel.circ(cx, y + 10, 5, 3)
        for sx in (cx - 5, cx, cx + 5):
            pyxel.tri(sx - 2, y + 1, sx + 2, y + 1, sx, y - 4, 2)
        face = 1 if g.p.x + 4 > cx else -1
        ex = cx + face * 3
        eye = 8 if self.phase == 1 or (self.t // 3) % 2 else 10
        pyxel.circ(ex, y + 5, 2, 0)
        pyxel.pset(ex, y + 5, eye)
        mouth = self.state == "spit" and any(-10 <= self.timer - ft < 6 for ft in self.spit_times())
        if mouth:                                 # 吐く前に口を開く（予告）
            pyxel.rect(cx - 5, y + 9, 10, 4, 0)
            for tx2 in (cx - 4, cx - 1, cx + 2):
                pyxel.pset(tx2, y + 9, 7)
            pyxel.pset(cx, y + 11, 11)
        else:
            pyxel.line(cx - 4, y + 10, cx + 4, y + 10, 0)
        g.redraw_acid(x - 8, x + 24, int(self.surf // TS))


class LadderBot(Enemy):
    """はしごロボ：はしごを上り下りする。下から上撃ちで落とせる"""
    score = 200

    def __init__(self, x, top, bottom):
        super().__init__(x, top + (bottom - top) / 2, 8, 10, 2)
        self.top, self.bottom = top, bottom
        self.dir = -1
        self.wait = 20

    def update(self, g):
        self.t += 1
        if self.wait > 0:
            self.wait -= 1
            return
        self.y += self.dir * 0.6
        if self.y <= self.top:
            self.y, self.dir, self.wait = self.top, 1, 40
        elif self.y >= self.bottom:
            self.y, self.dir, self.wait = self.bottom, -1, 40

    def draw(self, g):
        x, y = int(self.x), int(self.y)
        body = 7 if self.flash else 13
        pyxel.rect(x - 1, y + 2, 10, 2, 0)              # はしごをつかむ腕
        pyxel.pset(x - 1, y + 2, 10)
        pyxel.pset(x + 8, y + 2, 10)
        pyxel.rect(x + 1, y, 6, 9, 0)
        pyxel.rect(x + 2, y + 1, 4, 7, body)
        pyxel.rect(x + 2, y + 1, 4, 2, 5)
        eye = 8 if (self.t // 8) % 2 else 2
        pyxel.pset(x + 3 + (1 if self.dir > 0 else 0), y + 2, eye)
        f = (self.t // 6) % 2 if self.wait == 0 else 0
        pyxel.pset(x + 2, y + 9 + f, 5)
        pyxel.pset(x + 5, y + 10 - f, 5)


class Core(Enemy):
    """ボス：防衛コア（中継塔の頂上）
    4つのシールドが周りを回って弾を防ぐ（壊せる）。
    攻撃：リング弾（全方位） / 落雷（床に予告マークが出てから落ちる）
    体力50%以下で過負荷：速くなり、リング弾が増え、落雷の本数が増える"""
    score = 7000
    boss = True
    MAX_HP = 40
    HOME_Y = 46
    label = "CORE"
    warn_msg = ("防衛コア起動", "DEFENSE CORE ONLINE")
    defeat_msg = ("コアを破壊！", "CORE DESTROYED!")
    phase_msgs = {2: ("コアが過負荷状態に！", "CORE OVERLOAD!")}
    phase_marks = (0.5,)
    POD_R = 24

    def __init__(self, x, y, hp=None, **kw):
        hp = hp or self.MAX_HP
        super().__init__(x, -40, 20, 20, hp)
        self.max_hp = hp
        self.phase = 1
        self.state = "enter"
        self.timer = 0
        self.spin = 0.0
        self.ring_rot = 0.0
        self.pat_i = 0
        self.pods = [dict(a=i * math.pi / 2, hp=3, alive=True) for i in range(4)]

    @property
    def hittable(self):
        return self.state not in ("dying", "enter")

    @property
    def harmful(self):
        return self.hittable

    def set_state(self, st):
        self.state, self.timer = st, 0

    def start_dying(self):
        self.set_state("dying")

    def center(self):
        return self.x + 10, self.y + 10

    def pod_pos(self, pod):
        cx, cy = self.center()
        a = pod["a"] + self.spin
        return cx + math.cos(a) * self.POD_R, cy + math.sin(a) * self.POD_R * 0.8

    def absorb(self, g, s):
        """シールドに弾が当たったら True（弾は消える。レーザーは貫通してシールドを削る）"""
        if not self.hittable:
            return False
        for i, pod in enumerate(self.pods):
            if not pod["alive"]:
                continue
            px, py = self.pod_pos(pod)
            if s.x < px + 4 and px - 4 < s.x + s.w and s.y < py + 4 and py - 4 < s.y + s.h:
                if s.pierce:
                    if g.gt - s.hit.get(("pod", i), -999) < 15:
                        continue
                    s.hit[("pod", i)] = g.gt
                pod["hp"] -= s.dmg
                g.spark(px, py, 12)
                sfx(22, 3)
                if pod["hp"] <= 0:
                    pod["alive"] = False
                    g.boom(px, py, 6, debris=4, smoke=1)
                    g.add_score(100, px, py)
                return not s.pierce
        return False

    def update(self, g):
        self.t += 1
        self.timer += 1
        p = g.p
        if self.state == "dying":
            self.y += 0.2
            if self.timer % 6 == 0:
                g.boom(self.x + random.uniform(0, 20), self.y + random.uniform(0, 20),
                       random.uniform(6, 10), debris=3, smoke=1)
            if self.timer >= 100:
                self.alive = False
                g.boss_destroyed(self)
            return
        if self.state == "enter":
            if not g.boss_seen or g.warn_t > 30:
                return
            self.y += clamp((self.HOME_Y - self.y) * 0.05, 0.4, 1.5)
            if self.y >= self.HOME_Y - 1:
                self.set_state("idle")
            return
        if self.phase == 1 and self.hp <= self.max_hp * 0.5:
            self.phase = 2
            self.pat_i = 0
            self.set_state("idle")
            g.boss_phase(self)
        fast = self.phase == 2
        self.spin += 0.05 if fast else 0.03
        # 左右にゆっくり往復（真下に入って上撃ちするのが基本）
        self.x = W / 2 - 10 + math.sin(self.t * (0.016 if fast else 0.011)) * 84
        self.y = self.HOME_Y + math.sin(self.t * 0.04) * 6
        if fast and random.random() < 0.15:
            cx, cy = self.center()
            g.parts.append([cx + random.uniform(-8, 8), cy, random.uniform(-0.5, 0.5),
                            random.uniform(-1.2, -0.4), 12, random.choice((12, 7)), 0, 4])
        st = self.state
        if st == "idle":
            if self.timer >= (45 if fast else 70):
                pats = ["ring", "bolt"] if not fast else ["bolt", "ring", "bolt", "ring"]
                self.set_state(pats[self.pat_i % len(pats)])
                self.pat_i += 1
        elif st == "ring":                       # 光ってから全方位に撃つ
            if self.timer == 30:
                n = 12 if fast else 8
                self.ring_rot += 0.2
                cx, cy = self.center()
                for i in range(n):
                    a = self.ring_rot + i * 2 * math.pi / n
                    g.eshots.append(EnemyShot(cx - 3, cy - 3, math.cos(a) * 1.1, math.sin(a) * 1.1))
                g.flashes.append([cx, cy, 8])
                sfx(12, 3)
            if self.timer >= 50:
                self.set_state("idle")
        elif st == "bolt":                       # 床に予告マーク → 落雷
            if self.timer == 1:
                n = 4 if fast else 3
                xs = [p.x + 4]
                tries = 0
                while len(xs) < n and tries < 50:
                    tries += 1
                    gx = random.uniform(16, W - 16)
                    if all(abs(gx - o) > 30 for o in xs):
                        xs.append(gx)
                for i, gx in enumerate(xs):
                    g.add_bolt(gx, 40 if fast else 52, -i * 6)
            if self.timer >= 90:
                self.set_state("idle")

    def draw(self, g):
        cx, cy = self.center()
        cx, cy = int(cx), int(cy)
        if self.state != "enter" or self.y > -30:
            for pod in self.pods:                 # シールドとつなぐ光の線
                if pod["alive"]:
                    px, py = self.pod_pos(pod)
                    pyxel.line(cx, cy, px, py, 1)
        glow = self.state == "ring" and self.timer < 30 and (self.t // 3) % 2
        body = 7 if self.flash else 13
        pyxel.circ(cx, cy, 11, 0)
        pyxel.circ(cx, cy, 10, body)
        pyxel.circ(cx - 3, cy - 3, 4, 7 if not self.flash else 7)
        pyxel.circ(cx, cy, 7, 5)
        ring = 10 if glow else (12 if self.phase == 1 else 8)
        pyxel.circb(cx, cy, 7, ring)
        eye = 12 if self.phase == 1 else (8 if (self.t // 4) % 2 else 10)
        pyxel.circ(cx, cy, 3, 0)
        pyxel.circ(cx, cy, 2, eye)
        pyxel.pset(cx - 1, cy - 1, 7)
        for k in range(4):                        # 外周の発光
            a = self.t * 0.08 + k * math.pi / 2
            pyxel.pset(cx + math.cos(a) * 12, cy + math.sin(a) * 12, ring)
        for pod in self.pods:
            if not pod["alive"]:
                continue
            px, py = self.pod_pos(pod)
            px, py = int(px), int(py)
            pyxel.tri(px, py - 5, px - 4, py, px + 4, py, 0)
            pyxel.tri(px, py + 5, px - 4, py, px + 4, py, 0)
            pyxel.tri(px, py - 4, px - 3, py, px + 3, py, 6 if pod["hp"] >= 3 else 12)
            pyxel.tri(px, py + 4, px - 3, py, px + 3, py, 5)
            pyxel.pset(px, py, 7)
        if self.state == "dying" and (self.t // 3) % 2:
            pyxel.circ(cx, cy, 10, 8)


class CeilTurret(Enemy):
    """天井砲台：天井からぶら下がり、下にいるプレイヤーを撃つ。上撃ちで壊す"""
    score = 300

    def __init__(self, x, y):
        super().__init__(x, y, 10, 9, 3)
        self.cool = random.randint(40, 90)
        self.ang = math.pi / 2

    def update(self, g):
        self.t += 1
        p = g.p
        dx, dy = p.x + 4 - (self.x + 5), p.y + 6 - (self.y + 6)
        if dy > 0:
            target = math.atan2(dy, dx)
            diff = (target - self.ang + math.pi) % (2 * math.pi) - math.pi
            self.ang += clamp(diff, -0.06, 0.06)
        self.cool -= 1
        if self.cool <= 0:
            if abs(dx) < 120 and dy > 8 and not p.dead:
                ca, sa = math.cos(self.ang), math.sin(self.ang)
                g.eshots.append(EnemyShot(self.x + 5 + ca * 7 - 3, self.y + 6 + sa * 7 - 3, ca * 1.5, sa * 1.5))
                g.flashes.append([self.x + 5 + ca * 8, self.y + 6 + sa * 8, 4])
                sfx(12, 3)
                self.cool = g.sdef.get("ceil_cd", 130)
            else:
                self.cool = 20

    def draw(self, g):
        x, y = int(self.x), int(self.y)
        pyxel.rect(x - 1, y, 12, 3, 0)
        pyxel.rect(x, y, 10, 2, 5)
        bx, by = x + 5, y + 6
        ca, sa = math.cos(self.ang), math.sin(self.ang)
        for o in (0, 1):
            pyxel.line(bx + o, by, bx + ca * 8 + o, by + sa * 8, 0 if o else 13)
        pyxel.circ(bx, by, 4, 0)
        pyxel.circ(bx, by, 3, 7 if self.flash else 13)
        pyxel.pset(bx - 1, by - 1, 7)
        if self.cool < 22 and (self.t // 3) % 2:             # 発射の予告
            pyxel.circ(bx, by, 1, 8)


class Overlord(Enemy):
    """ボス：敵司令機（母艦の最深部に立つ巨大な二足メカ）
    段階1：両腕を壊す
        下の腕 … 胸の高さの連射（しゃがむ・跳ぶ・足場に乗ってかわす）
        上の腕 … 迫撃砲（着弾点から離れる。砲弾は撃ち落とせる）
    段階2：胸の装甲が開いてコアが露出（ジャンプ撃ち・足場から撃つ）
        床すれすれのビーム（しゃがむか足場でかわす）・砲弾・ドローン"""
    score = 10000
    boss = True
    label = "WARLORD"
    warn_msg = ("敵司令機 起動", "ENEMY WARLORD ONLINE")
    defeat_msg = ("司令機を撃破！", "WARLORD DOWN!")
    phase_msgs = {2: ("装甲が開いた！ コアを狙え", "ARMOR OPEN! HIT THE CORE!")}
    ARM_HP = 10
    CORE_HP = 24
    BW, BH = 40, 60

    def __init__(self, x, floor, hp=None, arm_hp=None, **kw):
        core = hp or self.CORE_HP
        arm = arm_hp or self.ARM_HP
        total = core + arm * 2
        self.bx, self.by, self.floor = x, floor - self.BH, floor
        # コアの当たり判定は胴体の前面から（絵は x+8 の位置）
        super().__init__(x, self.by + 10, 32, 24, total)
        self.max_hp = total
        self.phase_marks = (core / total,)
        self.arms = {"upper": dict(rx=-30, ry=6, w=30, h=12, hp=arm, alive=True, glow=0, flash=0),
                     "lower": dict(rx=-26, ry=40, w=26, h=14, hp=arm, alive=True, glow=0, flash=0)}
        self.phase = 1
        self.state = "enter"
        self.timer = 0
        self.t_low, self.t_up, self.t_core = 70, 140, 0
        self.burst = []
        self.beam = None
        self.beam_told = False

    def arm_rect(self, a):
        return self.bx + a["rx"], self.by + a["ry"], a["w"], a["h"]

    def arms_alive(self):
        return any(a["alive"] for a in self.arms.values())

    @property
    def hittable(self):
        return self.state == "fight" and not self.arms_alive()

    @property
    def harmful(self):
        return False

    def start_dying(self):
        self.state, self.timer = "dying", 0
        self.beam = None
        self.burst = []

    @staticmethod
    def _hit(s, x, y, w, h):
        return s.x < x + w and x < s.x + s.w and s.y < y + h and y < s.y + s.h

    def _cooldown(self, g, s, key):
        if not s.pierce:
            return True
        if g.gt - s.hit.get(key, -999) < 15:
            return False
        s.hit[key] = g.gt
        return True

    def absorb(self, g, s):
        if self.state == "dying":
            return False
        for name, a in self.arms.items():
            if not a["alive"]:
                continue
            x, y, w, h = self.arm_rect(a)
            if not self._hit(s, x, y, w, h):
                continue
            if self.state != "fight":
                return True
            if not self._cooldown(g, s, ("arm", name)):
                return False
            d = min(s.dmg, a["hp"])
            a["hp"] -= s.dmg
            self.hp -= d
            a["flash"] = 5
            g.spark(s.x + s.w / 2, s.y + s.h / 2, 7)
            sfx(2, 3)
            if s.kind == "grenade":
                g.boom(s.x + 2, s.y + 2, 8, debris=2, smoke=1)
            if a["hp"] <= 0:
                a["alive"] = False
                g.boom(x + w / 2, y + h / 2, 12, debris=10, smoke=4)
                g.add_score(1000, x + w / 2, y)
                g.shake = max(g.shake, 4)
                g.hitstop = max(g.hitstop, 6)
                if not self.arms_alive():
                    self.phase = 2
                    self.t_core = 0
                    self.burst = []
                    g.boss_phase(self)
            return not s.pierce
        if self.hittable and self._hit(s, self.x, self.y, self.w, self.h):
            return False                                 # 開いたコア：通常のダメージ処理へ
        if self._hit(s, self.bx, self.by, self.BW, self.BH):
            if self._cooldown(g, s, ("body",)):
                g.spark(s.x + s.w / 2, s.y + s.h / 2, 13)
                sfx(22, 3)
                if s.kind == "grenade":
                    g.boom(s.x + 2, s.y + 2, 8, debris=2, smoke=1)
            return True                                  # 装甲ではじく
        return False

    def fire_bullet(self, g):
        a = self.arms["lower"]
        if not a["alive"]:
            return
        x, y, w, h = self.arm_rect(a)
        g.eshots.append(EnemyShot(x - 12, self.floor - 16, -2.4, 0))    # 高さ 168〜174
        g.flashes.append([x - 8, self.floor - 13, 4])
        sfx(12, 3)

    def fire_shells(self, g, offsets, base_t=48):
        p = g.p
        a = self.arms["upper"]
        x, y, w, h = self.arm_rect(a)
        mx, my = (x - 6, y + 6) if a["alive"] else (self.bx + 20, self.by)
        for i, off in enumerate(offsets):
            T = base_t + i * 6
            ax = clamp(p.x + 4 + off, g.cam_x + 8, self.bx - 40)
            vx = (ax - mx) / T
            vy = (self.floor - my) / T - 0.06 * T
            g.eshots.append(Shell(mx - 3, my - 3, vx, vy))
        g.flashes.append([mx, my, 5])
        sfx(31, 3)

    def update(self, g):
        self.t += 1
        self.timer += 1
        p = g.p
        for a in self.arms.values():
            if a["flash"] > 0:
                a["flash"] -= 1
        if self.state == "dying":
            if self.timer % 5 == 0:
                g.boom(self.bx + random.uniform(-10, 40), self.by + random.uniform(0, 60),
                       random.uniform(6, 12), debris=3, smoke=1)
            if self.timer >= 140:
                self.alive = False
                g.boss_destroyed(self)
            return
        if not p.dead and p.invinc == 0 and overlap(p, Box(self.bx + 2, self.by + 4, self.BW - 4, self.BH - 4)):
            g.hurt_player(self.bx)                       # 体当たり
        if self.state == "enter":
            if g.boss_seen and g.warn_t <= 30:
                if self.timer > 40:
                    self.state, self.timer = "fight", 0
            else:
                self.timer = 0
            return
        if self.phase == 1:
            self.update_arms(g)
        else:
            self.update_core(g)
        rest = []
        for k in self.burst:
            k -= 1
            if k <= 0:
                self.fire_bullet(g)
            else:
                rest.append(k)
        self.burst = rest

    def update_arms(self, g):
        lo, up = self.arms["lower"], self.arms["upper"]
        both = lo["alive"] and up["alive"]
        if lo["alive"]:
            self.t_low -= 1
            lo["glow"] = 1 if self.t_low <= 30 else 0
            if self.t_low <= 0:
                self.burst += [1, 15, 29]
                self.t_low = 150 if both else 110
        if up["alive"]:
            self.t_up -= 1
            up["glow"] = 1 if self.t_up <= 30 else 0
            if self.t_up <= 0:
                self.fire_shells(g, (-36, 0, 36))
                self.t_up = 180 if both else 130

    def update_core(self, g):
        p = g.p
        self.t_core += 1
        k = self.t_core
        if k == 1:
            self.beam = 0
            sfx(29, 3)
            if not self.beam_told:
                self.beam_told = True
                g.toast(L("ビームはしゃがんでかわせ！", "DUCK UNDER THE BEAM!"), 120)
        if self.beam is not None:
            self.beam += 1
            if self.beam == 50:
                sfx(26, 3)
                g.shake = max(g.shake, 2)
            if 50 <= self.beam < 86 and not p.dead and p.invinc == 0:
                if overlap(p, Box(g.cam_x - 8, self.floor - 18, self.bx - g.cam_x + 8, 8)):
                    g.hurt_player(self.bx)
            if self.beam >= 86:
                self.beam = None
        if k in (110, 124):
            self.fire_shells(g, (-30,) if k == 110 else (30,), base_t=44)
        if k == 150 and sum(1 for e in g.enemies if isinstance(e, Drone) and e.alive) < 2:
            dr = Drone(self.bx + 15, self.by - 6)
            dr.state, dr.active, dr.vx = "fly", True, -1.0
            g.enemies.append(dr)
            g.flashes.append([self.bx + 20, self.by, 6])
            sfx(13, 3)
        if k >= 190:
            self.t_core = 0

    def draw(self, g):
        bx, by, f, t = int(self.bx), int(self.by), int(self.floor), self.t
        for lx in (bx + 4, bx + 26):                      # 脚
            pyxel.rect(lx, by + 44, 10, f - (by + 44), 0)
            pyxel.rect(lx + 1, by + 45, 8, f - (by + 46), 5)
            pyxel.line(lx + 1, by + 50, lx + 8, by + 50, 1)
            pyxel.rect(lx - 2, f - 4, 14, 4, 0)
            pyxel.rect(lx - 1, f - 3, 12, 2, 13)
        pyxel.rect(bx, by + 8, 40, 38, 0)                  # 胴体
        pyxel.rect(bx + 1, by + 9, 38, 36, 5)
        pyxel.line(bx + 1, by + 9, bx + 38, by + 9, 13)
        pyxel.line(bx + 38, by + 9, bx + 38, by + 44, 1)
        for yy in (by + 38, by + 42):
            pyxel.line(bx + 2, yy, bx + 37, yy, 1)
        pyxel.rect(bx + 10, by, 20, 10, 0)                 # 頭
        pyxel.rect(bx + 11, by + 1, 18, 8, 13)
        eye = 8 if self.state != "enter" or (t // 6) % 2 else 2
        pyxel.rect(bx + 12, by + 4, 10, 2, eye)
        pyxel.line(bx + 24, by - 6, bx + 24, by, 13)
        pyxel.pset(bx + 24, by - 7, 8 if (t // 10) % 2 else 2)
        cx, cy = int(self.x) + 8, int(self.y)              # 胸のコア
        if self.phase == 1:
            pyxel.rect(cx, cy, 24, 24, 0)
            pyxel.rect(cx + 1, cy + 1, 22, 22, 13)
            for i in range(3):
                pyxel.line(cx + 2, cy + 5 + i * 7, cx + 21, cy + 5 + i * 7, 5)
            pyxel.rect(cx + 10, cy + 1, 4, 22, 1)
        else:
            pyxel.rect(cx, cy, 24, 24, 0)
            pyxel.rect(cx - 3, cy, 4, 24, 13)
            pyxel.rect(cx + 23, cy, 4, 24, 13)
            r = 8 + (t // 4) % 2
            pyxel.circ(cx + 12, cy + 12, r, 2)
            pyxel.circ(cx + 12, cy + 12, r - 2, 7 if self.flash else 8)
            pyxel.circ(cx + 12, cy + 12, 3, 10)
            if self.beam is not None and self.beam < 50 and (t // 3) % 2:
                pyxel.circb(cx + 12, cy + 12, 12 - self.beam // 6, 10)
        for name, a in self.arms.items():                 # 腕
            x, y, w, h = self.arm_rect(a)
            if a["alive"]:
                col = 7 if a["flash"] else 13
                pyxel.rect(x, y, w, h, 0)
                pyxel.rect(x + 1, y + 1, w - 2, h - 2, col)
                pyxel.line(x + 1, y + h - 2, x + w - 2, y + h - 2, 5)
                if name == "upper":
                    pyxel.rect(x - 7, y + 3, 8, 7, 0)
                    pyxel.rect(x - 6, y + 4, 6, 5, 5)
                    mx, my = x - 6, y + 6
                else:
                    for k in range(3):
                        pyxel.line(x - 10, y + 3 + k * 4, x, y + 3 + k * 4, 0)
                        pyxel.line(x - 10, y + 4 + k * 4, x, y + 4 + k * 4, 13)
                    mx, my = x - 10, y + 7
                if a["glow"] and (t // 3) % 2:
                    pyxel.circ(mx, my, 3, 10)
                    pyxel.pset(mx, my, 7)
            else:
                pyxel.rect(bx - 5, y + 2, 6, h - 4, 0)
                pyxel.pset(bx - 4, y + 4, 8 if (t // 4) % 2 else 10)
                if random.random() < 0.08:
                    g.parts.append([bx - 3, y + 4, random.uniform(-1.5, 0), random.uniform(-1.5, 0.5),
                                    8, random.choice((10, 7)), 0.1, 4])
        if self.state == "dying" and (t // 3) % 2:
            pyxel.rect(bx + 1, by + 9, 38, 36, 8)
        if self.beam is not None:                          # ビーム（予告 → 照射）
            x0 = int(g.cam_x) - 8
            y0 = f - 18
            if self.beam < 50:
                if (t // 3) % 2:
                    for xx in range(x0, cx, 4):
                        pyxel.pset(xx, y0 + 4, 8)
            else:
                pyxel.rect(x0, y0, cx - x0, 8, 2)
                pyxel.rect(x0, y0 + 1, cx - x0, 6, 8)
                pyxel.line(x0, y0 + 3 + (t % 2), cx, y0 + 3 + (t % 2), 7)


class Icicle(Enemy):
    """つらら（溶岩洞では鍾乳石）：真下を通ると震えて落ちてくる。撃って先に落とすこともできる"""
    score = 50

    def __init__(self, x, y, rock=False):
        super().__init__(x + 1, y, 6, 12, 1)
        self.rock = rock
        self.state = "hang"
        self.timer = 0

    @property
    def harmful(self):
        return self.state == "fall"

    def update(self, g):
        self.t += 1
        p = g.p
        if self.state == "hang":
            if (abs(p.x + 4 - (self.x + 3)) < 22 and 0 < p.y - self.y < 170 and not p.dead):
                self.state, self.timer = "shake", 0
                sfx(54, 3)
        elif self.state == "shake":
            self.timer += 1
            if self.timer >= 34:
                self.state = "fall"
        else:
            self.vy = min(self.vy + 0.35, 6.0)
            self.y += self.vy
            st = g.stage
            if (st.solid(self.x + 3, self.y + self.h) or self.y > st.h * TS or
                    st.tile_at(self.x + 3, self.y + self.h) in LIQUID):
                self.alive = False
                self.shatter(g)

    def shatter(self, g):
        cols = (4, 2, 9) if self.rock else (7, 6, 12)
        for _ in range(8):
            g.parts.append([self.x + 3, self.y + self.h - 2, random.uniform(-1.6, 1.6),
                            random.uniform(-2.2, -0.6), random.randint(20, 35), random.choice(cols), 0.18, 2])
        sfx(55, 3)

    def on_death(self, g):
        self.shatter(g)

    def draw(self, g):
        x, y = int(self.x), int(self.y)
        if self.state == "shake":
            x += 1 if (self.timer // 2) % 2 else -1
        c0, c1, c2 = (2, 4, 9) if self.rock else (5, 12, 7)
        if self.flash:
            c1 = 7
        pyxel.tri(x - 1, y, x + 6, y, x + 2.5, y + 12, c0)
        pyxel.tri(x, y, x + 5, y, x + 2.5, y + 10, c1)
        pyxel.line(x + 1, y, x + 2, y + 6, c2)


class Roller(Enemy):
    """転がりロボ：トゲの球になって転がってくる。勢いがつくと止まれない。跳び越えるか撃つ"""
    score = 200

    def __init__(self, x, y):
        super().__init__(x, y, 10, 10, 3)
        self.state = "idle"
        self.ang = 0.0

    def update(self, g):
        self.t += 1
        p = g.p
        st = g.stage
        self.vy = min(self.vy + GRAV, MAX_FALL)
        if self.state == "idle":
            move_y(st, self, self.vy)
            if abs(p.x - self.x) < 110 and abs(p.y - self.y) < 40 and not p.dead:
                self.state = "roll"
                sfx(56, 3)
            return
        target = 1 if p.x + 4 > self.x + 5 else -1
        self.vx = clamp(self.vx + 0.05 * target, -1.9, 1.9)
        if move_x(st, self, self.vx):
            self.vx = -self.vx * 0.6
            if self.on_ground:
                self.vy = -2.0
        move_y(st, self, self.vy)
        self.ang += self.vx * 0.25
        if self.on_ground and abs(self.vx) > 1.2 and self.t % 4 == 0:
            g.parts.append([self.x + 5, self.y + 10, -self.vx * 0.3, -0.4, 10,
                            7 if g.theme in ("ice", "fort") else 13, 0.05, 0])
        if st.tile_at(self.x + 5, self.y + self.h - 1) in LIQUID:
            self.alive = False
            g.acid_splash(self.x + 5, self.y + self.h - 2, 8)
        elif self.y > st.h * TS or self.far_from_camera(g, 120):
            self.alive = False

    def draw(self, g):
        cx, cy = int(self.x + 5), int(self.y + 5)
        body = 7 if self.flash else 13
        for k in range(4):
            a = self.ang + k * math.pi / 4
            pyxel.line(cx - math.cos(a) * 7, cy - math.sin(a) * 7, cx + math.cos(a) * 7, cy + math.sin(a) * 7, 0)
        pyxel.circ(cx, cy, 5, 0)
        pyxel.circ(cx, cy, 4, body)
        pyxel.circ(cx - 1, cy - 1, 1, 7)
        eye = 8 if (self.t // 6) % 2 else 2
        pyxel.pset(cx + (1 if self.vx >= 0 else -1) * 2, cy, eye)


class Tank(Enemy):
    """ボス：雪上戦車（2-1）
    氷の上を走り回り、砲塔から山なりの砲弾を撃つ。エンジンを吹かしたら突進の合図
    （跳び越えるか、足場に逃げる）。体力50%以下で暴走：速くなり、床すれすれの機銃も撃つ"""
    score = 8000
    boss = True
    label = "TANK"
    warn_msg = ("雪上戦車 接近", "SNOW TANK INCOMING")
    defeat_msg = ("戦車を撃破！", "TANK DESTROYED!")
    phase_msgs = {2: ("戦車が暴走している！", "THE TANK IS RAMPAGING!")}
    phase_marks = (0.5,)
    BW, BH = 44, 22

    def __init__(self, x, floor, hp=None, **kw):
        hp = hp or 40
        super().__init__(x + 70, floor - self.BH, self.BW, self.BH, hp)
        self.max_hp = hp
        self.floor = floor
        self.home = x
        self.phase = 1
        self.state = "enter"
        self.timer = 0
        self.face = -1
        self.ang = -math.pi / 2
        self.shell_t = 90
        self.gun_t = 60
        self.drives = 0
        self.tx = x
        self.tread = 0.0
        self.burst = []
        self.hinted = False

    @property
    def hittable(self):
        return self.state not in ("enter", "dying")

    harmful = False              # 体当たりは update で、砲塔を除いた車体だけで判定する

    def set_state(self, st):
        self.state, self.timer = st, 0

    def start_dying(self):
        self.set_state("dying")
        self.burst = []

    def bounds(self, g):
        x0, x1 = g.sdef.get("arena", (g.cam_x, g.cam_x + W))
        return max(x0, g.cam_x + 2), min(x1 - self.w, g.cam_x + W - self.w - 2)

    def muzzle(self):
        mx, my = self.x + self.w / 2, self.y + 2
        return mx + math.cos(self.ang) * 12, my + math.sin(self.ang) * 12

    def fire_shells(self, g):
        p = g.p
        mx, my = self.muzzle()
        offs = (-44, 0, 44) if self.phase == 1 else (-48, -16, 16, 48)
        for i, off in enumerate(offs):
            T = 52 + i * 6
            ax = clamp(p.x + 4 + off, g.cam_x + 8, g.cam_x + W - 8)
            g.eshots.append(Shell(mx - 3, my - 3, (ax - mx) / T, (self.floor - my) / T - 0.06 * T))
        g.flashes.append([mx, my, 5])
        g.shake = max(g.shake, 1.5)
        sfx(31, 3)

    def drive_to(self, tx, sp):
        d = clamp(tx - self.x, -sp, sp)
        self.x += d
        self.tread += d
        return abs(tx - self.x) < 1

    def update(self, g):
        self.t += 1
        self.timer += 1
        p = g.p
        if self.state == "dying":
            if self.timer % 5 == 0:
                g.boom(self.x + random.uniform(0, self.w), self.y + random.uniform(0, self.h),
                       random.uniform(6, 11), debris=3, smoke=2)
            if self.timer >= 120:
                self.alive = False
                g.boss_destroyed(self)
            return
        if self.phase == 1 and self.state != "enter" and self.hp <= self.max_hp * 0.5:
            self.phase = 2
            g.boss_phase(self)
        fast = self.phase == 2
        target = math.atan2(min(p.y - self.y, -12), p.x + 4 - (self.x + self.w / 2))
        diff = (target - self.ang + math.pi) % (2 * math.pi) - math.pi
        self.ang += clamp(diff, -0.04, 0.04)
        st = self.state
        if st == "enter":
            if g.boss_seen and g.warn_t <= 30:
                if self.drive_to(self.home, 1.2):
                    self.set_state("drive")
                    self.tx = self.x
            return
        lo, hi = self.bounds(g)
        if st in ("drive", "recover"):
            self.face = 1 if p.x + 4 > self.x + self.w / 2 else -1
        if st == "drive":
            if self.drive_to(clamp(self.tx, lo, hi), 1.1 if fast else 0.8) and self.timer > 20:
                side = -1 if p.x + 4 > self.x + self.w / 2 else 1     # プレイヤーから離れた所へ
                self.tx = clamp(p.x + 4 - self.w / 2 + side * random.uniform(70, 110), lo, hi)
                self.drives += 1
                self.timer = 0
                if self.drives >= (2 if fast else 3):
                    self.drives = 0
                    self.set_state("rev")
            self.shell_t -= 1
            if self.shell_t <= 0:
                self.fire_shells(g)
                self.shell_t = 80 if fast else 110
            if fast:
                self.gun_t -= 1
                if self.gun_t <= 0:
                    self.gun_t = 100
                    self.burst += [24, 36, 48]
        elif st == "rev":                                # エンジンを吹かす（突進の予告）
            self.face = 1 if p.x + 4 > self.x + self.w / 2 else -1
            if self.timer == 1:
                sfx(56, 3)
                if not self.hinted:
                    self.hinted = True
                    g.toast(L("突進が来る！ 足場に上がれ", "IT'S CHARGING! GET ON A PLATFORM!"), 120)
            if self.timer % 3 == 0:
                g.parts.append([self.x + (self.w if self.face < 0 else 0), self.y + self.h - 8,
                                -self.face * random.uniform(0.5, 1.2), random.uniform(-0.8, -0.2), 30, 13, 0, 1])
            if self.timer >= (40 if fast else 54):
                self.set_state("charge")
        elif st == "charge":
            sp = 3.2 if fast else 2.6
            self.x += self.face * sp
            self.tread += self.face * sp
            for _ in range(2):
                g.parts.append([self.x + self.w / 2 - self.face * 20, self.floor - 2, -self.face * random.uniform(0.5, 1.5),
                                random.uniform(-1.5, -0.5), 18, 7, 0.1, 0])
            if self.x <= lo or self.x >= hi:
                self.x = clamp(self.x, lo, hi)
                g.shake = max(g.shake, 4)
                g.boom(self.x + (0 if self.face < 0 else self.w), self.y + 8, 6, debris=4, smoke=2, sound=False)
                sfx(57, 3)
                self.set_state("recover")
        elif st == "recover":
            if self.timer >= 40:
                self.set_state("drive")
                self.tx = clamp(self.x - self.face * 60, lo, hi)
        self.x = clamp(self.x, lo, hi)
        if not p.dead and p.invinc == 0 and overlap(p, Box(self.x + 2, self.y + 7, self.w - 4, self.h - 7)):
            g.hurt_player(self.x + self.w / 2)            # 車体に体当たりされた
        rest = []
        for k in self.burst:                              # 床すれすれの機銃（しゃがむか跳んでかわす）
            k -= 1
            if k <= 0:
                fx = self.x + (self.w if self.face > 0 else 0)
                g.eshots.append(EnemyShot(fx - 3, self.floor - 16, self.face * 2.3, 0))
                g.flashes.append([fx, self.floor - 13, 4])
                sfx(12, 3)
            else:
                rest.append(k)
        self.burst = rest

    def draw(self, g):
        x, y, w = int(self.x), int(self.y), self.w
        body = 7 if self.flash else 13
        red = self.phase == 2 and (self.t // 6) % 2
        pyxel.rect(x, y + 12, w, 10, 0)                   # 履帯
        pyxel.rect(x + 1, y + 13, w - 2, 8, 1)
        for i in range(6):
            wx = x + 4 + i * 7
            pyxel.circ(wx, y + 17, 3, 5)
            a = self.tread * 0.3 + i
            pyxel.pset(wx + math.cos(a) * 2, y + 17 + math.sin(a) * 2, 13)
        pyxel.rect(x + 2, y + 4, w - 4, 9, 0)             # 車体
        pyxel.rect(x + 3, y + 5, w - 6, 7, body)
        pyxel.line(x + 3, y + 5, x + w - 4, y + 5, 7)
        fx = x - 3 if self.face < 0 else x + w - 1        # 雪かきの刃
        pyxel.rect(fx, y + 8, 4, 13, 0)
        pyxel.rect(fx + 1, y + 9, 2, 11, 6)
        tx, ty = x + w // 2, y + 2                        # 砲塔
        mx, my = self.muzzle()
        pyxel.line(tx, ty - 1, mx, my - 1, 0)
        pyxel.line(tx, ty, mx, my, 13)
        pyxel.line(tx, ty + 1, mx, my + 1, 0)
        pyxel.circ(tx, ty, 6, 0)
        pyxel.circ(tx, ty, 5, 7 if self.flash else 6)
        pyxel.rect(tx - 3, ty - 1, 6, 2, 1)
        pyxel.pset(tx - 2, ty - 3, 7)
        lamp = 8 if red or self.state in ("rev", "charge") else 2
        pyxel.pset(x + 6, y + 7, lamp)
        pyxel.pset(x + w - 7, y + 7, lamp)
        if self.shell_t < 20 and self.state == "drive" and (self.t // 3) % 2:   # 砲撃の予告
            pyxel.circ(mx, my, 2, 10)
        if self.state == "dying" and (self.t // 3) % 2:
            pyxel.rect(x + 3, y + 5, w - 6, 7, 8)


class Golem(Enemy):
    """ボス：溶岩巨人（2-2）
    ゆっくり歩き、両腕を振り上げたら地面を叩いて左右に走る衝撃波を出す（跳び越える）。
    岩を投げる（撃ち落とせる）。体力50%以下で核が赤熱し、天井から岩を降らせる"""
    score = 9000
    boss = True
    label = "GOLEM"
    warn_msg = ("溶岩巨人 覚醒", "MAGMA GOLEM AWAKENS")
    defeat_msg = ("溶岩巨人を撃破！", "GOLEM DOWN!")
    phase_msgs = {2: ("巨人の核が赤熱している！", "THE CORE IS OVERHEATING!")}
    phase_marks = (0.5,)
    GW, GH = 30, 44

    def __init__(self, x, floor, hp=None, **kw):
        hp = hp or 48
        super().__init__(x, floor - self.GH, self.GW, self.GH, hp)
        self.max_hp = hp
        self.floor = floor
        self.phase = 1
        self.state = "enter"
        self.timer = 0
        self.pat = 0
        self.face = -1
        self.waking = False

    @property
    def hittable(self):
        return self.state not in ("enter", "dying")

    @property
    def harmful(self):
        return self.state not in ("enter", "dying")

    def set_state(self, st):
        self.state, self.timer = st, 0

    def start_dying(self):
        self.set_state("dying")

    def bounds(self, g):
        x0, x1 = g.sdef.get("arena", (g.cam_x, g.cam_x + W))
        return max(x0, g.cam_x + 4), min(x1 - self.w, g.cam_x + W - self.w - 4)

    def update(self, g):
        self.t += 1
        self.timer += 1
        p = g.p
        if self.state == "dying":
            if self.timer % 5 == 0:
                g.boom(self.x + random.uniform(0, self.w), self.y + random.uniform(0, self.h),
                       random.uniform(6, 12), debris=4, smoke=2)
            if self.timer >= 120:
                self.alive = False
                g.boss_destroyed(self)
            return
        if self.phase == 1 and self.state != "enter" and self.hp <= self.max_hp * 0.5:
            self.phase = 2
            g.boss_phase(self)
        fast = self.phase == 2
        if fast and random.random() < 0.2:
            g.parts.append([self.x + random.uniform(4, self.w - 4), self.y + random.uniform(8, 30),
                            random.uniform(-0.4, 0.4), random.uniform(-1.2, -0.4), 20, random.choice((9, 10, 8)), 0, 0])
        st = self.state
        if st == "enter":
            if g.boss_seen and g.warn_t <= 30:
                self.waking = True
                if self.timer % 8 == 0:
                    g.shake = max(g.shake, 1.5)
                if self.timer >= 60:
                    self.set_state("walk")
            else:
                self.timer = 0
            return
        lo, hi = self.bounds(g)
        if st == "walk":
            self.face = 1 if p.x + 4 > self.x + self.w / 2 else -1
            if abs(p.x + 4 - (self.x + self.w / 2)) > 50:     # 近づきすぎない（追い詰めない）
                self.x = clamp(self.x + self.face * (0.5 if fast else 0.35), lo, hi)
            if self.t % 40 == 0:
                sfx(57, 3)
                g.shake = max(g.shake, 1)
            if self.timer >= (70 if fast else 100):
                pats = ["slam", "throw", "rain", "slam", "throw"] if fast else ["slam", "throw"]
                self.set_state(pats[self.pat % len(pats)])
                self.pat += 1
        elif st == "slam":                               # 両腕を振り上げて → 地面を叩く
            if self.timer == 36 or (fast and self.timer == 76):
                for d in (-1, 1):
                    g.waves.append(dict(x=self.x + (2 if d < 0 else self.w - 2), y=self.floor, dir=d, t=0))
                g.shake = max(g.shake, 4)
                sfx(27, 3)
                g.boom(self.x + self.w / 2, self.floor - 2, 8, debris=6, smoke=3, sound=False)
            if self.timer >= (110 if fast else 70):
                self.set_state("walk")
        elif st == "throw":
            if self.timer in ((20, 40) if fast else (24,)):
                mx, my = self.x + self.w / 2 + self.face * 16, self.y + 4
                T = 50
                ax = p.x + 4 + random.uniform(-6, 6)
                g.eshots.append(Rock(mx - 3, my - 3, (ax - mx) / T, (self.floor - my) / T - 0.06 * T))
                sfx(31, 3)
            if self.timer >= 60:
                self.set_state("walk")
        elif st == "rain":                               # 吠えて天井を揺らす → 岩が降る
            if self.timer < 30 and self.timer % 6 == 0:
                g.shake = max(g.shake, 2)
            if self.timer in (30, 42, 54, 66):
                off = (-60, 30, -20, 64)[(self.timer - 30) // 12]
                g.drop_debris(clamp(p.x + 4 + off, g.cam_x + 8, g.cam_x + W - 8), warn=44)
            if self.timer >= 110:
                self.set_state("walk")

    def draw(self, g):
        x, y, t = int(self.x), int(self.y), self.t
        dorm = self.state == "enter" and not self.waking
        rock = 7 if self.flash else 4
        glow = 2 if dorm else (8 if self.phase == 1 else 10)
        if not dorm and (t // 8) % 2:
            glow = 9
        shake = (1 if (t // 2) % 2 else -1) if self.state == "enter" and self.waking else 0
        x += shake
        for lx in (x + 4, x + 18):                        # 脚
            pyxel.rect(lx, y + 32, 8, 12, 0)
            pyxel.rect(lx + 1, y + 33, 6, 10, 2)
        pyxel.rect(x + 1, y + 10, 28, 24, 0)              # 胴
        pyxel.rect(x + 2, y + 11, 26, 22, rock)
        pyxel.line(x + 2, y + 32, x + 27, y + 32, 2)
        pyxel.line(x + 8, y + 12, x + 12, y + 20, glow)   # 光る割れ目
        pyxel.line(x + 12, y + 20, x + 9, y + 28, glow)
        pyxel.line(x + 21, y + 14, x + 18, y + 24, glow)
        pyxel.circ(x + 15, y + 21, 4, 0)
        pyxel.circ(x + 15, y + 21, 3, glow)
        pyxel.pset(x + 15, y + 21, 2 if dorm else 7)
        pyxel.rect(x + 8, y, 14, 11, 0)                   # 頭
        pyxel.rect(x + 9, y + 1, 12, 9, rock)
        eye = 1 if dorm else 10
        pyxel.rect(x + 11, y + 4, 3, 2, eye)
        pyxel.rect(x + 16, y + 4, 3, 2, eye)
        raised = self.state == "slam" and (self.timer < 36 or (self.phase == 2 and 44 <= self.timer < 76))
        for ax in (x - 6, x + 29):                        # 腕
            if raised:
                pyxel.rect(ax, y - 8, 7, 20, 0)
                pyxel.rect(ax + 1, y - 7, 5, 18, rock)
                pyxel.rect(ax - 1, y - 12, 9, 6, 0)
                pyxel.rect(ax, y - 11, 7, 4, 2)
            else:
                pyxel.rect(ax, y + 12, 7, 22, 0)
                pyxel.rect(ax + 1, y + 13, 5, 20, rock)
                pyxel.rect(ax - 1, y + 32, 9, 6, 0)
                pyxel.rect(ax, y + 33, 7, 4, 2)
        if self.state == "dying" and (t // 3) % 2:
            pyxel.rect(x + 2, y + 11, 26, 22, 8)


class Twins(Enemy):
    """ボス：防衛ユニット（2-3）
    2つの球が回転しながら、間にビームを張って薙ぎ払う（点滅で予告。中心から離れてかわす）。
    それぞれ狙い撃ちもしてくる。片方を壊すと、残った一体が暴走して飛び回り、3方向弾と爆弾"""
    score = 12000
    boss = True
    hittable = False
    harmful = False
    label = "TWINS"
    warn_msg = ("防衛ユニット起動", "TWIN GUARDIANS ONLINE")
    defeat_msg = ("防衛ユニットを撃破！", "TWINS DESTROYED!")
    phase_msgs = {2: ("残った一体が暴走している！", "THE SURVIVOR GOES BERSERK!")}
    phase_marks = (0.5,)
    R = 60                   # 回転の半径。下側では球がプレイヤーの正面を通る（正面撃ちのチャンス）
    OFF, WARN, ON = 100, 40, 150

    def __init__(self, x, y, hp=None, **kw):
        orb = hp or 26
        super().__init__(x - 4, y, 8, 8, orb * 2)        # 出現判定は配置位置で（登場は画面の上から）
        self.max_hp = orb * 2
        self.cy0 = y
        self.ccx, self.ccy = x, -80
        self.ang = 0.3
        self.orbs = [dict(hp=orb, alive=True, flash=0, x=x, y=-80) for _ in range(2)]
        self.phase = 1
        self.state = "enter"
        self.timer = 0
        self.beam_t = 0
        self.fire_t = 90
        self.bomb_t = 60

    def set_state(self, st):
        self.state, self.timer = st, 0

    def start_dying(self):
        self.set_state("dying")

    def beam_k(self):
        return self.beam_t % (self.OFF + self.WARN + self.ON)

    def beam(self):
        if self.phase != 1 or self.state != "fight":
            return None
        k = self.beam_k()
        if k < self.OFF:
            return None
        return "warn" if k < self.OFF + self.WARN else "on"

    def place(self):
        if self.phase == 1:
            for i, o in enumerate(self.orbs):
                a = self.ang + i * math.pi
                o["x"], o["y"] = self.ccx + math.cos(a) * self.R, self.ccy + math.sin(a) * self.R
        self.x, self.y = self.ccx - 4, self.ccy - 4

    def absorb(self, g, s):
        if self.state != "fight":
            return False
        for i, o in enumerate(self.orbs):
            if not o["alive"]:
                continue
            if not (s.x < o["x"] + 9 and o["x"] - 9 < s.x + s.w and s.y < o["y"] + 9 and o["y"] - 9 < s.y + s.h):
                continue
            if s.pierce:
                if g.gt - s.hit.get(("orb", i), -999) < 15:
                    continue
                s.hit[("orb", i)] = g.gt
            d = min(s.dmg, o["hp"])
            o["hp"] -= s.dmg
            self.hp -= d
            o["flash"] = 5
            g.spark(o["x"], o["y"], 7)
            sfx(2, 3)
            if s.kind == "grenade":
                g.boom(s.x + 2, s.y + 2, 8, debris=2, smoke=1)
            if o["hp"] <= 0:
                o["alive"] = False
                g.boom(o["x"], o["y"], 12, debris=8, smoke=3)
                g.add_score(2000, o["x"], o["y"])
                g.shake = max(g.shake, 4)
                g.hitstop = max(g.hitstop, 6)
                if not any(q["alive"] for q in self.orbs):
                    self.hp = 0
                    self.ccx, self.ccy = o["x"], o["y"]
                    self.x, self.y = self.ccx - 4, self.ccy - 4
                    g.damage_enemy(self, 0)
                elif self.phase == 1:
                    self.phase = 2
                    self.timer = 0
                    self.fire_t = 60
                    g.boss_phase(self)
            return not s.pierce
        return False

    def aimed(self, g, ox, oy, spd, spread=(0,)):
        p = g.p
        base = math.atan2(p.y + 7 - oy, p.x + 4 - ox)
        for da in spread:
            a = base + da
            g.eshots.append(EnemyShot(ox - 3, oy - 3, math.cos(a) * spd, math.sin(a) * spd))
        g.flashes.append([ox, oy, 4])
        sfx(12, 3)

    def update(self, g):
        self.t += 1
        self.timer += 1
        p = g.p
        for o in self.orbs:
            if o["flash"] > 0:
                o["flash"] -= 1
        if self.state == "dying":
            if self.timer % 5 == 0:
                g.boom(self.ccx + random.uniform(-12, 12), self.ccy + random.uniform(-12, 12),
                       random.uniform(6, 11), debris=3, smoke=1)
            if self.timer >= 110:
                self.alive = False
                g.boss_destroyed(self)
            return
        if self.state == "enter":
            self.ccx = g.cam_x + W / 2
            if g.boss_seen and g.warn_t <= 30:
                self.ccy += clamp((self.cy0 - self.ccy) * 0.05, 0.5, 2.0)
                self.ang += 0.03
                if self.ccy >= self.cy0 - 1:
                    self.set_state("fight")
            self.place()
            return
        if self.phase == 1:
            self.ccx = g.cam_x + W / 2 + math.sin(self.t * 0.008) * 50
            self.ccy = self.cy0 + math.sin(self.t * 0.02) * 6
            self.beam_t += 1
            bm = self.beam()
            k = self.beam_k()
            self.ang += 0.02 if bm == "on" else 0.012
            if k == self.OFF:
                sfx(29, 3)
            elif k == self.OFF + self.WARN:
                sfx(26, 3)
                g.shake = max(g.shake, 2)
            self.place()
            if bm == "on" and not p.dead and p.invinc == 0:
                a, b = self.orbs
                n = int(self.R * 2 / 3)
                for i in range(n + 1):
                    f = i / n
                    bx, by = a["x"] + (b["x"] - a["x"]) * f, a["y"] + (b["y"] - a["y"]) * f
                    if p.x <= bx <= p.x + p.w and p.y <= by <= p.y + p.h:
                        g.toast(L("ビームに触れた！", "BEAM!"), 60)
                        g.hurt_player(bx)
                        break
            if bm is None:                               # ビームの予告・照射中は撃たない
                self.fire_t -= 1
            if self.fire_t <= 0:
                self.fire_t = 110
                # プレイヤーから遠い方の球だけが撃つ（至近距離からは撃たない）
                o = max(self.orbs, key=lambda q: math.hypot(q["x"] - p.x - 4, q["y"] - p.y - 7))
                if math.hypot(o["x"] - p.x - 4, o["y"] - p.y - 7) > 70:
                    self.aimed(g, o["x"], o["y"], 1.3)
        else:
            o = next(q for q in self.orbs if q["alive"])
            self.ccx = g.cam_x + W / 2 + math.cos(self.t * 0.025) * 92
            self.ccy = self.cy0 - 40 + math.sin(self.t * 0.05) * 28
            o["x"], o["y"] = self.ccx, self.ccy
            self.x, self.y = self.ccx - 4, self.ccy - 4
            c = self.timer % 200                         # 3方向弾 → 間をあけて → 爆弾を3つ（同時には来ない）
            if c == 20:
                self.aimed(g, o["x"], o["y"], 1.4, (-0.3, 0, 0.3))
            elif c in (110, 130, 150) and abs(p.x + 4 - o["x"]) < 80:
                g.eshots.append(Bomb(o["x"], o["y"] + 6, 0))
                sfx(17, 3)
        for o in self.orbs:                               # 球に体当たりされるとダメージ
            if o["alive"] and not p.dead and p.invinc == 0 and abs(p.x + 4 - o["x"]) < 8 and abs(p.y + 7 - o["y"]) < 10:
                g.hurt_player(o["x"])

    def draw(self, g):
        t = self.t
        bm = self.beam()
        if self.phase == 1 and self.state in ("fight", "enter"):
            a, b = self.orbs
            if bm == "warn":
                if (t // 3) % 2:
                    for i in range(33):
                        f = i / 32
                        pyxel.pset(a["x"] + (b["x"] - a["x"]) * f, a["y"] + (b["y"] - a["y"]) * f, 8)
            elif bm == "on":
                dx, dy = b["x"] - a["x"], b["y"] - a["y"]
                ln = max(1.0, math.hypot(dx, dy))
                nx, ny = -dy / ln, dx / ln
                for off, col in ((-2, 2), (2, 2), (-1, 8), (1, 8), (0, 7 if t % 2 else 14)):
                    pyxel.line(a["x"] + nx * off, a["y"] + ny * off, b["x"] + nx * off, b["y"] + ny * off, col)
            else:
                pyxel.line(a["x"], a["y"], b["x"], b["y"], 1)
        for i, o in enumerate(self.orbs):
            if not o["alive"]:
                continue
            x, y = int(o["x"]), int(o["y"])
            body = 7 if o["flash"] else 13
            pyxel.circ(x, y, 7, 0)
            pyxel.circ(x, y, 6, body)
            pyxel.circ(x - 2, y - 2, 2, 7)
            ring = 12 if i == 0 else 8
            for k in range(3):
                a2 = t * 0.1 + k * math.pi * 2 / 3 + i
                pyxel.pset(x + math.cos(a2) * 9, y + math.sin(a2) * 9, ring)
            eye = ring if self.phase == 1 else (8 if (t // 4) % 2 else 10)
            pyxel.circ(x, y, 3, 0)
            pyxel.circ(x, y, 2, eye)
            if self.state == "dying" and (t // 3) % 2:
                pyxel.circ(x, y, 6, 8)


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
    S[19].set("g2c2", "n", "4", "f", 5)                # acid splash
    S[20].set("c2g2c3", "t", "4", "s", 4)              # leap
    S[21].set("a2e2", "p", "3", "f", 6)                # spit
    S[22].set("c4", "p", "2", "f", 2)                  # armored (tink)
    S[23].set("c2c2", "n", "2", "f", 6)                # crumble creak
    S[24].set("f1c1", "n", "5", "f", 8)                # crumble break
    S[25].set("c3c4", "s", "3", "f", 3)                # laser on
    S[26].set("c4c1", "n", "6", "f", 6)                # lightning
    S[27].set("c1c0", "n", "7", "f", 8)                # crusher slam
    S[28].set("a3", "s", "4", "f", 6)                  # countdown beep
    S[29].set("c2d2e2f2g2a2b2c3", "p", "2", "n", 4)    # beam charge
    S[30].set("e1c1", "n", "4", "f", 6)                # debris
    S[31].set("c2c1", "n", "4", "f", 4)                # mortar
    S[54].set("c4b3", "n", "3", "f", 4)                # icicle crack
    S[55].set("c4g3e3", "n", "4", "f", 3)              # shatter
    S[56].set("c2d2c2", "n", "3", "f", 4)              # roller / engine
    S[57].set("c1", "n", "7", "f", 10)                 # stomp
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


TRACKS = {}


def _apply_music(slot, seqs):
    m = pyxel.musics[slot]
    try:
        m.set(*seqs)
    except TypeError:                      # 4チャンネル必須の古い Pyxel 用
        m.set(*(list(seqs) + [[] for _ in range(4 - len(seqs))]))


def _set_music(idx, *seqs):
    """曲を登録する。MUSIC_SLOT 以降の曲は、鳴らすときに musics[MUSIC_SLOT] に読み込む"""
    TRACKS[idx] = seqs
    if idx < MUSIC_SLOT:
        _apply_music(idx, seqs)


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
    # --- 1-2 酸の湿地：ねっとりした Dマイナー（Dm B♭ C A ×2）
    lead2 = ("d4:4 f4:2 e4:2 d4:4 a3:4 "
             "b-3:4 d4:2 f4:2 b-4:6 a4:2 "
             "g4:4 e4:2 c4:2 e4:4 g4:4 "
             "a4:6 g4:2 e4:4 c#4:4 "
             "d4:2 r:2 d4:2 f4:2 a4:4 g4:2 f4:2 "
             "f4:4 d4:4 b-3:4 d4:4 "
             "g4:2 a4:2 b-4:2 a4:2 g4:4 d4:4 "
             "e4:4 c#4:4 a3:6 r:2")
    _set_sound(38, _mel(lead2, vib=True), "s", "3", 14)
    _set_sound(39, _bass("d b- c a d b- g a", "L..LL.H.L..LL.H."), "t", "5", 14)
    _set_music(BGM_STAGE2, [38], [39])
    # --- 1-3 中継塔：上へ上へと登っていく Eマイナー（Em C D B ×2）
    lead3 = ("e4:2 g4:2 b4:4 a4:2 g4:2 f#4:2 g4:2 "
             "e4:4 c4:4 e4:2 g4:2 e4:4 "
             "f#4:2 a4:2 d4:4 f#4:2 a4:2 b4:2 a4:2 "
             "b3:6 d#4:2 f#4:4 b4:4 "
             "g4:2 f#4:2 e4:2 b3:2 e4:4 g4:4 "
             "a4:4 g4:2 e4:2 c4:4 e4:4 "
             "a3:2 c4:2 e4:2 a4:2 f#4:2 e4:2 d4:2 f#4:2 "
             "b3:4 d#4:4 f#4:4 r:2 b3:2")
    _set_sound(40, _mel(lead3, vib=True), "p", "3", 12)
    _set_sound(41, _bass("e c d b e c a b", "L.HLL.HLL.HLL.HL"), "t", "5", 12)
    _set_music(BGM_STAGE3, [40], [41])
    # --- 1-4 敵母艦：重い行進曲の Cマイナー（Cm A♭ B♭ G ×2）
    lead4 = ("c4:2 r:1 c4:1 e-4:2 g4:4 f4:2 e-4:2 d4:2 "
             "c4:4 a-3:4 c4:2 e-4:2 a-4:4 "
             "b-3:2 d4:2 f4:2 b-4:4 a-4:2 g4:2 f4:2 "
             "g4:6 d4:2 b3:4 r:2 g3:2 "
             "e-4:2 d4:2 c4:2 g3:2 c4:4 e-4:4 "
             "a-4:2 g4:2 f4:2 e-4:2 c4:4 a-3:4 "
             "f4:2 g4:2 a-4:2 b-4:2 a-4:2 g4:2 f4:2 d4:2 "
             "g4:4 b3:4 d4:4 r:2 g3:2")
    _set_sound(42, _mel(lead4, vib=True), "s", "3", 13)
    _set_sound(43, _bass("c a- b- g c a- b- g", "L.L.HL.LL.L.HL.H"), "t", "5", 13)
    _set_music(BGM_STAGE4, [42], [43])
    # --- エンディング：穏やかな Cメジャー
    _set_sound(44, _mel("e4:4 g4:4 c4:8 d4:4 e4:4 g3:8 a3:4 c4:4 f4:8 g4:4 f4:4 e4:4 d4:4",
                        vib=True), "s", "3", 18)
    _set_sound(45, _arp("c2g2e3g2 a1e2c3e2 f1c2a2c3 g1d2b2d3"), "t", "4", 18)
    _set_music(BGM_ENDING, [44], [45])
    # --- ワールド2 マップ：凍った静けさの Aマイナー
    _set_sound(46, _mel("a3:8 c4:8 e4:12 d4:4 c4:8 b3:8 a3:8 r:8", vib=True), "s", "2", 20)
    _set_sound(47, _arp("a1e2c3e2 f1c2a2c3 c2g2e3g2 e1b1g#2b2"), "t", "4", 20)
    _set_music(BGM_W2MAP, [46], [47])
    # --- 2-1 氷原：きらめく Gマイナー（Gm E♭ F D ×2）
    ice = ("g4:2 d4:2 b-3:2 d4:2 g4:4 a4:2 b-4:2 "
           "e-4:4 g4:2 b-4:2 a4:4 g4:4 "
           "f4:2 a4:2 c4:2 f4:2 a4:4 g4:2 f4:2 "
           "f#4:6 a4:2 d4:4 r:2 d4:2 "
           "g4:4 b-4:4 a4:2 g4:2 d4:4 "
           "e-4:2 f4:2 g4:2 e-4:2 b-3:4 e-4:4 "
           "f4:2 g4:2 a4:2 c4:2 f4:4 e-4:2 d4:2 "
           "d4:8 r:4 d3:2 f#3:2")
    _set_sound(48, _mel(ice, vib=True), "p", "3", 11)
    _set_sound(49, _bass("g e- f d g e- f d", "L.HLL.HLL.HLL.HL"), "t", "5", 11)
    _set_music(BGM_ICE, [48], [49])
    # --- 2-2 溶岩洞：重く沈む Cフリジアン（Cm D♭ Cm B♭）
    magma = ("c3:4 c3:2 d-3:2 c3:4 g3:4 "
             "d-3:4 f3:2 a-3:2 d-4:4 c4:4 "
             "c4:2 b-3:2 g3:2 e-3:2 c3:4 r:4 "
             "b-2:4 d3:2 f3:2 b-3:6 a-3:2 "
             "g3:4 a-3:2 g3:2 f3:4 e-3:4 "
             "d-3:4 e-3:2 f3:2 a-3:4 d-4:4 "
             "c4:4 b-3:2 a-3:2 g3:4 f3:4 "
             "g3:8 r:4 g2:2 b2:2")
    _set_sound(50, _mel(magma, vib=True), "s", "3", 15)
    _set_sound(51, _bass("c d- c b- c d- a- g", "LLHLLLHL.LLHL.HL"), "t", "5", 15)
    _set_music(BGM_MAGMA, [50], [51])
    # --- 2-3 氷の要塞：速い行進曲の Eマイナー（Em C Am B）
    fort = ("e4:2 e4:2 g4:2 b4:4 a4:2 g4:2 f#4:2 "
            "e4:4 c4:2 e4:2 g4:4 e4:4 "
            "a4:2 c4:2 e4:2 a4:2 g4:2 f#4:2 e4:4 "
            "b3:4 d#4:4 f#4:4 b4:4 "
            "g4:2 a4:2 b4:4 a4:2 g4:2 e4:4 "
            "c4:4 e4:2 g4:2 e4:4 c4:4 "
            "a3:2 c4:2 e4:2 a4:2 b4:2 a4:2 g4:2 f#4:2 "
            "e4:6 b3:2 e4:4 r:4")
    _set_sound(52, _mel(fort, vib=True), "p", "3", 11)
    _set_sound(53, _bass("e c a b e c a b", "L.L.L.HLL.L.L.HL"), "t", "5", 11)
    _set_music(BGM_FORT, [52], [53])
    # --- オープニング：静かに始まり、不穏に揺れる Dマイナー
    op = ("d4:8 a3:8 f4:8 e4:8 "
          "d4:8 c4:8 a3:16 "
          "b-3:8 d4:8 g4:8 f4:8 "
          "e4:8 c#4:8 a3:16")
    _set_sound(58, _mel(op, vib=True), "s", "2", 22)
    _set_sound(59, _arp("d2a2f3a2 d2a2f3a2 b-1f2d3f2 a1e2c#3e2 "
                        "d2a2f3a2 c2g2e3g2 b-1f2d3f2 a1e2c#3e2"), "t", "3", 22)
    _set_music(BGM_OPENING, [58], [59])


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
        self.world = 1
        self.jump_buf = 0
        self.fire_press = False
        self.map_move = None
        self.lives = 3
        self.score = 0
        self.keep_weapon = "blaster"
        self.keep_hp = 2
        self.music_on = True
        self.cur_bgm = None
        self.checkpoint = None
        self.cp_reached = set()
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
            slot = n
            if n >= MUSIC_SLOT:
                _apply_music(MUSIC_SLOT, TRACKS[n])
                slot = MUSIC_SLOT
            pyxel.playm(slot, loop=True)

    def set_theme(self):
        theme = self.sdef.get("theme", "crash")
        self.theme = theme
        self.Ly = self.A.layers[theme]
        self.Lt = self.A.lights[theme]
        self.flick_alt = 9 if theme == "magma" else 12

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
        # ボタンを押した瞬間を覚えておく（ヒットストップ中に押しても取りこぼさない）
        if self.inp.pressed("jump"):
            self.jump_buf = JUMP_BUFFER
        if self.inp.pressed("fire"):
            self.fire_press = True
        if self.inp.pressed("quit"):
            pyxel.quit()
        if self.inp.pressed("reload"):
            self.A.load()
            if getattr(self, "stage", None) is not None:
                self.stage.render(self.A.tiles)
                self.set_theme()
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
            self.op_page, self.op_t = 0, 0
            self.state, self.state_t = "opening", 0

    # ---------- オープニング（ストーリー） ----------
    def update_opening(self):
        self.bgm(BGM_OPENING)
        self.op_t += 1
        page = OPENING[self.op_page]
        total = sum(len(L(*ln)) for ln in page["text"])
        typed = self.op_t // OP_TYPE_SPEED
        if self.inp.pressed("pause"):                 # Enter / START：全部飛ばす
            self.end_opening()
            return
        if self.inp.pressed("jump") or self.op_t >= page["time"]:
            if typed < total and self.op_t < page["time"]:
                self.op_t = total * OP_TYPE_SPEED     # 文字送り中なら、まず全文を表示
            else:
                sfx(7)
                self.op_page += 1
                self.op_t = 0
                if self.op_page >= len(OPENING):
                    self.end_opening()

    def end_opening(self):
        self.state, self.state_t = "map", 0
        self.jump_buf = 0
        self.fire_press = False
        self.toast(L("作戦開始！ 降下艇から出撃せよ", "MISSION START! DEPLOY FROM THE DROPSHIP"), 180)

    # ---------- ワールドマップ ----------
    def reachable(self):
        open_nodes = {"base", "w2base"} | self.cleared
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

    def warp_world(self, w):
        """ワールドを切り替える（マップ上のワープ地点・エンディングの後）"""
        self.world = w
        self.map_node = WORLDS[w]["arrive"]
        self.map_move = None
        self.state_t = 0
        sfx(13, 3)
        self.toast(L(*WORLDS[w]["name"]), 150)

    def update_map(self):
        self.bgm(BGM_MAP if self.world == 1 else BGM_W2MAP)
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
            if node.get("target"):
                self.warp_world(node["target"])
                return
            if node["stage"] is not None:
                sfx(7)
                self.checkpoint = None
                self.cp_reached = set()
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
        self.plats = [Platform(*a) for a in self.sdef.get("platforms", [])]
        self.plats += [Crumble(*a) for a in self.sdef.get("crumbles", [])]
        self.lasers = [LaserGate(*a) for a in self.sdef.get("lasers", [])]
        self.geysers = []
        self.bolts = []
        self.crushers = [Crusher(self.stage, *a) for a in self.sdef.get("crushers", [])]
        self.escape_t = None
        self.debris = []
        self.waves = []
        self.jets = []
        for jx, per, ph in self.sdef.get("jets", []):     # 火柱：溶岩の表面の高さを探す
            jy = 0
            while jy < self.stage.h and self.stage.get(jx, jy) not in LIQUID:
                jy += 1
            self.jets.append((jx * TS + 4, jy * TS, per, int(ph * per)))
        self.set_theme()
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
                self.enemies.append(Mech(bx, ty * TS, **self.sdef.get("boss", {})))
            elif ch == "U":
                self.enemies.append(Turret(bx - 1, by - 8))
            elif ch == "C":
                self.enemies.append(Supply(bx - 2, by - 8))
            elif ch == "O":
                self.enemies.append(Barrel(bx, by - 10))
            elif ch == "X":
                self.enemies.append(Wreck(bx - 2, by - 8))
            elif ch == "J":
                self.enemies.append(Leaper(bx, ty * TS))
            elif ch == "S":
                self.enemies.append(Spitter(bx - 1, by - 10))
            elif ch == "W":
                x0 = x1 = tx
                while self.stage.get(x0 - 1, ty) == ACID:
                    x0 -= 1
                while self.stage.get(x1 + 1, ty) == ACID:
                    x1 += 1
                self.enemies.append(Worm(bx, ty * TS, (x0, x1), **self.sdef.get("boss", {})))
            elif ch == "R":
                t0 = t1 = ty
                while self.stage.get(tx, t0 - 1) in LADDER:
                    t0 -= 1
                while self.stage.get(tx, t1 + 1) in LADDER:
                    t1 += 1
                self.enemies.append(LadderBot(bx, t0 * TS + 2, (t1 + 1) * TS - 28))   # 下の人の頭上で引き返す
            elif ch == "Q":
                self.enemies.append(Core(bx, ty * TS, **self.sdef.get("boss", {})))
            elif ch == "V":
                self.enemies.append(CeilTurret(bx - 1, ty * TS))
            elif ch == "A":
                self.enemies.append(Icicle(bx, ty * TS, rock=self.theme == "magma"))
            elif ch == "E":
                self.enemies.append(Roller(bx - 1, by - 10))
            elif ch == "L":
                self.enemies.append(Leaper(bx, ty * TS, lava=True))
            elif ch == "T":
                self.enemies.append(Tank(bx, by, **self.sdef.get("boss", {})))
            elif ch == "Y":
                self.enemies.append(Golem(bx, by, **self.sdef.get("boss", {})))
            elif ch == "N":
                self.enemies.append(Twins(bx, ty * TS, **self.sdef.get("boss", {})))
            elif ch == "M":
                self.enemies.append(Overlord(bx, by, **self.sdef.get("boss", {})))
            elif ch == "*":
                self.items.append(Item("cell", bx, by - 8, static=True))
            elif ch == "F":
                self.flags.append(dict(x=bx + 4, y=by, reached=False))
            elif ch == "G":
                self.door = dict(x=bx, y=by - 24, w=16, h=24)
        if from_cp and self.checkpoint:
            start = self.checkpoint
            for f in self.flags:
                if (f["x"], f["y"]) in self.cp_reached:
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
        self.cam_ymax = max(0, self.stage.h * TS - VIEW_H)
        self.cam_y = float(self.cam_ymax)
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
        self.cam_y = self.cam_target_y()
        self.state, self.state_t = "intro", 0

    def update_intro(self):
        if self.state_t > 100 or (self.state_t > 20 and self.in_ok()):
            self.state, self.state_t = "play", 0
            self.jump_buf = 0                  # 決定ボタン（Z）でジャンプしないように
            self.fire_press = False
            self.bgm(self.sdef.get("bgm", BGM_STAGE))

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
        for pl in self.plats:
            pl.update()
            if hasattr(pl, "step"):
                pl.step(self)
        for lz in self.lasers:
            lz.update(self)
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
            if (not e.active and self.cam_x - 24 <= e.x <= self.cam_x + W + 24 and
                    self.cam_y - 48 <= e.y <= self.cam_y + VIEW_H + 24):
                e.active = True
            if e.active and e.alive:
                if e.flash > 0:
                    e.flash -= 1
                e.update(self)
        self.update_shots()
        self.update_eshots()
        self.update_geysers()
        self.update_bolts()
        self.check_lasers()
        for cr in self.crushers:
            cr.update(self)
        self.update_escape()
        self.update_jets()
        self.update_waves()
        self.update_debris()
        self.update_items()
        self.update_pending()
        self.check_collisions()
        self.update_fx()
        self.update_ambient()
        self.enemies = [e for e in self.enemies if e.alive]

        for f in self.flags:
            if not f["reached"] and self.flag_hit(f):
                f["reached"] = True
                self.cp_reached.add((f["x"], f["y"]))
                self.checkpoint = (f["x"], f["y"] - Player.H_STAND)
                sfx(4)
                self.toast(L("ビーコン起動！ 中間地点", "BEACON ONLINE! CHECKPOINT"))
        if not self.boss_alive():
            self.gate_k = min(1.0, self.gate_k + 0.02)
        if self.door and not self.p.dead:
            d = self.door
            if abs(self.p.x - d["x"]) < 20 and abs(self.p.y + self.p.h - (d["y"] + 24)) < 16:
                if self.boss_alive():
                    if self.msg_t <= 0:
                        self.toast(L("隔壁はロックされている…", "THE BULKHEAD IS LOCKED..."), 60)
                elif self.gate_k >= 1 and d["x"] + 4 < self.p.x + self.p.w and self.p.x < d["x"] + 12:
                    self.stage_clear()

    def flag_hit(self, f):
        p = self.p
        if self.sdef.get("vertical"):
            return abs(p.x + 4 - f["x"]) < 16 and abs(p.y + p.h - f["y"]) < 12
        return p.x >= f["x"]

    def cam_target_y(self):
        """縦スクロールの目標。ボス部屋に入ったら一番上で固定"""
        p = self.p
        if self.cam_ymax <= 0:
            return 0.0
        ay = self.sdef.get("arena_y")
        if ay is not None and p.y + p.h <= ay + 1:
            return 0.0
        return clamp(p.y + p.h / 2 - VIEW_H * 0.58, 0, self.cam_ymax)

    def update_camera(self):
        p = self.p
        max_cam = self.stage.w * TS - W
        cam = clamp(p.x + 4 - W / 2, 0, max_cam)
        if any(e.boss and e.alive and e.active for e in self.enemies):
            if not self.boss_seen:
                self.boss_seen = True
                self.warn_t = 150
                self.bgm(None)
                hatch = self.sdef.get("hatch")
                if hatch:                                # ボス部屋の床を閉じる
                    for tx, ty in hatch:
                        self.stage.tiles[ty][tx] = "="
                    self.stage.render(self.A.tiles)
            self.cam_min = max(self.cam_min, cam)
        self.cam_x = max(cam, self.cam_min)
        ax = self.sdef.get("arena_x_max")
        if ax and self.boss_seen and self.boss_alive():
            self.cam_x = min(self.cam_x, ax - W)
        if p.x < self.cam_x:
            p.x = self.cam_x
        if self.cam_ymax > 0:
            ty = self.cam_target_y()
            self.cam_y += (ty - self.cam_y) * 0.15
            if not p.dead:                                # 画面外に出ないように
                self.cam_y = clamp(self.cam_y, p.y + p.h - VIEW_H + 8, p.y - 20)
            self.cam_y = clamp(self.cam_y, 0, self.cam_ymax)

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
        if p.ride is not None:                   # 動く足場に乗っている
            pl = p.ride
            if (p.climbing or p.vy < 0 or not getattr(pl, "solid", True) or
                    not (p.x + p.w > pl.x and p.x < pl.x + pl.w)):
                p.ride = None
            else:
                self.player_move_x(pl.dx)
                p.y = pl.y - p.h
        if p.invinc > 0:
            p.invinc -= 1
        if p.shoot_cd > 0:
            p.shoot_cd -= 1
        if p.throw_t > 0:
            p.throw_t -= 1

        lft, rgt, up, dn = self.in_left(), self.in_right(), self.in_up(), self.in_down()
        jump = self.jump_buf > 0
        if self.jump_buf > 0:
            self.jump_buf -= 1
        wd = WEAPONS[p.weapon]
        fire_held = self.inp.held("fire")
        if self.fire_press:
            self.fire_press = False
            p.fire_buf = FIRE_BUFFER
        elif p.fire_buf > 0:
            p.fire_buf -= 1
        fire = p.fire_buf > 0 or (wd["auto"] and fire_held)
        move_in = (1 if rgt else 0) - (1 if lft else 0)

        if p.climbing:
            if not jump:                                  # はしごの上でも左右に撃てる
                if lft and not rgt:
                    p.facing = -1
                elif rgt and not lft:
                    p.facing = 1
            if fire and self.player_shoot():
                p.fire_buf = 0
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
        # はしご：↑を少し押し続けるとつかむ。その間に攻撃ボタンを押したら上撃ちを優先
        on_ladder = st.get(ctx, mid_ty) in LADDER or st.get(ctx, feet_ty) in LADDER
        if fire_held:
            p.grab = -10
        elif p.grab < 0:
            p.grab += 1
        elif up and on_ladder and not p.crouch and (move_in == 0 or p.grab > 0 or self.inp.pressed("up")):
            p.grab += 1
        else:
            p.grab = 0
        if p.grab >= LADDER_GRAB_DELAY and on_ladder:
            p.grab = 0
            self.start_climb(ctx)
            return
        if dn and p.on_ground and st.get(ctx, int((p.y + p.h + 1) // TS)) in LADDER:
            self.start_climb(ctx)
            p.y += 3
            return

        p.set_crouch(st, dn and p.on_ground)
        move = (1 if rgt else 0) - (1 if lft else 0)
        if p.on_ground:
            target_vx = 0 if p.crouch else move * WALK_SPEED
            if self.on_ice():                                 # 氷の上はすべる
                p.vx += clamp(target_vx - p.vx, -ICE_ACCEL, ICE_ACCEL)
                if abs(p.vx - target_vx) > 0.4 and self.gt % 3 == 0:
                    self.parts.append([p.x + 4, p.y + p.h, -p.vx * 0.3, -0.5, 12, 7, 0.05, 0])
            else:
                p.vx = target_vx
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
            self.jump_buf = 0
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
        self.player_move_x(p.vx)
        self.player_move_y()
        if p.on_ground and p.vx != 0:
            p.anim += 1
        if p.on_ground and p.ride is None:            # ベルトコンベアに流される
            c = st.get(int((p.x + 4) // TS), int((p.y + p.h + 1) // TS))
            if c in CONVEYOR:
                self.player_move_x(CONVEY_SPEED * (1 if c == ">" else -1))
        self.check_hazards()

    def on_ice(self):
        p, st = self.p, self.stage
        ty = int((p.y + p.h + 1) // TS)
        return any(st.get(int(px // TS), ty) == ICE for px in (p.x + 1, p.x + 4, p.x + p.w - 2))

    def player_move_x(self, dx):
        """横移動。足元の 3px 以内の段差（動く足場と床のずれ）は自動で乗り越える"""
        p, st = self.p, self.stage
        ox, oy = p.x, p.y
        if move_x(st, p, dx) and p.on_ground and dx != 0:
            for up in (1, 2, 3):
                if not collide_solid(st, ox + dx, oy - up, p.w, p.h):
                    p.x, p.y = ox + dx, oy - up
                    break

    def player_move_y(self):
        p = self.p
        was_ground = p.on_ground
        if not was_ground:
            p.air_top = min(p.air_top, p.y)
        old_bottom = p.y + p.h
        move_y(self.stage, p, p.vy)
        if p.on_ground:
            p.ride = None
        elif p.vy >= 0:                          # 動く足場への着地
            p.ride = None
            for pl in self.plats:
                if not getattr(pl, "solid", True):
                    continue
                if (p.x + p.w > pl.x and p.x < pl.x + pl.w and p.y + p.h >= pl.y and
                        old_bottom <= pl.y - pl.dy + 0.5):
                    p.y = pl.y - p.h
                    p.vy = 0
                    p.on_ground = True
                    p.ride = pl
                    break
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
        p.ride = None
        p.set_crouch(self.stage, False)
        p.climbing = True
        p.x = ctx * TS + TS / 2 - p.w / 2
        p.vx = p.vy = 0

    def update_climb(self, lft, rgt, up, dn, jump):
        p, st = self.p, self.stage
        if jump and (lft or rgt):
            self.jump_buf = 0
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
        if st.tile_at(p.x + 4, p.y + p.h - 1) in LIQUID:
            self.acid_bounce()
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
        if p.shoot_cd > 0:
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
                    or (beam and (s.y + s.h < self.cam_y - 2 or s.y > self.cam_y + VIEW_H + 2))):
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
            if s.kind in ("bomb", "shell", "rock"):
                if st.solid(s.x + 3, s.y + 6) or s.y > st.h * TS:
                    s.alive = False
                    self.bomb_blast(s.x + 3, s.y + 5)
                continue
            in_acid = s.kind == "blob" and st.tile_at(s.x + 3, s.y + 3) in LIQUID
            if (st.solid(s.x + 3, s.y + 3) or in_acid or s.t > 300 or s.y > st.h * TS or
                    s.x < self.cam_x - 16 or s.x > self.cam_x + W + 16 or
                    s.y < self.cam_y - 40 or s.y > self.cam_y + VIEW_H + 40):
                s.alive = False
                if st.solid(s.x + 3, s.y + 3) or in_acid:
                    if s.kind == "blob":
                        self.acid_splash(s.x + 3, s.y + 3, 5, sound=False)
                    else:
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
                if st.tile_at(it.x + 4, it.y + it.h - 1) in LIQUID:
                    it.alive = False
                    self.acid_splash(it.x + 4, it.y + it.h - 2, 5, sound=False)
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
            for e in self.enemies:                   # ボスのシールド
                if e.alive and e.active and hasattr(e, "absorb") and e.absorb(self, s):
                    s.alive = False
                    break
            if not s.alive:
                continue
            for e in self.enemies:
                if not (e.alive and e.active and e.hittable) or not overlap(s, e):
                    continue
                if s.kind == "grenade":
                    s.alive = False
                    self.explode(s.x + 2, s.y + 2, 20, s.dmg)
                    break
                if getattr(e, "armored", False):        # 閉じた酸吐き草は弾をはじく
                    s.alive = False
                    self.spark(s.x + s.w / 2, s.y + s.h / 2, 13)
                    sfx(22, 3)
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
                if b.alive and b.kind in ("bomb", "shell", "rock") and overlap(s, b):
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
        if p.hp <= 1 and random.random() < 0.7:
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
            self.toast(L(*e.defeat_msg), 100)
            return
        e.alive = False
        self.add_score(e.score, e.cx(), e.y)
        e.on_death(self)
        self.hitstop = max(self.hitstop, 1 if e.prop else 3)
        if not e.prop and random.random() < 0.08:
            self.items.append(Item(self.roll_item(), e.x, e.y))

    # ---------- 酸・間欠泉・動く足場 ----------
    def acid_splash(self, x, y, n=8, sound=True):
        st = self.stage
        lava = LAVA in (st.tile_at(x, y - 1), st.tile_at(x, y + 3), st.tile_at(x, y + 9))
        cols = (10, 9, 9, 8) if lava else (11, 11, 3, 7)
        for _ in range(n):
            self.parts.append([x + random.uniform(-3, 3), y, random.uniform(-1.2, 1.2),
                               random.uniform(-2.6, -0.8), random.randint(14, 24),
                               random.choice(cols), 0.15, 0])
        if sound:
            sfx(19, 3)

    def acid_bounce(self):
        """酸に触れた：ダメージ（無敵中は無し）を受けて、近い岸の方へ跳ね上がる"""
        p, st = self.p, self.stage
        tx, ty = int((p.x + 4) // TS), int((p.y + p.h - 1) // TS)
        d = p.facing
        for k in range(1, 30):
            if st.get(tx + k, ty) not in LIQUID:
                d = 1
                break
            if st.get(tx - k, ty) not in LIQUID:
                d = -1
                break
        self.acid_splash(p.x + 4, ty * TS)
        if p.invinc == 0:
            if st.get(tx, ty) == LAVA:
                self.toast(L("溶岩に落ちた！", "LAVA!"), 60)
            else:
                self.toast(L("酸に落ちた！", "ACID!"), 60)
            self.hurt_player(p.x + 4 - d * 8)
        if p.dead:
            return
        p.hurt, p.climbing, p.ride = True, False, None
        p.vx, p.vy = d * 1.6, -5.0
        p.on_ground = False
        p.air_top = p.y

    def update_geysers(self):
        p = self.p
        for gz in self.geysers:
            gz["t"] += 1
            t, x, sy = gz["t"], gz["x"], gz["y"]
            if t < 0:
                continue
            if t < 45:                                   # 予告：泡が立つ
                if random.random() < 0.5:
                    self.parts.append([x + random.uniform(-5, 5), sy, random.uniform(-0.3, 0.3),
                                       random.uniform(-1.2, -0.4), 12,
                                       random.choice((10, 9) if gz.get("lava") else (11, 7)), 0, 0])
            else:
                if t == 45:
                    sfx(19, 3)
                    self.shake = max(self.shake, 2)
                hh = 50 * min(1.0, (t - 45) / 6)
                if (not p.dead and p.invinc == 0 and abs(p.x + 4 - x) < 8 and
                        p.y + p.h > sy - hh and p.y < sy):
                    self.hurt_player(x)
                if random.random() < 0.6:
                    self.parts.append([x + random.uniform(-4, 4), sy - hh, random.uniform(-1, 1),
                                       random.uniform(-1.5, -0.5), 14, 9 if gz.get("lava") else 11, 0.15, 0])
        self.geysers = [gz for gz in self.geysers if gz["t"] < 78]

    def check_lasers(self):
        p = self.p
        if p.dead or p.invinc > 0:
            return
        for lz in self.lasers:
            if lz.on() and overlap(p, lz):
                self.toast(L("レーザーに触れた！", "LASER!"), 60)
                for _ in range(6):
                    self.parts.append([p.x + 4, p.y + 7, random.uniform(-2, 2), random.uniform(-2, 0),
                                       10, random.choice((8, 7)), 0.1, 4])
                self.hurt_player(lz.x + lz.w / 2 if lz.orient == "v" else p.x + 4 - p.facing * 4)
                return

    def add_bolt(self, x, warn, delay=0):
        """落雷：床に予告マーク（warn フレーム）→ 18 フレームの稲妻"""
        st = self.stage
        top = self.cam_y - 4
        bottom = top + VIEW_H + 8
        for yy in range(int(self.cam_y + 40), int(self.cam_y + VIEW_H + 8), 4):
            if st.solid(x, yy):
                bottom = yy - yy % TS
                break
        self.bolts.append(dict(x=x, t=-delay, warn=warn, top=top, bottom=bottom))

    def update_bolts(self):
        p = self.p
        for b in self.bolts:
            b["t"] += 1
            t, w = b["t"], b["warn"]
            if t == w:
                sfx(26, 3)
                self.shake = max(self.shake, 2)
                for _ in range(6):
                    self.parts.append([b["x"], b["bottom"] - 1, random.uniform(-1.5, 1.5),
                                       random.uniform(-2, -0.5), 12, random.choice((12, 7)), 0.1, 4])
            if w <= t < w + 18 and not p.dead and p.invinc == 0:
                if abs(p.x + 4 - b["x"]) < 7 and p.y < b["bottom"] and p.y + p.h > b["top"]:
                    self.hurt_player(b["x"])
        self.bolts = [b for b in self.bolts if b["t"] < b["warn"] + 18]

    def redraw_acid(self, x0, x1, ty):
        """ボスの頭の下に酸の表面を描き直す（水面から出ているように見せる）"""
        st = self.stage
        for tx in range(int(x0 // TS), int(x1 // TS) + 1):
            if st.get(tx, ty) == ACID and st.get(tx, ty - 1) != ACID:
                fr = (self.gt // 8 + tx) % 3
                pyxel.blt(tx * TS, ty * TS, self.A.tiles, 56 + fr * 8, 16, TS, TS, KEY)

    def draw_platform(self, pl):
        x, y, w = int(pl.x), int(pl.y), pl.w
        pyxel.rect(x, y, w, 4, 0)
        pyxel.rect(x + 1, y, w - 2, 3, 13)
        pyxel.line(x + 1, y, x + w - 2, y, 7)
        pyxel.line(x + 1, y + 2, x + w - 2, y + 2, 5)
        for i in range(x + 4, x + w - 3, 4):
            pyxel.pset(i, y + 1, 5)
        glow = 12 if (self.gt // 3) % 2 else 6
        for ex in (x + 2, x + w - 3):
            pyxel.pset(ex, y + 4, glow)
            pyxel.pset(ex, y + 5 + (self.gt // 2) % 2, 12)

    def boss_phase(self, e):
        self.hitstop = 10
        self.shake = 5
        sfx(18, 3)
        for _ in range(3):
            self.boom(e.x + random.uniform(0, 20), e.y + random.uniform(0, 14), 6,
                      debris=4, smoke=2, sound=False)
        self.eshots = [s for s in self.eshots if s.kind == "bomb"]
        msg = e.phase_msgs.get(e.phase)
        if msg:
            self.toast(L(*msg), 100)

    def boss_destroyed(self, e):
        sfx(8, 3)
        self.add_score(e.score, e.cx(), e.y)
        self.explode(e.cx(), e.cy(), 30, 0)
        self.shake = 8
        self.hitstop = 12
        self.items.append(Item("power", self.p.x, self.p.y - 24))
        if self.sdef.get("escape"):
            self.start_escape()
        else:
            self.toast(L("隔壁ロック解除！", "BULKHEAD UNLOCKED!"), 150)

    # ---------- 脱出（母艦の自爆） ----------
    def start_escape(self):
        for tx, ty in self.sdef.get("escape_open", []):
            self.stage.tiles[ty][tx] = "."
        self.stage.render(self.A.tiles)
        self.escape_t = self.sdef["escape"] * 60
        self.debris = []
        self.toast(L("自爆装置が作動！ 脱出せよ！", "SELF-DESTRUCT! ESCAPE NOW!"), 180)
        self.bgm(BGM_BOSS)

    def floor_y(self, x):
        st = self.stage
        y = 0
        while st.solid(x, y) and y < st.h * TS:
            y += 1
        while not st.solid(x, y) and y < st.h * TS:
            y += 1
        return y

    def ceil_y(self, x):
        st = self.stage
        y = 0
        while st.solid(x, y) and y < st.h * TS:
            y += 1
        return y

    def drop_debris(self, x, warn=40):
        """天井から岩・瓦礫を落とす（床に影で予告）"""
        self.debris.append(dict(x=x, t=0, warn=warn, y0=self.ceil_y(x), fy=self.floor_y(x)))

    def update_debris(self):
        p = self.p
        for d in self.debris:
            d["t"] += 1
            k = d["t"] - d["warn"]
            if k < 0:
                if random.random() < 0.3:
                    self.parts.append([d["x"] + random.uniform(-4, 4), d["y0"] + 2, 0, random.uniform(0.5, 1.5),
                                       14, 13, 0.1, 0])
                continue
            d["y"] = d["y0"] + k * k * 0.32
            if p.invinc == 0 and not p.dead and overlap(p, Box(d["x"] - 4, d["y"] - 6, 8, 9)):
                self.hurt_player(d["x"])
            if d["y"] >= d["fy"] - 4:
                d["done"] = True
                self.boom(d["x"], d["fy"] - 3, 6, debris=4, smoke=1, sound=False)
                sfx(30, 3)
        self.debris = [d for d in self.debris if not d.get("done")]

    # ---------- 溶岩の火柱・地面を走る衝撃波 ----------
    def update_jets(self):
        for x, y, per, off in self.jets:
            if (self.gt + off) % per == 0 and abs(x - (self.cam_x + W / 2)) < W:
                self.geysers.append(dict(x=x, y=y, t=0, lava=True))

    def update_waves(self):
        p, st = self.p, self.stage
        for wv in self.waves:
            wv["t"] += 1
            if wv["t"] <= WAVE_RISE:                     # 叩きつけた直後は炎が立ち上がるだけ（跳ぶ猶予）
                continue
            wv["x"] += wv["dir"] * WAVE_SPEED
            if (st.solid(wv["x"] + wv["dir"] * 4, wv["y"] - 4) or not st.solid(wv["x"], wv["y"] + 2)
                    or wv["t"] > 160):
                wv["done"] = True
                continue
            if random.random() < 0.5:
                self.parts.append([wv["x"] + random.uniform(-3, 3), wv["y"] - random.uniform(0, 10),
                                   random.uniform(-0.5, 0.5), random.uniform(-1.5, -0.5), 10,
                                   random.choice((9, 10, 8)), 0.1, 4])
            if not p.dead and p.invinc == 0 and overlap(p, Box(wv["x"] - 4, wv["y"] - 12, 8, 12)):
                self.hurt_player(wv["x"])
        self.waves = [w for w in self.waves if not w.get("done")]

    def update_escape(self):
        if self.escape_t is None or self.p.dead:
            return
        if self.state != "play":
            return
        self.escape_t -= 1
        if self.escape_t % 60 == 0 and self.escape_t <= 600:
            sfx(28, 3)
        if self.gt % 3 == 0:
            self.shake = max(self.shake, 1.2)
        if self.gt % DEBRIS_EVERY == 0:                  # 天井から落ちてくる瓦礫（影で予告）
            px = self.p.x + 4
            for _ in range(8):
                x = clamp(px + random.uniform(-24, 120), self.cam_x + 8, self.cam_x + W - 8)
                if abs(x - px) > 12 and all(abs(x - d["x"]) > 18 for d in self.debris):
                    self.drop_debris(x)
                    break
        if self.escape_t <= 0:
            self.toast(L("脱出に失敗した…", "TOO LATE..."), 120)
            self.kill_player()

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
        p.invinc = 120
        p.climbing = False
        p.ride = None
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
        if self.spawn_t < self.sdef.get("spawn_every", 110):
            return
        self.spawn_t = 0
        p, st = self.p, self.stage
        ptx = int(p.x // TS)
        zones = self.sdef.get("spawn_zones", [])
        if not any(a <= ptx <= b for a, b in zones):
            return
        if (sum(1 for e in self.enemies if isinstance(e, Mutant)) >= self.sdef.get("spawn_max", 3)
                or random.random() > self.sdef.get("spawn_chance", 0.8)):
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
        for tx, ty in self.stage.lava_tiles:
            if random.random() < 0.015 and abs(tx * TS - (self.cam_x + W / 2)) < W / 2 + 16:
                self.parts.append([tx * TS + random.uniform(1, 7), ty * TS + 2, random.uniform(-0.2, 0.2),
                                   random.uniform(-0.9, -0.3), 22, random.choice((10, 9, 8)), 0.02, 0])
        for tx, ty in self.stage.acid_tiles:
            if random.random() < 0.012 and abs(tx * TS - (self.cam_x + W / 2)) < W / 2 + 16:
                self.parts.append([tx * TS + random.uniform(1, 7), ty * TS + 3, 0, -0.25, 18,
                                   random.choice((11, 7)), 0, 0])
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
            if self.theme in ("ice", "fort"):              # 雪が降る
                m[1] += 0.45 + m[2]
            elif self.theme == "magma":                    # 火の粉が舞い上がる
                m[1] -= 0.3 + m[2]
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
            if self.sdef.get("final"):
                self.state, self.state_t = "ending", 0
                return
            self.state, self.state_t = "map", 0
            if first:
                self.toast(L("新しいルートが開いた！", "A NEW ROUTE OPENED!"), 150)

    def update_ending(self):
        self.bgm(BGM_ENDING)
        if (self.state_t > 360 and self.in_ok()) or self.state_t > 3600:
            self.state, self.state_t = "map", 0
            if self.sdef.get("world", 1) == 1:
                self.warp_world(2)
                self.toast(L("氷の衛星フロストへ向かう！", "OFF TO THE FROST MOON!"), 240)
            else:
                self.toast(L("ワールド2 クリア！ 次のワールドは準備中", "WORLD 2 CLEAR! NEXT WORLD COMING SOON"), 240)

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

    # ---------- オープニング ----------
    def draw_opening(self):
        pyxel.cls(0)
        page = OPENING[self.op_page]
        t = self.op_t
        getattr(self, "op_scene_" + page["scene"])(t)
        pyxel.rect(0, 0, W, 18, 0)                       # シネマスコープ風の黒帯
        pyxel.rect(0, 160, W, H - 160, 0)
        pyxel.line(0, 160, W, 160, 1)
        shown = t // OP_TYPE_SPEED                         # 字幕（1文字ずつ表示）
        y = 168
        for ln in page["text"]:
            s = L(*ln)
            if shown <= 0:
                break
            part = s[:shown]
            txt(14, y, part, 7, shadow=1)
            shown -= len(s)
            y += 14
        if t < 16:                                         # 場面の切り替えはフェードイン風に
            for yy in range(18, 160, 2):
                if (yy // 2 + t) % 16 > t:
                    pyxel.line(0, yy, W, yy, 0)
        total = sum(len(L(*ln)) for ln in page["text"])
        if t // OP_TYPE_SPEED >= total and (t // 20) % 2 == 0:
            pyxel.tri(W - 16, 208, W - 8, 208, W - 12, 213, 10)
        for i in range(len(OPENING)):                      # ページの印
            pyxel.rect(W - 10 - (len(OPENING) - i) * 6, 6, 4, 4, 10 if i == self.op_page else 5)
        txt(6, 4, L("Enter:スキップ", "ENTER:SKIP"), 5)

    def op_planet(self, cy, r, col=1, rim=12):
        pyxel.circ(W // 2, cy, r, col)
        pyxel.circb(W // 2, cy, r, rim)
        pyxel.circb(W // 2, cy, r - 1, 5)

    def op_scene_colony(self, t):
        self.draw_stars(t)
        self.op_planet(300, 170)
        for i, (x, dy) in enumerate(((70, 4), (96, -2), (120, 0), (150, 2), (176, -3), (200, 5))):
            gy = 300 - int((170 ** 2 - (x - W // 2) ** 2) ** 0.5) + 6 + dy   # 地表のコロニーの灯り
            on = t < 200 + i * 25 or (t // 3 + i) % 7 == 0 and t < 280 + i * 25
            col = 10 if on else 1
            pyxel.rect(x - 3, gy - 2, 6, 3, 5 if on else 1)
            pyxel.pset(x, gy - 3, col)
            if on and (t // 20 + i) % 3:
                pyxel.pset(x - 2, gy - 1, 10)
        ry = 40 + int(math.sin(t * 0.02) * 2)              # 静かに光る衛星
        pyxel.circ(206, ry, 10, 13)
        pyxel.circ(203, ry - 3, 3, 7)
        if 200 < t < 300 and (t // 4) % 2:                 # 通信途絶の表示
            ctxt(W / 2, 30, L("― 通信途絶 ―", "- SIGNAL LOST -"), 8)

    def op_scene_invasion(self, t):
        self.draw_stars(t)
        self.op_planet(330, 190, 1, 8 if (t // 10) % 2 else 2)
        my = min(70, -40 + t * 0.6)                         # 降りてくる母艦
        mx = W // 2
        pyxel.elli(mx - 70, my - 12, 140, 26, 0)
        pyxel.elli(mx - 66, my - 10, 132, 20, 1)
        pyxel.rect(mx - 20, my - 22, 40, 12, 1)
        pyxel.rect(mx - 6, my - 30, 12, 8, 1)
        for i in range(-60, 61, 10):
            pyxel.pset(mx + i, my + 4, 8 if (t // 6 + i) % 3 else 10)
        pyxel.circ(mx, my + 8, 4, 8 if (t // 5) % 2 else 2)
        if t > 120:                                         # 光の柱と降下するドローン
            for k in range(-2, 3):
                pyxel.line(mx + k * 3, my + 10, mx + k * 14, 160, 2 if k % 2 else 8)
            for i in range(16):
                d = (t * 1.3 + i * 23) % 120
                x = mx + math.sin(i * 1.7) * (8 + d * 0.8)
                pyxel.rect(x, my + 10 + d, 3, 2, 13)
                pyxel.pset(x + 1, my + 12 + d, 8)
        if t > 300:                                         # 地表の炎
            for i in range(12):
                x = 30 + i * 18
                h = 4 + (t // 3 + i * 5) % 6
                pyxel.tri(x - 3, 160, x + 3, 160, x, 160 - h, 9)

    def op_scene_drop(self, t):
        pyxel.cls(1)
        for x, y, ph in self.map_stars:                     # 流れる星（高速で降下中）
            yy = (y + t * 3 + ph) % 140 + 18
            pyxel.line(x, yy, x, yy + 3, 5)
        self.op_planet(340, 200, 0, 8)
        pyxel.elli(150, 24, 70, 14, 0)                      # 遠くに母艦
        for i in range(6):
            pyxel.pset(160 + i * 9, 31, 8)
        k = min(1.0, t / 300)                                # 突入する降下艇
        sx, sy = int(40 + k * 120), int(28 + k * 100)
        for i in range(10):
            fx = sx - 4 - i * 4 + random.randint(-1, 1)
            fy = sy - 4 - i * 3 + random.randint(-1, 1)
            pyxel.circ(fx, fy, 4 - i * 0.35, (10, 9, 8, 2)[min(3, i // 3)])
        pyxel.tri(sx - 6, sy - 6, sx + 10, sy + 4, sx - 2, sy + 8, 13)
        pyxel.tri(sx - 6, sy - 6, sx + 10, sy + 4, sx + 2, sy - 2, 6)
        pyxel.pset(sx + 4, sy + 1, 12)
        if (t // 12) % 2:
            pyxel.pset(sx - 4, sy - 2, 8)

    def op_scene_hero(self, t):
        pyxel.cls(0)
        self.draw_stars(t)
        for i in range(14):                                 # 背後の放射状の光
            a = i * math.pi / 7 + t * 0.004
            pyxel.line(W // 2, 92, W // 2 + math.cos(a) * 200, 92 + math.sin(a) * 200, 1)
        sc = 5                                              # 主人公を拡大して描く
        ox, oy = W // 2 - 8 * sc, 92 - 8 * sc + int(math.sin(t * 0.05) * 2)
        u, v = 0, SPR_ROW[2] * SPR
        img = self.A.hero
        for yy in range(SPR):
            for xx in range(SPR):
                c = img.pget(u + xx, v + yy)
                if c != KEY:
                    pyxel.rect(ox + xx * sc, oy + yy * sc, sc, sc, c)
        if 40 < t % 160 < 52:                               # バイザーがきらりと光る
            k = (t % 160) - 40
            pyxel.line(ox + 6 * sc + k * 2, oy + 3 * sc, ox + 6 * sc + k * 2 - 6, oy + 5 * sc, 7)
        if t > 200:
            ctxt(W / 2, 30, "NOVA TROOPER", 10 if (t // 8) % 2 else 9, shadow=2)

    # ---------- ワールドマップ ----------
    def draw_map(self):
        t = self.state_t
        pyxel.cls(0)
        self.draw_stars(t)
        if self.world == 2:
            self.draw_map_w2(t)
        else:
            self.draw_map_w1(t)

        reach = self.reachable()
        for a, b in WORLD_EDGES:
            if WORLD_NODES[a]["w"] != self.world:
                continue
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
            if n["w"] != self.world:
                continue
            x, y = n["x"], n["y"]
            if n["kind"] == "home":
                pyxel.elli(x - 10, y + 2, 20, 6, 0)
                pyxel.tri(x - 9, y + 3, x + 11, y + 3, x + 1, y - 9, 13)
                pyxel.tri(x + 1, y - 9, x + 11, y + 3, x + 4, y + 3, 5)
                pyxel.rect(x - 2, y - 2, 4, 3, 12)
                pyxel.pset(x + 1, y - 10, 8 if (t // 15) % 2 else 2)
            elif n["kind"] == "castle" and nid in self.cleared:     # 撃破後の残骸
                pyxel.elli(x - 16, y - 2, 30, 8, 0)
                pyxel.tri(x - 14, y + 2, x - 4, y - 8, x + 2, y + 2, 1)
                pyxel.tri(x + 2, y + 2, x + 10, y - 5, x + 14, y + 2, 1)
                for i in range(3):
                    sy = y - 10 - ((t // 4 + i * 7) % 18)
                    pyxel.pset(x - 4 + i * 6 + ((t // 9 + i) % 3) - 1, sy, 5 if i % 2 else 13)
            elif n["kind"] == "castle":
                by = y + int(math.sin(t * 0.05) * 2)
                pyxel.elli(x - 18, by - 6, 36, 12, 0)
                pyxel.elli(x - 16, by - 5, 32, 9, 1)
                pyxel.rect(x - 6, by - 10, 12, 5, 1)
                for i in range(-12, 13, 4):
                    pyxel.pset(x + i, by, 12 if (t // 8 + i) % 3 else 7)
                pyxel.pset(x + 16, by - 2, 8 if nid not in reach or (t // 10) % 2 else 2)
                pyxel.elli(x - 8, by + 10, 16, 4, 1)
            elif n["kind"] == "warp":                     # ワールド間のワープ地点
                if nid in reach:
                    for k in range(3):
                        pyxel.circb(x, y, 4 + k * 2 + (t // 6) % 2, (12, 6, 5)[k])
                    pyxel.circ(x, y, 3, 7 if (t // 8) % 2 else 12)
                    pyxel.text(x - 7, y + 11, "W" + str(n["target"]), 7)
                else:
                    pyxel.circb(x, y, 5, 5)
            elif n["kind"] == "fort":                     # 氷の要塞
                cl = nid in self.cleared
                body = 1 if cl else 5
                pyxel.rect(x - 11, y - 8, 22, 12, 0)
                pyxel.rect(x - 10, y - 7, 20, 10, body)
                for i in range(-10, 10, 4):
                    pyxel.rect(x + i, y - 11, 2, 3, body)
                pyxel.rect(x - 3, y - 17, 6, 9, body)
                pyxel.line(x - 10, y - 7, x + 9, y - 7, 7)
                pyxel.rect(x - 2, y - 2, 4, 6, 0)
                if cl:
                    for i in range(3):
                        sy = y - 18 - ((t // 4 + i * 7) % 16)
                        pyxel.pset(x - 4 + i * 4, sy, 5 if i % 2 else 13)
                else:
                    pyxel.pset(x, y - 18, 8 if (t // 10) % 2 else 2)
                pyxel.text(x - 5, y + 9, nid, 7)
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
        txt(4, 3, L(*WORLDS[self.world]["name"]), 12 if self.world == 1 else 6)
        txt(170, 3, f"x{self.lives}  {self.score:06d}", 10)
        pyxel.rect(0, 198, W, 26, 0)
        pyxel.rectb(0, 198, W, 26, 5)
        if not self.map_move:
            n = WORLD_NODES[self.map_node]
            name = L(*n["name"])
            if self.map_node in self.cleared:
                name += L("  ★クリア済", "  *CLEAR")
            elif n["kind"] not in ("home", "warp") and n["stage"] is None:
                name += L("  （準備中）", "  (SOON)")
            txt(6, 201, name, 7)
        txt(6, 212, L("矢印/十字キー:移動  Z/A:決定", "ARROWS/DPAD:MOVE  Z/A:ENTER"), 13)
        draw_item(self.keep_weapon, 176, 202, t)
        txt(188, 201, L(*WEAPONS[self.keep_weapon]["name"]), 7)
        suit = {3: (L("パワースーツ", "POWER SUIT"), 10)}.get(self.keep_hp, (L("スーツ", "SUIT"), 13))
        txt(188, 212, suit[0], suit[1])
        if self.msg_t > 0:
            pyxel.rect(30, 172, W - 60, 16, 0)
            pyxel.rectb(30, 172, W - 60, 16, 12)
            ctxt(W / 2, 175, self.msg, 10)

    def draw_map_w1(self, t):
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


    def draw_map_w2(self, t):
        """ワールド2：氷の衛星フロスト"""
        pyxel.elli(-50, 34, 356, 240, 5)
        pyxel.ellib(-50, 34, 356, 240, 6)
        pyxel.ellib(-49, 35, 354, 238, 12)
        pyxel.elli(48, 96, 96, 50, 6)                     # 氷原
        pyxel.elli(58, 104, 72, 32, 12)
        for k in range(5):
            x0 = 64 + k * 12
            pyxel.line(x0, 106 + k % 2 * 6, x0 + 9, 112 + k % 3 * 3, 1)
        pyxel.tri(116, 186, 150, 140, 184, 186, 4)        # 火山
        pyxel.tri(150, 140, 184, 186, 158, 186, 2)
        pyxel.elli(141, 137, 18, 6, 8 if (t // 10) % 2 else 9)
        for k in range(3):
            pyxel.line(150 + k * 4 - 4, 142, 146 + k * 8 - 8, 170 + k * 4, 9)
        for mx, my in ((182, 70), (226, 84), (238, 120), (196, 124)):   # 要塞の山
            pyxel.tri(mx - 14, my + 10, mx, my - 12, mx + 14, my + 10, 1)
            pyxel.tri(mx - 5, my - 4, mx, my - 12, mx + 5, my - 4, 7)
        for cx, cy, r in self.map_craters:
            if any(math.hypot(cx - n["x"], cy - n["y"]) < r + 12 for n in WORLD_NODES.values() if n["w"] == 2):
                continue
            if 116 < cx < 184 and cy > 130:
                continue
            pyxel.circ(cx, cy, r, 1)
            pyxel.circ(cx + 1, cy + 1, r - 1, 5)
        for i in range(24):                               # 舞う雪
            x = (i * 37 + t // 3) % W
            y = 40 + (i * 53 + t // 2) % 150
            pyxel.pset(x, y, 7 if i % 3 else 6)

    def draw_intro(self):
        pyxel.cls(0)
        self.draw_stars(self.state_t)
        if self.sdef.get("mission"):
            ctxt(W / 2, 64, L(*self.sdef["mission"]), 8)
        else:
            ctxt(W / 2, 64, f"MISSION {self.node_id}", 12)
        ctxt(W / 2, 82, L(*self.sdef["name"]), 7)
        draw_hero(self.A, W / 2 - 20, 108, 14, 1, 2)
        txt(W / 2 - 4, 112, f"x {self.lives}", 7)
        if (self.state_t // 15) % 2 == 0:
            ctxt(W / 2, 150, "READY", 10)

    # ---------- 背景（パララックス） ----------
    def draw_layer(self, img, factor, ox, oy, vf=0.0, boy=0, tile_y=False):
        """背景レイヤーを横にくり返して描く。vf: 縦スクロール率（登るほど沈む）"""
        w, h = img.width, img.height
        off = int(self.cam_x * factor) % w
        y = HUD_H + VIEW_H - h + oy + boy + int((self.cam_ymax - self.cam_y) * vf)
        if tile_y:
            ys = list(range(HUD_H + (y - HUD_H) % h - h, H, h))
        else:
            ys = [y] if (y < H and y + h > HUD_H) else []
        for yy in ys:
            x = -off - w + ox
            while x < W:
                if x + w > 0:
                    pyxel.blt(x, yy, img, 0, 0, w, h, KEY)
                x += w
        return off, y, w

    def layer(self, name, ox, oy):
        hf, vf, boy, tile_y = LAYER_CFG[self.theme][name]
        return self.draw_layer(self.Ly[name], hf, ox, oy, vf, boy, tile_y)

    def draw_lights(self, lights, off, y0, w, ox, mode):
        for i, (lx, ly, c) in enumerate(lights):
            if mode == "blink":
                if ((self.gt // 20) + i) % 3 == 0:
                    continue
                col = c
            else:
                col = c if (self.gt // 4 + i) % 2 else self.flick_alt
            for k in (-1, 0, 1):
                sx = lx - off + k * w + ox
                if 0 <= sx < W:
                    pyxel.pset(sx, y0 + ly, col)
                    if mode == "blink" and ((self.gt // 20) + i) % 3 == 1:
                        pyxel.pset(sx - 1, y0 + ly, 2)
                        pyxel.pset(sx + 1, y0 + ly, 2)

    def draw_background(self, ox, oy):
        Ly, Lt = self.Ly, self.Lt
        pyxel.blt(ox, HUD_H + oy, Ly["sky"], 0, 0, Ly["sky"].width, Ly["sky"].height)
        for x, y, ph in (self.twinkles if self.theme not in ("ship", "magma") else ()):
            k = (self.gt + ph) % 120
            if k < 4:
                pyxel.pset(x + ox, HUD_H + y + oy, 7)
                if k < 2:
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        pyxel.pset(x + dx + ox, HUD_H + y + dy + oy, 6)
        if self.meteor and self.theme not in ("ship", "magma"):
            mx, my, _ = self.meteor
            pyxel.line(mx + ox, HUD_H + my + oy, mx + 8 + ox, HUD_H + my - 4 + oy, 6)
            pyxel.pset(mx + ox, HUD_H + my + oy, 7)
        off, y0, w = self.layer("far", ox, oy)
        self.draw_lights(Lt["far"], off, y0, w, ox, "flicker")
        if self.ship_wait == 0 and self.theme not in ("ship", "magma"):
            sx, sy = int(self.ship_x) + ox, HUD_H + 72 + oy
            pyxel.rect(sx, sy, 10, 2, 1)
            pyxel.tri(sx + 10, sy, sx + 14, sy + 1, sx + 10, sy + 2, 1)
            pyxel.pset(sx - 1, sy + 1, 12 if self.gt % 4 < 2 else 6)
            pyxel.pset(sx + 4, sy - 1, 8 if (self.gt // 10) % 2 else 1)
        off, y0, w = self.layer("mid", ox, oy)
        self.draw_lights(Lt["mid"], off, y0, w, ox, "blink")
        self.layer("near", ox, oy)

    # ---------- ステージ ----------
    def draw_world(self, ox, oy):
        st, A = self.stage, self.A
        cx = int(self.cam_x)
        cyi = int(self.cam_y)
        pyxel.camera(cx - ox, cyi - HUD_H - oy)
        for q in self.bgparts:                     # 背景の煙
            age = 90 - q[4]
            r = 1 + age / 22
            col = 13 if q[4] > 60 else 5 if q[4] > 30 else 1
            pyxel.circ(q[0], q[1], r, col)
        u = max(0, cx - 8)
        w = min(W + 16, st.img.width - u)
        v = max(0, cyi - 8)
        hh = min(VIEW_H + 16, st.img.height - v)
        pyxel.blt(u, v, st.img, u, v, w, hh, KEY)
        for tx, ty in st.anim_tiles:
            if cx - 8 <= tx * TS <= cx + W:
                fr = (self.gt // 3 + tx) % 3
                pyxel.blt(tx * TS, ty * TS, A.tiles, 32 + fr * 8, 16, TS, TS, KEY)
        for tx, ty, c in st.conv_tiles:
            if cx - 8 <= tx * TS <= cx + W:
                fr = (self.gt // 5) % 3
                pyxel.blt(tx * TS, ty * TS, A.tiles, 64 + fr * 8, 8, TS if c == ">" else -TS, TS, KEY)
        for cr in self.crushers:
            if cx - cr.w - 8 <= cr.x <= cx + W + 8:
                cr.draw(self)
        for tx, ty in st.acid_tiles:
            if cx - 8 <= tx * TS <= cx + W:
                fr = (self.gt // 8 + tx) % 3
                pyxel.blt(tx * TS, ty * TS, A.tiles, 56 + fr * 8, 16, TS, TS, KEY)
        for tx, ty in st.lava_tiles:
            if cx - 8 <= tx * TS <= cx + W:
                fr = (self.gt // 10 + tx) % 3
                pyxel.blt(tx * TS, ty * TS, A.tiles, 64 + fr * 8, 32, TS, TS, KEY)
        for pl in self.plats:
            if cx - pl.w <= pl.x <= cx + W and cyi - 16 <= pl.y <= cyi + VIEW_H + 8:
                if hasattr(pl, "step"):
                    pl.draw(self)
                else:
                    self.draw_platform(pl)
        for lz in self.lasers:
            if cyi - lz.h - 8 <= lz.y <= cyi + VIEW_H + 8:
                lz.draw(self)
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
            if s.kind == "rock":
                pyxel.circ(s.x + 3, s.y + 3, 4, 0)
                pyxel.circ(s.x + 3, s.y + 3, 3, 4)
                pyxel.pset(s.x + 2, s.y + 2, 9)
                pyxel.pset(s.x + 4, s.y + 4, 2)
                continue
            if s.kind == "shell":
                pyxel.circ(s.x + 3, s.y + 3, 3, 0)
                pyxel.circ(s.x + 3, s.y + 3, 2, 5)
                pyxel.pset(s.x + 2, s.y + 2, 13)
                pyxel.pset(s.x + 4, s.y + 4, 8 if (s.t // 3) % 2 else 10)
                continue
            if s.kind == "blob":
                pyxel.circ(s.x + 3, s.y + 3, 3, 3)
                pyxel.circ(s.x + 3, s.y + 2, 2, 11)
                pyxel.pset(s.x + 2, s.y + 1, 7)
                continue
            c = 10 if (s.t // 3) % 2 else 7
            pyxel.circ(s.x + 3, s.y + 3, 3, 8)
            pyxel.circ(s.x + 3, s.y + 3, 1, c)
        for b in self.bolts:
            t, x = b["t"], int(b["x"])
            if t < 0:
                continue
            if t < b["warn"]:                             # 予告：床の印と細い線
                if (t // 4) % 2:
                    pyxel.elli(x - 7, b["bottom"] - 3, 14, 4, 10)
                    for yy in range(int(b["top"]), int(b["bottom"]), 6):
                        pyxel.pset(x, yy, 2)
                else:
                    pyxel.elli(x - 5, b["bottom"] - 2, 10, 3, 8)
            else:
                top, bot = int(b["top"]), int(b["bottom"])
                pyxel.rect(x - 5, top, 11, bot - top, 1)
                px = x
                for yy in range(top, bot, 6):              # ぎざぎざの稲妻
                    nx = x + random.randint(-3, 3)
                    pyxel.line(px, yy, nx, yy + 6, 12)
                    pyxel.line(px + 1, yy, nx + 1, yy + 6, 7)
                    px = nx
                pyxel.elli(x - 8, bot - 4, 16, 6, 7)
        for d in getattr(self, "debris", []):           # 落ちてくる瓦礫
            x = int(d["x"])
            k = d["t"] - d["warn"]
            if k < 0:
                if (d["t"] // 4) % 2:
                    pyxel.elli(x - 6, d["fy"] - 2, 12, 3, 2)
            else:
                y = int(d["y"])
                pyxel.rect(x - 5, y - 6, 10, 9, 0)
                pyxel.rect(x - 4, y - 5, 8, 7, 5)
                pyxel.pset(x - 2, y - 4, 13)
                pyxel.pset(x + 2, y - 1, 1)
        for gz in self.geysers:
            t, x, sy = gz["t"], gz["x"], gz["y"]
            if t < 0:
                continue
            co, ci, ch = (8, 9, 10) if gz.get("lava") else (3, 11, 7)
            if t < 45:
                if (t // 4) % 2:
                    pyxel.elli(x - 6, sy - 2, 12, 4, ci)
            else:
                hh = 50 * min(1.0, (t - 45) / 6)
                top = sy - hh
                pyxel.rect(x - 5, top, 10, hh, co)
                pyxel.rect(x - 3, top, 6, hh, ci)
                pyxel.line(x, top, x, sy, ch)
                pyxel.circ(x, top, 5, ci)
                pyxel.circ(x - 2, top - 1, 2, ch)
        for wv in self.waves:                             # 地面を走る衝撃波（炎の柱）
            x, y = int(wv["x"]), int(wv["y"])
            grow = min(1.0, wv["t"] / WAVE_RISE)
            for dx, hh in ((-3, 8), (0, 12), (3, 8)):
                hh = int((hh + (self.gt // 2 + dx) % 3) * grow) + 1
                pyxel.tri(x + dx - 2, y, x + dx + 2, y, x + dx, y - hh, 8)
                pyxel.tri(x + dx - 1, y, x + dx + 1, y, x + dx, y - hh + 3, 10)
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
        self.layer("front", ox, oy)
        marsh = self.theme == "marsh"               # 湿地では光る胞子
        for m in self.motes:
            x = (m[0] - self.cam_x * 0.2) % W
            col = (11 if m[2] > 0.25 else 3) if marsh else (13 if m[2] > 0.25 else 5)
            if self.theme == "tower":                    # 高空の風に舞うちり
                col = 6 if m[2] > 0.25 else 5
            elif self.theme == "ship":                   # 船内に舞う火の粉
                col = 8 if m[2] > 0.25 else 2
            elif self.theme in ("ice", "fort"):          # 雪
                col = 7 if m[2] > 0.25 else 6
            elif self.theme == "magma":                  # 火の粉
                col = 10 if m[2] > 0.25 else 9
            pyxel.pset(x + ox, HUD_H + m[1] + oy, col)

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

    def draw_escape(self):
        if self.escape_t is None:
            return
        if (self.gt // 15) % 2:                          # 赤い警報の枠
            pyxel.rect(0, HUD_H, W, 2, 8)
            pyxel.rect(0, H - 2, W, 2, 8)
            pyxel.rect(0, HUD_H, 2, VIEW_H, 8)
            pyxel.rect(W - 2, HUD_H, 2, VIEW_H, 8)
        secs = max(0, math.ceil(self.escape_t / 60))
        label = L(f"脱出まで {secs:2d}秒", f"ESCAPE  0:{secs:02d}")
        w = text_w(label) + 12
        x = (W - w) // 2
        y = HUD_H + 22
        pyxel.rect(x, y, w, 14, 0)
        pyxel.rectb(x, y, w, 14, 8 if secs > 5 or (self.gt // 6) % 2 else 10)
        txt(x + 6, y + 2, label, 10 if secs > 5 else 8)

    def draw_warning(self):
        k = self.warn_t
        if k <= 0:
            return
        top, h = HUD_H + 70, 34
        pyxel.rect(0, top, W, h, 0)
        sh = self.gt % 8
        for i in range(-1, W // 8 + 2):
            x = i * 8 - sh
            pyxel.tri(x, top, x + 4, top, x, top + 4, 8)
            pyxel.tri(x, top + h - 1, x + 4, top + h - 1, x + 4, top + h - 5, 8)
        if (k // 8) % 2 == 0:
            ctxt(W / 2, top + 9, "!! WARNING !!", 8)
        b = self.boss_obj
        ctxt(W / 2, top + 20, L(*b.warn_msg) if b else "", 7)

    def draw_boss_bar(self):
        b = self.boss_obj
        if b is None or not self.boss_seen or self.boss_bar <= 0.001:
            return
        x, y, w = 64, H - 10, 128
        txt(x - 30, y - 2, b.label, 8)
        pyxel.rect(x - 1, y - 1, w + 2, 6, 0)
        pyxel.rectb(x - 2, y - 2, w + 4, 8, 5)
        cur = max(0, b.hp) / b.max_hp if b.alive and b.state not in ("enter", "dying") else self.boss_bar
        col = 11 if b.phase == 1 else 10 if b.phase == 2 else 8
        pyxel.rect(x, y, int(w * self.boss_bar), 4, 2)
        pyxel.rect(x, y, int(w * min(cur, self.boss_bar)), 4, col)
        pyxel.line(x, y, x + int(w * min(cur, self.boss_bar)) - 1, y, 7)
        for f in b.phase_marks:
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
        self.draw_escape()
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

    def draw_ending(self):
        t = self.state_t
        pyxel.cls(0)
        for x, y, ph in self.map_stars:
            sx = (x - t // 6) % W
            pyxel.pset(sx, y, 7 if (t + ph) % 97 < 3 else (13 if ph % 3 else 5))
        wn = self.sdef.get("world", 1)
        pc = (1, 12, 5) if wn == 1 else (5, 7, 6)          # 惑星ゼータ / 衛星フロスト
        pyxel.circ(W // 2, 430, 260, pc[0])
        pyxel.circb(W // 2, 430, 260, pc[1])
        pyxel.circb(W // 2, 430, 259, pc[2])
        ex, ey = 190, 74                                  # 敵母艦の爆発
        if t < 180:
            rnd = random.Random(t // 4)
            for _ in range(3):
                bx, by = ex + rnd.randint(-22, 22), ey + rnd.randint(-8, 8)
                r = rnd.randint(3, 9)
                pyxel.circ(bx, by, r, rnd.choice((8, 9, 10)))
                pyxel.circ(bx, by, max(1, r - 3), 7)
            if t < 60:
                pyxel.elli(ex - 26, ey - 6, 52, 12, 1)
        elif t < 210:
            pyxel.circ(ex, ey, (t - 180) * 2, 7)
        else:
            for i in range(10):                          # 残骸のかけら
                a = i * 0.63
                d = (t - 210) * 0.3 + i * 3
                pyxel.pset(ex + math.cos(a) * d, ey + math.sin(a) * d * 0.6, 5 if i % 2 else 13)
        k = min(1.0, t / 300)                             # 帰っていく降下艇
        sx, sy = int(150 - k * 120), int(150 - k * 110)
        pyxel.tri(sx, sy, sx + 10, sy - 3, sx + 10, sy + 3, 13)
        pyxel.pset(sx + 11, sy, 12 if t % 4 < 2 else 6)
        story = (L("敵母艦を撃破し、惑星ゼータを解放した。", "THE MOTHERSHIP IS DOWN. ZETA IS FREE.")
                 if wn == 1 else
                 L("氷の要塞は陥落し、衛星フロストに光が戻った。", "THE ICE FORTRESS HAS FALLEN."))
        lines = [(60, 30, f"WORLD {wn} CLEAR!", 10),
                 (120, 52, story, 7),
                 (180, 70, f"SCORE {self.score:06d}", 12),
                 (240, 176, f"TO BE CONTINUED ... WORLD {wn + 1}", 13)]
        for t0, y, s, col in lines:
            if t >= t0:
                ctxt(W / 2, y, s, col)
        if t > 360 and (t // 30) % 2 == 0:
            ctxt(W / 2, 196, L("Z / A でマップへ", "PRESS Z / A"), 7)

    def draw_gameover(self):
        pyxel.cls(0)
        ctxt(W / 2, 90, "GAME OVER", 8)
        ctxt(W / 2, 110, L("マップに戻ります", "RETURNING TO MAP"), 13)


if __name__ == "__main__":
    App()
