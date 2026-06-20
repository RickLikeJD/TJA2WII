import os
import struct

VERSIONS = {
    3: "Taiko Wii: Minna no Party Sandaime",
    4: "Taiko Wii: Keitebban",
    5: "Taiko Wii: Chogouka-Ban"
}

# Slot representations: e = Easy (Kantan), n = Normal (Futsuu), h = Hard (Muzukashii), m = Oni (Mania)
SLOT_LABELS = ["e", "n", "h", "m"]

# Base score values per difficulty
SCORE_PER_DIFF = [6000, 7000, 7000, 8000, 8000]

# Extraído do dump original do Wii 3: Janelas de Acerto e Incrementos da Soul Gauge
# Sem isso, o motor das engines antigas (Wii 1 ao 4) oculta as estrelas!
DIFF_CONSTANTS = [
    # 0 = Easy
    {0x0C: 1050, 0x10: 450, 0x18: 2, 0x1C: 6, 0x20: 7, 0x30: 219, 0x34: 164, 0x38: -110 & 0xFFFFFFFF},
    # 1 = Normal
    {0x0C: 1260, 0x10: 380, 0x18: 2, 0x1C: 6, 0x20: 7, 0x30: 128, 0x34: 96,  0x38: -96 & 0xFFFFFFFF},
    # 2 = Hard
    {0x0C: 800,  0x10: 210, 0x18: 1, 0x1C: 4, 0x20: 6, 0x30: 61,  0x34: 46,  0x38: -76 & 0xFFFFFFFF},
    # 3 = Oni / Ura
    {0x0C: 860,  0x10: 210, 0x18: 1, 0x1C: 4, 0x20: 6, 0x30: 47,  0x34: 24,  0x38: -76 & 0xFFFFFFFF}
]

class TuningCooker:
    def __init__(self, target_version="wii5"):
        self.target_version = target_version.lower()
        self.songs_metadata = []

        # ==========================================
        # 🎮 PERFIS DE HARDWARE / ENGINE
        # ==========================================
        if self.target_version == "wii3":
            self.FUMEN_SIZE = 120
            self.PAD_SIZE = 600
            self.USE_INLINE_STRINGS = True
            self.INJECT_DIFF_CONSTANTS = True # Crucial para Wii 3

        elif self.target_version in ["wii4", "wii5"]:
            self.FUMEN_SIZE = 124
            self.PAD_SIZE = 620
            self.USE_INLINE_STRINGS = False
            self.INJECT_DIFF_CONSTANTS = False # Wii 5 ignora/calcula na engine
        else:
            raise ValueError(f"Versão de target não suportada: {self.target_version}")

        # Os offsets base são idênticos em todos os jogos!
        # A diferença é apenas o limite de bytes no final (120 vs 124).
        self.FUMEN_CONST_FIELDS = {
            0x24: 4,      0x28: 16,     0x2c: 0,      0x3c: 10000,
            0x44: 65536,  0x48: 65536,  0x4c: 65536,  0x50: 20,
            0x54: 10,     0x58: 0,      0x5c: 1,      0x60: 20,
            0x64: 10,     0x68: 1,      0x6c: 30,     0x70: 30,
            0x74: 0,
        }

    def add_song(self, song_id, jpname, bpm, stars_list):
        self.songs_metadata.append({
            "id": song_id,
            "jpname": jpname,
            "bpm": bpm,
            "stars": stars_list
        })
        is_ura_only = song_id.startswith("ex_")
        if is_ura_only:
            print(f"[Tuning] URA-Only Song '{song_id}' scheduled! (E/N/H will be nulled)")
        else:
            print(f"[Tuning] Song '{song_id}' scheduled for compilation!")

    def _build_fumen(self, ptr, stars, bpm, diff_index):
        raw = bytearray(self.FUMEN_SIZE)

        # 1. Variáveis Dinâmicas
        struct.pack_into(">I", raw, 0x00, ptr)
        struct.pack_into(">I", raw, 0x04, int(stars))
        struct.pack_into(">I", raw, 0x08, int(bpm))
        struct.pack_into(">I", raw, 0x40, SCORE_PER_DIFF[diff_index])

        # 2. Constantes Obrigatórias da Engine Antiga (Hit Windows / Gauge)
        if self.INJECT_DIFF_CONSTANTS:
            diff_data = DIFF_CONSTANTS[min(diff_index, 3)] # Ura usa os stats do Oni
            for off, val in diff_data.items():
                struct.pack_into(">I", raw, off, val)

        # 3. Constantes de Base da Memória (Idêntico para todos os Wiis)
        for off, val in self.FUMEN_CONST_FIELDS.items():
            if off < self.FUMEN_SIZE: # Previne overflow no Wii 3
                struct.pack_into(">I", raw, off, val)

        return raw

    def cook_tuning(self):
        if not self.songs_metadata:
            return

        print(f"\nCooking Tuning (.bin) for {self.target_version.upper()} with {len(self.songs_metadata)} songs...")
        output_dir = os.path.join("output", "sheet", "tuning", "bin")
        os.makedirs(output_dir, exist_ok=True)
        save_path = os.path.join(output_dir, "tuning.bin")

        self.songs_metadata.sort(key=lambda x: x["id"])

        final_binary = bytearray()
        final_binary.extend(struct.pack('>I', len(self.songs_metadata)))

        if self.USE_INLINE_STRINGS:
            # Wii 3: Strings Inline (Ponteiros 0-indexed por música)
            for song in self.songs_metadata:
                song_id = song["id"]
                jpname = song["jpname"]

                inline_pool = bytearray()
                inline_dict = {}

                def get_inline_ptr(text, is_utf=False):
                    if not text: return 0xFFFFFFFF
                    if text in inline_dict: return inline_dict[text]

                    # O pulo do gato: Retorna SOMENTE o tamanho atual da pool (Ponteiro Relativo!)
                    offset = len(inline_pool)
                    encoding = 'utf-8' if is_utf else 'ascii'
                    inline_pool.extend(text.encode(encoding, errors='replace') + b'\x00')
                    inline_dict[text] = offset
                    return offset

                record_data = bytearray()
                p_id = get_inline_ptr(song_id)
                p_mu = get_inline_ptr(f"music_{song_id}")
                p_jp = get_inline_ptr(jpname, is_utf=True)

                record_data.extend(struct.pack('>3I', p_id, p_mu, p_jp))
                is_ura = song_id.startswith("ex_")

                for player in ["1p", "2p"]:
                    for slot_idx, label in enumerate(SLOT_LABELS):
                        if is_ura and label in ["e", "n", "h"]:
                            record_data.extend(b'\xff' * self.FUMEN_SIZE)
                        else:
                            star_idx = 4 if (is_ura and label == "m" and len(song["stars"]) > 4) else slot_idx
                            stars = song["stars"][star_idx]
                            ptr = get_inline_ptr(f"{song_id}{player}_{label}")
                            chart_data = self._build_fumen(ptr, stars, song["bpm"], slot_idx)
                            record_data.extend(chart_data)
                    record_data.extend(b'\xff' * self.PAD_SIZE)

                record_data.extend(inline_pool)
                final_binary.extend(record_data)

        else:
            # Wii 5: Global Pool (Ponteiros 0-indexed para toda a pool)
            global_pool = bytearray()
            global_dict = {}

            def get_global_ptr(text, is_utf=False):
                if not text: return 0xFFFFFFFF
                if text in global_dict: return global_dict[text]

                # O pulo do gato: Retorna SOMENTE o tamanho atual da pool global (Ponteiro Relativo!)
                offset = len(global_pool)
                encoding = 'utf-8' if is_utf else 'ascii'
                global_pool.extend(text.encode(encoding, errors='replace') + b'\x00')
                global_dict[text] = offset
                return offset

            for song in self.songs_metadata:
                song_id = song["id"]
                jpname = song["jpname"]
                is_ura = song_id.startswith("ex_")

                record_data = bytearray()
                p_id = get_global_ptr(song_id)
                p_mu = get_global_ptr(f"music_{song_id}")
                p_jp = get_global_ptr(jpname, is_utf=True)
                record_data.extend(struct.pack('>3I', p_id, p_mu, p_jp))

                for player in ["1p", "2p"]:
                    for slot_idx, label in enumerate(SLOT_LABELS):
                        if is_ura and label in ["e", "n", "h"]:
                            record_data.extend(b'\xff' * self.FUMEN_SIZE)
                        else:
                            star_idx = 4 if (is_ura and label == "m" and len(song["stars"]) > 4) else slot_idx
                            stars = song["stars"][star_idx]
                            ptr = get_global_ptr(f"{song_id}{player}_{label}")
                            chart_data = self._build_fumen(ptr, stars, song["bpm"], slot_idx)
                            record_data.extend(chart_data)
                    record_data.extend(b'\xff' * self.PAD_SIZE)

                final_binary.extend(record_data)
            final_binary.extend(global_pool)

        with open(save_path, 'wb') as f:
            f.write(final_binary)

        print(f"[OK] Global tuning.bin successfully generated at {save_path}!")
        print(f"    Total: {len(final_binary)} bytes ({len(self.songs_metadata)} songs processed)")