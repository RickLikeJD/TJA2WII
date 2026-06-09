import struct

class LZ11:
    """
    Global LZ11 Compressor for Taiko no Tatsujin Wii modding.
    Used to compress lyrics (.cbin), textures, and other assets.
    """

    @staticmethod
    def compress(data: bytes) -> bytes:
        result = bytearray()
        size = len(data)

        # LZ11 Header: 0x11 followed by the 24-bit uncompressed size
        result.append(0x11)
        result += struct.pack('<I', size)[:3]

        pos = 0

        while pos < size:
            flag_pos = len(result)
            result.append(0)
            flags = 0

            for i in range(8):
                if pos >= size:
                    break

                best_length = 0
                best_disp = 0
                search_start = max(0, pos - 0x1000)

                for search_pos in range(search_start, pos):
                    length = 0
                    while (
                            length < 0x10110
                            and pos + length < size
                            and data[search_pos + length] == data[pos + length]
                    ):
                        length += 1

                    if length > best_length and length >= 3:
                        best_length = length
                        best_disp = pos - search_pos - 1

                if best_length >= 3:
                    flags |= (1 << (7 - i))
                    length = best_length
                    disp = best_disp

                    # 2-byte format
                    if length <= 0x10:
                        result.append(((length - 1) << 4) | ((disp >> 8) & 0xF))
                        result.append(disp & 0xFF)
                    # 3-byte format
                    elif length <= 0x110:
                        length -= 0x11
                        result.append((length >> 4) & 0xF)
                        result.append(((length & 0xF) << 4) | ((disp >> 8) & 0xF))
                        result.append(disp & 0xFF)
                    # 4-byte format
                    else:
                        length -= 0x111
                        result.append((1 << 4) | ((length >> 12) & 0xF))
                        result.append((length >> 4) & 0xFF)
                        result.append(((length & 0xF) << 4) | ((disp >> 8) & 0xF))
                        result.append(disp & 0xFF)

                    pos += best_length
                else:
                    result.append(data[pos])
                    pos += 1

            result[flag_pos] = flags

        return bytes(result)