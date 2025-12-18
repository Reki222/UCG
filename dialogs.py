import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import filedialog
import os
import json
from PIL import ImageTk
import constants as const


# カード枚数を一括入力するためのモーダルウィンドウ
class QuantityInputWindow(tk.Toplevel):
    def __init__(self, master, filepaths):
        super().__init__(master)
        self.title("カード枚数指定 (合計9枚まで)")
        self.transient(master) # メインウィンドウに紐づけ
        self.grab_set()        # モーダル化（最前面に固定され、親ウィンドウ操作をブロック）
        self.master = master
        
        self.filepaths = filepaths
        self.spinbox_vars = {}
        self.result = None # Stores the final dictionary of {filepath: quantity}

        # ウィンドウを画面中央に配置
        self.update_idletasks()
        width = 600
        height = min(len(self.filepaths) * 40 + 150, 450)
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
        
        self.create_widgets()
        
        # ダイナミックアップデートの開始と結果を待つ
        self.after(100, self.update_total_count)
        self.master.wait_window(self)

    def create_widgets(self):
        main_frame = tk.Frame(self, padx=10, pady=10)
        main_frame.pack(fill="both", expand=True)

        tk.Label(main_frame, text="✅ 印刷するカードの枚数を指定してください (合計9枚まで)", 
                 font=("", 12, "bold")).pack(anchor="w", pady=(0, 10))

        # スクロールエリア
        canvas = tk.Canvas(main_frame, borderwidth=0)
        vscrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas)

        canvas.configure(yscrollcommand=vscrollbar.set)
        
        vscrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        
        canvas.bind('<Configure>', lambda e: canvas.itemconfigure(canvas_window, width=e.width))
        canvas_window = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

        scroll_frame.bind("<Configure>", 
                          lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        # 入力行の生成
        for path in self.filepaths:
            card_name = os.path.basename(path).replace('.json', '')
            
            row_frame = tk.Frame(scroll_frame, pady=3)
            row_frame.pack(fill="x")
            
            # 「枚」ラベルとスピンボックスを右側に配置
            tk.Label(row_frame, text="枚").pack(side="right", padx=5)
            
            var = tk.IntVar(value=1)
            self.spinbox_vars[path] = var
            spinbox = tk.Spinbox(row_frame, from_=0, to=9, width=3, textvariable=var)
            spinbox.pack(side="right", padx=5)
            
            # カード名を左側に配置
            tk.Label(row_frame, text=f"■ {card_name}", anchor="w").pack(side="left", padx=5, fill="x", expand=True)
        
        # 合計枚数表示ラベル
        self.total_label_var = tk.StringVar(value="合計: 0枚 / 9枚")
        tk.Label(main_frame, textvariable=self.total_label_var, font=("", 10)).pack(anchor="e", pady=(10, 5))


        # コントロールボタン
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill="x", pady=10)
        
        tk.Button(button_frame, text="キャンセル", command=self.cancel).pack(side="right")
        self.apply_button = tk.Button(button_frame, text="プリント実行", command=self.apply)
        self.apply_button.pack(side="right", padx=10)
        
    def update_total_count(self):
        total = 0
        current_quantities = {}
        
        # 1. 合計枚数の計算
        for path, var in self.spinbox_vars.items():
            try:
                q = var.get()
                if q < 0: q = 0; var.set(0) # 0未満は0に強制
                current_quantities[path] = q
                total += q
            except tk.TclError:
                # 数値入力エラーを無視
                pass 
                
        # 2. ステータスラベルとボタンの更新
        if total > 9 or total == 0:
            self.apply_button.config(state=tk.DISABLED)
            error_msg = ""
            if total > 9:
                 error_msg = " (エラー: 9枚を超えています)"
            elif total == 0:
                 error_msg = " (エラー: 1枚以上指定してください)"
            self.total_label_var.set(f"合計: {total}枚 / 9枚{error_msg}")
        else:
            self.apply_button.config(state=tk.NORMAL)
            self.total_label_var.set(f"合計: {total}枚 / 9枚")

        # 500ms後に再実行
        self._trace_id = self.after(500, self.update_total_count) 
        
    def cancel(self):
        # トレースを停止
        if hasattr(self, '_trace_id'):
            self.after_cancel(self._trace_id)
        self.result = None
        self.destroy()

    def apply(self):
        # トレースを停止
        if hasattr(self, '_trace_id'):
            self.after_cancel(self._trace_id)

        total = 0
        final_quantities = {}
        for path, var in self.spinbox_vars.items():
            try:
                q = var.get()
                if q > 0:
                    final_quantities[path] = q
                    total += q
            except:
                pass

        if total > 9 or total == 0:
            messagebox.showwarning("エラー", "合計枚数は1枚から9枚までで指定してください。")
            self.after(500, self.update_total_count) # トレースを再開
            return

        # メイン関数に結果を返す
        self.result = final_quantities
        self.destroy()

# フォント選択設定ウィンドウ
class FontSelectorWindow(tk.Toplevel):
    def __init__(self, master, current_path, save_callback):
        super().__init__(master)
        self.title("デザイン設定 - フォント指定")
        self.transient(master)
        self.grab_set()
        self.master = master
        self.save_callback = save_callback
        self.default_font_dir_name = "fonts" # フォルダ名
        
        self.font_path_var = tk.StringVar(value=current_path)
        
        # ウィンドウを画面中央に配置
        self.update_idletasks()
        width = 500
        height = 150
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
        
        self.create_widgets()
        
        self.master.wait_window(self)

    def create_widgets(self):
        main_frame = tk.Frame(self, padx=10, pady=10)
        main_frame.pack(fill="both", expand=True)

        tk.Label(main_frame, text="✅ カード描画用フォントファイル (.ttf / .ttc) を指定", 
                 font=("", 10, "bold")).pack(anchor="w", pady=(0, 5))

        # フォントパス入力行
        path_frame = tk.Frame(main_frame)
        path_frame.pack(fill="x", pady=5)
        
        ttk.Entry(path_frame, textvariable=self.font_path_var, width=50).pack(side="left", fill="x", expand=True, padx=(0, 5))
        tk.Button(path_frame, text="参照...", command=self.browse_font).pack(side="left")

        # コントロールボタン
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill="x", pady=10)
        
        tk.Button(button_frame, text="キャンセル", command=self.destroy).pack(side="right")
        tk.Button(button_frame, text="適用 & 保存", command=self.apply_and_save).pack(side="right", padx=10)
        
        tk.Label(button_frame, text=f"ヒント: {self.default_font_dir_name} フォルダに置くと便利です。", fg="gray").pack(side="left")

    def browse_font(self):
        # ユーザーが指定したfontsフォルダを初期ディレクトリとする
        initial_dir = const.DEFAULT_FONT_DIR
        
        filepath = filedialog.askopenfilename(
            initialdir=initial_dir if os.path.exists(initial_dir) else const.APP_DIR,
            title="フォントファイルを選択",
            filetypes=(("TrueTypeフォント", "*.ttf *.ttc"), ("すべてのファイル", "*.*"))
        )
        if filepath:
            self.font_path_var.set(filepath)

    def apply_and_save(self):
        new_path = self.font_path_var.get().strip()
        if new_path and not os.path.exists(new_path):
            messagebox.showwarning("警告", "指定されたフォントファイルが見つかりません。\n設定を保存しますが、フォントの描画に失敗する可能性があります。")
            
        self.save_callback(new_path)
        NonModalInfo(self.master, "設定完了", "フォント設定を保存しました。プレビューを更新します。")
        self.destroy()

# テキスト位置調整設定ウィンドウ (新規追加)
class DesignConfigWindow(tk.Toplevel):
    def __init__(self, master, initial_config, preview_callback, save_callback):
        super().__init__(master)
        self.title("デザイン・レイアウト設定")
        self.transient(master)
        self.grab_set()
        self.master = master
        self.initial_config = initial_config # キャンセル用に初期設定を保持
        self.preview_callback = preview_callback
        self.save_callback = save_callback
        
        # 変数をネストした辞書構造で管理
        current_config = json.loads(json.dumps(initial_config)) # ディープコピーして編集に使う
        self.config_vars = {
            "offsets": {k: tk.IntVar(value=v) for k, v in current_config.get("offsets", {}).items()},
            "font_sizes": {k: tk.IntVar(value=v) for k, v in current_config.get("font_sizes", {}).items()},
            "layout_options": {k: tk.IntVar(value=v) for k, v in current_config.get("layout_options", {}).items()}
        }
        
        self.update_idletasks()
        width = 450
        height = 400
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
        
        self.create_widgets()
        self.master.wait_window(self)

    def create_widgets(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=15, pady=10)

        # --- タブの作成 ---
        tab_offsets = self.create_tab_frame(notebook, "位置調整 (Yオフセット)")
        tab_fonts = self.create_tab_frame(notebook, "フォントサイズ")
        tab_layout = self.create_tab_frame(notebook, "その他レイアウト")

        notebook.add(tab_offsets, text="位置調整")
        notebook.add(tab_fonts, text="フォントサイズ")
        notebook.add(tab_layout, text="その他")

        # --- 各タブにウィジェットを配置 ---
        self.create_offset_widgets(tab_offsets)
        self.create_font_size_widgets(tab_fonts)
        self.create_layout_option_widgets(tab_layout)

        # --- コントロールボタン ---
        button_frame = tk.Frame(self)
        button_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        tk.Button(button_frame, text="キャンセル", command=self.cancel).pack(side="right")
        tk.Button(button_frame, text="適用 & 保存", command=self.apply_and_save).pack(side="right", padx=10)
        tk.Button(button_frame, text="適用", command=self.apply_preview).pack(side="right")

    def create_tab_frame(self, parent, title):
        frame = tk.Frame(parent, padx=10, pady=10)
        tk.Label(frame, text=f"✍️ {title}", font=("", 10, "bold")).pack(anchor="w", pady=(0, 10))
        return frame
    
    def create_spinbox_row(self, parent, text, var_x, var_y, from_, to):
        """XとYのSpinboxを持つ行を作成する"""
        row = tk.Frame(parent)
        row.pack(fill="x", pady=3)
        tk.Label(row, text=text, width=20, anchor="w").pack(side="left")
        
        # Y座標
        ttk.Spinbox(row, from_=from_, to=to, width=6, textvariable=var_y).pack(side="right", padx=(0, 5))
        tk.Label(row, text="Y:").pack(side="right")
        
        # X座標
        ttk.Spinbox(row, from_=from_, to=to, width=6, textvariable=var_x).pack(side="right", padx=(0, 5))
        tk.Label(row, text="X:").pack(side="right")

    def create_offset_widgets(self, parent):
        offset_labels = {
            "name": "カード名",
            "cost_num": "コスト数字",
            "pow": "POW",
            "param": "特徴",
            "effects": "効果テキスト全体",
            "footer_type": "フッター(カードタイプ)",
            "footer_color": "フッター(属性)",
        }
        for key, text in offset_labels.items():
            # フッターはY座標を共有
            var_y_key = "footer_y" if "footer" in key else f"{key}_y"
            
            var_x = self.config_vars["offsets"].get(f"{key}_x")
            var_y = self.config_vars["offsets"].get(var_y_key)
            if var_x is not None and var_y is not None:
                self.create_spinbox_row(parent, text, var_x, var_y, -50, 50)

    def create_font_size_widgets(self, parent):
        font_size_labels = {
            "name_1line": "カード名 (1行)",
            "name_2line": "カード名 (2行)",
            "cost": "コスト数字",
            "pow_param": "POW / 特徴",
            "effects_header": "効果ヘッダー",
            "effects_body": "効果テキスト本体",
            "footer": "フッター (カードタイプ等)",
        }
        for key, text in font_size_labels.items():
            row = tk.Frame(parent)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=text, width=20, anchor="w").pack(side="left")
            if key in self.config_vars["font_sizes"]:
                ttk.Spinbox(row, from_=8, to=40, width=6, textvariable=self.config_vars["font_sizes"][key]).pack(side="right", padx=(0,5))

    def create_layout_option_widgets(self, parent):
        layout_option_labels = {
            "effects_max_width_px": "効果テキストの最大幅 (px)",
        }
        for key, text in layout_option_labels.items():
            if key in self.config_vars["layout_options"]:
                row = tk.Frame(parent)
                row.pack(fill="x", pady=3)
                tk.Label(row, text=text, width=25, anchor="w").pack(side="left")
                ttk.Spinbox(row, from_=10, to=const.CARD_W - 20, width=6, textvariable=self.config_vars["layout_options"][key]).pack(side="right", padx=(0,5))

    def _get_current_config_from_vars(self):
        """UIの現在の値から設定辞書を生成する"""
        return {
            "offsets": {k: v.get() for k, v in self.config_vars["offsets"].items()},
            "font_sizes": {k: v.get() for k, v in self.config_vars["font_sizes"].items()},
            "layout_options": {k: v.get() for k, v in self.config_vars["layout_options"].items()}
        }

    def apply_preview(self):
        """プレビューのみ更新する"""
        current_config = self._get_current_config_from_vars()
        self.preview_callback(current_config)

    def apply_and_save(self):
        """設定を保存してウィンドウを閉じる"""
        current_config = self._get_current_config_from_vars()
        self.save_callback(current_config)
        self.destroy()

    def cancel(self):
        """変更を破棄して元の設定でプレビューを更新し、ウィンドウを閉じる"""
        self.preview_callback(self.initial_config) # ウィンドウを開いた時の設定に戻す
        # 各カテゴリの変数を辞書に変換
        self.destroy()

# 画像プレビューと保存のためのダイアログ (新規追加)
class ImagePreviewAndSaveDialog(tk.Toplevel):
    def __init__(self, master, image_obj, default_save_path):
        super().__init__(master)
        self.title("画像プレビューと保存")
        self.transient(master)
        self.grab_set()
        self.master = master
        self.image_obj = image_obj
        self.default_save_path = default_save_path

        # PIL ImageをTkinterで使える形式に変換
        self.tk_image = ImageTk.PhotoImage(image_obj)

        # ウィンドウサイズを画像に合わせる
        img_w = self.tk_image.width()
        img_h = self.tk_image.height()
        self.geometry(f"{img_w + 40}x{img_h + 100}")
        self.resizable(False, False)

        # ウィジェット作成
        self.create_widgets()

        self.master.wait_window(self)

    def create_widgets(self):
        # 画像表示ラベル
        image_label = tk.Label(self, image=self.tk_image)
        image_label.pack(pady=20)

        # ボタンフレーム
        button_frame = tk.Frame(self)
        button_frame.pack(fill="x", padx=20, pady=(0, 20))

        tk.Button(button_frame, text="キャンセル", command=self.destroy).pack(side="right")
        tk.Button(button_frame, text="💾 画像を保存...", command=self.save_image).pack(side="right", padx=10)

    def save_image(self):
        """画像保存ダイアログを開き、画像を保存する"""
        try:
            save_path = filedialog.asksaveasfilename(
                initialdir=os.path.dirname(self.default_save_path),
                initialfile=os.path.basename(self.default_save_path),
                title="カード画像をPNGで保存",
                defaultextension=".png",
                filetypes=(("PNGファイル", "*.png"),)
            )
            if save_path:
                self.image_obj.save(save_path)
                NonModalInfo(self.master, "保存完了", f"カード画像を保存しました:\n{os.path.basename(save_path)}")
                self.destroy() # 保存後にウィンドウを閉じる
        except Exception as e:
            messagebox.showerror("保存エラー", f"PNGファイルの保存中にエラーが発生しました:\n{e}", parent=self)

# 他の操作を妨げない非モーダルな情報ウィンドウ
class NonModalInfo(tk.Toplevel):
    def __init__(self, master, title, message, duration=3000):
        super().__init__(master)
        self.title(title)
        self.transient(master) # 親ウィンドウに紐づける

        # ウィンドウの装飾をシンプルにする
        self.overrideredirect(True)

        # メッセージラベル
        self.label = tk.Label(self, text=message, padx=20, pady=10,
                              bg="#323232", fg="white", justify=tk.LEFT,
                              wraplength=400) # 長いメッセージは折り返す
        self.label.pack()

        # ウィンドウを親ウィンドウの中央下部に配置
        self.update_idletasks()
        master_x = master.winfo_x()
        master_y = master.winfo_y()
        master_w = master.winfo_width()
        master_h = master.winfo_height()
        
        win_w = self.winfo_width()
        win_h = self.winfo_height()
        
        x = master_x + (master_w // 2) - (win_w // 2)
        y = master_y + master_h - win_h - 60 # 下から60pxの位置
        self.geometry(f"+{x}+{y}")

        # 指定時間後、またはウィンドウがクリックされたら自動で閉じる
        self.after(duration, self.destroy)
        self.bind("<Button-1>", lambda e: self.destroy())
        self.label.bind("<Button-1>", lambda e: self.destroy())

    def update_message(self, new_message):
        """表示されているメッセージを更新する"""
        self.label.config(text=new_message)

# 特徴選択ウィンドウ (新規追加)
class ParamSelectorWindow(tk.Toplevel):
    def __init__(self, master, all_params, current_params, save_callback, add_param_callback, delete_param_callback):
        super().__init__(master)
        self.title("特徴の選択と追加")
        self.transient(master)
        self.grab_set()
        self.master = master
        self.all_params = sorted(list(all_params)) # 全特徴リスト
        self.add_param_callback = add_param_callback # 新しい特徴を追加するコールバック
        self.delete_param_callback = delete_param_callback # 特徴を削除するコールバック
        self.save_callback = save_callback
        self.result = None

        # --- 変数 ---
        self.param_vars = {p: tk.BooleanVar(value=(p in current_params)) for p in self.all_params}
        self.new_param_var = tk.StringVar()

        # --- ウィンドウサイズと位置 ---
        self.update_idletasks()
        width = 350
        height = 450
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

        self.create_widgets()
        self.master.wait_window(self)

    def create_widgets(self):
        main_frame = tk.Frame(self, padx=10, pady=10)
        main_frame.pack(fill="both", expand=True)

        # --- 新規追加セクション ---
        add_frame = tk.Frame(main_frame)
        add_frame.pack(fill="x", pady=(0, 10))
        tk.Label(add_frame, text="新規追加:").pack(side="left")
        new_entry = ttk.Entry(add_frame, textvariable=self.new_param_var)
        new_entry.pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(add_frame, text="追加", command=self.add_new_param).pack(side="left")
        new_entry.bind("<Return>", lambda e: self.add_new_param())

        # --- 既存リストセクション ---
        list_frame = tk.LabelFrame(main_frame, text="既存の特徴リスト (複数選択可)")
        list_frame.pack(fill="both", expand=True)

        canvas = tk.Canvas(list_frame, borderwidth=0)
        v_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        self.scroll_frame = tk.Frame(canvas)
        canvas.configure(yscrollcommand=v_scroll.set)

        v_scroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas_window = canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")

        def on_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfigure(canvas_window, width=event.width)

        self.scroll_frame.bind("<Configure>", on_configure)
        canvas.bind("<Configure>", on_configure)

        self.populate_checkboxes()

        # --- コントロールボタン ---
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(10, 0))

        # 削除ボタン用のスタイルを定義
        style = ttk.Style(self)
        style.configure("Danger.TButton", foreground="red")
        ttk.Button(button_frame, text="選択項目を削除", command=self.delete_selected_params, style="Danger.TButton").pack(side="left")
        ttk.Button(button_frame, text="キャンセル", command=self.destroy).pack(side="right")
        ttk.Button(button_frame, text="決定", command=self.apply).pack(side="right", padx=10)

    def populate_checkboxes(self):
        # 既存のチェックボックスをクリア
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        # 新しいリストで再生成
        for param in sorted(self.param_vars.keys()):
            cb = ttk.Checkbutton(self.scroll_frame, text=param, variable=self.param_vars[param])
            cb.pack(anchor="w", fill="x")

    def add_new_param(self):
        new_param = self.new_param_var.get().strip()
        if new_param and new_param not in self.param_vars:
            self.param_vars[new_param] = tk.BooleanVar(value=True)
            self.add_param_callback(new_param) # 親ウィンドウに新しい特徴を通知
            self.populate_checkboxes()
            self.new_param_var.set("")
        elif new_param in self.param_vars:
            # 既にあればチェックを入れる
            self.param_vars[new_param].set(True)
            self.new_param_var.set("")

    def delete_selected_params(self):
        """チェックされた項目をリストから削除する"""
        params_to_delete = [p for p, var in self.param_vars.items() if var.get()]

        if not params_to_delete:
            messagebox.showinfo("情報", "削除する特徴が選択されていません。", parent=self)
            return

        confirm = messagebox.askyesno(
            "削除の確認",
            f"以下の特徴をリストから完全に削除しますか？\n（この操作は取り消せません）\n\n- " + "\n- ".join(params_to_delete),
            parent=self
        )

        if confirm:
            self.delete_param_callback(params_to_delete)
            for p in params_to_delete:
                del self.param_vars[p]
            
            self.populate_checkboxes()

    def apply(self):
        selected_params = [p for p, var in self.param_vars.items() if var.get()]
        self.result = sorted(selected_params)
        self.save_callback(self.result)
        self.destroy()