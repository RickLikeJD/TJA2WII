import subprocess
import os
import struct

class AudioCooker:
    def __init__(self, audiofile):
        self.audiofile = audiofile

    def align_offset(self, offset, alignment):
        remainder = offset % alignment
        if remainder == 0:
            return offset
        return offset + (alignment - remainder)

    def CookWAV(self, InFile, SongID):
        print(f"Converting {SongID} audio to WAV.")
        ffmpeg_path = os.path.abspath("src/Audio/bin/ffmpeg.exe")

        # Garante que a pasta temp existe
        OutFile = os.path.abspath(f"temp/SONG_{SongID.upper()}.wav")

        subprocess.run([
            ffmpeg_path,
            '-y', # Sobrescreve se o arquivo já existir
            '-i', f'{InFile}', # The OGG/MP3 from .TJA
            '-ar', '32000',
            f'{OutFile}'
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Repassa o arquivo WAV gerado e a ID pra próxima etapa
        self.CookIDSP(OutFile, SongID)

    def CookIDSP(self, InFile, SongID):
        """
        Cook a Wii IDSP from a 32000 WAV
        """
        print(f"Converting {SongID} audio to IDSP.")
        vgaudiocli_path = os.path.abspath("src/Audio/bin/VGAudioCli.exe")
        OutFile = os.path.abspath(f"temp/SONG_{SongID.upper()}.idsp")

        subprocess.run([
            vgaudiocli_path,
            f'{InFile}',
            f'{OutFile}'
        ])

        # Repassa o arquivo IDSP gerado e a ID pra etapa final
        self.CookNUB(OutFile, SongID)

    def CookNUB(self, idsp_file_path, SongID, file_id=0x36):
        """
        Cook an IDSP to Namco NUB FINALLY :)
        """
        print(f"Cooking {SongID} audio to NUB.")

        # Garante que a pasta de output existe
        os.makedirs("output/sound", exist_ok=True)
        output_nub_path = os.path.abspath(f"output/sound/SONG_{SongID.upper()}.nub")

        # ========================================================
        # LOAD IDSP
        # ========================================================
        with open(idsp_file_path, 'rb') as f:
            idsp_data = f.read()

        if idsp_data[:4] != b'IDSP':
            print("Invalid IDSP File...")
            return

        print("Valid IDSP File!")

        # ========================================================
        # PARSE IDSP HEADER
        # ========================================================
        channels = struct.unpack('>I', idsp_data[0x08:0x0C])[0]
        sample_rate = struct.unpack('>I', idsp_data[0x0C:0x10])[0]
        sample_count = struct.unpack('>I', idsp_data[0x10:0x14])[0]

        idsp_header_size = struct.unpack('>I', idsp_data[0x28:0x2C])[0]

        # ========================================================
        # SPLIT
        # ========================================================
        idsp_header = idsp_data[:idsp_header_size]
        idsp_stream = idsp_data[idsp_header_size:]

        # ========================================================
        # ALIGN STREAM
        # ========================================================
        aligned_stream_size = self.align_offset(len(idsp_stream), 0x20)

        if aligned_stream_size != len(idsp_stream):
            idsp_stream += (b'\x00' * (aligned_stream_size - len(idsp_stream)))

        stream_size = len(idsp_stream)

        # ========================================================
        # MAIN HEADER
        # ========================================================
        version = 0x00020100
        total_subsongs = 1
        main_header_size = 0x20
        toc_size = 0x04

        tone_header_start = self.align_offset(main_header_size + toc_size, 0x10)

        # ========================================================
        # CONFIG BLOCK (Original Namco)
        # ========================================================
        taiko_config_block = bytes.fromhex(
            "FF FF FF FF C0 80 00 00 C2 C6 00 00 00 00 00 00"
            "00 00 00 00 42 70 00 00 3F 80 00 00 00 00 00 00"
            "00 00 00 00 00 00 00 00 3F 80 00 00 3F 80 00 00"
            "00 00 00 01 00 00 00 00 00 00 00 00 C2 C8 00 00"
            "00 00 03 E8 00 00 00 64 00 00 00 00 00 00 00 01"
            "00 00 00 00 00 00 00 00 00 00 00 00 3F 80 00 00"
            "00 00 00 14 00 00 00 00 00 00 00 00 00 00 00 00"
            "00 00 00 00 00 00 00 00 3F 80 00 00 00 00 00 09"
            "00 00 00 00 00 00 00 00 00 00 00 00"
        )

        tone_header_size = self.align_offset(0x30 + len(taiko_config_block) + idsp_header_size, 0x10)
        header_end = tone_header_start + tone_header_size

        data_start = self.align_offset(header_end, 0x800)
        data_end = data_start + stream_size
        relative_audio_offset = data_start - tone_header_start

        # ========================================================
        # WRITE FILE
        # ========================================================
        with open(output_nub_path, 'wb') as out:
            # MAIN HEADER
            out.write(struct.pack('>I', version))
            out.write(struct.pack('>I', 0))
            out.write(struct.pack('>I', file_id))
            out.write(struct.pack('>I', total_subsongs))
            out.write(struct.pack('>I', data_start))
            out.write(struct.pack('>I', stream_size))
            out.write(struct.pack('>I', main_header_size))
            out.write(struct.pack('>I', tone_header_start))

            # TOC
            out.write(struct.pack('>I', tone_header_start))

            # ALIGN
            out.write(b'\x00' * (tone_header_start - out.tell()))

            # TONE HEADER
            out.write(b'idsp')
            out.write(struct.pack('>I', file_id))
            out.write(struct.pack('>I', 0))
            out.write(struct.pack('>I', 0x06)) # codec
            out.write(struct.pack('>I', 0))
            out.write(struct.pack('>I', stream_size))
            out.write(struct.pack('>I', 0)) # CORREÇÃO 2: Evita desync de pause
            out.write(struct.pack('>I', idsp_header_size))
            out.write(b'\x00' * 16) # reserved

            # NAMCO CONFIG
            out.write(taiko_config_block)

            # ORIGINAL IDSP HEADER
            out.write(idsp_header)

            # ALIGN HEADER
            out.write(b'\x00' * (header_end - out.tell()))

            # ALIGN TO 0x800
            out.write(b'\x00' * (data_start - out.tell()))

            # AUDIO STREAM
            out.write(idsp_stream)
