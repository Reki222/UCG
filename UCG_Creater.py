import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import filedialog
import os
from PIL import Image
import sys, traceback
import json

# --- 他のファイルからクラスや関数をインポート ---
import constants as const
from dialogs import (QuantityInputWindow, FontSelectorWindow, DesignConfigWindow, 
                     ImagePreviewAndSaveDialog, NonModalInfo, ParamSelectorWindow)
from ui_panels import CardPreview, InputPanel
import utils
from renderer import CardRenderer


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("UCG Maker")
        self.current_filepath = None # 読み込んだファイルのパスを記憶する
        
        self.all_params = set() # 全カードの特徴を保持するセット
        self.geometry("1000x650")
        self.state('zoomed')
        
        # --- 設定管理 (新規追加) ---
        # 描画クラスのインスタンス化 (renderer.pyから)
        self.renderer = CardRenderer()


        self.app_config = {} # <--- 修正: 変数名をself.app_configに変更

        # --- メニューバーの作成と設定 ---
        menubar = tk.Menu(self)
        super().config(menu=menubar) # self.configとの衝突を避けるため、super()経由で呼び出す
        self.app_config = utils.load_config()
        
        # ファイルメニュー
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ファイル", menu=file_menu)
        file_menu.add_command(label="💾 上書き保存 (Ctrl+S)", command=self.overwrite_save_data)
        file_menu.add_command(label="📂 読込 (Ctrl+O)", command=self.load_data)
        file_menu.add_command(label="💾 名前を付けて保存...", command=self.save_as_data)
        file_menu.add_separator()
        file_menu.add_command(label="🖼️ カード単体画像生成", command=self.generate_single_card_image)
        file_menu.add_command(label="�️ プリントレイアウト生成", command=self.generate_print_layout)
        file_menu.add_separator()
        file_menu.add_command(label="終了", command=self.quit)
        
        # デザインメニュー (新規追加)
        design_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="デザイン", menu=design_menu)
        design_menu.add_command(label="使用フォント指定...", command=self.open_font_selector)
        design_menu.add_command(label="レイアウト詳細設定...", command=self.open_design_config_window)

        # キーバインドの設定
        self.bind('<Control-s>', lambda event: self.overwrite_save_data())
        self.bind('<Control-o>', lambda event: self.load_data())
        self.bind('<Control-Shift-P>', lambda event: self.generate_all_card_images())

        # ウィンドウが閉じられるときの処理をフック
        self.protocol("WM_DELETE_WINDOW", self._on_closing)


        self.left_frame = tk.Frame(self, bg="gray", width=350)
        self.left_frame.pack(side="left", fill="y")
        self.right_frame = tk.Frame(self, width=650)
        self.right_frame.pack(side="right", fill="both", expand=True)

        self.preview = CardPreview(self.left_frame)
        self.preview.pack(padx=20, pady=20)

        # reset_card メソッドを InputPanel に渡す
        self.input_panel = InputPanel(self.right_frame, self.update_preview, self.load_data, self.reset_card, self.save_as_data, self.overwrite_save_data, self.generate_current_card_image, self.open_param_selector, self.generate_centered_name_image)
        self.input_panel.pack(fill="both", expand=True)
        
        # ディレクトリの確認・作成
        if not os.path.exists(const.DATA_DIR):
            os.makedirs(const.DATA_DIR)
        if not os.path.exists(const.DEFAULT_FONT_DIR):
            os.makedirs(const.DEFAULT_FONT_DIR)
        
        # 特徴リストをファイルから読み込む
        self._load_params()
        
        # 初回プレビュー更新
        self.input_panel.on_type_change()

    # --- 設定管理メソッド ---
    def _save_config(self):
        try:
            with open(const.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.app_config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            messagebox.showerror("保存エラー", f"設定ファイルの保存中にエラーが発生しました:\n{e}")

    def open_font_selector(self):
        FontSelectorWindow(
            self, 
            self.app_config.get("font_path", ""), # <--- self.app_configを使用
            self._update_font_config
        )

    def _update_font_config(self, new_path):
        self.app_config["font_path"] = new_path # <--- self.app_configを使用
        self._save_config()
        # フォント設定変更後、全画面を再描画するためにプレビューを更新
        self.input_panel.on_input_change() 
        
    def open_design_config_window(self):
        # 現在の設定をディープコピーして渡す
        initial_config = json.loads(json.dumps(self.app_config))
        DesignConfigWindow(
            self, 
            initial_config,
            self._preview_design_config, # プレビュー用コールバック
            self._update_design_config
        )

    def _preview_design_config(self, temp_config):
        """設定を保存せずにプレビューのみ更新する"""
        # 一時的な設定オブジェクトを作成
        preview_config = json.loads(json.dumps(self.app_config))
        preview_config["offsets"].update(temp_config.get("offsets", {}))
        preview_config["font_sizes"].update(temp_config.get("font_sizes", {}))
        preview_config["layout_options"].update(temp_config.get("layout_options", {}))
        self.update_preview(self.input_panel.current_card, self.input_panel.card_type_name, [line.strip() for line in self.input_panel.current_card.name.split('\n') if line.strip()], temp_config=preview_config)

    def _update_design_config(self, new_config):
        # 新しい設定でapp_configを更新
        self.app_config["offsets"].update(new_config.get("offsets", {}))
        self.app_config["font_sizes"].update(new_config.get("font_sizes", {}))
        self.app_config["layout_options"].update(new_config.get("layout_options", {}))
        self._save_config()
        self.input_panel.on_input_change() 

    def generate_centered_name_image(self):
        """カード名を中央揃え(size 24)で画像生成する"""
        card_obj = self.input_panel.current_card
        if not card_obj or not card_obj.name:
            messagebox.showwarning("警告", "カード名が入力されていないため、画像を生成できません。")
            return

        # 一時的な設定オブジェクトを作成
        temp_config = json.loads(json.dumps(self.app_config))
        temp_config["font_sizes"]["name_1line"] = 24
        temp_config["offsets"]["name_x"] = 0

        # 一時設定を使って画像を生成
        name_lines = [line.strip() for line in card_obj.name.split('\n') if line.strip()]
        card_img = self.renderer.draw_single_card(card_obj, self.input_panel.card_type_name, name_lines, temp_config)

        if not card_img:
            messagebox.showerror("エラー", "画像の生成に失敗しました。")
            return

        # ファイル名を決定して保存ダイアログを開く
        card_name_safe = card_obj.name.replace('\n', ' ').strip().replace('/', '／').replace('\\', '￥')
        image_filename = f"{card_name_safe}.png"
        if self.input_panel.card_type_name == const.CARD_TYPE_BOSS:
            image_filename = f"BOSS_{card_name_safe}.png"
        default_save_path = os.path.join(const.PICTURES_DIR, image_filename)
        ImagePreviewAndSaveDialog(self, card_img, default_save_path)

    def _load_params(self):
        """特徴リストをparams.jsonから読み込む。ファイルがなければ既存のカードから生成する。"""
        try:
            with open(const.PARAMS_FILE, 'r', encoding='utf-8') as f:
                param_list = json.load(f)
                self.all_params = set(param_list)
        except (FileNotFoundError, json.JSONDecodeError):
            # ファイルがない、または不正な形式の場合は既存のカードからスキャンして生成
            self._scan_all_params()
            self._save_params() # 生成したリストをファイルに保存

    def _save_params(self):
        """現在の特徴リストをparams.jsonに保存する。"""
        try:
            # setをリストに変換してソートしてから保存
            param_list = sorted(list(self.all_params))
            with open(const.PARAMS_FILE, 'w', encoding='utf-8') as f:
                json.dump(param_list, f, ensure_ascii=False, indent=4)
        except Exception as e:
            # ユーザーにエラーを通知するが、アプリの終了は妨げない
            print(f"Warning: 特徴リストの保存に失敗しました: {e}")

    def _on_closing(self):
        """アプリケーション終了時の処理。"""
        self._save_params()
        self.destroy()

    def _scan_all_params(self):
        """datasディレクトリ内の全JSONをスキャンして特徴リストを生成する"""
        params = set()
        if not os.path.exists(const.DATA_DIR):
            return
        
        # os.walkを使ってサブディレクトリも再帰的に探索する
        for root, dirs, files in os.walk(const.DATA_DIR):
            for filename in files:
                if filename.endswith(".json"):
                    filepath = os.path.join(root, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if "param" in data and isinstance(data["param"], list):
                                for p in data["param"]:
                                    if p: params.add(p)
                    except Exception as e:
                        print(f"特徴のスキャン中にエラー ({filename}): {e}")
        self.all_params = params

    def open_param_selector(self):
        """特徴選択ダイアログを開く"""
        current_params = self.input_panel.current_card.param if hasattr(self.input_panel.current_card, "param") else []
        ParamSelectorWindow(self, self.all_params, current_params, self.input_panel.update_param_from_selector, self._add_new_param, self._delete_params)

    def _add_new_param(self, new_param):
        """ParamSelectorWindowから新しい特徴を受け取り、全体リストに追加する"""
        if new_param and new_param not in self.all_params:
            self.all_params.add(new_param)
            
    def _delete_params(self, params_to_delete):
        """ParamSelectorWindowから削除対象の特徴リストを受け取り、全体リストから削除する"""
        for param in params_to_delete:
            self.all_params.discard(param) # discardは要素がなくてもエラーにならない

    # リセット機能（警告付き）
    def reset_card(self):
        confirm = messagebox.askyesno( # askyesnoを使用して確認ダイアログを表示
            "確認",
            "現在の入力内容をすべて破棄してリセットします。未保存のデータは失われますがよろしいですか？"
        )
        if confirm:
            self.input_panel.reset_ui() # 「はい」が押された場合のみリセットを実行
            # UIの更新を待ってから通知を表示する
            self.update_idletasks()
            NonModalInfo(self, "リセット完了", "入力フォームがリセットされ、新規カード作成状態になりました。")

    def update_preview(self, card_obj, card_type_str, name_lines, temp_config=None):
        # プレビュー用の設定が渡された場合はそれを使用し、なければ通常の設定を使用
        self.update_title() # ウィンドウタイトルを更新
        config_to_use = temp_config if temp_config is not None else self.app_config
        # renderer.CardRendererを使って描画し、結果のImageをCardPreviewに渡す
        image = self.renderer.draw_single_card(card_obj, card_type_str, name_lines, config_to_use)
        self.preview.draw_card(image)


    def save_as_data(self):
        """名前を付けて保存"""
        card_name = self.input_panel.current_card.name.replace('\n', ' ').strip()
        card_name_safe = card_name.replace('/', '／').replace('\\', '￥')
        
        # BOSSカードの場合、ファイル名の先頭に "BOSS_" を付ける
        initial_filename = f"{card_name_safe}.json"
        if self.input_panel.card_type_name == const.CARD_TYPE_BOSS:
            initial_filename = f"BOSS_{card_name_safe}.json"
        
        filepath = filedialog.asksaveasfilename(
            initialdir=const.DATA_DIR,
            title="カード情報を保存",
            defaultextension=".json",
            filetypes=(("JSONファイル", "*.json"), ("すべてのファイル", "*.*")),
            initialfile=initial_filename
        )
        
        if not filepath:
            return 
        
        data = self.input_panel.get_data_as_dict()

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            self.current_filepath = filepath # 保存後、このパスを記憶する
            NonModalInfo(self, "保存完了", f"カード情報を保存しました:\n{os.path.basename(filepath)}")
        except Exception as e:
            messagebox.showerror("保存エラー", f"ファイルの保存中にエラーが発生しました:\n{e}")
        
        self.update_title()

    def overwrite_save_data(self):
        """上書き保存"""
        if not self.current_filepath:
            # 読み込んだファイルがない場合は「名前を付けて保存」を実行
            self.save_as_data()
            return

        data = self.input_panel.get_data_as_dict()
        try:
            with open(self.current_filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            NonModalInfo(self, "上書き保存完了", f"カード情報を上書き保存しました:\n{os.path.basename(self.current_filepath)}")
        except Exception as e:
            messagebox.showerror("上書き保存エラー", f"ファイルの上書き保存中にエラーが発生しました:\n{e}")
        
        self.update_title()


    def _load_card_data_from_file(self, filepath):
        """JSONファイルパスからカードデータを読み込むヘルパー関数"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            messagebox.showerror("エラー", f"ファイルが見つかりません:\n{filepath}")
        except json.JSONDecodeError:
            messagebox.showerror("エラー", f"JSONファイルの形式が正しくありません:\n{os.path.basename(filepath)}")
        except Exception as e:
            messagebox.showerror("読込エラー", f"ファイルの読み込み中にエラーが発生しました:\n{e}")
        return None

    def _create_card_image_from_data(self, data):
        """カードデータ(dict)からカード画像(Image)を生成するヘルパー関数"""
        try:
            name_lines = [line.strip() for line in data.get("name", "").split('\n') if line.strip()]
            return self.renderer.draw_single_card(data, data.get("card_type", ""), name_lines, self.app_config)
        except Exception as e:
            messagebox.showerror("描画エラー", f"カード画像の描画中にエラーが発生しました:\n{e}")
            return None

    # JSON読込機能 
    def generate_current_card_image(self):
        """現在プレビューに表示されているカードの画像を生成・保存する"""
        card_obj = self.input_panel.current_card
        if not card_obj or not card_obj.name:
            messagebox.showwarning("警告", "カード名が入力されていないため、画像を生成できません。")
            return

        # プレビューと同じ画像オブジェクトを生成
        name_lines = [line.strip() for line in card_obj.name.split('\n') if line.strip()]
        card_img = self.renderer.draw_single_card(card_obj, self.input_panel.card_type_name, name_lines, self.app_config)

        if not card_img:
            messagebox.showerror("エラー", "画像の生成に失敗しました。")
            return

        # 保存ダイアログのデフォルトファイル名をカード名から生成
        image_filename = utils.get_image_filename_for_card(self.input_panel.get_data_as_dict())
        default_save_path = os.path.join(const.PICTURES_DIR, image_filename)
        
        ImagePreviewAndSaveDialog(self, card_img, default_save_path)

    def load_data(self):
        filepath = filedialog.askopenfilename(
            initialdir=const.DATA_DIR,
            title="カード情報ファイルを選択",
            filetypes=(("JSONファイル", "*.json"), ("すべてのファイル", "*.*"))
        )
        if not filepath:
            return 
        
        data = self._load_card_data_from_file(filepath)
        if data:
            # 読込時に未知の特徴があれば、全体リストに自動で追加する
            loaded_params = data.get("param", [])
            if isinstance(loaded_params, list):
                for param in loaded_params:
                    if param and param not in self.all_params:
                        self.all_params.add(param)

            def show_notification():
                self.update_idletasks()
                NonModalInfo(self, "読込完了", f"カード情報を読み込みました:\n{os.path.basename(filepath)}")

            self.current_filepath = filepath # 読み込んだファイルのパスを記憶
            self.input_panel.set_data_to_ui(data, on_complete_callback=show_notification)
        self.update_title()

    def update_title(self):
        """ウィンドウのタイトルを現在のファイル名で更新する"""
        base_title = "UCG Maker"
        if self.current_filepath:
            self.title(f"{base_title} - {os.path.basename(self.current_filepath)}")
        else:
            self.title(f"{base_title} - (新規カード)")

    # カード単体画像生成機能
    def generate_single_card_image(self):
        filepath = filedialog.askopenfilename(
            initialdir=const.DATA_DIR,
            title="画像生成するカード情報ファイルを選択",
            filetypes=(("JSONファイル", "*.json"), ("すべてのファイル", "*.*"))
        )
        if not filepath:
            return

        data = self._load_card_data_from_file(filepath)
        if not data:
            return

        card_img = self._create_card_image_from_data(data)
        if not card_img:
            return

        # 4. プレビュー＆保存ダイアログを開く
        # picturesディレクトリが存在しない場合は作成
        if not os.path.exists(const.PICTURES_DIR):
            os.makedirs(const.PICTURES_DIR)

        image_filename = utils.get_image_filename_for_card(data)
        default_save_path = os.path.join(const.PICTURES_DIR, image_filename)

        ImagePreviewAndSaveDialog(self, card_img, default_save_path)

    def _create_layout_from_images(self, image_paths):
        """画像ファイルのパスリストからプリントレイアウトを生成する"""
        # 一括入力ウィンドウで枚数を指定
        quantity_dialog = QuantityInputWindow(self, image_paths)
        final_quantities = quantity_dialog.result
        if not final_quantities:
            return None

        all_images_to_print = []
        for path, quantity in final_quantities.items():
            try:
                img = Image.open(path).resize((const.CARD_W, const.CARD_H))
                all_images_to_print.extend([img] * quantity)
            except Exception as e:
                messagebox.showwarning("画像読込エラー", f"画像の読み込みに失敗しました:\n{os.path.basename(path)}\n\n{e}")
        return all_images_to_print

    # プリントレイアウト生成機能 
    def generate_print_layout(self):
        # UX改善: 複数選択のガイダンス
        messagebox.showinfo("プリントレイアウト生成手順", 
                            "手順1: 表示されるファイル選択ダイアログで、印刷したいカードのJSONファイルを\n"
                            "**Ctrlキー (MacではCommandキー) や Shiftキーを使って**\n"
                            "**すべて同時に**選択してください。\n\n"
                            "手順2: 次のウィンドウで、選択した各カードの枚数（合計9枚まで）を一括で指定します。")

        # --- 作成方法の選択 ---
        dialog = tk.Toplevel(self)
        dialog.title("作成方法の選択")
        dialog.transient(self)
        dialog.grab_set()
        
        # ウィンドウを中央に配置
        w, h = 350, 120
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        dialog.geometry(f'{w}x{h}+{x}+{y}')

        tk.Label(dialog, text="どのファイルからプリントレイアウトを作成しますか？", pady=15).pack()
        
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=5)

        source_type = tk.StringVar()

        def set_source_and_close(src_type):
            source_type.set(src_type)
            dialog.destroy()

        tk.Button(btn_frame, text="カード情報 (JSON)", width=18, command=lambda: set_source_and_close("json")).pack(side="left", padx=10)
        tk.Button(btn_frame, text="カード画像 (PNG/JPG)", width=18, command=lambda: set_source_and_close("image")).pack(side="left", padx=10)
        
        self.wait_window(dialog)
        # --- 選択ここまで ---

        # --- 選択されたソースタイプに応じて処理を分岐 ---
        selected_source = source_type.get()
        if not selected_source: # ダイアログが閉じられた場合
            return

        if selected_source == "json":
            filepaths = filedialog.askopenfilenames(
                initialdir=const.DATA_DIR, title="プリントするカード情報ファイルを選択 (最大9種類)", filetypes=(("JSONファイル", "*.json"),)
            )
        elif selected_source == "image":
            filepaths = filedialog.askopenfilenames(
                initialdir=const.PICTURES_DIR, title="プリントするカード画像ファイルを選択 (最大9種類)", 
                filetypes=(("画像ファイル", "*.png *.jpg *.jpeg"), ("すべてのファイル", "*.*"))
            )

        if not filepaths:
            return 
        
        if len(filepaths) > 9:
            messagebox.showwarning("警告", "選択できるカードの種類は最大9つまでです。最初の9つのみを使用します。")
            filepaths = filepaths[:9]

        # --- 選択されたソースに応じてカード画像リストを作成 ---
        all_images_to_print = []
        if selected_source == "json":
            # 一括入力ウィンドウで枚数を指定
            quantity_dialog = QuantityInputWindow(self, filepaths)
            final_quantities = quantity_dialog.result
            if not final_quantities:
                NonModalInfo(self, "キャンセル", "枚数指定がキャンセルされました。")
                return

            # 結果を基にカードリストを作成
            for path, quantity in final_quantities.items():
                data = self._load_card_data_from_file(path)
                if data:
                    for _ in range(quantity):
                        card_img = self._create_card_image_from_data(data)
                        if card_img:
                            all_images_to_print.append(card_img)
        
        elif selected_source == "image":
            all_images_to_print = self._create_layout_from_images(filepaths)

        # _create_layout_from_imagesがNoneを返す場合（キャンセル時）のチェックを追加
        if all_images_to_print is None:
            return

        # 9枚に満たない場合はここで終了
        if not all_images_to_print:
            NonModalInfo(self, "情報", "プリントするカードがありませんでした。")
            return

        # 3. 共通関数を呼び出してレイアウト生成と保存を行う
        # picturesディレクトリが存在しない場合は作成
        if not os.path.exists(const.PICTURES_DIR):
            os.makedirs(const.PICTURES_DIR)

        utils.create_and_save_print_layouts(self, all_images_to_print)

    def generate_all_card_images(self):
        """datasフォルダ内のすべてのJSONからカード画像を生成する（隠し機能）"""
        if not messagebox.askyesno("一括画像生成の確認", 
                                   "datasフォルダ内のすべてのカードデータから画像を生成します。\n"
                                   "cardフォルダ内に同名の画像ファイルが存在する場合、上書きされます。\n\n"
                                   "実行しますか？"):
            return

        if not os.path.exists(const.PICTURES_DIR):
            os.makedirs(const.PICTURES_DIR)

        success_count = 0
        error_count = 0
        skipped_count = 0
        error_files = []

        # datasフォルダを再帰的にスキャン
        for root, _, files in os.walk(const.DATA_DIR):
            for filename in files:
                if not filename.endswith(".json"):
                    continue
                
                filepath = os.path.join(root, filename)
                try:
                    data = self._load_card_data_from_file(filepath)
                    if not data:
                        raise ValueError("JSONデータの読み込みに失敗しました。")

                    card_img = self._create_card_image_from_data(data)
                    if not card_img:
                        raise ValueError("カード画像の生成に失敗しました。")

                    # 共通関数を使ってファイル名を決定
                    image_filename = utils.get_image_filename_for_card(data)
                    save_path = os.path.join(const.PICTURES_DIR, image_filename)
                    
                    should_save = True
                    if os.path.exists(save_path):
                        # ファイルが存在する場合、上書き確認ダイアログを表示
                        if not messagebox.askyesno("上書き確認", f"ファイルは既に存在します:\n{image_filename}\n\n上書きしますか？"):
                            should_save = False
                            skipped_count += 1
                    
                    if should_save:
                        card_img.save(save_path)
                        success_count += 1

                except Exception as e:
                    error_count += 1
                    error_files.append(f"{filename} ({e})")
        
        message = f"一括画像生成が完了しました。\n\n成功: {success_count}件\nスキップ: {skipped_count}件\n失敗: {error_count}件"
        if error_count > 0:
            message += "\n\n失敗したファイル:\n- " + "\n- ".join(error_files)
        
        messagebox.showinfo("処理完了", message)

if __name__ == '__main__':
    try:
        app = App()
        app.mainloop()
    except Exception as e:
        # 予期せぬエラーをファイルに記録
        error_log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "error.log")
        with open(error_log_path, "a", encoding="utf-8") as f:
            f.write(f"--- UCG_Creater.py Error ---\n")
            f.write(f"Timestamp: {__import__('datetime').datetime.now()}\n")
            traceback.print_exc(file=f)
            f.write("\n")
        # ユーザーにエラーが発生したことを通知
        messagebox.showerror("致命的なエラー", f"予期せぬエラーが発生しました。詳細は error.log を確認してください。\n\n{e}")