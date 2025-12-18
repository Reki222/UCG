from PIL import Image, ImageDraw, ImageFont
import os
import classtype as ctp
import constants as const

DEFAULT_FONT = "arial.ttf" # フォールバック用
LINE_SPACING = 3

# --- フォント読み込みロジック ---
def get_font(size, config_font_path=None):
    # 1. config.jsonで指定されたパスを試す (最優先)
    if config_font_path and os.path.exists(config_font_path):
        try:
            return ImageFont.truetype(config_font_path, size)
        except:
            print(f"Warning: Failed to load font from config path: {config_font_path}")
            pass

    # 2. 同梱されたデフォルトフォント (ipaexm.ttf) を試す
    default_bundled_font = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts", "ipaexm.ttf")
    if os.path.exists(default_bundled_font):
        try:
            return ImageFont.truetype(default_bundled_font, size)
        except:
            print(f"Warning: Failed to load bundled default font: {default_bundled_font}")
    
    # 3. 最終フォールバック (Arialまたはデフォルト)
    try:
        return ImageFont.truetype(DEFAULT_FONT, size)
    except:
        return ImageFont.load_default()


class CardRenderer:
    """カード画像の描画に関するすべてのロジックを担うクラス"""
    def draw_single_card(self, data, card_type_name, name_lines, config):
        image = Image.new("RGB", (const.CARD_W, const.CARD_H), (255, 255, 255))
        draw = ImageDraw.Draw(image)
        
        # データの種類を判定 (オブジェクトか辞書か)
        is_object = not isinstance(data, dict)
        
        # --- ヘルパー関数 ---
        def _get_prop(key, default=None):
            if is_object:
                return getattr(data, key, default)
            return data.get(key, default)
        
        def _get_font(size):
            return get_font(size, config.get("font_path"))

        # --- 各パーツの描画 ---
        self._draw_base_frame(draw)
        self._draw_name(draw, name_lines, _get_font, config)
        self._draw_cost(draw, _get_prop, _get_font, config)
        self._draw_spell_mana(draw, card_type_name, _get_prop, _get_font, config)
        self._draw_pow_and_param(draw, _get_prop, _get_font, config)
        self._draw_effects(draw, _get_prop, _get_font, config, is_object)
        self._draw_footer(draw, card_type_name, _get_prop, _get_font, config)
            
        return image

    def _draw_base_frame(self, draw):
        """カードの基本枠と中央線を描画"""
        draw.rectangle((const.LAYOUT["PADDING"], const.LAYOUT["PADDING"], const.CARD_W - const.LAYOUT["PADDING"] - 1, const.CARD_H - const.LAYOUT["PADDING"] - 1), outline="black", width=const.LAYOUT["BORDER_WIDTH"])
        # イラスト描画エリアの枠線（デバッグ用、必要ならコメントアウト）
        # draw.rectangle((10, 50, 290, 230), outline="gray")
        draw.line((const.LAYOUT["PADDING"], const.LAYOUT["MID_LINE_Y"], const.CARD_W - const.LAYOUT["PADDING"], const.LAYOUT["MID_LINE_Y"]), fill="black", width=2)

    def _draw_name(self, draw, name_lines, font_getter, config):
        """カード名を描画"""
        if not name_lines: return
        
        offset_y = config["offsets"]["name_y"]
        
        if len(name_lines) >= 2:
            font = font_getter(config["font_sizes"]["name_2line"])
            y_start = const.LAYOUT["NAME_AREA_Y"] + offset_y
            bbox = draw.textbbox((0, 0), "A", font=font)
            line_height = (bbox[3] - bbox[1]) * 1.2 # フォントの高さに少しマージンを追加

            for i, line_text in enumerate(name_lines[:2]):
                y_pos = y_start + (i * line_height)
                bbox = draw.textbbox((0, 0), line_text, font=font)
                w = bbox[2] - bbox[0] 
                x_pos = (const.CARD_W - w) / 2
                draw.text((x_pos, y_pos), line_text, font=font, fill="black")
        else:
            text_to_draw = name_lines[0]
            font_size_1line = config["font_sizes"]["name_1line"]
            font = font_getter(font_size_1line) # 常に設定されたサイズを使用
            
            bbox = draw.textbbox((0, 0), text_to_draw, font=font)
            w = bbox[2] - bbox[0]
            x_pos = (const.CARD_W - w) / 2 + config["offsets"]["name_x"] # Xオフセットを追加
            y_pos = const.LAYOUT["NAME_AREA_Y"] + offset_y # Yオフセット
            draw.text((x_pos, y_pos), text_to_draw, font=font, fill="black")

    def _draw_cost(self, draw, prop_getter, font_getter, config):
        """コスト円と数値を描画"""
        cost_val = str(prop_getter("cost", 0))
        if cost_val == "0" or cost_val == "": return

        offset_x = config["offsets"]["cost_num_x"]
        offset_x = 0 # 削除されたため0をハードコード
        offset_y = config["offsets"]["cost_num_y"]
        cx, cy, r = const.LAYOUT["COST_CIRCLE_CX"], const.LAYOUT["COST_CIRCLE_CY"], const.LAYOUT["COST_CIRCLE_R"]
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline="black", width=2)
        
        font_num = font_getter(config["font_sizes"]["cost"])
        bbox = draw.textbbox((0, 0), cost_val, font=font_num)
        cw, ch = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text((cx - cw/2 + offset_x, cy - ch/2 + offset_y), cost_val, font=font_num, fill="black")

    def _draw_spell_mana(self, draw, card_type_name, prop_getter, font_getter, config):
        """スペルカードのマナコストを描画"""
        if card_type_name != const.CARD_TYPE_SPELLCARD: return

        color_data = prop_getter("color", {})
        if not isinstance(color_data, dict): color_data = {}

        active_mana = {k: v for k, v in color_data.items() if v > 0}
        if not active_mana: return

        COLOR_RGB = {"赤": (255, 0, 0), "青": (0, 0, 255), "緑": (0, 200, 0), "黄": (255, 255, 0), "紫": (150, 0, 150)}
        current_y = const.LAYOUT["SPELL_MANA_START_Y"]
        font_mana = font_getter(12) # これは固定でも良いか

        for color in const.COLORS:
            value = active_mana.get(color)
            if value:
                size = const.LAYOUT["SPELL_MANA_SIZE"]
                x0 = const.LAYOUT["COST_CIRCLE_CX"] - size / 2
                y0 = current_y
                fill_color = COLOR_RGB.get(color, (128, 128, 128))
                draw.ellipse((x0, y0, x0 + size, y0 + size), fill=fill_color, outline="black", width=1)

                mana_text = str(value)
                bbox = draw.textbbox((0, 0), mana_text, font=font_mana)
                cw, ch = bbox[2] - bbox[0], bbox[3] - bbox[1]
                draw.text((x0 + size/2 - cw/2, y0 + size/2 - ch/2), mana_text, font=font_mana, fill="black")
                
                current_y += size + const.LAYOUT["SPELL_MANA_PADDING"]

    def _draw_pow_and_param(self, draw, prop_getter, font_getter, config):
        """パワーと特徴を描画"""
        pow_val = prop_getter("pow", "")
        param_list = prop_getter("param", [])
        font_p = font_getter(config["font_sizes"]["pow_param"])
        offset_pow_x, offset_pow_y = config["offsets"]["pow_x"], config["offsets"]["pow_y"]
        offset_param_x, offset_param_y = config["offsets"]["param_x"], config["offsets"]["param_y"]
        offset_pow_x, offset_pow_y = 0, config["offsets"]["pow_y"] # Xオフセットは削除
        offset_param_x, offset_param_y = 0, config["offsets"]["param_y"] # Xオフセットは削除
        y_pos_pow = const.LAYOUT["MID_LINE_Y"] + const.LAYOUT["POW_PARAM_Y_OFFSET"] + offset_pow_y
        y_pos_param = const.LAYOUT["MID_LINE_Y"] + const.LAYOUT["POW_PARAM_Y_OFFSET"] + offset_param_y

        if pow_val:
            draw.text((const.LAYOUT["FOOTER_X_PADDING"] + offset_pow_x, y_pos_pow), f"POW {pow_val}", font=font_p, fill="black")
            draw.text((const.LAYOUT["FOOTER_X_PADDING"], y_pos_pow), f"POW {pow_val}", font=font_p, fill="black")

        if param_list and param_list[0]:
            p_text = " ".join(param_list) if isinstance(param_list, list) else str(param_list)
            bbox = draw.textbbox((0, 0), p_text, font=font_p)
            pw = bbox[2] - bbox[0]
            draw.text((const.CARD_W - pw - const.LAYOUT["FOOTER_X_PADDING"] + offset_param_x, y_pos_param), p_text, font=font_p, fill="black")
            draw.text((const.CARD_W - pw - const.LAYOUT["FOOTER_X_PADDING"], y_pos_param), p_text, font=font_p, fill="black")

    def _wrap_text_by_width(self, draw, text, font, max_width):
        """
        指定されたピクセル幅に基づいてテキストを折り返す。
        textwrap.wrapの代替。
        """
        lines = []
        if not text:
            return []

        current_line = ""
        for char in text:
            test_line = current_line + char

            # Pillow 9.2.0以降で推奨されるtextlengthを使用
            if hasattr(draw, 'textlength'):
                line_width = draw.textlength(test_line, font=font)
            else:  # 古いバージョン用のフォールバック
                bbox = draw.textbbox((0, 0), test_line, font=font)
                line_width = bbox[2] - bbox[0]

            if line_width <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = char
        lines.append(current_line)  # 最後の行を追加
        return lines

    def _draw_effects(self, draw, prop_getter, font_getter, config, is_object):
        """効果テキストを描画"""
        effe_list = prop_getter("effe", [])
        if not effe_list: return
        
        # --- 描画設定 ---
        offset_x = config["offsets"]["effects_x"]
        offset_x = 0 # 削除されたため0をハードコード
        offset_y = config["offsets"]["effects_y"]
        font_head = font_getter(config["font_sizes"]["effects_header"])
        font_body = font_getter(config["font_sizes"]["effects_body"])
        max_width = config["layout_options"].get("effects_max_width_px", 250)
        
        # --- 動的なY座標管理 ---
        current_y = const.LAYOUT["MID_LINE_Y"] + const.LAYOUT["EFFECT_AREA_Y_START"] + offset_y
        effect_spacing = 8 # 各効果ブロック間の余白
        
        for eff in effe_list: # 効果の数だけループ (制限を撤廃)
            if is_object:
                mana_data, eff_type, eff_place, eff_text = eff.mana, eff.type, eff.place, eff.text
            else:
                mana_data, eff_type, eff_place, eff_text = eff.get("mana", {}), eff.get("type", ""), eff.get("place", ""), eff.get("text", "")
            
            # 空の効果はスキップ
            if not eff_text and not any(mana_data.values()) and not eff_type and not eff_place: continue

            # --- ヘッダーの構築と描画 ---
            header_parts = []
            if eff_type and eff_type != "": header_parts.append(eff_type)
            if eff_place and eff_place != "": header_parts.append(eff_place)
            
            mana_list = [f"{c}{v}" for c, v in mana_data.items() if v > 0] if isinstance(mana_data, dict) else []
            if mana_list: header_parts.append(" ".join(mana_list))

            if header_parts:
                header_text = "｜".join(header_parts)
                bbox = draw.textbbox((0, 0), header_text, font=font_head)
                header_height = bbox[3] - bbox[1]
                draw.text((const.LAYOUT["FOOTER_X_PADDING"] + offset_x, current_y), header_text, font=font_head, fill="black")
                current_y += header_height + LINE_SPACING # ヘッダーの高さと少しの余白を加算

            # --- 効果テキストの描画 (行数制限なし) ---
            if eff_text:
                # ピクセル幅でテキストを折り返す
                # textwrap.wrapの代わりに新しい関数を使用
                # まずは改行コードで分割
                paragraphs = eff_text.split('\n')
                wrapped_lines = [line for p in paragraphs for line in self._wrap_text_by_width(draw, p, font_body, max_width)]
                for line in wrapped_lines: # 折り返された全ての行を描画
                    bbox = draw.textbbox((0, 0), line, font=font_body)
                    line_height = bbox[3] - bbox[1]
                    draw.text((const.LAYOUT["FOOTER_X_PADDING"] + offset_x, current_y), line, font=font_body, fill="black")
                    current_y += line_height + LINE_SPACING # 描画した行の高さと行間を加算

            current_y += effect_spacing # 次の効果ブロックとの間に余白を追加

    def _draw_footer(self, draw, card_type_name, prop_getter, font_getter, config):
        """カードタイプと属性を描画"""
        font_foot = font_getter(config["font_sizes"]["footer"])
        offset_type_x, offset_type_y = config["offsets"]["footer_type_x"], config["offsets"]["footer_y"]
        offset_color_x, offset_color_y = config["offsets"]["footer_color_x"], config["offsets"]["footer_y"]
        offset_type_x, offset_type_y = 0, config["offsets"]["footer_y"] # Xオフセットは削除
        offset_color_x, offset_color_y = 0, config["offsets"]["footer_y"] # Xオフセットは削除
        y_pos_type = const.CARD_H + const.LAYOUT["FOOTER_Y_OFFSET"] + offset_type_y
        y_pos_color = const.CARD_H + const.LAYOUT["FOOTER_Y_OFFSET"] + offset_color_y
        
        # カードタイプ
        draw.text((const.LAYOUT["FOOTER_X_PADDING"] + offset_type_x, y_pos_type), card_type_name, font=font_foot, fill="black")

        # 属性
        color_data = prop_getter("color", {})
        if not isinstance(color_data, dict): color_data = {}
        if color_data:
            active_colors = [k for k, v in color_data.items() if v > 0]
            c_text = "／".join(active_colors) if active_colors else "無"
            bbox = draw.textbbox((0, 0), c_text, font=font_foot)
            cw = bbox[2] - bbox[0] 
            draw.text((const.CARD_W - cw - const.LAYOUT["FOOTER_X_PADDING"] + offset_color_x, y_pos_color), c_text, font=font_foot, fill="black")