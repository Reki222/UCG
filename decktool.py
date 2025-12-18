import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
from dialogs import NonModalInfo # NonModalInfoをインポート
import json
import constants as const
from PIL import Image, ImageTk
from tkinter.font import Font
import utils
from renderer import CardRenderer
import sys, traceback

class DeckToolApp(tk.Tk):
    """ デッキ構築ツールメインアプリケーション """
    def __init__(self):
        super().__init__()
        self.title("UCG Deck Tool")
        self.geometry("800x600")
        self.state('zoomed') # 全画面表示で起動

        # --- データ管理 ---
        self.all_cards_data = [] # すべてのカードデータ (辞書リスト)
        self.deck = {} # 現在のデッキ {card_name: quantity}
        self.cards_by_path = {} # パスをキーにしたカードデータの辞書（高速化用）
        self.boss_card_path = None # BOSSカードのファイルパスを保持
        self.all_params = [] # すべての特徴リスト
        self.renderer = CardRenderer() # レンダラーのインスタンスを作成
        self.renderer_config = {} # 描画設定を保持
        self.drag_data = None # ドラッグ＆ドロップ用のデータ保持

        # --- 絞り込み用変数 ---
        self.search_var = tk.StringVar()
        self.color_vars = {c: tk.BooleanVar() for c in const.COLORS}
        self.color_mode_var = tk.StringVar(value="AND")
        self.param_var = tk.StringVar()
        self.card_type_var = tk.StringVar()
        self.cost_min_var = tk.StringVar()
        self.cost_max_var = tk.StringVar()
        self.pow_min_var = tk.StringVar()
        self.pow_max_var = tk.StringVar()

        # --- 初期化処理 ---
        self.load_all_params() # カードより先に特徴リストを読み込む
        self.renderer_config = utils.load_config() # 共通関数で描画設定を読み込む
        # --- UI ---
        self.create_widgets()
        self.load_all_cards()

    def _get_image_path_for_card(self, card_data):
        """カードデータから正しい画像パスを生成する"""
        return os.path.join(const.PICTURES_DIR, utils.get_image_filename_for_card(card_data))

    def create_widgets(self):
        # --- メインのPanedWindow ---
        main_pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True)

        # --- 左側: デッキリスト ---
        deck_frame = ttk.LabelFrame(main_pane, text="Deck List")
        main_pane.add(deck_frame, weight=1)

        # BOSSカード専用スロット
        boss_slot_frame = ttk.LabelFrame(deck_frame, text="BOSS")
        boss_slot_frame.pack(fill=tk.X, padx=5, pady=5)
        self.boss_label_var = tk.StringVar(value="(None)")
        boss_label = tk.Label(boss_slot_frame, textvariable=self.boss_label_var, anchor='w', bg="white", relief="sunken")
        boss_label.pack(fill=tk.X, ipady=2)
        # BOSSラベルの右クリックで削除
        boss_label.bind("<Button-3>", self.remove_boss_card)
        # BOSSラベルのダブルクリックで画像表示 (ファイルパスを渡すように変更)


        # デッキ操作ボタン
        deck_button_frame = tk.Frame(deck_frame)
        deck_button_frame.pack(fill=tk.X, padx=5, pady=5)
        tk.Button(deck_button_frame, text="デッキ保存", command=self.save_deck).pack(side=tk.LEFT)
        tk.Button(deck_button_frame, text="デッキ読込", command=self.load_deck).pack(side=tk.LEFT, padx=5)
        tk.Button(deck_button_frame, text="Clear Deck", command=self.clear_deck).pack(side=tk.LEFT, padx=5)

        # デッキ枚数表示
        self.deck_count_var = tk.StringVar(value="Total: 0 cards")
        tk.Label(deck_frame, textvariable=self.deck_count_var, anchor='e').pack(fill=tk.X, padx=5)

        # デッキリスト表示 (Treeview)
        self.deck_tree = ttk.Treeview(deck_frame, columns=("qty", "cost", "color", "type", "name", "path"), show="headings")
        self.deck_tree.heading("qty", text="Qty")
        self.deck_tree.heading("cost", text="コスト")
        self.deck_tree.heading("color", text="属性")
        self.deck_tree.heading("type", text="タイプ")
        self.deck_tree.heading("name", text="カード名")
        self.deck_tree.column("qty", width=40, anchor='center', stretch=tk.NO)
        self.deck_tree.column("cost", width=50, anchor='center', stretch=tk.NO)
        self.deck_tree.column("color", width=60, anchor='center')
        self.deck_tree.column("type", width=80)
        self.deck_tree.column("name", width=150)
        self.deck_tree.column("path", width=0, stretch=tk.NO) # pathカラムは非表示
        self.deck_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 右クリックメニュー
        self.deck_menu = tk.Menu(self, tearoff=0)
        self.deck_menu.add_command(label="Add 1 copy", command=self.add_to_deck_from_menu)
        self.deck_tree.bind("<Double-1>", self.show_deck_card_image)
        self.deck_tree.bind("<Button-3>", self.show_deck_menu)

        # カード検索結果リスト用の右クリックメニュー
        self.card_list_menu = tk.Menu(self, tearoff=0)
        self.card_list_menu.add_command(label="Add 1 copy", command=self.add_to_deck_from_card_list_menu)
        self.card_list_menu.add_command(label="Remove 1 copy", command=self.remove_from_deck_from_card_list_menu)

        # BOSSラベルのダブルクリックで画像表示 (ファイルパスを渡すように変更)
        boss_label.bind("<Double-1>", self.show_boss_card_image)
        self.deck_menu.add_command(label="Remove 1 copy", command=self.remove_from_deck)

        # デッキ操作ボタンの「デッキ印刷」を右端に配置
        tk.Button(deck_button_frame, text="デッキ印刷", command=self.print_deck).pack(side=tk.RIGHT)


        # --- 右側: カード検索 ---
        search_frame = ttk.LabelFrame(main_pane, text="Card Search")
        main_pane.add(search_frame, weight=2)

        # --- 上部: 検索バーとリロードボタン ---
        search_bar_frame = tk.Frame(search_frame)
        search_bar_frame.pack(fill=tk.X, padx=5, pady=5)
        tk.Label(search_bar_frame, text="Search:").pack(side=tk.LEFT)
        
        search_entry = tk.Entry(search_bar_frame, textvariable=self.search_var)
        search_entry.pack(fill=tk.X, expand=True, side=tk.LEFT, padx=5)
        search_entry.bind("<Return>", self.perform_search) # Enterキーで検索

        tk.Button(search_bar_frame, text="Reload Cards", command=self.load_all_cards).pack(side=tk.RIGHT)

        # --- 中段: 詳細検索フィルター ---
        filter_frame = ttk.LabelFrame(search_frame, text="詳細検索")
        filter_frame.pack(fill=tk.X, padx=5, pady=5)

        # 属性フィルター
        color_filter_frame = tk.Frame(filter_frame)
        color_filter_frame.pack(fill=tk.X, pady=2)
        tk.Label(color_filter_frame, text="属性:", width=8).pack(side=tk.LEFT)
        for color in const.COLORS:
            ttk.Checkbutton(color_filter_frame, text=color, variable=self.color_vars[color]).pack(side=tk.LEFT)
        
        ttk.Radiobutton(color_filter_frame, text="AND", variable=self.color_mode_var, value="AND").pack(side=tk.LEFT, padx=(10, 2))
        ttk.Radiobutton(color_filter_frame, text="OR", variable=self.color_mode_var, value="OR").pack(side=tk.LEFT)

        # 特徴フィルター
        param_filter_frame = tk.Frame(filter_frame)
        param_filter_frame.pack(fill=tk.X, pady=2)
        tk.Label(param_filter_frame, text="特徴:", width=8).pack(side=tk.LEFT)
        param_combo = ttk.Combobox(param_filter_frame, textvariable=self.param_var, values=[""] + self.all_params, state="readonly")
        param_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # カードタイプフィルター
        type_filter_frame = tk.Frame(filter_frame)
        type_filter_frame.pack(fill=tk.X, pady=2)
        tk.Label(type_filter_frame, text="タイプ:", width=8).pack(side=tk.LEFT)
        type_combo = ttk.Combobox(type_filter_frame, textvariable=self.card_type_var, values=["(すべて)"] + const.CARD_TYPE_LIST, state="readonly")
        type_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # コスト・POWフィルター
        num_filter_frame = tk.Frame(filter_frame)
        num_filter_frame.pack(fill=tk.X, pady=2)

        # Cost
        tk.Label(num_filter_frame, text="コスト:", width=8).pack(side=tk.LEFT)
        tk.Entry(num_filter_frame, textvariable=self.cost_min_var, width=5).pack(side=tk.LEFT)
        tk.Label(num_filter_frame, text="～").pack(side=tk.LEFT)
        tk.Entry(num_filter_frame, textvariable=self.cost_max_var, width=5).pack(side=tk.LEFT)

        # POW
        tk.Label(num_filter_frame, text="POW:", width=8).pack(side=tk.LEFT, padx=(10, 0))
        tk.Entry(num_filter_frame, textvariable=self.pow_min_var, width=5).pack(side=tk.LEFT)
        tk.Label(num_filter_frame, text="～").pack(side=tk.LEFT)
        tk.Entry(num_filter_frame, textvariable=self.pow_max_var, width=5).pack(side=tk.LEFT)

        # フィルター操作ボタン
        filter_button_frame = tk.Frame(filter_frame)
        filter_button_frame.pack(fill=tk.X, pady=5)
        tk.Button(filter_button_frame, text="絞り込みリセット", command=self.reset_filters).pack(side=tk.RIGHT)
        tk.Button(filter_button_frame, text="絞り込み実行", command=self.perform_search).pack(side=tk.RIGHT, padx=5)

        # --- 下段: 検索結果リスト ---
        # TreeviewからCanvasベースのカスタムリストに変更
        self.create_card_list_widgets(search_frame)

        # 属性色用のスタイルを定義
        self.color_styles = {"赤": "#FFEBEE", "青": "#E3F2FD", "緑": "#E8F5E9", "黄": "#FFFDE7", "紫": "#F3E5F5", "無": "#FAFAFA"}
        
    def load_all_params(self):
        """ params.jsonから特徴リストを読み込む """
        try:
            with open(const.PARAMS_FILE, 'r', encoding='utf-8') as f:
                self.all_params = sorted(json.load(f))
        except (FileNotFoundError, json.JSONDecodeError):
            self.all_params = []
            # UCG_Createrが未起動の場合もあるので、ここではスキャンはしない

    def create_card_list_widgets(self, parent):
        """カード検索結果を表示するためのカスタムリストウィジェットを作成"""
        list_container = tk.Frame(parent)
        list_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # インスタンス変数としてcanvasを保持
        self.card_list_canvas = tk.Canvas(list_container)
        scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=self.card_list_canvas.yview)
        self.scrollable_frame = tk.Frame(self.card_list_canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.card_list_canvas.configure(scrollregion=self.card_list_canvas.bbox("all"))
        )

        # Canvas内にFrameを配置し、そのIDを取得
        canvas_window_id = self.card_list_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.card_list_canvas.configure(yscrollcommand=scrollbar.set)

        self.card_list_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Canvasのサイズが変更されたときに、中のFrameの幅も追従させる
        def on_canvas_configure(event):
            self.card_list_canvas.itemconfig(canvas_window_id, width=event.width)
        self.card_list_canvas.bind("<Configure>", on_canvas_configure)

    def load_all_cards(self):
        """ 'datas' ディレクトリからすべてのカードJSONを読み込み、検索用キャッシュを作成する """
        self.all_cards_data = []
        self.cards_by_path = {} # 初期化
        if not os.path.exists(const.DATA_DIR):
            messagebox.showwarning("Warning", f"Card data directory not found:\n{const.DATA_DIR}")
            return

        for root, _, files in os.walk(const.DATA_DIR):
            for filename in files:
                if not filename.endswith(".json"): continue
                filepath = os.path.join(root, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    data['__filepath'] = filepath
                    data['_search_text'] = self._create_search_cache(data) # 検索用キャッシュを作成
                    self.all_cards_data.append(data)
                    self.cards_by_path[filepath] = data
                except Exception as e:
                    print(f"Error loading {filename}: {e}")

        self.all_cards_data.sort(key=lambda x: x.get('name', ''))
        self.perform_search()
        NonModalInfo(self, "読込完了", f"{len(self.all_cards_data)} 枚のカードを読み込みました。")

    def _create_search_cache(self, card_data):
        """カードデータから検索用のキャッシュ文字列を生成する"""
        searchable_text = [
            card_data.get('name', ''),
            card_data.get('card_type', '')
        ]
        params = card_data.get('param', [])
        if isinstance(params, list):
            searchable_text.extend(params)
        
        effects = card_data.get('effe', [])
        if isinstance(effects, list):
            for effect in effects:
                searchable_text.append(effect.get('text', ''))
        
        return " ".join(searchable_text).lower()

    def reload_all_cards(self):
        """ 'datas' ディレクトリからすべてのカードJSONを読み込む """
        self.all_cards_data = []
        self.cards_by_path = {} # 初期化
        if not os.path.exists(const.DATA_DIR):
            messagebox.showwarning("Warning", f"Card data directory not found:\n{const.DATA_DIR}")
            return

        # os.walkを使ってサブディレクトリも再帰的に探索する
        for root, dirs, files in os.walk(const.DATA_DIR):
            for filename in files:
                if filename.endswith(".json"):
                    filepath = os.path.join(root, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)

                        # どのファイルから来たかを識別するためにパスを保存
                        data['__filepath'] = filepath

                        # 画像パスは表示時に動的に決定するため、ここでは読み込まない
                        image_path = self._get_image_path_for_card(data)
                        data['image_path'] = None # 初期化
                        if os.path.exists(image_path):
                            data['image_path'] = image_path

                        self.all_cards_data.append(data)
                        self.cards_by_path[filepath] = data # 高速ルックアップ用の辞書を構築
                    except Exception as e:
                        print(f"Error loading {filename}: {e}")

        self.all_cards_data.sort(key=lambda x: x.get('name', ''))
        self.perform_search() # ロード後にリストを更新
        NonModalInfo(self, "読込完了", f"{len(self.all_cards_data)} 枚のカードを読み込みました。")

    def reset_filters(self):
        """ 詳細検索のフィルターをリセットする """
        self.search_var.set("")
        for var in self.color_vars.values():
            var.set(False)
        self.color_mode_var.set("AND")
        self.param_var.set("")
        self.card_type_var.set("(すべて)")
        self.cost_min_var.set("")
        self.cost_max_var.set("")
        self.pow_min_var.set("")
        self.pow_max_var.set("")
        self.perform_search()

    def perform_search(self, *args):
        """ 検索クエリに基づいてカードをフィルタリングし、結果リストを更新 """
        # 検索実行前にスクロールを一番上に戻す
        self.card_list_canvas.yview_moveto(0)

        # 既存のウィジェットをクリア
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()


        # --- フィルター条件の取得 ---
        query = self.search_var.get().lower().strip()
        selected_colors = [c for c, v in self.color_vars.items() if v.get()]
        color_mode = self.color_mode_var.get()
        selected_param = self.param_var.get()
        selected_type = self.card_type_var.get()
        
        try: cost_min = int(self.cost_min_var.get()) if self.cost_min_var.get() else None
        except ValueError: cost_min = None
        try: cost_max = int(self.cost_max_var.get()) if self.cost_max_var.get() else None
        except ValueError: cost_max = None
        try: pow_min = int(self.pow_min_var.get()) if self.pow_min_var.get() else None
        except ValueError: pow_min = None
        try: pow_max = int(self.pow_max_var.get()) if self.pow_max_var.get() else None
        except ValueError: pow_max = None

        # --- フィルタリング実行 ---
        filtered_cards = []
        for card in self.all_cards_data:
            card_type = card.get('card_type', '')

            # 0. BOSSカードの特別扱い
            if selected_type == const.CARD_TYPE_BOSS:
                # BOSSで絞り込んだ場合、BOSSのみを対象とする
                if card_type != const.CARD_TYPE_BOSS:
                    continue
            else:
                # それ以外の場合、BOSSは除外する
                if card_type == const.CARD_TYPE_BOSS:
                    continue

            # 1. フリーワード検索
            if query:
                # キャッシュされた検索テキストに対して検索を実行
                if query not in card.get('_search_text', ''):
                    continue

            # 2. 属性フィルター
            if selected_colors:
                card_colors = card.get('color', {})
                if color_mode == "AND":
                    if not all(card_colors.get(c, 0) > 0 for c in selected_colors):
                        continue
                else: # OR
                    if not any(card_colors.get(c, 0) > 0 for c in selected_colors):
                        continue
            
            # 3. 特徴フィルター
            if selected_param and selected_param not in card.get('param', []):
                continue

            # 4. カードタイプフィルター
            if selected_type and selected_type != "(すべて)" and card_type != selected_type:
                continue

            # 5. コストフィルター
            card_cost = card.get('cost', 0)
            if cost_min is not None and card_cost < cost_min:
                continue
            if cost_max is not None and card_cost > cost_max:
                continue

            # 6. POWフィルター
            card_pow_str = card.get('pow', "")
            if pow_min is not None or pow_max is not None:
                try:
                    card_pow = int(card_pow_str)
                    if pow_min is not None and card_pow < pow_min:
                        continue
                    if pow_max is not None and card_pow > pow_max:
                        continue
                except (ValueError, TypeError):
                    # POWが数値でないカードは範囲指定フィルターから除外
                    continue

            # ソート用の情報を付与して追加
            sort_info = self.get_sort_keys(card)
            filtered_cards.append((card, sort_info))

        # --- ソート実行 ---
        filtered_cards.sort(key=lambda x: x[1])

        # --- 結果をリストに表示 ---
        for i, (card, _) in enumerate(filtered_cards):
            row_frame = self.create_card_row(self.scrollable_frame, card, i)
            card['__widget_ref'] = row_frame # ウィジェットへの参照をカードデータに保存
            self._bind_scroll_recursive(row_frame) # 作成された各行にスクロールイベントをバインド

    def get_sort_keys(self, card):
        """ソート用のキーをタプルで返す"""
        # 1. カードタイプ順
        type_order_map = {
            const.CARD_TYPE_CHARACTER: 0,
            const.CARD_TYPE_SPELLCARD: 1,
            const.CARD_TYPE_ITEM: 2,
            const.CARD_TYPE_MOVE: 3,
            const.CARD_TYPE_TERRITORY: 4,
        }
        type_order = type_order_map.get(card.get('card_type', ''), 99)

        # 2. 属性順
        color_order_map = {name: i for i, name in enumerate(const.COLORS)}
        active_colors = [k for k, v in card.get('color', {}).items() if v > 0]
        color_order = color_order_map.get(active_colors[0], 99) if active_colors else 99

        # 3. コスト降順 (マイナスを付けて昇順ソート)
        cost = -card.get('cost', 0)
        
        # 4. POW降順 (マイナスを付けて昇順ソート)
        try: pow_val = -int(card.get('pow', ''))
        except (ValueError, TypeError): pow_val = 0 # POWが数値でない場合は0として扱う

        return (type_order, color_order, cost, pow_val)

    def create_card_row(self, parent, card, index):
        """検索結果の1行分のウィジェットを作成して配置する"""
        card_name = card.get('name', '')
        card_type = card.get('card_type', '')
        active_colors = [k for k, v in card.get('color', {}).items() if v > 0]
        bg_color = self.color_styles.get(active_colors[0] if active_colors else "無", "#FFFFFF")

        row_frame = tk.Frame(parent, relief="solid", bd=1, bg=bg_color)
        row_frame.pack(fill="x", pady=(0, 2))

        # pack_propagate(False) を使うことで、中のウィジェットのサイズに影響されず、
        # フレーム自体のwidth指定が有効になります。

        # --- 左側: デッキ操作エリア ---
        control_frame = tk.Frame(row_frame, width=110, bg=bg_color)
        control_frame.pack_propagate(False) # 幅を110pxに固定
        control_frame.pack(side="left", fill="y", padx=5, pady=5)
        
        qty_in_deck = self.deck.get(card.get('__filepath'), 0) if card_type != const.CARD_TYPE_BOSS else (1 if self.boss_card_path == card.get('__filepath') else 0)
        # ラベルに一意な名前を付けて、後でアクセスできるようにする
        qty_label = tk.Label(control_frame, text=f"{qty_in_deck}枚" if qty_in_deck > 0 else "", font=("", 10, "bold"), width=5, bg=bg_color)
        row_frame.qty_label = qty_label # フレームオブジェクトにラベルへの参照を保持させる
        qty_label.pack(side="left")

        minus_btn = tk.Button(control_frame, text="－", command=lambda c=card: self.adjust_deck_qty(c, -1), width=2)
        # packの順序を調整して中央に寄せる
        minus_btn.pack(side="left", padx=(5,2))
        plus_btn = tk.Button(control_frame, text="＋", command=lambda c=card: self.adjust_deck_qty(c, 1), width=2)
        plus_btn.pack(side="left")

        # --- 右側: カード情報エリア ---
        info_frame = tk.Frame(row_frame, bg=bg_color)
        info_frame.pack(side="left", fill="both", expand=True, pady=5)

        # 1行目: 名前、コスト、POW、タイプ、属性
        top_info = tk.Frame(info_frame, bg=bg_color)
        top_info.pack(fill="x")
        
        # 右寄せ用のフレーム
        right_aligned_frame = tk.Frame(top_info, bg=bg_color)
        right_aligned_frame.pack(side="right")

        # 左寄せの要素 (カード名)
        tk.Label(top_info, text=card_name, font=("", 11, "bold"), anchor="w", bg=bg_color).pack(side="left")
        
        # 右寄せの要素 (属性、タイプ、Cost, POW)
        tk.Label(right_aligned_frame, text="／".join(active_colors) or "無", anchor="e", bg=bg_color).pack(side="right", padx=5)
        tk.Label(right_aligned_frame, text=card_type, width=8, anchor="e", bg=bg_color).pack(side="right", padx=5)
        if card.get('pow'): 
            tk.Label(right_aligned_frame, text=f"POW: {card.get('pow')}", anchor="e", bg=bg_color).pack(side="right", padx=5)
        if card.get('cost') is not None:
            tk.Label(right_aligned_frame, text=f"Cost: {card.get('cost', 0)}", anchor="e", bg=bg_color).pack(side="right", padx=5)


        # 2行目: 特徴
        params = " ".join(card.get('param', []))
        if params:
            tk.Label(info_frame, text=f"特徴: {params}", font=("", 9), anchor="w", justify="left", bg=bg_color).pack(fill="x")

        # 3行目: 効果
        effects_list = card.get('effe', [])
        # 各効果テキストを改行で連結し、テキスト内の改行も維持する
        # これにより、複数行で表示されるようになる
        # さらに、句点「。」の後にも改行を追加する
        effects_text = "\n".join([e.get('text', '').replace('。', '。\n') for e in effects_list if e.get('text')])

        if effects_text:
            effect_frame = tk.Frame(info_frame, bg=bg_color)
            effect_frame.pack(fill="x")

            # 画像表示ボタン
            img_button = tk.Button(effect_frame, text="🖼️", command=lambda c=card: self.show_card_image(c))
            img_button.pack(side="right", padx=5)

            # 全角40文字相当のピクセル幅を計算して折り返し幅とする
            # フォントオブジェクトを作成して、'Ｍ'（全角文字の代表）45文字分の幅を測定
            font_obj = Font(family="TkDefaultFont", size=9) # デフォルトフォントとサイズを指定
            wrap_width = font_obj.measure('Ｍ' * 30) # 全角30文字分に調整

            # ラベルのテキストの先頭に "効果: " を追加
            tk.Label(effect_frame, text=f"効果: {effects_text}", font=font_obj, anchor="w", justify="left", wraplength=wrap_width, bg=bg_color).pack(side="left", fill="x")

        # row_frame全体にドラッグイベントを再帰的にバインド
        self.bind_drag_events(row_frame, card)

        return row_frame # バインド用にフレームを返す

    def bind_drag_events(self, widget, card_data):
        """ウィジェットにドラッグ＆ドロップイベントを再帰的にバインドする"""
        widget.bind("<ButtonPress-1>", lambda e, c=card_data: self.start_drag(e, c))
        widget.bind("<B1-Motion>", self.do_drag)
        widget.bind("<ButtonRelease-1>", self.end_drag)
        widget.bind("<Button-3>", lambda e, c=card_data: self.show_card_list_menu(e, c)) # 右クリックメニュー
        for child in widget.winfo_children():
            # ボタンなど、既にクリックイベントが設定されているウィジェットは除外
            if isinstance(child, (tk.Button, ttk.Button)):
                continue
            self.bind_drag_events(child, card_data)

    def start_drag(self, event, card_data):
        """カード検索リストからのドラッグ開始"""
        self.drag_data = {"type": "card", "data": card_data, "widget": event.widget}

    def do_drag(self, event):
        """ドラッグ中のカーソル変更"""
        if self.drag_data:
            event.widget.config(cursor="hand2")

    def end_drag(self, event):
        """ドラッグ終了時の処理"""
        if not self.drag_data:
            return
        
        # ドロップ先がデッキリスト(Treeview)かチェック
        x_root, y_root = event.x_root, event.y_root
        drop_target = self.winfo_containing(x_root, y_root)

        if drop_target == self.deck_tree and self.drag_data.get("type") == "card":
            self.adjust_deck_qty(self.drag_data["data"], 1)
        
        event.widget.config(cursor="")
        self.drag_data = None

    def _on_mousewheel(self, event):
        """マウスホイールイベントを処理してCanvasをスクロールする"""
        # Windows/macOS
        scroll_val = -1 * (event.delta // 120)
        self.card_list_canvas.yview_scroll(scroll_val, "units")

    def _bind_scroll_recursive(self, widget):
        """指定されたウィジェットとその子孫に再帰的にスクロールイベントをバインドする"""
        widget.bind("<MouseWheel>", self._on_mousewheel)
        for child in widget.winfo_children():
            self._bind_scroll_recursive(child)

    def _get_or_create_card_image(self, card_data):
        """
        カード画像のパスを取得する。存在しない場合は生成を試みる。
        成功した場合はPIL Imageオブジェクトを、失敗した場合はNoneを返す。
        """
        image_path = self._get_image_path_for_card(card_data)
        if not os.path.exists(image_path):
            if not messagebox.askyesno("確認", f"画像がありません:\n{os.path.basename(image_path)}\n\n生成しますか？"):
                return None
            try:
                name_lines = [line.strip() for line in card_data.get("name", "").split('\n') if line.strip()]
                card_img = self.renderer.draw_single_card(card_data, card_data.get("card_type", ""), name_lines, self.renderer_config)
                if not card_img: raise Exception("カード画像の生成に失敗しました。")
                if not os.path.exists(const.PICTURES_DIR): os.makedirs(const.PICTURES_DIR)
                card_img.save(image_path)
                NonModalInfo(self, "生成完了", f"画像を生成しました:\n{os.path.basename(image_path)}")
            except Exception as e:
                messagebox.showerror("生成エラー", f"画像の生成中にエラーが発生しました:\n{e}")
                return None
        
        try:
            return Image.open(image_path)
        except Exception as e:
            messagebox.showerror("画像読込エラー", f"画像ファイルの読み込みに失敗しました:\n{e}")
            return None

    def show_card_image(self, card_data):
        """指定されたパスのカード画像を新しいウィンドウで表示する"""
        pil_img = self._get_or_create_card_image(card_data)
        if not pil_img: return

        win = tk.Toplevel(self)
        win.title(card_data.get("name", "Card Image"))
        tk_img = ImageTk.PhotoImage(pil_img)
        
        label = tk.Label(win, image=tk_img)
        label.image = tk_img # ガベージコレクションを防ぐために参照を保持
        label.pack()
        win.bind("<Button-1>", lambda e: win.destroy()) # ウィンドウクリックで閉じる

    def show_deck_card_image(self, event=None):
        """デッキリストでダブルクリックされたカードの画像を表示する"""
        selection = self.deck_tree.selection()
        if not selection:
            return
        
        item_values = self.deck_tree.item(selection[0])['values']
        card_path = item_values[5] # 6番目のカラム(path)からパスを取得
        card_data = next((c for c in self.all_cards_data if c.get('__filepath') == card_path), None)
        
        if card_data:
            self.show_card_image(card_data)

    def show_boss_card_image(self, event=None):
        """BOSSスロットのカード画像を表示する"""
        if not self.boss_card_path: return
        card_data = next((c for c in self.all_cards_data if c.get('__filepath') == self.boss_card_path), None)
        if card_data: self.show_card_image(card_data)
        
    def adjust_deck_qty(self, card_data, amount):
        """デッキ内のカード枚数を増減させる"""
        if not card_data: return

        card_type = card_data.get('card_type', '')
        card_name = card_data.get('name', '')
        card_path = card_data.get('__filepath', '')

        # BOSSカードの場合の処理
        if card_type == const.CARD_TYPE_BOSS:
            if amount < 0: # 減らす操作はBOSSスロットから
                self.remove_boss_card()
                return

            if self.boss_card_path and self.boss_card_path != card_path:
                boss_name = os.path.basename(self.boss_card_path).replace('.json', '')
                if not messagebox.askyesno("BOSSの入れ替え", f"既にBOSSカード '{boss_name}' が設定されています。\n'{card_name}' に入れ替えますか？"):
                    return
            self.boss_card_path = card_path
            self.update_deck_view()
            return

        # 通常カードの場合の処理
        current_qty = self.deck.get(card_path, 0)
        new_qty = current_qty + amount

        # 4枚の上限チェック (警告なし)
        if new_qty > 4:
            # 5枚以上になろうとした場合は何もしない
            return

        if new_qty <= 0:
            if card_path in self.deck:
                del self.deck[card_path]
        else:
            self.deck[card_path] = new_qty

        # データの変更後、UIの更新を呼び出す
        self.update_deck_view(update_search_list=True, updated_card_path=card_path)

    def add_to_deck_from_menu(self):
        """ デッキリストの右クリックメニューからカードを1枚増やす """
        selected_items = self.deck_tree.selection()
        if not selected_items: return
        card_path = self.deck_tree.item(selected_items[0])['values'][5]

        card_data = self.cards_by_path.get(card_path)
        if card_data:
            self.adjust_deck_qty(card_data, 1)

    def show_card_list_menu(self, event, card_data):
        """カード検索結果リストの右クリックメニューを表示"""
        self.card_list_menu.card_data = card_data  # メニューにカードデータを一時保存
        self.card_list_menu.post(event.x_root, event.y_root)

    def add_to_deck_from_card_list_menu(self):
        """カード検索結果リストのメニューからカードを1枚増やす"""
        card_data = getattr(self.card_list_menu, 'card_data', None) # qty_labelは特定できないのでNone
        self.adjust_deck_qty(card_data, 1)

    def remove_from_deck_from_card_list_menu(self):
        """カード検索結果リストのメニューからカードを1枚減らす"""
        card_data = getattr(self.card_list_menu, 'card_data', None)
        self.adjust_deck_qty(card_data, -1)

    def remove_from_deck(self):
        """ デッキから選択したカードを1枚削除 """
        selected_items = self.deck_tree.selection()
        if not selected_items: return
        card_path = self.deck_tree.item(selected_items[0])['values'][5]

        if card_path in self.deck:
            self.deck[card_path] -= 1
            if self.deck[card_path] <= 0:
                del self.deck[card_path]
        
        self.update_deck_view(update_search_list=True, updated_card_path=card_path) # 検索結果リストの枚数表示も更新

    def remove_boss_card(self, event=None):
        """ BOSSカードをデッキから削除 """
        self.boss_card_path = None
        self.update_deck_view()

    def update_deck_view(self, update_search_list=False, updated_card_path=None):
        """ デッキリストの表示を更新 """
        # Treeviewをクリア
        for item in self.deck_tree.get_children():
            self.deck_tree.delete(item)

        # デッキの内容をソートして表示
        # この時点での合計枚数を保持
        total_cards = sum(self.deck.values())
        
        # パスからカード名を取得してソート
        deck_with_names = []
        for path, qty in self.deck.items(): # self.deckは {path: qty}
            card_data = self.cards_by_path.get(path) # 高速化したルックアップ
            if card_data:
                card_name = card_data.get('name', 'Unknown')
                cost = card_data.get('cost', '')
                card_type = card_data.get('card_type', '')
                active_colors = [k for k, v in card_data.get('color', {}).items() if v > 0]
                color_str = "／".join(active_colors) or "無"
                sort_keys = self.get_sort_keys(card_data) # ソートキーを取得
                deck_with_names.append({'name': card_name, 'qty': qty, 'path': path, 'cost': cost, 'color': color_str, 'type': card_type, 'sort_keys': sort_keys})
            else:
                # データが見つからない場合（念のため）
                deck_with_names.append({'name': 'Unknown', 'qty': qty, 'path': path, 'cost': '', 'color': '', 'type': '', 'sort_keys': (99,99,0,0)})
        
        for item in sorted(deck_with_names, key=lambda x: x['sort_keys']):
            self.deck_tree.insert("", tk.END, values=(item['qty'], item['cost'], item['color'], item['type'], item['name'], item['path']))

        self.deck_count_var.set(f"Total: {total_cards} cards")

        # BOSSスロットの表示を更新
        if self.boss_card_path:
            boss_data = self.cards_by_path.get(self.boss_card_path) # 高速化したルックアップ
            self.boss_label_var.set(boss_data.get('name', 'Unknown') if boss_data else 'Unknown')
        else:
            self.boss_label_var.set("(None)")

        # 検索結果リストの枚数表示が変更された可能性があるため、再描画
        if update_search_list and updated_card_path:
            # 全面再描画ではなく、該当カードのラベルのみを更新する
            card_data = self.cards_by_path.get(updated_card_path)
            if card_data and '__widget_ref' in card_data:
                widget = card_data['__widget_ref']
                try:
                    # ウィジェットに保持させた参照を使って直接ラベルを更新
                    if widget.winfo_exists() and hasattr(widget, 'qty_label'):
                        new_qty = self.deck.get(updated_card_path, 0)
                        widget.qty_label.config(text=f"{new_qty}枚" if new_qty > 0 else "")
                except (IndexError, AttributeError):
                    # ウィジェットの構造が予期しない、または破棄済みの場合
                    pass
        elif update_search_list: # パス指定がない場合は全検索結果を更新
            self.perform_search()

    def show_deck_menu(self, event):
        """ デッキリストの右クリックメニューを表示 """
        selected_item = self.deck_tree.identify_row(event.y)
        if selected_item:
            self.deck_tree.selection_set(selected_item)
            self.deck_menu.post(event.x_root, event.y_root)

    def clear_deck(self):
        """ デッキを空にする """
        if messagebox.askyesno("Confirm", "Are you sure you want to clear the entire deck?"):
            self.boss_card_path = None
            self.deck = {}
            # update_search_list=Trueで両方のUIを更新
            self.update_deck_view(update_search_list=True)

    def save_deck(self):
        """現在のデッキ構成を.ucgdeckファイルに保存する"""
        if not self.deck and not self.boss_card_path:
            NonModalInfo(self, "情報", "デッキが空です。保存するものがありません。")
            return

        filepath = filedialog.asksaveasfilename(
            title="デッキを保存",
            defaultextension=".ucgdeck",
            filetypes=(("UCG Deck File", "*.ucgdeck"), ("All Files", "*.*")),
            initialfile="my_deck.ucgdeck"
        )

        if not filepath:
            return

        deck_data = {
            "boss": self.boss_card_path,
            "deck": self.deck
        }

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(deck_data, f, ensure_ascii=False, indent=4)
            NonModalInfo(self, "保存完了", f"デッキを保存しました:\n{os.path.basename(filepath)}")
        except Exception as e:
            messagebox.showerror("保存エラー", f"デッキの保存中にエラーが発生しました:\n{e}")

    def load_deck(self):
        """ .ucgdeckファイルからデッキ構成を読み込む """
        if self.deck or self.boss_card_path:
            if not messagebox.askyesno("確認", "現在のデッキはクリアされます。新しいデッキを読み込みますか？"):
                return

        filepath = filedialog.askopenfilename(
            title="デッキを読み込む",
            filetypes=(("UCG Deck File", "*.ucgdeck"), ("All Files", "*.*"))
        )

        if not filepath:
            return

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                deck_data = json.load(f)
            
            self.boss_card_path = deck_data.get("boss", None)
            self.deck = deck_data.get("deck", {})
            # 読み込み後、検索結果リストの枚数表示も更新する
            self.update_deck_view(update_search_list=True)
            NonModalInfo(self, "読込完了", f"デッキを読み込みました:\n{os.path.basename(filepath)}")
        except Exception as e:
            messagebox.showerror("読込エラー", f"デッキの読み込み中にエラーが発生しました:\n{e}")

    def print_deck(self):
        """
        .ucgdeckファイルを選択し、その内容を印刷用のA4画像として出力する。
        """
        # 1. デッキファイルを選択
        filepath = filedialog.askopenfilename(
            title="印刷するデッキを読み込む",
            filetypes=(("UCG Deck File", "*.ucgdeck"), ("All Files", "*.*"))
        )
        if not filepath:
            return

        # 2. デッキデータを読み込み
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                deck_data = json.load(f)
        except Exception as e:
            messagebox.showerror("読込エラー", f"デッキファイルの読み込みに失敗しました:\n{e}")
            return

        # 3. カード画像のパスリストを作成
        card_paths_to_print = []
        # BOSSカード
        boss_path = deck_data.get("boss")
        if boss_path:
            card_paths_to_print.append(boss_path)

        # デッキカード
        deck_dict = deck_data.get("deck", {})
        for path, qty in deck_dict.items():
            card_paths_to_print.extend([path] * qty)

        if not card_paths_to_print:
            NonModalInfo(self, "情報", "デッキにカードがありません。")
            return

        # 4. カード画像の準備（存在しない場合は生成）
        image_objects = []
        progress_win = NonModalInfo(self, "処理中", "カード画像を準備しています...", 30000) # タイムアウトを長めに設定
        self.update()

        for i, card_path in enumerate(card_paths_to_print):
            progress_win.update_message(f"カード画像を準備中... ({i + 1}/{len(card_paths_to_print)})")
            self.update_idletasks()

            card_data = self.cards_by_path.get(card_path)
            if not card_data:
                print(f"警告: カードデータが見つかりません: {card_path}")
                continue
            
            # 共通化された画像取得/生成関数を呼び出す
            img = self._get_or_create_card_image(card_data)
            if img:
                image_objects.append(img)
            else:
                # 画像の取得/生成に失敗した場合は処理を中断
                progress_win.destroy()
                return

        progress_win.destroy()

        # 5. 共通関数を呼び出してレイアウト生成と保存を行う
        # 保存先は読み込んだデッキファイルと同じディレクトリとする
        deck_file_dir = os.path.dirname(filepath)
        
        base_name = os.path.splitext(os.path.basename(filepath))[0]
        utils.create_and_save_print_layouts(self, image_objects, initial_filename_base=base_name, initial_dir=deck_file_dir)

if __name__ == '__main__':
    try:
        # ディレクトリが存在しない場合は作成
        if not os.path.exists(const.DATA_DIR):
            os.makedirs(const.DATA_DIR)
            
        app = DeckToolApp()
        app.mainloop()
    except Exception as e:
        # 予期せぬエラーをファイルに記録
        error_log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "error.log")
        with open(error_log_path, "a", encoding="utf-8") as f:
            f.write(f"--- decktool.py Error ---\n")
            f.write(f"Timestamp: {__import__('datetime').datetime.now()}\n")
            traceback.print_exc(file=f)
            f.write("\n")
        # ユーザーにエラーが発生したことを通知
        messagebox.showerror("致命的なエラー", f"予期せぬエラーが発生しました。詳細は error.log を確認してください。\n\n{e}")