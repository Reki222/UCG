import os

# --- アプリケーションのベースパス ---
APP_DIR = os.path.dirname(os.path.abspath(__file__))

# --- ディレクトリパス ---
CONFIG_FILE = os.path.join(APP_DIR, "config.json")
PARAMS_FILE = os.path.join(APP_DIR, "params.json")
DEFAULT_FONT_DIR = os.path.join(APP_DIR, "fonts")
DATA_DIR = os.path.join(APP_DIR, "datas")
PICTURES_DIR = os.path.join(APP_DIR, "card")

# --- カードの基本仕様 ---
CARD_W, CARD_H = 223,325
COLORS = ["赤", "青", "緑", "黄", "紫"]
MAX_EFFECTS = 4

# --- カードタイプ定数 ---
CARD_TYPE_CHARACTER = "キャラクター"
CARD_TYPE_SPELLCARD = "スペルカード"
CARD_TYPE_ITEM = "アイテム"
CARD_TYPE_MOVE = "特技"
CARD_TYPE_TERRITORY = "土地"
CARD_TYPE_BOSS = "BOSS"

CARD_TYPE_LIST = [
    CARD_TYPE_CHARACTER, CARD_TYPE_SPELLCARD, CARD_TYPE_ITEM,
    CARD_TYPE_MOVE, CARD_TYPE_TERRITORY, CARD_TYPE_BOSS
]

# --- 効果の選択肢 ---
EFFECT_TYPELIST = ("", "誘発", "起動", "常時")
EFFECT_PLACELIST = ("", "手札", "場", "墓地", "デッキ")

# --- デザインレイアウト定数 ---
LAYOUT = {
    "PADDING": 5,
    "BORDER_WIDTH": 3,
    "MID_LINE_Y": 175,
    "COST_CIRCLE_CX": 25,
    "COST_CIRCLE_CY": 25,
    "COST_CIRCLE_R": 12,
    "NAME_AREA_Y": 12,
    "NAME_MAX_WIDTH": CARD_W - 50,
    "POW_PARAM_Y_OFFSET": -22,
    "EFFECT_AREA_Y_START": 8,
    "FOOTER_Y_OFFSET": -28,
    "FOOTER_X_PADDING": 15,
    "SPELL_MANA_START_Y": 40,
    "SPELL_MANA_SIZE": 18,
    "SPELL_MANA_PADDING": 3,
}