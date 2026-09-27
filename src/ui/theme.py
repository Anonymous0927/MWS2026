from __future__ import annotations


INK = (22, 32, 47)
GREY = (94, 110, 136)
WHITE = (255, 255, 255)
BG = (244, 247, 251)
CARD = (255, 255, 255)
LINE = (211, 221, 235)
GREEN = (14, 158, 138)
AMBER = (201, 122, 22)
RED = (206, 59, 74)
BLUE = (60, 106, 214)
BLUE_HOVER = (44, 84, 182)

CONFIRM = (0, 105, 92)
CONFIRM_HOVER = (0, 80, 70)
NEXT = (40, 78, 180)
NEXT_HOVER = (29, 59, 145)
BUTTON_SHADOW = (194, 204, 219)

GREEN_BG = (223, 242, 238)
AMBER_BG = (253, 243, 226)
RED_BG = (251, 228, 230)
BLUE_BG = (231, 239, 248)
GREY_BG = (238, 242, 248)

RESULT_PALETTE = {
    "complete": (GREEN, GREEN_BG),
    "near": (BLUE, BLUE_BG),
    "caution": (AMBER, AMBER_BG),
    "bankrupt": (RED, RED_BG),
}


SIZE_TITLE = 34
SIZE_HEAD = 24
SIZE_BODY = 18
SIZE_NOTE = 15
SIZE_TINY = 13
SIZE_SCORE = 72


STATUS = {
    "ok": (GREEN, "守れている"),
    "warn": (AMBER, "注意"),
    "ng": (RED, "守れていない"),
}

STATUS_BG = {
    "ok": GREEN_BG,
    "warn": AMBER_BG,
    "ng": RED_BG,
}

TIMELINE_STYLE = {
    "導入": (BLUE, BLUE_BG),
    "強化": (GREEN, GREEN_BG),
    "解除": (GREY, GREY_BG),
    "取消": (GREY, GREY_BG),
    "施策": (TEAL := (16, 132, 148), (222, 240, 244)),
    "維持費": (AMBER, AMBER_BG),
    "前兆": (PURPLE := (124, 82, 190), (238, 232, 250)),
    "防げた": (GREEN, GREEN_BG),
    "注意": (AMBER, AMBER_BG),
    "あぶない": (RED, RED_BG),
    "被害": (RED, RED_BG),
    "買った": (BLUE, BLUE_BG),
    "拡大": (BLUE, BLUE_BG),
    "決算": (GREY, GREY_BG),
}

MEASURE_STYLE = {
    "owned": (GREEN, GREEN_BG, INK),
    "selected": (BLUE, BLUE_BG, INK),
    "available": (LINE, CARD, INK),
    "disabled": (LINE, GREY_BG, GREY),
    "canceling": (RED, RED_BG, INK),
}


SCREEN_W = 1440
SCREEN_H = 900
FPS = 60

MARGIN = 24
HUD_H = 88
CONTENT_TOP = 118
BUTTON_H = 68
MIN_TAP = 44
RADIUS = 10


COL_GAP = 12

COL_LEFT_X = 24
COL_LEFT_W = 232

COL_CENTER_X = 268
COL_CENTER_W = 852

COL_RIGHT_X = 1132
COL_RIGHT_W = 284

TAB_H = 48
PANEL_Y = 174
PANEL_H = 628
COLUMN_H = 684

BOTTOM_Y = 812
BOTTOM_H = 64

assert COL_LEFT_X + COL_LEFT_W + COL_GAP == COL_CENTER_X, "左列と中央列のあいだが合わない"
assert COL_CENTER_X + COL_CENTER_W + COL_GAP == COL_RIGHT_X, "中央列と右列のあいだが合わない"
assert COL_RIGHT_X + COL_RIGHT_W + MARGIN == SCREEN_W, "右列が画面の幅に収まらない"
assert CONTENT_TOP + TAB_H < PANEL_Y, "タブ帯と中央パネルが重なる"
assert CONTENT_TOP + COLUMN_H == PANEL_Y + PANEL_H, "左右の列と中央パネルの下端がそろわない"
assert PANEL_Y + PANEL_H < BOTTOM_Y, "中央パネルと下部バーが重なる"
assert BOTTOM_Y + BOTTOM_H + MARGIN <= SCREEN_H, "下部バーが画面の高さを超えている"
assert BOTTOM_H >= 60, "下部バーのボタンの高さは 60 以上（要件定義書 OP-5）"

SCRIM_ALPHA = 140
