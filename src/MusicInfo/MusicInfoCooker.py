import os
import struct
from dataclasses import dataclass

# ============================================================
# CONSTANTS
# ============================================================

GENRES = {
    0: "0 - J-Pop",
    1: "1 - Anime",
    2: "2 - Variety",
    3: "3 - Classic",
    4: "4 - Namco Original",
    5: "5 - 童謡 (Children/Folk)",
    6: "6 - Game Music",
    7: "7 - NULL"
}

DANCERS = {
    0: "00 - Default",
    1: "01 - Mappy",
    2: "02 - Panda",
    3: "03 - Mario",
    4: "04 - Monster Hunter",
    5: "05 - Idolmaster",
    6: "06 - Idolmaster Variant",
    7: "07 - Mii"
}

@dataclass
class SongEntry:
    raw_data: bytearray
    id_str: str
    title_str: str
    preview_ms: int
    genre: int
    has_lyrics: bool
    dancer_type: int

# ============================================================
# COOKER CLASS
# ============================================================

class MusicInfoCooker:
    """
    Handles the serialization and compilation of Taiko no Tatsujin musicinfo.bin files.
    """
    def __init__(self):
        self.struct_size = 108
        self.songs = []

    def _create_default_raw(self):
        """Generates the base byte structure filled with default blank values."""
        raw = bytearray(self.struct_size)
        raw[20:24] = b'\xff\xff\xff\xff'
        raw[36:40] = b'\xff\xff\xff\xff'
        raw[72:92] = b'\xff' * 20
        return raw

    def add_song(self, song_id, title, preview_ms, genre, has_lyrics, dancer_type):
        """Adds a song to the current session before compiling the final binary."""
        new_song = SongEntry(
            raw_data=self._create_default_raw(),
            id_str=song_id,
            title_str=title,
            preview_ms=preview_ms,
            genre=genre,
            has_lyrics=has_lyrics,
            dancer_type=dancer_type
        )
        self.songs.append(new_song)
        print(f"[MusicInfo] Song '{song_id}' added to session!")

    def cook_musicinfo(self):
        """Compiles all accumulated songs and generates the output file."""
        if not self.songs:
            print("No songs in session to generate MusicInfo.")
            return

        print(f"\nCooking MusicInfo (.bin) with {len(self.songs)} songs...")

        output_dir = os.path.join("output", "sheet", "musicinfo", "bin")
        os.makedirs(output_dir, exist_ok=True)
        save_path = os.path.join(output_dir, "musicinfo.bin")

        self._save_file(save_path)

        print(f"[OK] Global MusicInfo.bin successfully generated at {save_path}!")

    def _save_file(self, save_path):
        """Packs the binary structures and string pools, generating the .bin file."""
        new_structs_data = bytearray()
        new_strings_data = bytearray()

        for index, song in enumerate(self.songs):
            id_offset = len(new_strings_data)
            new_strings_data.extend(song.id_str.encode('ascii') + b'\x00')

            title_offset = len(new_strings_data)
            new_strings_data.extend(song.title_str.encode('shift_jis', errors='replace') + b'\x00')

            macro_bytes = f"SONG_{song.id_str.upper()}".encode('ascii') + b'\x00'
            new_strings_data.extend(macro_bytes)

            struct.pack_into('>LL', song.raw_data, 0, id_offset, title_offset)
            struct.pack_into('>L', song.raw_data, 8, song.genre)
            struct.pack_into('>L', song.raw_data, 44, song.dancer_type)

            p_base = song.preview_ms
            struct.pack_into('>L', song.raw_data, 48, p_base)

            lyric_val = 1 if song.has_lyrics else 0
            struct.pack_into('>L', song.raw_data, 52, lyric_val)

            struct.pack_into('>LLLL', song.raw_data, 92, p_base, p_base + 3000, p_base, p_base + 5000)
            struct.pack_into('>LLLL', song.raw_data, 56, index, index, index, index)

            new_structs_data.extend(song.raw_data)

        # Calculates total file offsets and writes the header
        total_songs = len(self.songs)
        data_offset = 12
        string_table_offset = data_offset + len(new_structs_data)
        header = struct.pack('>LLL', total_songs, data_offset, string_table_offset)

        with open(save_path, 'wb') as f:
            f.write(header)
            f.write(new_structs_data)
            f.write(new_strings_data)