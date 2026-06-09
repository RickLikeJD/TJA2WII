import os
import struct
import csv
import shutil
import sys
from collections import defaultdict
import re

# ===========================================================================
# CONSTANTS TJA -> WII5 (BIG ENDIAN)
# ===========================================================================
TJA_TO_WII5 = {
    '1': 0x1,   # Small Don
    '2': 0x4,   # Small Ka
    '3': 0x7,   # BIG DON
    '4': 0x8,   # BIG KA
    '5': 0x6,   # Small Drumroll
    '6': 0x9,   # BIG DRUMROLL
    '7': 0xa,   # Balloon
    '9': 0xc,   # Kusudama
    'A': 0xb,   # DON 2 hands
    'B': 0xd,   # KA 2 hands
}
LONG_NOTE_TYPES = {'5', '6', '7', '9'}
BALLOON_IDS     = {0xa, 0xc}
DRUMROLL_IDS    = {0x6, 0x9, 0x62}

# '>' forces Big Endian packing
ORDER = '>'

STAR_TO_KEY = {
    'Oni':    {1:'17',2:'17',3:'17',4:'17',5:'17',6:'17',7:'17',8:'8', 9:'910',10:'910'},
    'Hard':   {1:'12',2:'12',3:'3', 4:'4', 5:'58',6:'58',7:'58',8:'58',9:'58',10:'58'},
    'Normal': {1:'12',2:'12',3:'3', 4:'4', 5:'57',6:'57',7:'57',8:'57',9:'57',10:'57'},
    'Easy':   {1:'1', 2:'23',3:'23',4:'45',5:'45',6:'45',7:'45',8:'45',9:'45',10:'45'},
}

HP_CLEAR = {'Easy': 6000, 'Normal': 7000, 'Hard': 7000, 'Oni': 8000, 'Ura': 8000}

TIMING_WINDOWS = {
    'Easy':   (41.7083358764648,  108.441665649414, 125.125),
    'Normal': (41.7083358764648,  108.441665649414, 125.125),
    'Hard':   (25.0250015258789,  75.075004577637,  108.441665649414),
    'Oni':    (25.0250015258789,  75.075004577637,  108.441665649414),
    'Ura':    (25.0250015258789,  75.075004577637,  108.441665649414),
}

COURSE_NORMALIZE = {
    'easy':'Easy','normal':'Normal','hard':'Hard',
    'oni':'Oni','ura':'Ura','edit':'Ura',
    '0':'Easy','1':'Normal','2':'Hard','3':'Oni','4':'Ura',
}

# ===========================================================================
# MAIN CLASS
# ===========================================================================
class SheetCooker:
    def __init__(self, tja_path, song_id):
        self.tja_path = tja_path
        self.song_id = song_id.lower()
        self.tja_content = ""
        self.courses_found = []

        self.suffix_map = {
            'easy': 'e',  '0': 'e',
            'normal': 'n','1': 'n',
            'hard': 'h',  '2': 'h',
            'oni': 'm',   '3': 'm',
            'ura': 'x',   '4': 'x',
            'edit': 'x'
        }

        # Load the TJA file immune to invisible EOF characters (\x1A)
        for enc in ('utf-8-sig', 'shift-jis', 'latin-1'):
            try:
                with open(self.tja_path, 'rb') as f:
                    self.tja_content = f.read().decode(enc)
                break
            except Exception:
                continue

        seen = set()
        for line in self.tja_content.split('\n'):
            l = line.split('//')[0].strip()
            if re.match(r'^COURSE\s*:', l, re.IGNORECASE):
                raw = re.split(r':', l, maxsplit=1)[1]
                course_val = self.normalize_course(raw)
                if course_val in self.suffix_map and course_val not in seen:
                    self.courses_found.append(course_val)
                    seen.add(course_val)

    def normalize_course(self, s: str):
        return (
            s.split('//')[0]
            .replace('"', '')
            .replace("'", '')
            .strip()
            .lower()
        )

    def _find_hp_csv(self) -> str:
        try:
            base = os.path.dirname(os.path.abspath(__file__))
        except NameError:
            base = os.path.dirname(os.path.abspath(sys.argv[0]))

        candidate = os.path.join(base, 'hp_values.csv')
        if os.path.exists(candidate):
            return candidate
        return os.path.join(os.getcwd(), 'hp_values.csv')

    def get_hp_values(self, n_notes: int, difficulty: str, stars: int):
        diff = 'Oni' if difficulty in ('Ura', 'Edit') else difficulty
        if diff not in STAR_TO_KEY or not (0 < n_notes <= 2500):
            return 10, 5, -20
        key_suffix = STAR_TO_KEY[diff].get(stars, '17')
        col_key = f"{diff}-{key_suffix}"

        hp_csv_path = self._find_hp_csv()
        if not os.path.exists(hp_csv_path):
            return 10, 5, -20

        try:
            with open(hp_csv_path, newline='', encoding='utf-8') as f:
                for i, row in enumerate(csv.DictReader(f)):
                    if i + 1 == n_notes:
                        return (int(row[f"good_{col_key}"]), int(row[f"ok_{col_key}"]), int(row[f"bad_{col_key}"]))
        except Exception:
            pass
        return 10, 5, -20

    def fix_dk_note_types(self, notes_data: list, song_bpm: float):
        DON_TYPES = {0x1, 0x2, 0x3}
        KA_TYPES  = {0x4, 0x5}
        BIG_TYPES = {0x7, 0x8, 0xb, 0xd}

        dk = [n for n in notes_data if n['type'] in DON_TYPES | KA_TYPES]
        if not dk: return

        dk.sort(key=lambda n: n['abs_time_ms'])

        for i in range(len(dk) - 1):
            dk[i]['_diff'] = int(dk[i+1]['abs_time_ms'] - dk[i]['abs_time_ms'])
        dk[-1]['_diff'] = 999999

        measure_dur = (4 * 60000) / song_bpm
        quarter_dur = int(measure_dur / 4)
        eighth_dur  = int(measure_dur / 8)

        diffs_unique = sorted({n['_diff'] for n in dk})
        diffs_under_q = [d for d in diffs_unique if d < quarter_dur]
        diffs_under_8 = [d for d in diffs_under_q if d < eighth_dur]
        diffs_8th     = [d for d in diffs_under_q if d >= eighth_dur]

        diffs_to_cluster = [[d] for d in diffs_8th]
        if diffs_under_8: diffs_to_cluster.insert(0, diffs_under_8)

        def cluster(items, diff_vals):
            result, cur = [], []
            for item in items:
                if isinstance(item, list):
                    if cur: result.append(cur); cur = []
                    result.append(item)
                else:
                    if item['_diff'] in diff_vals: cur.append(item)
                    else:
                        if cur: cur.append(item); result.append(cur); cur = []
                        else: result.append(item)
            if cur: result.append(cur)
            return result

        semi = list(dk)
        for dv in diffs_to_cluster: semi = cluster(semi, dv)

        clustered = [c if isinstance(c, list) else [c] for c in semi]

        for cl in clustered:
            for n in cl:
                if n['type'] not in BIG_TYPES:
                    if n['type'] in DON_TYPES: n['type'] = 0x2
                    elif n['type'] in KA_TYPES: n['type'] = 0x5

            all_dons = all(n['type'] in {0x2, 0x3} for n in cl)
            if all_dons and len(cl) % 2 == 1:
                for i, n in enumerate(cl):
                    if i % 2 == 1 and n['type'] not in BIG_TYPES:
                        n['type'] = 0x3

            is_fast4 = (len(cl) == 4 and all(n.get('_diff', 999999) < eighth_dur for n in cl[:-1]))
            if not is_fast4:
                last = cl[-1]
                if last['type'] == 0x2: last['type'] = 0x1
                elif last['type'] == 0x3: last['type'] = 0x1
                elif last['type'] == 0x5: last['type'] = 0x4

    def build_header(self, n_measures: int, difficulty: str, n_notes: int, stars: int) -> bytes:
        diff = COURSE_NORMALIZE.get(difficulty.lower(), 'Oni')
        diff_hp = 'Oni' if diff in ('Ura', 'Edit') else diff
        tw = TIMING_WINDOWS.get(diff, TIMING_WINDOWS['Oni'])
        good, ok, bad = self.get_hp_values(n_notes, diff_hp, stars)
        hp_clear = HP_CLEAR.get(diff_hp, 8000)

        fmt  = ORDER + 'f'*108 + 'i'*22
        vals = list(tw) * 36 + [
            0, 10000, hp_clear, good, ok, bad, 65536, 65536, 65536,
            20, 10, 0, 1, 20, 10, 1, 30, 30, 20, 12345678, n_measures, 0,
        ]
        return struct.pack(fmt, *vals)

    def auto_calculate_scores(self, total_notes):
        if total_notes == 0: return 300, 120
        diff_sum = 0
        for i in range(1, total_notes + 1):
            multiplier = 10 if i >= 100 else i // 10
            diff_sum += multiplier
        peso_total = (4 * total_notes) + diff_sum
        if peso_total <= 0: return 300, 120
        score_diff = int(1000000 / peso_total)
        score_diff = (score_diff // 10) * 10
        if score_diff < 10: score_diff = 10
        return score_diff * 4, score_diff

    def cook_course(self, target_course: str, output_filename: str):
        lines = self.tja_content.split('\n')
        bpm_base, offset_s = 120.0, 0.0

        for line in lines:
            l = line.split('//')[0].strip().upper()
            if l.startswith('BPM:'): bpm_base = float(l.split(':',1)[1].strip())
            elif l.startswith('OFFSET:'): offset_s = float(l.split(':',1)[1].strip())

        balloon_hits = []
        in_target = False
        for line in lines:
            l = line.split('//')[0].strip()
            if l.upper().startswith('COURSE:'):
                in_target = self.normalize_course(l.split(':',1)[1]) == target_course
            elif l == '#END' and in_target:
                break
            elif l.upper().startswith('BALLOON:') and in_target:
                v = l.split(':',1)[1].strip()
                if v:
                    balloon_hits = [int(x) for x in v.split(',') if x.strip()]
                break

        level, score_init, score_diff = 5, None, None
        in_target2 = False
        for line in lines:
            l = line.split('//')[0].strip()
            if l.upper().startswith('COURSE:'):
                in_target2 = self.normalize_course(l.split(':',1)[1]) == target_course
            elif l == '#END' and in_target2:
                break
            elif in_target2:
                if l.upper().startswith('LEVEL:'):
                    try: level = int(l.split(':',1)[1].strip())
                    except: pass
                elif l.upper().startswith('SCOREINIT:'):
                    val = l.split(':',1)[1].strip()
                    if val: score_init = int(val.split(',')[0].strip())
                elif l.upper().startswith('SCOREDIFF:'):
                    val = l.split(':',1)[1].strip()
                    if val: score_diff = int(val.split(',')[0].strip())

        # =================================================================
        # NOVO MOTOR DE RENDERIZAÇÃO DE TEMPO (SLICE-BY-SLICE PRECISION)
        # =================================================================
        current_bpm, current_scroll, current_measure_beats = bpm_base, 1.0, 4.0
        is_gogo, open_long_note = False, None
        notes_data, measures_raw = [], []

        in_target_course, in_start = False, False
        measure_buf, measure_events = "", []

        # Converte o OFFSET do TJA de segundos para milissegundos absolutos (Hit Time inicial)
        abs_time_ms = (offset_s * -1 * 1000.0)

        for line in lines:
            line = line.split('//')[0].strip()
            if not line: continue

            if line.upper().startswith('COURSE:'):
                current_course = self.normalize_course(line.split(':', 1)[1])
                in_target_course = (current_course == self.normalize_course(target_course))
                continue

            if not in_target_course: continue
            if line == '#START': in_start = True; continue
            if line == '#END': break
            if not in_start: continue

            # Captura de Eventos de Header / Measure
            if line.startswith('#'):
                cmd = line.split()
                if not cmd: continue
                command = cmd[0].upper()
                ev_idx = len(measure_buf)

                if command == '#GOGOSTART': measure_events.append({'idx':ev_idx,'type':'GOGO','value':True})
                elif command == '#GOGOEND': measure_events.append({'idx':ev_idx,'type':'GOGO','value':False})
                elif command == '#BPMCHANGE': measure_events.append({'idx':ev_idx,'type':'BPM','value':float(cmd[1])})
                elif command == '#SCROLL': measure_events.append({'idx':ev_idx,'type':'SCROLL','value':float(cmd[1])})
                elif command == '#DELAY': measure_events.append({'idx':ev_idx,'type':'DELAY','value':float(cmd[1])})
                elif command == '#MEASURE':
                    parts = cmd[1].strip().split('/')
                    measure_events.append({'idx':ev_idx,'type':'MEASURE','value':float(parts[0]) * (4.0 / float(parts[1]))})

                # 👇 AQUI ESTÁ O PARSE QUE ESTAVA FALTANDO! 👇
                elif command == '#LYRIC':
                    # Pega o texto da letra ignorando o comando '#LYRIC' (mantendo maiúsculas e minúsculas)
                    lyric_text = line[len(cmd[0]):].strip()
                    measure_events.append({'idx':ev_idx,'type':'LYRIC','value':lyric_text})
                continue

            for char in line:
                if char != ',':
                    measure_buf += char
                    continue

                # Bateu na vírgula! Processa o compasso acumulado.
                measure_str = measure_buf
                slices = max(1, len(measure_str))
                note_count = len(measure_str)

                # Processa os eventos do ÍNICIO do compasso (idx == 0)
                for ev in measure_events:
                    if ev['idx'] == 0:  # ⬅️ IMPORTANTE: Isso aqui tem que ser 0, não idx!
                        if ev['type'] == 'BPM': current_bpm = ev['value']
                        elif ev['type'] == 'GOGO': is_gogo = ev['value']
                        elif ev['type'] == 'SCROLL': current_scroll = ev['value']
                        elif ev['type'] == 'MEASURE': current_measure_beats = ev['value']
                        elif ev['type'] == 'DELAY':
                            delay_val = ev['value'] * 1000.0
                            abs_time_ms += delay_val
                        # Hook da Letra
                        elif ev['type'] == 'LYRIC':
                            if hasattr(self, 'lyric_cooker') and self.lyric_cooker:
                                self.lyric_cooker.add_lyric(abs_time_ms / 1000.0, ev['value'])

                meas_bpm_h = current_bpm
                meas_scroll_h = current_scroll
                meas_gogo_h = is_gogo

                # A MÁGICA DE VERDADE: Draw Lead Time
                fumen_offset = abs_time_ms - (4.0 * 60000.0 / meas_bpm_h)

                drums_start = len(notes_data)

                slice_beats = current_measure_beats / slices
                current_time_ms = abs_time_ms
                current_measure_pos_ms = 0.0

                # Itera a malha (slice by slice) garantindo que mudanças de BPM/Delay AFETEM o tempo real
                for idx in range(slices):
                    if idx > 0:
                        for ev in measure_events:
                            if ev['idx'] == idx:
                                if ev['type'] == 'BPM': current_bpm = ev['value']
                                elif ev['type'] == 'GOGO': is_gogo = ev['value']
                                elif ev['type'] == 'SCROLL': current_scroll = ev['value']
                                elif ev['type'] == 'DELAY':
                                    delay_val = ev['value'] * 1000.0
                                    current_time_ms += delay_val
                                    current_measure_pos_ms += delay_val
                                # Hook da Letra
                                elif ev['type'] == 'LYRIC':
                                    if hasattr(self, 'lyric_cooker') and self.lyric_cooker:
                                        self.lyric_cooker.add_lyric(current_time_ms / 1000.0, ev['value'])

                    slice_ms = slice_beats * (60000.0 / current_bpm)
                    note_abs_ms = current_time_ms
                    note_pos_ms = current_measure_pos_ms

                    if note_count > 0:
                        n_char = measure_str[idx]
                        if n_char == '8':
                            if open_long_note is not None:
                                ni, start_t = open_long_note
                                notes_data[ni]['duration'] = max(1.0, note_abs_ms - start_t)
                                open_long_note = None
                        elif n_char in TJA_TO_WII5:
                            nt = TJA_TO_WII5[n_char]
                            if n_char in LONG_NOTE_TYPES and open_long_note is not None:
                                ni, start_t = open_long_note
                                notes_data[ni]['duration'] = max(1.0, note_abs_ms - start_t)

                            note = {'type': nt, 'pos': note_pos_ms, 'duration': 0.0, 'hits': 0, 'abs_time_ms': note_abs_ms}

                            if n_char in LONG_NOTE_TYPES:
                                if n_char in ('7', '9'):
                                    note['hits'] = balloon_hits.pop(0) if balloon_hits else 5
                                open_long_note = (len(notes_data), note_abs_ms)
                            notes_data.append(note)

                    # Avança o Playhead para a próxima fatia do compasso
                    current_time_ms += slice_ms
                    current_measure_pos_ms += slice_ms

                # Processa os eventos pendurados no final exato do compasso
                for ev in measure_events:
                    if ev['idx'] == note_count and note_count > 0:
                        if ev['type'] == 'BPM': current_bpm = ev['value']
                        elif ev['type'] == 'GOGO': is_gogo = ev['value']
                        elif ev['type'] == 'SCROLL': current_scroll = ev['value']
                        elif ev['type'] == 'DELAY': current_time_ms += ev['value'] * 1000.0
                        elif ev['type'] == 'MEASURE': current_measure_beats = ev['value']
                        # Hook da Letra
                        elif ev['type'] == 'LYRIC':
                            if hasattr(self, 'lyric_cooker') and self.lyric_cooker:
                                self.lyric_cooker.add_lyric(current_time_ms / 1000.0, ev['value'])

                drums_cnt = len(notes_data) - drums_start
                measures_raw.append({
                    'bpm': meas_bpm_h, 'fumen_offset': fumen_offset, 'scroll': meas_scroll_h,
                    'gogo': meas_gogo_h, 'drums_start': drums_start, 'drums_cnt': drums_cnt,
                })

                # O tempo absoluto do próximo compasso começa exatamente de onde a agulha parou
                abs_time_ms = current_time_ms
                measure_buf = ""
                measure_events = []

        # =================================================================
        # FIM DA RENDERIZAÇÃO DO COMPASSO
        # =================================================================

        if measures_raw:
            bpm_counts = defaultdict(int)
            for m in measures_raw: bpm_counts[m['bpm']] += 1
            song_bpm = max(bpm_counts, key=bpm_counts.get)
            self.fix_dk_note_types(notes_data, song_bpm)

        n_notes_total = sum(1 for n in notes_data if n['type'] not in DRUMROLL_IDS)
        if score_init is None or score_diff is None:
            score_init, score_diff = self.auto_calculate_scores(n_notes_total)

        n_measures = len(measures_raw)
        diff_norm = COURSE_NORMALIZE.get(target_course.lower(), 'Oni')
        header = self.build_header(n_measures, diff_norm, n_notes_total, level)

        chunks = [header]
        for m in measures_raw:
            mstruct = struct.pack(ORDER + 'ffBBHiiiiiii',
                                  m['bpm'], m['fumen_offset'], int(m['gogo']), 1, 0, -1, -1, -1, -1, -1, -1, 0)
            chunks.append(mstruct)

            start, end = m['drums_start'], m['drums_start'] + m['drums_cnt']
            for bi, cnt in enumerate([m['drums_cnt'], 0, 0]):
                chunks.append(struct.pack(ORDER + 'HHf', cnt, 0, m['scroll']))
                if bi == 0:
                    for nd in notes_data[start:end]:
                        nt = nd['type']
                        is_balloon, is_drumroll = nt in BALLOON_IDS, nt in DRUMROLL_IDS

                        if is_balloon: si, sd = nd['hits'] & 0xFFFF, 0
                        elif is_drumroll: si, sd = 0, 0
                        else: si, sd = score_init, score_diff

                        nstruct = struct.pack(ORDER + 'ififHHf', nt, nd['pos'], 0, 0.0, si, sd, nd['duration'])
                        chunks.append(nstruct)
                        if is_drumroll: chunks.append(b'\x00' * 8)

        with open(output_filename, 'wb') as f:
            for c in chunks: f.write(c)

    def cook_all_sheets(self):
        print(f"Cooking Fumens for {self.song_id}...")

        solo_dir = "output/sheet/newsht/solo"
        duet_dir = "output/sheet/newsht/duet"

        os.makedirs(solo_dir, exist_ok=True)
        os.makedirs(duet_dir, exist_ok=True)

        if not self.courses_found:
            print("No difficulties found in TJA!")
            return

        generated_suffixes = []
        for course in self.courses_found:
            course_clean = course.split('//')[0].strip().lower()

            if course_clean not in self.suffix_map:
                continue

            suffix = self.suffix_map[course_clean]

            # 🎵 URA ONI (Extra) LOGIC:
            if suffix == 'x':
                current_id = f"ex_{self.song_id}" if not self.song_id.startswith("ex_") else self.song_id
                file_suffix = 'm'
            else:
                current_id = self.song_id
                file_suffix = suffix

            # 🔥 O FIX DO IMPOSTOR ESTÁ AQUI:
            # Se o ID começar com "ex_", nós PROIBIMOS qualquer dificuldade que não seja o Edit original ('x').
            # Isso impede que o Oni normal ('m') sobrescreva o arquivo da Edit!
            if self.song_id.startswith("ex_") and suffix != 'x':
                continue

            solo_filename = os.path.join(solo_dir, f"{current_id}_{file_suffix}.bin")
            self.cook_course(course, solo_filename)
            generated_suffixes.append(suffix)

            shutil.copy2(solo_filename, os.path.join(duet_dir, f"{current_id}_{file_suffix}_1.bin"))
            shutil.copy2(solo_filename, os.path.join(duet_dir, f"{current_id}_{file_suffix}_2.bin"))

            print(f"[OK] Generated {course} ({file_suffix}) for ID '{current_id}': Solo + Duet")

        if not generated_suffixes:
            print("Failed to compile any difficulty! (If making an ex_ song, ensure the TJA has an 'Edit' or 'Ura' course)")
            return

        # Hierarchy for fallback (lowest to highest)
        hierarchy = ['e', 'n', 'h', 'm', 'x']

        # Sort the generated difficulties based on hierarchy to pick the highest available
        sorted_generated = sorted(generated_suffixes, key=lambda s: hierarchy.index(s))
        fallback_source = sorted_generated[-1]
        
        fallback_id = f"ex_{self.song_id}" if (fallback_source == 'x' and not self.song_id.startswith("ex_")) else self.song_id
        fallback_suffix = 'm' if fallback_source == 'x' else fallback_source

        source_bin = os.path.join(solo_dir, f"{fallback_id}_{fallback_suffix}.bin")

        if self.song_id.startswith("ex_"):
            required_suffixes = ['m']
        else:
            required_suffixes = ['e', 'n', 'h', 'm']
            
        for req in required_suffixes:
            # Se precisamos de 'm' e ele já foi gerado através da tag 'x', ignoramos o fallback
            if req == 'm' and 'x' in generated_suffixes:
                continue
                
            if req not in generated_suffixes:
                print(f"Creating placeholder '{req}' from '{fallback_suffix}' to prevent engine crash...")
                shutil.copy2(source_bin, os.path.join(solo_dir, f"{self.song_id}_{req}.bin"))
                shutil.copy2(source_bin, os.path.join(duet_dir, f"{self.song_id}_{req}_1.bin"))
                shutil.copy2(source_bin, os.path.join(duet_dir, f"{self.song_id}_{req}_2.bin"))