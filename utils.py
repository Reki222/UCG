import os
import json
import constants as const

from tkinter import filedialog, messagebox
from PIL import Image
def load_config():
    """
    config.jsonを読み込み、デフォルト値で補完して返す共通関数。
    """
    default_config = {
        "font_path": os.path.join(const.APP_DIR, "fonts", "ipaexm.ttf"),
        "offsets": {
            "name_x": 0, "name_y": 0, "cost_num_x": 0, "cost_num_y": 0,
            "pow_x": 0, "pow_y": 0, "param_x": 0, "param_y": 0,
            "effects_x": 0, "effects_y": 0, "footer_type_x": 0, "footer_color_x": 0, "footer_y": 0,
        },
        "font_sizes": {
            "name_1line": 24, "name_2line": 20, "cost": 20, "pow_param": 18,
            "effects_header": 13, "effects_body": 11, "footer": 15
        },
        "layout_options": {
            "effects_max_width_px": 250
        }
    }

    try:
        with open(const.CONFIG_FILE, 'r', encoding='utf-8') as f:
            loaded_config = json.load(f)
        
        # デフォルト値を基準に、読み込んだ設定で上書き・補完する
        config = default_config
        for category, items in default_config.items():
            if category in loaded_config:
                if isinstance(items, dict):
                    for key, default_val in items.items():
                        config[category][key] = loaded_config[category].get(key, default_val)
                else:
                    config[category] = loaded_config[category]
        return config
    except (FileNotFoundError, json.JSONDecodeError):
        return default_config

def get_image_filename_for_card(card_data, extension=".png"):
    """
    カードデータ(dict)から、BOSSの命名規則を考慮した画像ファイル名を生成する。
    """
    card_name_safe = card_data.get("name", "").replace('\n', ' ').strip().replace('/', '／').replace('\\', '￥')
    filename = f"{card_name_safe}{extension}"
    if card_data.get("card_type") == const.CARD_TYPE_BOSS:
        filename = f"BOSS_{card_name_safe}{extension}"
    return filename

def create_and_save_print_layouts(master, image_objects, initial_filename_base="Card_Layout_3x3", initial_dir=None):
    """
    PIL.Imageオブジェクトのリストから3x3の印刷レイアウト画像を生成し、ユーザーに保存させる共通関数。
    
    Args:
        master (tk.Widget): tkinterの親ウィジェット。ダイアログの表示に使用。
        image_objects (list): 印刷するPIL.Imageオブジェクトのリスト。
        initial_filename_base (str): 保存ダイアログの初期ファイル名のベース部分。
        initial_dir (str, optional): 保存ダイアログの初期ディレクトリ。Defaults to PICTURES_DIR.
    """
    # dialogsは関数内でのみインポートし、循環参照のリスクを避ける
    from dialogs import NonModalInfo

    GRID_W, GRID_H = 3, 3
    MARGIN = 10 # カード間の余白
    CARD_WIDTH, CARD_HEIGHT = const.CARD_W, const.CARD_H

    # initial_dirが指定されていない場合は、UCG_CreaterのデフォルトであるPICTURES_DIRを使用
    save_dir = initial_dir if initial_dir is not None else const.PICTURES_DIR

    # 最終的なレイアウト画像のサイズを計算
    final_w = GRID_W * CARD_WIDTH + (GRID_W + 1) * MARGIN
    final_h = GRID_H * CARD_HEIGHT + (GRID_H + 1) * MARGIN

    page_num = 1
    total_pages = (len(image_objects) + (GRID_W * GRID_H - 1)) // (GRID_W * GRID_H)

    for i in range(0, len(image_objects), GRID_W * GRID_H):
        chunk = image_objects[i:i + (GRID_W * GRID_H)]
        
        page = Image.new('RGB', (final_w, final_h), (200, 200, 200))

        for j, card_img in enumerate(chunk):
            resized_card_img = card_img.resize((CARD_WIDTH, CARD_HEIGHT))
            row, col = j // GRID_W, j % GRID_W
            x = col * CARD_WIDTH + (col + 1) * MARGIN
            y = row * CARD_HEIGHT + (row + 1) * MARGIN
            page.paste(resized_card_img, (x, y))

        initial_file = f"{initial_filename_base}.png"
        if total_pages > 1:
            initial_file = f"{initial_filename_base}({page_num}).png"

        try:
            save_path = filedialog.asksaveasfilename(
                initialdir=save_dir,
                title=f"プリントレイアウトを保存 ({page_num}/{total_pages})",
                defaultextension=".png",
                filetypes=(("PNGファイル", "*.png"),),
                initialfile=initial_file
            )
            if not save_path:
                NonModalInfo(master, "キャンセル", "処理を中断しました。")
                return
            page.save(save_path)
            page_num += 1
        except Exception as e:
            messagebox.showerror("保存エラー", f"画像の保存中にエラーが発生しました:\n{e}", parent=master)
            return

    if page_num > 1:
        NonModalInfo(master, "保存完了", f"{page_num - 1} 枚の画像を保存しました。")

def create_and_save_print_layouts(master, image_objects, initial_filename_base="Card_Layout_3x3", initial_dir=None):
    """
    PIL.Imageオブジェクトのリストから3x3の印刷レイアウト画像を生成し、ユーザーに保存させる共通関数。
    
    Args:
        master (tk.Widget): tkinterの親ウィジェット。ダイアログの表示に使用。
        image_objects (list): 印刷するPIL.Imageオブジェクトのリスト。
        initial_filename_base (str): 保存ダイアログの初期ファイル名のベース部分。
        initial_dir (str, optional): 保存ダイアログの初期ディレクトリ。Defaults to PICTURES_DIR.
    """
    # dialogsは関数内でのみインポートし、循環参照のリスクを避ける
    from dialogs import NonModalInfo

    GRID_W, GRID_H = 3, 3
    MARGIN = 10 # カード間の余白
    CARD_WIDTH, CARD_HEIGHT = const.CARD_W, const.CARD_H

    # initial_dirが指定されていない場合は、UCG_CreaterのデフォルトであるPICTURES_DIRを使用
    save_dir = initial_dir if initial_dir is not None else const.PICTURES_DIR

    # 最終的なレイアウト画像のサイズを計算
    final_w = GRID_W * CARD_WIDTH + (GRID_W + 1) * MARGIN
    final_h = GRID_H * CARD_HEIGHT + (GRID_H + 1) * MARGIN

    page_num = 1
    total_pages = (len(image_objects) + (GRID_W * GRID_H - 1)) // (GRID_W * GRID_H)

    for i in range(0, len(image_objects), GRID_W * GRID_H):
        chunk = image_objects[i:i + (GRID_W * GRID_H)]
        
        page = Image.new('RGB', (final_w, final_h), (200, 200, 200))

        for j, card_img in enumerate(chunk):
            resized_card_img = card_img.resize((CARD_WIDTH, CARD_HEIGHT))
            row, col = j // GRID_W, j % GRID_W
            x = col * CARD_WIDTH + (col + 1) * MARGIN
            y = row * CARD_HEIGHT + (row + 1) * MARGIN
            page.paste(resized_card_img, (x, y))

        initial_file = f"{initial_filename_base}.png"
        if total_pages > 1:
            initial_file = f"{initial_filename_base}({page_num}).png"

        try:
            save_path = filedialog.asksaveasfilename(
                initialdir=save_dir,
                title=f"プリントレイアウトを保存 ({page_num}/{total_pages})",
                defaultextension=".png",
                filetypes=(("PNGファイル", "*.png"),),
                initialfile=initial_file
            )
            if not save_path:
                NonModalInfo(master, "キャンセル", "処理を中断しました。")
                return
            page.save(save_path)
            page_num += 1
        except Exception as e:
            messagebox.showerror("保存エラー", f"画像の保存中にエラーが発生しました:\n{e}", parent=master)
            return

    if page_num > 1:
        NonModalInfo(master, "保存完了", f"{page_num - 1} 枚の画像を保存しました。")