import os, shutil, re, json
import questionary
import time
from src.Audio.AudioCooker import AudioCooker
from src.Lyrics.LyricCooker import LyricCooker
from src.Sheet.SheetCooker import SheetCooker
from src.Texture.TextureCooker import TextureCooker
from src.MusicInfo.MusicInfoCooker import MusicInfoCooker, GENRES, DANCERS
from src.Tuning.TuningCooker import TuningCooker
from src.MusicInfo.FumenSyncCooker import FumenSyncCooker
from src.Config.config import get_songs_folder

def sanitize_song_id(raw_id):
    """
    Removes special characters and enforces the 6-character limit.
    Preserves the 'ex_' prefix if present (allowing up to 9 characters total).
    Example: 'bang-bang' -> 'bangba' | 'ex_bang-bang' -> 'ex_bangba'
    """
    raw_id = raw_id.lower().strip()

    if raw_id.startswith("ex_"):
        base = raw_id[3:]
        base_clean = re.sub(r'[^a-z0-9]', '', base)[:6]
        return f"ex_{base_clean}"
    else:
        return re.sub(r'[^a-z0-9]', '', raw_id)[:6]

def main():
    songs_folder = get_songs_folder()

    if not os.path.exists(songs_folder):
        print(f"The folder '{songs_folder}' not found.")
        return

    # Inicia as Sessões Globais!
    info_cooker = MusicInfoCooker()
    tuning_cooker = TuningCooker()
    sync_cooker = FumenSyncCooker()
    texture_cooker = TextureCooker()

    session_file = "session.json"
    session_data = []

    # =========================================================
    # 💾 SISTEMA DE LOAD STATE (Continuar Sessão Anterior)
    # =========================================================
    if os.path.exists(session_file):
        load_session = questionary.confirm("Found a previous modding session! Do you want to load it and continue adding songs?").ask()
        if load_session:
            with open(session_file, "r", encoding="utf-8") as f:
                session_data = json.load(f)
            
            # Repopula a memória dos Cookers com as músicas antigas
            for s in session_data:
                info_cooker.add_song(s['id'], s['title'], s['preview'], s['genre'], s['lyrics'], s['dancer'])
                tuning_cooker.add_song(s['id'], s['title'], s['bpm'], s['stars'])
                sync_cooker.add_song(s['id'], s['offset'])
                texture_cooker.add_song(s['title'], s['artist'], s['id'])
            
            print(f"\n[Session Manager] Successfully loaded {len(session_data)} previous songs into memory!\n")
        else:
            clear_session = questionary.confirm("Do you want to delete the previous session and start fresh?").ask()
            if clear_session:
                os.remove(session_file)
                print("[Session Manager] Previous session cleared.\n")

    while True:
        options_menu = []
        songs_directory = {}

        print("\nLoading TJA Files...")
        time.sleep(0.5)

        for item in os.listdir(songs_folder):
            item_path = os.path.join(songs_folder, item)

            if os.path.isdir(item_path):
                tja_files = [f for f in os.listdir(item_path) if f.endswith('.tja')]

                if tja_files:
                    tja_path = os.path.join(item_path, tja_files[0])

                    song_title = "Unknown Title"
                    song_artist = ""
                    song_title_ja = ""
                    song_artist_ja = ""
                    song_wave = ""
                    song_demostart = 15000
                    song_bpm = 120
                    song_stars = [1, 3, 5, 7, 0] 
                    song_offset = 0.0

                    current_course = None

                    for encoding in ['utf-8', 'shift_jis', 'latin-1']:
                        try:
                            with open(tja_path, 'r', encoding=encoding) as file:
                                for line in file:
                                    line_lower = line.strip().lower()

                                    if line_lower.startswith("title:"):
                                        song_title = line.split(":", 1)[1].strip()
                                    elif line_lower.startswith("subtitle:"):
                                        raw_artist = line.split(":", 1)[1].strip()
                                        if raw_artist.startswith("--"):
                                            song_artist = raw_artist[2:].strip()
                                        else:
                                            song_artist = raw_artist

                                    elif line_lower.startswith("titleja:"):
                                        song_title_ja = line.split(":", 1)[1].strip()
                                    elif line_lower.startswith("subtitleja:"):
                                        raw_artist = line.split(":", 1)[1].strip()
                                        if raw_artist.startswith("--"):
                                            song_artist_ja = raw_artist[2:].strip()
                                        else:
                                            song_artist_ja = raw_artist

                                    elif line_lower.startswith("wave:"):
                                        song_wave = line.split(":", 1)[1].strip()

                                    elif line_lower.startswith("offset:"):
                                        try:
                                            song_offset = float(line_lower.split("offset:")[1].strip())
                                        except ValueError:
                                            pass

                                    elif line_lower.startswith("demostart:"):
                                        try:
                                            raw_val = line_lower.split("demostart:")[1].strip()
                                            val = float(raw_val)
                                            if val > 2000:
                                                song_demostart = int(val)
                                            else:
                                                song_demostart = int(val * 1000)
                                        except ValueError:
                                            pass
                                    elif line_lower.startswith("bpm:"):
                                        try:
                                            song_bpm = int(float(line_lower.split("bpm:")[1].strip()))
                                        except ValueError:
                                            pass
                                    elif line_lower.startswith("course:"):
                                        current_course = line_lower.split("course:")[1].strip()
                                    elif line_lower.startswith("level:"):
                                        try:
                                            level = int(line_lower.split("level:")[1].strip())
                                            if current_course in ["easy", "0"]:
                                                song_stars[0] = level
                                            elif current_course in ["normal", "1"]:
                                                song_stars[1] = level
                                            elif current_course in ["hard", "2"]:
                                                song_stars[2] = level
                                            elif current_course in ["oni", "3"]:
                                                song_stars[3] = level
                                            elif current_course in ["edit", "ura", "4", "x"]:
                                                song_stars[4] = level
                                        except ValueError:
                                            pass

                            if song_title != "Unknown Title":
                                break
                        except UnicodeDecodeError:
                            continue

                    if song_title_ja:
                        song_title = song_title_ja
                    if song_artist_ja:
                        song_artist = song_artist_ja

                    if song_artist:
                        display_text = f"{song_title} ({song_artist}) [{item}]"
                    else:
                        display_text = f"{song_title}  [{item}]"

                    options_menu.append(display_text)

                    songs_directory[display_text] = {
                        "folder": item_path,
                        "wave": song_wave,
                        "tja_path": tja_path,
                        "title": song_title,
                        "artist": song_artist,
                        "demostart": song_demostart,
                        "bpm": song_bpm,
                        "stars": song_stars,
                        "offset": song_offset
                    }

        if not options_menu:
            print("No one .tja file found on the folders.")
            break

        print(f"Loaded successfully {len(options_menu)} songs!")

        # ---------------------------------------------------------
        # MENU PAGINATION SYSTEM
        # ---------------------------------------------------------
        PAGE_SIZE = 15
        current_page = 0
        total_pages = (len(options_menu) - 1) // PAGE_SIZE + 1
        selected_option = None

        while True:
            start_idx = current_page * PAGE_SIZE
            end_idx = start_idx + PAGE_SIZE
            page_choices = options_menu[start_idx:end_idx]

            choices_with_nav = []

            if current_page > 0:
                choices_with_nav.append("<-  Previous Page")

            choices_with_nav.extend(page_choices)

            if current_page < total_pages - 1:
                choices_with_nav.append("->  Next Page")

            choices_with_nav.append("[X] Cancel")

            menu_title = f"Which song do you want to process to Taiko Wii 5? (Page {current_page + 1}/{total_pages})"

            selected = questionary.select(
                menu_title,
                choices=choices_with_nav
            ).ask()

            if selected == "->  Next Page":
                current_page += 1
            elif selected == "<-  Previous Page":
                current_page -= 1
            elif selected == "[X] Cancel" or not selected:
                selected_option = None
                break
            else:
                selected_option = selected
                break

        if not selected_option:
            print("Operation canceled.")
            break
        # ---------------------------------------------------------

        selected_data = songs_directory[selected_option]
        selected_folder = selected_data["folder"]
        expected_wave = selected_data["wave"]
        real_tja_path = selected_data["tja_path"]

        real_title = selected_data["title"]
        real_artist = selected_data["artist"]
        real_preview_ms = selected_data["demostart"]
        real_bpm = selected_data["bpm"]
        real_stars = selected_data["stars"]
        real_offset = selected_data["offset"]

        print(f"\nYou selected: {selected_option}")
        print(f"Loaded: {selected_folder} successfully\n")

        id_choice = questionary.confirm("Do you want to put a custom ID for your song?").ask()

        if id_choice:
            raw_id = questionary.text("Song Id (Base Max 6 Chars):").ask()
            song_id = sanitize_song_id(raw_id)
        else:
            folder_name = os.path.basename(selected_folder)
            song_id = sanitize_song_id(folder_name)

        print(f"\nDefined Song ID: {song_id}")

        genre_choice = questionary.select("Select Genre:", choices=list(GENRES.values())).ask()
        genre_id = int(genre_choice.split(" - ")[0])

        dancer_choice = questionary.select("Select Dancer / Theme:", choices=list(DANCERS.values())).ask()
        dancer_id = int(dancer_choice.split(" - ")[0])

        has_lyrics = questionary.confirm("Does this song have lyrics (Vocal)?").ask()

        convert_to_kana = False
        if has_lyrics:
            convert_to_kana = questionary.confirm("Are these lyrics in Romaji? Convert them to Japanese Kana?").ask()

        audio_path = None
        if expected_wave:
            temp_path = os.path.join(selected_folder, expected_wave)
            if os.path.exists(temp_path):
                audio_path = temp_path
                print(f"Audio found exactly from TJA: {expected_wave}")
            else:
                print(f"Warning: The file '{expected_wave}' specified in TJA doesn't exist.")

        if not audio_path:
            print("Searching for any available audio file...")
            audio_files = [f for f in os.listdir(selected_folder) if f.lower().endswith(('.ogg', '.mp3', '.wav'))]
            if not audio_files:
                print(f"Error: No audio file (.ogg, .mp3, .wav) found in {selected_folder}!")
                continue

            audio_path = os.path.join(selected_folder, audio_files[0])
            print(f"Fallback audio selected: {audio_files[0]}")

        # --- COOKING ---
        os.makedirs("temp", exist_ok=True)

        audio_cooker = AudioCooker(audio_path)
        audio_cooker.CookWAV(audio_path, song_id)
        shutil.rmtree("temp")

        sheet_cooker = SheetCooker(real_tja_path, song_id)
        lyric_cooker = LyricCooker(song_id, convert_romaji=convert_to_kana)

        if has_lyrics:
            lyric_source = questionary.select(
                "Where are the lyrics coming from?",
                choices=["1 - External .lrc file", "2 - TJA File (#LYRIC tags)"]
            ).ask()

            if "External" in lyric_source:
                lrc_files = [f for f in os.listdir(selected_folder) if f.endswith('.lrc')]
                if lrc_files:
                    lrc_path = os.path.join(selected_folder, lrc_files[0])
                    print(f"LRC found: {lrc_files[0]}")
                    lyric_cooker.parse_lrc(lrc_path, real_offset)
                else:
                    print("[Warning] No .lrc file found in the folder! Skipping lyrics...")
            else:
                sheet_cooker.lyric_cooker = lyric_cooker

        sheet_cooker.cook_all_sheets()

        if has_lyrics:
            if not lyric_cooker.lyrics:
                print("[Aviso] Nenhuma letra foi encontrada no LRC ou TJA. Binario nao gerado.")
            else:
                lyric_cooker.cook_lyrics(use_lz11=True)

        texture_cooker.add_song(real_title, real_artist, song_id)
        info_cooker.add_song(song_id, real_title, real_preview_ms, genre_id, has_lyrics, dancer_id)
        tuning_cooker.add_song(song_id, real_title, real_bpm, real_stars)
        sync_cooker.add_song(song_id, real_offset)

        # =========================================================
        # 💾 SALVANDO O STATE DA SESSÃO ATUAL
        # =========================================================
        song_dict = {
            'id': song_id,
            'title': real_title,
            'artist': real_artist,
            'preview': real_preview_ms,
            'genre': genre_id,
            'lyrics': has_lyrics,
            'dancer': dancer_id,
            'bpm': real_bpm,
            'stars': real_stars,
            'offset': real_offset
        }
        session_data.append(song_dict)
        
        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(session_data, f, ensure_ascii=False, indent=4)

        add_more = questionary.confirm("\nDo you want to process another song and add it to this mod session?").ask()
        if not add_more:
            break

    print("\n--- Modding session finished. ---")
    info_cooker.cook_musicinfo()
    tuning_cooker.cook_tuning()
    sync_cooker.cook_sync()
    texture_cooker.cook_all_textures()

if __name__ == "__main__":
    main()