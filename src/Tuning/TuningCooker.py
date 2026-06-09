import os
import struct

# ========= TECHNICAL CONFIGURATIONS =========
RECORD_SIZE = 2244
FUMEN_SIZE = 124     # Exact, non-negotiable size per chart slot
PAD_SIZE = 620       # Strict padding with 0xFF bytes for unused slots

# Slot representations: e = Easy (Kantan), n = Normal (Futsuu), h = Hard (Muzukashii), m = Oni (Mania)
SLOT_LABELS = ["e", "n", "h", "m"]

# Base score values per difficulty (Easy, Normal, Hard, Oni, Ura)
SCORE_PER_DIFF = [6000, 7000, 7000, 8000, 8000]

# Fixed byte values required by the game engine for valid chart loading
FUMEN_CONST_FIELDS = {
    0x24: 4,
    0x28: 16,
    0x2c: 0,         # Course ID: Kept at 0 (engine infers difficulty by physical memory offset)
    0x3c: 10000,
    0x44: 65536,
    0x48: 65536,
    0x4c: 65536,
    0x50: 20,
    0x54: 10,
    0x58: 0,
    0x5c: 1,
    0x60: 20,
    0x64: 10,
    0x68: 1,
    0x6c: 30,
    0x70: 30,
    0x74: 0,
}

class TuningCooker:
    """
    Handles the serialization and compilation of Taiko no Tatsujin tuning.bin files.
    Manages memory pointers, string pooling, and strict byte alignment.
    """
    
    def __init__(self):
        self.songs = []
        self.string_pool = bytearray()
        self.reuse_strings = {}

    def _add_string(self, text, encoding='ascii'):
        """
        Adds a string to the global memory pool and returns its pointer (offset).
        Prevents string duplication to optimize memory footprint.
        """
        if not text:
            return 0xFFFFFFFF
        if text in self.reuse_strings:
            return self.reuse_strings[text]

        offset = len(self.string_pool)
        self.string_pool.extend(text.encode(encoding, errors='replace') + b'\x00')
        self.reuse_strings[text] = offset
        return offset

    def _build_fumen(self, ptr, stars, bpm, diff_index):
        """
        Builds the 124-byte struct for a single chart difficulty.
        """
        raw = bytearray(FUMEN_SIZE)

        # Write dynamic variables first to prevent overwrites
        struct.pack_into(">I", raw, 0x00, ptr)
        struct.pack_into(">I", raw, 0x04, int(stars))
        struct.pack_into(">I", raw, 0x08, int(bpm))
        struct.pack_into(">I", raw, 0x40, SCORE_PER_DIFF[diff_index])

        # Write required engine constants, skipping the offsets already populated
        for off, val in FUMEN_CONST_FIELDS.items():
            if off not in [0x00, 0x04, 0x08, 0x40]:
                struct.pack_into(">I", raw, off, val)

        return raw

    def add_song(self, song_id, jpname, bpm, stars_list):
        """
        Generates the complete 2244-byte binary record for a single song.
        Includes 1P and 2P chart structs and required 0xFF memory padding.
        """
        p_id = self._add_string(song_id, 'ascii')
        p_mu = self._add_string(f"music_{song_id}", 'ascii')
        p_jp = self._add_string(jpname, 'utf-8')

        record_data = bytearray()

        # Header (12 bytes)
        record_data.extend(struct.pack('>3I', p_id, p_mu, p_jp))

        # 🔥 VERIFICAÇÃO DO URA EXCLUSIVO
        is_ura_only = song_id.startswith("ex_")

        # 1P and 2P chart data generation
        for player in ["1p", "2p"]:
            for slot_idx, label in enumerate(SLOT_LABELS):
                
                # 🔥 SE FOR 'ex_' E A DIFICULDADE NÃO FOR 'm' (Oni), NULA O BLOCO!
                if is_ura_only and label in ["e", "n", "h"]:
                    record_data.extend(b'\xff' * FUMEN_SIZE)
                else:
                    # 🔥 FIX: Puxar as estrelas do Edit (índice 4) em vez do Oni (índice 3) para músicas Ura
                    if is_ura_only and label == "m":
                        star_idx = 4 if len(stars_list) > 4 else slot_idx
                    else:
                        star_idx = slot_idx

                    stars = int(stars_list[star_idx])
                    ptr = self._add_string(f"{song_id}{player}_{label}", "ascii")
                    
                    chart_data = self._build_fumen(ptr, stars, bpm, slot_idx)
                    record_data.extend(chart_data)

            # Strict padding to ensure the block meets the 1116-byte requirement per player
            record_data.extend(b'\xff' * PAD_SIZE)
        
        # Store as a tuple (song_id, data) to allow binary search sorting later
        self.songs.append((song_id, record_data))
        
        if is_ura_only:
            print(f"[Tuning] URA-Only Song '{song_id}' processed! (E/N/H nulled)")
        else:
            print(f"[Tuning] Song '{song_id}' processed to memory!")

    def cook_tuning(self):
        """
        Compiles all processed songs into the final tuning.bin file.
        Sorts the entries alphabetically by song_id to support the engine's bsearch algorithm.
        """
        if not self.songs:
            return

        print(f"\nCooking Tuning (.bin) with {len(self.songs)} songs...")
        output_dir = os.path.join("output", "sheet", "tuning", "bin")
        os.makedirs(output_dir, exist_ok=True)
        save_path = os.path.join(output_dir, "tuning.bin")

        # Header: Total song count
        new_data = bytearray(struct.pack('>I', len(self.songs)))

        # Alphabetical sort required by the game's native C++ binary search implementation
        self.songs.sort(key=lambda x: x[0])

        for song_id, record in self.songs:
            new_data.extend(record)

        # Append the global string pool at the end of the file
        new_data.extend(self.string_pool)

        with open(save_path, 'wb') as f:
            f.write(new_data)
        
        print(f"[OK] Global tuning.bin successfully sorted and generated at {save_path}!")
        print(f"    Total: {len(new_data)} bytes ({len(self.songs)} songs + string pool)")