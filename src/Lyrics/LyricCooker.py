import os
import re
import struct
import unicodedata
import jaconv
from src.Compression.LZ11 import LZ11

class LyricCooker:
    """
    Handles parsing from .lrc files or .tja tags to build Taiko no Tatsujin lyrics.
    Includes optional Romaji -> Kana conversion!
    """
    def __init__(self, song_id, convert_romaji=False):
        self.song_id = song_id
        self.lyrics = []
        self.convert_romaji = convert_romaji

    def clean_text(self, text):
        """
        Converts to Hiragana if requested, then removes accents to prevent engine crashes.
        """
        if self.convert_romaji:
            # Transforma Romaji em Hiragana usando o jaconv
            text = jaconv.alphabet2kana(text)

        # Limpeza de acentos anti-crash (para o que sobrar de alfabeto latino)
        normalized = unicodedata.normalize('NFD', text)
        return ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')

    def parse_lrc(self, lrc_path, offset_seconds=0.0):
        """Reads an .lrc file and converts timestamps."""
        if not os.path.exists(lrc_path):
            print(f"[Warning] LRC file not found: {lrc_path}")
            return

        with open(lrc_path, "r", encoding="utf-8") as f:
            for line in f:
                match = re.match(r'\[(\d{2}):(\d{2}\.\d{2,3})\](.*)', line.strip())
                if match:
                    minutes = int(match.group(1))
                    seconds = float(match.group(2))
                    text = match.group(3).strip()

                    time_base_sec = (minutes * 60) + seconds
                    final_time_sec = time_base_sec - offset_seconds

                    self.add_lyric(final_time_sec, text)
        print(f"[Lyrics] {len(self.lyrics)} lines imported from LRC!")

    def add_lyric(self, time_sec, text):
        clean = self.clean_text(text)
        self.lyrics.append((time_sec, clean))

    def cook_lyrics(self, use_lz11=True):
        """Generates the final binary file (.bin or .cbin)."""
        if not self.lyrics:
            print(f"[Aviso] Nenhuma letra processada para {self.song_id}.")
            return

        print(f"Cooking Lyrics for {self.song_id}...")

        # Garante a ordem cronológica
        self.lyrics.sort(key=lambda x: x[0])

        binario = bytearray()

        # Header Taiko Wii com a quantidade original de letras
        binario += struct.pack('>I 12x', len(self.lyrics))

        for time_sec, text in self.lyrics:
            # Shift-JIS é crucial para renderizar o Kana nativo no Wii
            encoded_text = text.encode('shift_jis', errors='ignore')[:127]
            texto_bytes = encoded_text.ljust(128, b'\x00')

            bloco = struct.pack('>f 12x 128s', float(time_sec), texto_bytes)
            binario += bloco

        output_dir = os.path.join("output", "sheet", "lyrics", "bin")
        os.makedirs(output_dir, exist_ok=True)

        if use_lz11:
            final_data = LZ11.compress(binario)
            ext = ".cbin"
        else:
            final_data = binario
            ext = ".bin"

        save_path = os.path.join(output_dir, f"{self.song_id}{ext}")

        with open(save_path, "wb") as f:
            f.write(final_data)

        print(f"[OK] Lyrics generated at {save_path} (LZ11: {use_lz11})")