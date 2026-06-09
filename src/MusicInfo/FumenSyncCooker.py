import os
import struct

class FumenSyncCooker:
    """
    Generates the fumensync.bin file.
    Forces the frame offset to 0, as the actual #OFFSET is now baked directly
    into the Fumen files natively by the SheetCooker.
    """
    def __init__(self):
        self.songs = []

    def add_song(self, song_id, offset_seconds=0.0):
        # Ignoramos o offset_seconds recebido do main.py para evitar duplo offset in-game
        macro_str = f"SONG_{song_id.upper()}"

        self.songs.append({
            'macro': macro_str,
            'frames': 0
        })
        print(f"[Sync] Song '{song_id}' added to FumenSync.")

    def cook_sync(self):
        if not self.songs:
            return

        print(f"\nCooking FumenSync (.bin) with {len(self.songs)} songs...")
        output_dir = os.path.join("output", "sheet", "musicinfo", "bin")
        os.makedirs(output_dir, exist_ok=True)
        save_path = os.path.join(output_dir, "fumensync.bin")

        with open(save_path, 'wb') as f:
            for song in self.songs:
                b_macro = song['macro'].encode('ascii')[:27]

                block = struct.pack('>28s i', b_macro, song['frames'])
                f.write(block)

        print(f"[OK] fumensync.bin generated on {save_path}!")