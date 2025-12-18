import constants as const

class Effect:
    def __init__(self, num=1, type="", place="", mana=None, turn=0, text=""):
        self.num   = num
        self.type  = type
        self.place = place
        self.mana  = mana if mana is not None else {c: 0 for c in const.COLORS}
        self.turn  = turn
        self.text  = text

class Card:
    """全てのカードの基底クラス"""
    def __init__(self):
        self.name = ""
        self.effe = []

class PlayableCard(Card):
    """コストや色を持つ、プレイ可能なカードの基底クラス"""
    def __init__(self):
        super().__init__()
        self.cost = 0
        self.color = {c: 0 for c in const.COLORS}

class Boss(Card):
    """BOSSカード。名前と効果のみを持つ。pow, param, cost, colorを持たない。"""
    def __init__(self):
        super().__init__()
        # pow, param, cost, colorを持たない

class Character(PlayableCard):
    def __init__(self):
        super().__init__()
        self.pow = ""
        self.param = []

class Spellcard(PlayableCard):
    def __init__(self):
        super().__init__()
        self.pow = ""
        self.param = []
        #スペルカードはparamとpowを持つカードタイプです

class Cardtemp_IMT(PlayableCard):
    """アイテム、特技、土地など。powは持たないがparamは持つ。"""
    def __init__(self):
        super().__init__()
        self.param = []