import os, re, unicodedata, subprocess, shutil
from PIL import Image, ImageDraw, ImageFont
from src.Compression.LZ11 import LZ11

# =====================================================================
# 🎛️ PAINEL DE CONTROLE (Proporções do Wii)
# =====================================================================
SCALE_FACTOR = 2
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

TEXTURE_SPECS = {
    "V_FULL": {
        "width": 80, "height": 296, "type": "vertical",
        "solo_song_x": 40, "solo_song_y": 2, "solo_song_w": 48, "solo_song_h": 276,
        "duo_song_x": 56, "duo_song_y": 2, "duo_song_w": 34, "duo_song_h": 276,
        "duo_art_x": 24, "duo_art_y": 12, "duo_art_w": 34, "duo_art_h": 260
    },
    "V_SHORT": {
        "width": 48, "height": 296, "type": "vertical",
        "song_x": 24, "song_y": 2, "song_w": 38, "song_h": 276
    },
    "H_CENTER_360x80": {
        "width": 360, "height": 80, "type": "horizontal", "align": "center", "pad": 0, "size": 34, "y_offset": 0
    },
    "H_CENTER": {
        "width": 512, "height": 32, "type": "horizontal", "align": "left", "pad": 36, "size": 18, "y_offset": 0
    },
    "H_LEFT": {
        "width": 512, "height": 32, "type": "horizontal", "align": "left", "pad": 4, "size": 18, "y_offset": 0
    },
    "H_RIGHT_MI": {
        "width": 512, "height": 32, "type": "horizontal", "align": "right", "pad": 10, "size": 18, "y_offset": 0
    },
    "H_RIGHT_BLACK": {
        "width": 640, "height": 32, "type": "horizontal_black", "align": "right", "pad": 10, "size": 18, "y_offset": 0
    }
}

FILENAME_MAP = {
    "H_CENTER_360x80": "result",
    "H_RIGHT_BLACK": "game",
    "V_FULL": "select_full",
    "V_SHORT": "select_short"
}

LITTLE_HIRAKATA = set("ぁぃぅぇぉァィゥェォっッゃャゅュょョゎヮヵゕヶゖ")
PUNCTUATION = {"、", "．", "'", "’", '"', ".", ",", "“", "。"}

TO_REPLACE = {"【", "】", "∀"}
TO_REPLACE_VERTICAL = {
    'ー': '丨', '「': '﹁', '」': '﹂', '(': '︵', ')': '︶',
    '/': '／', '[': '﹇', ']': '﹈', ':': '‥', '～': '﹬',
    '~': '﹬', '〜': '﹬', '-': '︲', '‐': '︲', '…': '⋮',
    '＝': '\ufe1a'
}

class TextureCooker:
    def __init__(self, font_name="TnT.ttf"):
        self.songs = []
        self.font_path = os.path.join(CURRENT_DIR, font_name)
        self.genre_color = self._hex_to_rgba("004A52")
        self.text_color = (255, 255, 255, 255)
        self.stroke_width_base = 5
        self.wimgt_path = os.path.abspath(os.path.join("src", "Texture", "bin", "wimgt.exe"))

    def add_song(self, song_title, song_artist, song_id):
        self.songs.append({
            "title": self._normalize_text(song_title),
            "artist": self._normalize_text(song_artist),
            "id": song_id.upper()
        })
        print(f"[Texture] '{song_id}' registered in the texture queue.")

    def _strip_accents(self, text):
        normalized = unicodedata.normalize('NFD', text)
        return ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')

    def _normalize_text(self, text):
        text = re.sub(r' +', ' ', text).strip()
        return self._strip_accents(text)

    def _hex_to_rgba(self, hex_color):
        hex_color = hex_color.strip().replace("#", "")
        if len(hex_color) != 6:
            return (0, 0, 0, 255)
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        return (r, g, b, 255)

    # =================================================================
    # SISTEMA DE MEDIÇÃO PIXEL-PERFECT
    # =================================================================

    def _get_char_dims(self, char, font):
        temp = Image.new('RGBA', (128, 128), (0, 0, 0, 0))
        draw = ImageDraw.Draw(temp)
        draw.text((64, 64), char, font=font, fill="white", anchor="mt")
        bbox = temp.getbbox()
        if bbox:
            return bbox[0]-64, bbox[1]-64, bbox[2]-64, bbox[3]-64
        return 0, 0, 0, 0

    def _measure_vertical_text(self, text, font_size, has_ura=False):
        font = ImageFont.truetype(self.font_path, font_size)
        max_w = 0
        total_h = 0
        for char in text:
            if char in {" ", " "}:
                total_h += int(font_size * 0.4)
                continue
            mapped = TO_REPLACE_VERTICAL.get(char, char)
            x0, y0, x2, y2 = self._get_char_dims(mapped, font)
            w = x2 - x0
            h = y2 - y0
            if w > max_w: max_w = w
            total_h += h

        if has_ura:
            render_mul = (font_size / 40.0) * SCALE_FACTOR
            r = int(18 * render_mul)
            stroke_w = int(self.stroke_width_base * render_mul)
            total_h += int(5 * render_mul) + (r * 2) + (stroke_w * 2)

        return max_w, total_h

    def _get_optimal_font_size(self, text, max_w, max_h, has_ura=False, base_size=40):
        font_size = base_size * SCALE_FACTOR
        while font_size > (8 * SCALE_FACTOR):
            w, h = self._measure_vertical_text(text, font_size, has_ura)
            render_mul = (font_size / 40.0)
            stroke_w = max(1, int(self.stroke_width_base * render_mul))
            
            total_w = w + (stroke_w * 2)
            total_h = h + (stroke_w * 2)

            if total_w <= max_w and total_h <= max_h:
                break
            font_size -= 1
        return font_size

    # =================================================================
    # MOTORES DE DESENHO (2 CAMADAS)
    # =================================================================

    def _draw_dds_vertical(self, img_final, text, x_center, y_start, max_w, max_h, outline_color, font_size=40):
        has_ura = False
        if "（裏）" in text or "(裏)" in text or "裏" == text[-1]:
            has_ura = True
            text = text.replace("（裏）", "").replace("(裏)", "").rstrip("裏")

        opt_size = self._get_optimal_font_size(text, max_w, max_h, has_ura, base_size=font_size)
        font = ImageFont.truetype(self.font_path, opt_size)

        render_mul = (opt_size / (40.0 * SCALE_FACTOR)) * SCALE_FACTOR
        stroke_w = max(1, int(self.stroke_width_base * render_mul))

        _, ink_h = self._measure_vertical_text(text, opt_size, has_ura)

        padding = stroke_w * 2
        temp_w = max_w + (padding * 2)
        layer_h = ink_h + (padding * 2)

        back_img = Image.new('RGBA', (temp_w, layer_h), (0, 0, 0, 0))
        front_img = Image.new('RGBA', (temp_w, layer_h), (0, 0, 0, 0))

        back_draw = ImageDraw.Draw(back_img)
        front_draw = ImageDraw.Draw(front_img)

        y_draw = padding
        draw_x = temp_w // 2

        for char in text:
            if char in {" ", " "}:
                y_draw += int(opt_size * 0.4)
                continue

            mapped = TO_REPLACE_VERTICAL.get(char, char)
            x0, y0, x2, y2 = self._get_char_dims(mapped, font)

            if y2 <= y0: continue

            h = y2 - y0
            draw_y = y_draw - y0

            # Camada Traseira (Gorda)
            back_draw.text((draw_x, draw_y), mapped, font=font,
                           fill=outline_color, stroke_width=stroke_w,
                           stroke_fill=outline_color, anchor="mt")
            # Camada Frontal (Limpa)
            front_draw.text((draw_x, draw_y), mapped, font=font,
                            fill=self.text_color, anchor="mt")
            y_draw += h

        if has_ura:
            ura_size = int(30 * render_mul)
            r = int(18 * render_mul)
            try:
                u_font = ImageFont.truetype(self.font_path, ura_size)
                y_draw += int(5 * render_mul)
                cy = y_draw + r

                # Borda do círculo na camada de trás
                back_draw.ellipse((draw_x - r - stroke_w, cy - r - stroke_w,
                                   draw_x + r + stroke_w, cy + r + stroke_w),
                                  fill=outline_color)
                # Texto Ura na frente
                front_draw.text((draw_x, cy), "裏", font=u_font, fill=self.text_color, anchor="mm")
            except IOError:
                pass

        back_img.alpha_composite(front_img)
        bbox = back_img.getbbox()
        final_temp = back_img.crop(bbox) if bbox else back_img

        final_w = min(final_temp.width, max_w)
        final_h = min(final_temp.height, max_h)

        if final_temp.width > max_w or final_temp.height > max_h:
            final_temp = final_temp.resize((final_w, final_h), Image.Resampling.BICUBIC)

        paste_x = x_center - (final_temp.width // 2)
        paste_y = y_start 

        img_final.alpha_composite(final_temp, dest=(paste_x, paste_y))

    def _draw_dds_horizontal(self, draw, song_name, specs, outline_color):
        font_size = specs["size"] * SCALE_FACTOR
        font = ImageFont.truetype(self.font_path, font_size)
        stroke_w = int((self.stroke_width_base * (specs["size"] / 40.0)) * SCALE_FACTOR)

        while font_size > 8 * SCALE_FACTOR:
            bbox = draw.textbbox((0, 0), song_name, font=font, stroke_width=stroke_w)
            if (bbox[2] - bbox[0]) <= (specs["width"] * SCALE_FACTOR) - (specs.get("pad", 0) * SCALE_FACTOR * 2):
                break
            font_size -= 1
            font = ImageFont.truetype(self.font_path, font_size)

        bbox = draw.textbbox((0, 0), song_name, font=font, stroke_width=stroke_w)
        x0, y0, x2, y2 = bbox
        text_w, text_h = x2 - x0, y2 - y0

        pad = specs.get("pad", 0) * SCALE_FACTOR
        w = specs["width"] * SCALE_FACTOR
        h = specs["height"] * SCALE_FACTOR
        align = specs.get("align", "left")

        if align == "right": x = w - text_w - pad - x0
        elif align == "center": x = (w - text_w) // 2 - x0
        else: x = pad - x0

        y = (h - text_h) // 2 - y0

        if specs["type"] == "horizontal_black":
            draw.text((x, y), song_name, font=font, fill=self.text_color)
        else:
            draw.text((x, y), song_name, font=font, fill=self.text_color, stroke_width=stroke_w, stroke_fill=outline_color)

    # =================================================================
    # PIPELINE DE TEXTURAS E CONVERSÕES WII
    # =================================================================

    def _generate_select_non(self, temp_dir, song, idx_str):
        specs = TEXTURE_SPECS["V_SHORT"]
        w = specs["width"] * SCALE_FACTOR
        h = specs["height"] * SCALE_FACTOR
        img = Image.new('RGBA', (w, h), (0, 0, 0, 0))

        self._draw_dds_vertical(
            img, song["title"], specs["song_x"] * SCALE_FACTOR, specs["song_y"] * SCALE_FACTOR,
            specs["song_w"] * SCALE_FACTOR, specs["song_h"] * SCALE_FACTOR, self.genre_color, font_size=30
        )

        filename = f"select_non_{idx_str}.png"
        final_img = img.resize((specs["width"], specs["height"]), Image.Resampling.BICUBIC)
        final_img.save(os.path.join(temp_dir, filename))

    def _generate_taiko_texture(self, suffix, specs, temp_dir, song, idx_str):
        w = specs["width"] * SCALE_FACTOR
        h = specs["height"] * SCALE_FACTOR

        if specs["type"] == "horizontal_black":
            img = Image.new('RGBA', (w, h), (0, 0, 0, 255))
        else:
            img = Image.new('RGBA', (w, h), (0, 0, 0, 0))

        draw = ImageDraw.Draw(img)
        outline_color = (0, 0, 0, 255)

        try:
            if specs["type"] == "vertical":
                if suffix == "V_FULL":
                    if song["artist"]:
                        self._draw_dds_vertical(
                            img, song["artist"], specs["duo_art_x"] * SCALE_FACTOR, specs["duo_art_y"] * SCALE_FACTOR,
                            specs["duo_art_w"] * SCALE_FACTOR, specs["duo_art_h"] * SCALE_FACTOR, outline_color, font_size=21
                        )
                        self._draw_dds_vertical(
                            img, song["title"], specs["duo_song_x"] * SCALE_FACTOR, specs["duo_song_y"] * SCALE_FACTOR,
                            specs["duo_song_w"] * SCALE_FACTOR, specs["duo_song_h"] * SCALE_FACTOR, outline_color, font_size=28
                        )
                    else:
                        self._draw_dds_vertical(
                            img, song["title"], specs["solo_song_x"] * SCALE_FACTOR, specs["solo_song_y"] * SCALE_FACTOR,
                            specs["solo_song_w"] * SCALE_FACTOR, specs["solo_song_h"] * SCALE_FACTOR, outline_color, font_size=40
                        )

                elif suffix == "V_SHORT":
                    self._draw_dds_vertical(
                        img, song["title"], specs["song_x"] * SCALE_FACTOR, specs["song_y"] * SCALE_FACTOR,
                        specs["song_w"] * SCALE_FACTOR, specs["song_h"] * SCALE_FACTOR, outline_color, font_size=30
                    )
            else:
                self._draw_dds_horizontal(draw, song["title"], specs, outline_color)

        except IOError:
            print(f"Erro: Fonte '{self.font_path}' não encontrada.")
            return

        base_name = FILENAME_MAP.get(suffix, f"SONG_{suffix}")
        filename = f"{base_name}_{idx_str}.png"

        final_img = img.resize((specs["width"], specs["height"]), Image.Resampling.BICUBIC)
        final_img.save(os.path.join(temp_dir, filename))

    def _run_wimgt(self, input_paths, output_tpl):
        if not os.path.exists(self.wimgt_path):
            print(f"[Error] wimgt.exe not found at {self.wimgt_path}")
            return False

        cmd = [self.wimgt_path, "ENCODE"] + input_paths + ["-d", output_tpl, "-x", "TPL.RGB5A3"]
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return True
        except Exception as e:
            print(f"[Error] Falha ao converter com wimgt: {e}")
            return False

    def _compress_to_ctpl(self, tpl_path, output_ctpl_path):
        if not os.path.exists(tpl_path):
            print(f"[Aviso] TPL não encontrado para compressão: {tpl_path}")
            return
        with open(tpl_path, "rb") as f:
            data = f.read()
        compressed = LZ11.compress(data)
        with open(output_ctpl_path, "wb") as f:
            f.write(compressed)

    def cook_all_textures(self):
        if not self.songs:
            return

        print(f"\nCooking Textures and TPLs for {len(self.songs)} songs...")
        temp_dir = "temp_textures"
        output_dir = os.path.join("output", "texture")

        os.makedirs(temp_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)

        for i, song in enumerate(self.songs, start=1):
            idx_str = f"{i:03d}"
            for suffix, specs in TEXTURE_SPECS.items():
                self._generate_taiko_texture(suffix, specs, temp_dir, song, idx_str)
            self._generate_select_non(temp_dir, song, idx_str)

        for i, song in enumerate(self.songs, start=1):
            idx_str = f"{i:03d}"
            for single_type in ["game", "result"]:
                png_path = os.path.join(temp_dir, f"{single_type}_{idx_str}.png")
                tpl_path = os.path.join(temp_dir, f"{single_type}_{idx_str}.tpl")
                out_path = os.path.join(output_dir, f"{single_type}_{idx_str}.ctpl")

                if os.path.exists(png_path):
                    if self._run_wimgt([png_path], tpl_path):
                        self._compress_to_ctpl(tpl_path, out_path)
                        print(f"[OK] Generated {single_type}_{idx_str}.ctpl")

        for global_type in ["select_full", "select_short", "select_non"]:
            exported = []

            for i in range(1, len(self.songs) + 1):
                idx_str = f"{i:03d}"
                src = os.path.join(temp_dir, f"{global_type}_{idx_str}.png")

                if not os.path.exists(src):
                    continue

                if len(exported) == 0:
                    dst = os.path.join(temp_dir, f"{global_type}.tpl.png")
                else:
                    dst = os.path.join(temp_dir, f"{global_type}.tpl.mm{len(exported)}.png")

                shutil.copy2(src, dst)
                exported.append(dst)

            if exported:
                tpl_path = os.path.join(temp_dir, f"{global_type}.tpl")
                ctpl_path = os.path.join(output_dir, f"{global_type}.ctpl")

                base_png = os.path.join(temp_dir, f"{global_type}.tpl.png")
                if self._run_wimgt([base_png], tpl_path):
                    self._compress_to_ctpl(tpl_path, ctpl_path)
                    print(f"[OK] Generated Global {global_type}.ctpl (Contains {len(exported)} textures)")

        shutil.rmtree(temp_dir)
        print(f"All textures successfully converted and compressed!")