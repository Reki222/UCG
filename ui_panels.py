import tkinter as tk
import sys
from tkinter import ttk
from PIL import ImageTk
import classtype as ctp
import constants as const
from dialogs import ParamSelectorWindow

class CardPreview(tk.Canvas):
    def __init__(self, master):
        super().__init__(master, width=const.CARD_W, height=const.CARD_H, bg="gray", highlightthickness=0)
        self.image = None # 初期状態はNone
        self.tk_img = None
        self.create_text(const.CARD_W / 2, const.CARD_H / 2, text="Card Preview", fill="white")

    def draw_card(self, image):
        self.delete("all") # 既存の描画内容（テキスト含む）を削除
        self.image = image
        self.tk_img = ImageTk.PhotoImage(self.image)
        self.create_image(0, 0, image=self.tk_img, anchor=tk.NW)


# 1つの効果入力UIを担うフレーム
class SingleEffectInput(tk.LabelFrame):
    def __init__(self, master, eff_num, update_callback, remove_callback):
        # --- デバウンス用タイマーID ---
        self._debounce_job = None
        self.DEBOUNCE_DELAY = 250 # 250ms

        super().__init__(master, text=f"効果 #{eff_num}", padx=5, pady=5)
        self.update_callback = update_callback
        self.eff_num = eff_num
        self.remove_callback = remove_callback
        
        # --- 変数定義 ---
        self.vars = {
            "eff_type": tk.StringVar(value=const.EFFECT_TYPELIST[0]), 
            "eff_place": tk.StringVar(value=const.EFFECT_PLACELIST[0]), 
            "eff_text": tk.StringVar(value=""),
        }
        self.mana_vars = {c: tk.IntVar(value=0) for c in const.COLORS} 
        
        # --- UI構築 ---
        
        # --- ヘッダーフレーム (テキスト以外をすべて横並びにする) ---
        header_frame = tk.Frame(self)
        header_frame.pack(fill="x", pady=2)
        
        # 削除ボタンを一番右に配置
        remove_btn = tk.Button(header_frame, text="×", command=self.remove_self, fg="red", width=2)
        remove_btn.pack(side="right", padx=(5, 0))
        
        # Type
        w_etype = ttk.Combobox(header_frame, values=const.EFFECT_TYPELIST, textvariable=self.vars["eff_type"], state="readonly", width=8)
        w_etype.current(0)
        w_etype.pack(side="left", padx=(0, 2))
        
        # Place
        w_eplace = ttk.Combobox(header_frame, values=const.EFFECT_PLACELIST, textvariable=self.vars["eff_place"], state="readonly", width=8)
        w_eplace.current(0)
        w_eplace.pack(side="left", padx=2)
        
        # Effect Mana Cost
        w_emana_frame = tk.LabelFrame(header_frame, text="コスト")
        w_emana_frame.pack(side="left", padx=5)
        
        for col in const.COLORS:
            subf = tk.Frame(w_emana_frame)
            subf.pack(side="left", padx=2)
            sp = tk.Spinbox(subf, from_=0, to=10, width=2, textvariable=self.mana_vars[col], command=self.on_input_changed)
            sp.bind("<KeyRelease>", self.on_input_changed) # キー入力でも更新
            sp.pack(side="left")
            tk.Label(subf, text=col, font=("", 10)).pack(side="left")

        # Effect Text
        tk.Label(self, text="効果テキスト:").pack(anchor="w")
        self.text_widget = tk.Text(self, height=2, width=30)
        self.text_widget.bind("<KeyRelease>", self.on_input_changed) # キー入力で更新
        self.text_widget.pack(fill="x") 

        # --- リアルタイム更新のためのバインド ---
        w_etype.bind("<<ComboboxSelected>>", self.on_input_changed)
        w_eplace.bind("<<ComboboxSelected>>", self.on_input_changed)

        self.on_input_changed()

    def on_input_changed(self, event=None):
        """入力があったときにデバウンス処理を呼び出す"""
        # 既存のタイマーがあればキャンセル
        if self._debounce_job:
            self.after_cancel(self._debounce_job)
        # 新しいタイマーを設定
        self._debounce_job = self.after(self.DEBOUNCE_DELAY, lambda: self.update_callback(event))

    def remove_self(self):
        """自分自身を削除するコールバックを呼ぶ"""
        self.remove_callback(self)

    def set_data(self, eff_data):
        self.vars["eff_type"].set(eff_data.get("type", const.EFFECT_TYPELIST[0]))
        self.vars["eff_place"].set(eff_data.get("place", const.EFFECT_PLACELIST[0]))
        
        self.text_widget.delete("1.0", "end")
        self.text_widget.insert("1.0", eff_data.get("text", ""))
        
        for col in const.COLORS:
            self.mana_vars[col].set(eff_data["mana"].get(col, 0))
            
    def get_data(self):
        return {
            "type": self.vars["eff_type"].get(),
            "place": self.vars["eff_place"].get(),
            "mana": {k: v.get() for k, v in self.mana_vars.items()},
            "text": self.text_widget.get("1.0", "end-1c").strip() 
        }

    def reset_data(self):
        self.vars["eff_type"].set(const.EFFECT_TYPELIST[0])
        self.vars["eff_place"].set(const.EFFECT_PLACELIST[0])
        self.text_widget.delete("1.0", "end")
        for col in const.COLORS:
            self.mana_vars[col].set(0)


class InputPanel(tk.Frame):
    def __init__(self, master, update_callback, load_callback, reset_callback, save_as_callback, overwrite_save_callback, generate_image_callback, open_param_selector_callback, generate_centered_name_image_callback):
        super().__init__(master, padx=10, pady=10)
        self.update_callback = update_callback
        # --- デバウンス用タイマーID ---
        self._debounce_job = None
        self.DEBOUNCE_DELAY = 250 # 250ms
        self.save_as_callback = save_as_callback
        self.overwrite_save_callback = overwrite_save_callback
        self.generate_image_callback = generate_image_callback
        self.open_param_selector_callback = open_param_selector_callback
        self.generate_centered_name_image_callback = generate_centered_name_image_callback

        self.load_callback = load_callback 
        self.reset_callback = reset_callback 
        self.current_card = None
        self.card_type_name = ""

        # --- 変数管理 ---
        self.vars = {
            "name": tk.StringVar(),
            "cost": tk.StringVar(), 
            "pow": tk.StringVar(),
            "param": tk.StringVar(),
        }
        # 属性/マナコストは数値 (0-10) で管理
        self.vars_color = {c: tk.IntVar(value=0) for c in const.COLORS}
        
        self.effect_input_frames = []

        # --- UI構築 ---
        self.form_frame = tk.Frame(self)
        self.form_frame.pack(fill="both", expand=True)

        self.create_widgets()
        self.type_combo.current(0)
        self.on_type_change()

    def create_widgets(self):
        f = self.form_frame
        
        # --- Type & Reset Row --- 
        type_row_frame = tk.Frame(f)
        type_row_frame.pack(fill="x", pady=5)
        
        tk.Label(type_row_frame, text="◆ カードタイプ", font=("bold", 12)).pack(side="left")
        
        self.type_combo = ttk.Combobox(type_row_frame, state="readonly", 
                                       values=const.CARD_TYPE_LIST, width=15)
        self.type_combo.pack(side="left", padx=5)
        self.type_combo.bind("<<ComboboxSelected>>", self.on_type_change)
        
        # リセットボタン
        tk.Button(type_row_frame, text="🗑️ リセット", command=self.reset_callback, fg="red").pack(side="right", padx=5)
        # 保存ボタン
        self.save_as_button = tk.Button(type_row_frame, text="💾 名前を付けて保存...", command=self.save_as_callback)
        self.save_as_button.pack(side="right", padx=5)
        self.overwrite_button = tk.Button(type_row_frame, text="💾 上書き保存", command=self.overwrite_save_callback, font=("", 9, "bold"))
        self.overwrite_button.pack(side="right", padx=5)
        # 画像生成ボタン
        self.generate_image_button = tk.Button(type_row_frame, text="🖼️ プレビューを画像化...", command=self.generate_image_callback, bg="#e0f0ff")
        self.generate_image_button.pack(side="right", padx=(15, 5))


        # --- 基本情報入力エリア ---
        self.base_info_frame = tk.Frame(f)
        self.base_info_frame.pack(fill="x")
        
        # Name
        name_frame = tk.Frame(self.base_info_frame)
        name_frame.pack(fill="x")
        tk.Label(name_frame, text="カード名 (改行で二行表示):").pack(side="left", anchor="w")
        # カード名中央揃えボタン
        tk.Button(name_frame, text="🖼️ 中央揃えで画像化", command=self.generate_centered_name_image_callback, bg="#cceeff").pack(side="right", padx=5)

        self.name_text_widget = tk.Text(self.base_info_frame, height=2)
        self.name_text_widget.bind("<KeyRelease>", self.on_input_changed)
        self.name_text_widget.bind("<ButtonRelease-1>", self.on_name_change)
        self.name_text_widget.bind("<FocusOut>", self.on_name_change)
        self.name_text_widget.pack(fill="x")

        
        # Cost
        tk.Label(self.base_info_frame, text="コスト (Cost):").pack(anchor="w")
        w_cost = tk.Entry(self.base_info_frame, textvariable=self.vars["cost"])
        w_cost.bind("<KeyRelease>", self.on_input_changed)
        w_cost.pack(fill="x")
        
        # Pow, Param, Color...
        self.w_pow_l = tk.Label(self.base_info_frame, text="パワー (POW):")
        self.w_pow = tk.Entry(self.base_info_frame, textvariable=self.vars["pow"])
        self.w_pow.bind("<KeyRelease>", self.on_input_changed)
        
        # 特徴 (Param) 入力エリア
        self.w_param_l = tk.Label(self.base_info_frame, text="特徴 (Param):")
        param_frame = tk.Frame(self.base_info_frame)
        self.w_param_entry = tk.Entry(param_frame, textvariable=self.vars["param"], state="readonly")
        self.w_param_entry.pack(side="left", fill="x", expand=True)
        self.w_param_button = tk.Button(param_frame, text="選択...", command=self.open_param_selector_callback)
        self.w_param_button.pack(side="left", padx=(5,0))
        self.w_param_frame = param_frame # pack/pack_forget用にフレームを保持

        # 属性/マナコスト入力エリア (Spinboxに変更)
        self.w_color_frame = tk.LabelFrame(self.base_info_frame, text="属性 / マナコスト (0-10)")
        
        for col in const.COLORS:
            subf = tk.Frame(self.w_color_frame)
            subf.pack(side="left", padx=5)
            
            tk.Label(subf, text=col).pack(side="top")
            
            spinbox = tk.Spinbox(subf, from_=0, to=10, width=3, textvariable=self.vars_color[col], command=self.on_input_changed)
            spinbox.bind("<KeyRelease>", self.on_input_changed) # ライブアップデート
            spinbox.pack(side="top")
            
            
        # --- 効果管理エリア ---
        self.effect_control_frame = tk.LabelFrame(f, text="◆ 効果リスト", fg="blue", padx=5, pady=5)
        self.effect_control_frame.pack(fill="both", expand=True, pady=10)
        
        # --- 効果コントロールボタン ---
        effect_button_frame = tk.Frame(self.effect_control_frame)
        effect_button_frame.pack(fill="x", pady=(0, 5))
        tk.Button(effect_button_frame, text="＋ 効果を追加", command=self.add_effect_frame).pack(side="left")

        # --- スクロール可能な効果入力エリア ---
        canvas = tk.Canvas(self.effect_control_frame, borderwidth=0)
        scrollbar = ttk.Scrollbar(self.effect_control_frame, orient="vertical", command=canvas.yview)
        self.scrollable_effects_frame = tk.Frame(canvas)

        self.scrollable_effects_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas_window = canvas.create_window((0, 0), window=self.scrollable_effects_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Canvasのサイズ変更時に中のFrameの幅も追従させる
        def on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind("<Configure>", on_canvas_configure)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # マウスホイールイベントをバインド
        def _on_mousewheel(event):
            # Windows/macOSでのスクロール量の違いを吸収
            scroll_val = -1 * (event.delta // 120) if sys.platform == 'win32' else -1 * event.delta
            canvas.yview_scroll(scroll_val, "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # 初期状態で効果を1つ追加 (プレビュー更新はしない)
        self.add_effect_frame(update_preview=False)

    def add_effect_frame(self, eff_data=None, update_preview=True):
        """新しい効果入力フレームを追加する"""
        eff_num = len(self.effect_input_frames) + 1
        eff_frame = SingleEffectInput(self.scrollable_effects_frame, eff_num, self.on_input_changed, self.remove_effect_frame)
        if eff_data:
            eff_frame.set_data(eff_data)
        eff_frame.pack(fill="x", expand=True, padx=2, pady=2)
        self.effect_input_frames.append(eff_frame)
        if update_preview:
            self.on_input_changed()

    def remove_effect_frame(self, frame_to_remove):
        """指定された効果入力フレームを削除する"""
        if len(self.effect_input_frames) > 1: # 最後の1つは消せない
            frame_to_remove.destroy()
            self.effect_input_frames.remove(frame_to_remove)
            # 残りのフレームの番号を振り直す
            for i, frame in enumerate(self.effect_input_frames):
                frame.config(text=f"効果 #{i + 1}")
            self.on_input_changed()
            
    # UI入力内容を初期状態に戻す
    def reset_ui(self):
        # 1. カードタイプを初期値（Character）に設定し、on_type_changeをトリガー
        self.type_combo.set(const.CARD_TYPE_CHARACTER)
        
        # 2. テキスト・エントリーをリセット
        self.name_text_widget.delete("1.0", "end")
        self.vars["cost"].set("0")
        self.vars["pow"].set("")
        self.vars["param"].set("")

        # 3. 属性マナコストをリセット (0に設定)
        for col in const.COLORS:
            self.vars_color[col].set(0)

        # 4. 効果入力をリセット
        for frame in self.effect_input_frames:
            frame.destroy()
        self.effect_input_frames = []
        self.add_effect_frame(update_preview=False) # 新しく1つだけ追加

        # 5. UIとプレビューを更新 
        self.on_type_change()

    def on_name_change(self, event=None):
        name_value = self.name_text_widget.get("1.0", "end-1c").strip()
        self.vars["name"].set(name_value) 
        self.on_input_changed(event)

    def on_input_changed(self, event=None):
        """入力があったときにデバウンス処理を呼び出す"""
        # 既存のタイマーがあればキャンセル
        if self._debounce_job:
            self.after_cancel(self._debounce_job)
        # 新しいタイマーを設定
        self._debounce_job = self.after(self.DEBOUNCE_DELAY, self.on_input_change)
        
    def on_type_change(self, event=None):
        selection = self.type_combo.get()
        self.card_type_name = selection

        if selection == const.CARD_TYPE_BOSS: self.current_card = ctp.Boss()
        elif selection == const.CARD_TYPE_CHARACTER: self.current_card = ctp.Character()
        elif selection == const.CARD_TYPE_SPELLCARD: self.current_card = ctp.Spellcard()
        else: self.current_card = ctp.Cardtemp_IMT()
        
        self.refresh_ui_visibility()
        self.on_input_change()

    def refresh_ui_visibility(self):
        self.w_pow_l.pack_forget(); self.w_pow.pack_forget()
        self.w_param_l.pack_forget(); self.w_param_frame.pack_forget()
        self.w_color_frame.pack_forget()

        c = self.current_card
        
        # Color/Mana input is required for all cards except BOSS
        if hasattr(c, "color"): 
            self.w_color_frame.pack(fill="x", pady=5)
            
        if hasattr(c, "param"):
            self.w_param_l.pack(anchor="w"); self.w_param_frame.pack(fill="x")

        if hasattr(c, "pow"):
            self.w_pow_l.pack(anchor="w"); self.w_pow.pack(fill="x")

        if hasattr(c, "effe"):
            self.effect_control_frame.pack(fill="both", expand=True, pady=10)
        else:
            self.effect_control_frame.pack_forget()

    
    def on_input_change(self, event=None):
        if not self.current_card: return
        c = self.current_card
        
        # 1. 基本情報更新
        c.name = self.vars["name"].get()
        
        if hasattr(c, "cost"):
            val = self.vars["cost"].get()
            try: c.cost = int(val)
            except: c.cost = 0 
        if hasattr(c, "pow"): c.pow = self.vars["pow"].get()
        if hasattr(c, "param"):
            # vars["param"]は表示用の文字列。実際のデータはc.paramリストに直接保持される
            pass # データはParamSelectorWindowから直接更新されるため、ここでは何もしない
            
        # color属性をSpinboxの数値 (IntVar) から取得
        if hasattr(c, "color"):
            for col in const.COLORS:
                try:
                    # 数値を直接取得
                    val = self.vars_color[col].get()
                    if val < 0: val = 0 
                    c.color[col] = val
                except tk.TclError:
                    # 入力が不正な場合 (空欄など)
                    c.color[col] = 0

        # 2. 複数の効果を更新
        if hasattr(c, "effe"):
            c.effe = []

            for i, eff_frame in enumerate(self.effect_input_frames):
                eff_data = eff_frame.get_data()
                
                new_effect = ctp.Effect(num=i + 1)
                new_effect.type = eff_data["type"]
                new_effect.place = eff_data["place"]
                new_effect.text = eff_data["text"]
                new_effect.mana = eff_data["mana"]

                # 空の効果はリストに追加しない
                if new_effect.text or any(new_effect.mana.values()) or new_effect.type != const.EFFECT_TYPELIST[0] or new_effect.place != const.EFFECT_PLACELIST[0]:
                    c.effe.append(new_effect)
            
        # 3. プレビュー更新 (temp_configを削除)
        name_lines = [line.strip() for line in c.name.split('\n') if line.strip()]
        self.update_callback(c, self.card_type_name, name_lines)
        
    def update_param_from_selector(self, new_param_list):
        """特徴選択ダイアログからのコールバックで呼ばれる"""
        if self.current_card and hasattr(self.current_card, "param"):
            self.current_card.param = new_param_list
            self.vars["param"].set(" ".join(new_param_list)) # 表示用Entryを更新
            self.on_input_change() # プレビューを更新

    def set_data_to_ui(self, data, on_complete_callback=None):
        # 1. カードタイプ
        card_type = data.get("card_type", const.CARD_TYPE_CHARACTER)
        self.type_combo.set(card_type)
        self.on_type_change() 

        # 2. 基本情報
        # 型チェックを追加
        card_name = data.get("name", "")
        if isinstance(card_name, str):
            self.vars["name"].set(card_name)
            self.name_text_widget.delete("1.0", "end")
            self.name_text_widget.insert("1.0", card_name)
        
        cost = data.get("cost", 0)
        self.vars["cost"].set(str(cost) if isinstance(cost, int) else "0")
        
        pow_val = data.get("pow", "")
        self.vars["pow"].set(str(pow_val)) # 数値でも文字列に変換
        
        param_list = data.get("param", [])
        # 内部データとUI表示の両方を更新
        if self.current_card and hasattr(self.current_card, "param"):
            self.current_card.param = param_list if isinstance(param_list, list) else []
            
            if isinstance(param_list, list) and param_list:
                self.vars["param"].set(" ".join(map(str, param_list)))
            else:
                self.vars["param"].set("")
        
        # 3. 属性マナコストを数値でセット
        color_data = data.get("color", {})
        if isinstance(color_data, dict):
            for col in const.COLORS:
                value = color_data.get(col, 0)
                self.vars_color[col].set(value if isinstance(value, int) else 0)

        # 4. 効果リスト
        effects_data = data.get("effe", [])
        # 既存の効果フレームをすべて削除
        for frame in self.effect_input_frames:
            frame.destroy()
        self.effect_input_frames = []

        if isinstance(effects_data, list):
            for eff_data in effects_data:
                self.add_effect_frame(eff_data, update_preview=False)

        # プレビュー更新を即時実行し、完了後にコールバックを呼ぶ
        self.on_input_change()
        if on_complete_callback:
            # デバウンス時間より少し長く待ってからコールバックを実行
            self.after(self.DEBOUNCE_DELAY + 50, on_complete_callback)

    def get_data_as_dict(self):
        """現在のUIの状態からカードデータ辞書を生成する"""
        c = self.current_card
        color_data = getattr(c, 'color', {})
        
        return {
            "card_type": self.card_type_name,
            "name": c.name,
            "cost": getattr(c, 'cost', 0),
            "pow": getattr(c, 'pow', ""),
            "param": [p for p in getattr(c, 'param', []) if p], # 空文字列を除外
            "color": color_data,
            "effe": [
                {
                    "type": e.type,
                    "place": e.place,
                    "mana": e.mana,
                    "text": e.text
                } 
                for e in c.effe if e.text or any(e.mana.values())
            ]
        }