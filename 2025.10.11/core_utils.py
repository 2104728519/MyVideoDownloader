# core_utils.py

import os
import sys
import json
import base64
import zlib
from PIL import Image
import struct

def get_base_path():
    """获取应用的基础路径，兼容打包和开发环境。"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))

APP_DIR = get_base_path()
CARD_WORKSPACE = os.path.join(APP_DIR, "Character_Cards")
BOOK_WORKSPACE = os.path.join(APP_DIR, "World_Books")
CONFIG_FILE = os.path.join(APP_DIR, "config.json")

def _read_png_chunks(file_path):
    """手动从PNG文件流中读取所有块，不依赖Pillow。"""
    with open(file_path, 'rb') as f:
        png_signature = f.read(8)
        if png_signature != b'\x89PNG\r\n\x1a\n':
            raise ValueError("文件不是一个有效的PNG。")

        while True:
            chunk_length_bytes = f.read(4)
            if not chunk_length_bytes:
                break
            chunk_length = struct.unpack('>I', chunk_length_bytes)[0]
            chunk_type = f.read(4)
            chunk_data = f.read(chunk_length)
            f.read(4)  # CRC校验码

            yield chunk_type, chunk_data

            if chunk_type == b'IEND':
                break

def extract_character_data_from_png(file_path):
    """从PNG文件中提取角色数据。"""
    try:
        chara_v2_data = None
        chara_v3_data = None

        for chunk_type, chunk_data in _read_png_chunks(file_path):
            keyword = None
            decoded_text = None

            if chunk_type == b'tEXt':
                if b'\x00' in chunk_data:
                    keyword_bytes, text_bytes = chunk_data.split(b'\x00', 1)
                    keyword = keyword_bytes.decode('latin-1').lower()
                    if keyword in ['chara', 'ccv3']:
                        try:
                            decoded_text = base64.b64decode(text_bytes).decode('utf-8')
                        except Exception:
                            continue

            elif chunk_type == b'zTXt':
                if b'\x00' in chunk_data:
                    keyword_bytes, compressed_part = chunk_data.split(b'\x00', 1)
                    keyword = keyword_bytes.decode('latin-1').lower()
                    if keyword in ['chara', 'ccv3'] and compressed_part[0] == 0:
                        try:
                            decompressed = zlib.decompress(compressed_part[1:])
                            decoded_text = base64.b64decode(decompressed).decode('utf-8')
                        except Exception:
                            continue

            if decoded_text:
                if keyword == 'chara':
                    chara_v2_data = decoded_text
                elif keyword == 'ccv3':
                    chara_v3_data = decoded_text

        if chara_v3_data:
            return json.loads(chara_v3_data), "TavernAI V3"
        if chara_v2_data:
            return json.loads(chara_v2_data), "TavernAI V2"

        with Image.open(file_path) as img:
            img.load()
            info = img.info or {}

            if 'chara' in info:
                try:
                    data = json.loads(info['chara'])
                    if 'data' not in data:
                        v2_data = {
                            'name': data.get('name', ''), 'description': data.get('description', ''),
                            'personality': data.get('personality', ''), 'scenario': data.get('scenario', ''),
                            'first_mes': data.get('first_mes', ''), 'mes_example': data.get('mes_example', ''),
                            'data': data
                        }
                        return v2_data, "NovelAI V1"
                    return data, "NovelAI V1"
                except (json.JSONDecodeError, TypeError):
                    pass

            if 'parameters' in info:
                try:
                    sd_text = info['parameters']
                    name_guess = sd_text.split(',')[0].strip()
                    data = {
                        'name': f"[SD] {name_guess[:30]}...",
                        'description': f"这是一个包含Stable Diffusion生成参数的图片。\n\n--- Parameters ---\n{sd_text}",
                        'personality': '', 'scenario': '', 'first_mes': '', 'mes_example': '',
                        'data': {'is_sd_card': True, 'parameters': sd_text}
                    }
                    return data, "Stable Diffusion"
                except Exception:
                    pass

    except (IOError, ValueError):
        return None, "Invalid Image"
    except Exception:
        pass

    return None, None

def write_character_data_to_png(file_path, character_data):
    """将角色数据写入PNG文件。"""
    try:
        if character_data.get('data', {}).get('is_sd_card'):
            return False, "Stable Diffusion 卡片是只读的，不支持修改保存。"

        v2_json_str = json.dumps(character_data, ensure_ascii=False)
        v2_b64_str = base64.b64encode(v2_json_str.encode('utf-8'))
        v2_chunk_content = b'chara\x00' + v2_b64_str

        with open(file_path, 'rb') as f_in:
            original_data = f_in.read()

        if not original_data.startswith(b'\x89PNG\r\n\x1a\n'):
            raise ValueError("Invalid PNG")

        new_png_data = bytearray(b'\x89PNG\r\n\x1a\n')
        offset = 8

        while offset < len(original_data):
            length = struct.unpack('>I', original_data[offset:offset + 4])[0]
            chunk_type = original_data[offset + 4:offset + 8]

            if chunk_type == b'IEND':
                iend_chunk = original_data[offset: offset + 12 + length]
                break

            is_char_chunk = False
            if chunk_type in [b'tEXt', b'zTXt']:
                if b'\x00' in original_data[offset + 8:offset + 8 + length]:
                    keyword = original_data[offset + 8:offset + 8 + length].split(b'\x00', 1)[0]
                    if keyword.lower() in [b'chara', b'ccv3']:
                        is_char_chunk = True

            if not is_char_chunk:
                new_png_data.extend(original_data[offset: offset + 12 + length])

            offset += 12 + length

        chunk_type = b'tEXt'
        new_png_data.extend(struct.pack('>I', len(v2_chunk_content)))
        new_png_data.extend(chunk_type)
        new_png_data.extend(v2_chunk_content)
        new_png_data.extend(struct.pack('>I', zlib.crc32(chunk_type + v2_chunk_content)))

        new_png_data.extend(iend_chunk)

        with open(file_path, 'wb') as f_out:
            f_out.write(new_png_data)

        return True, "保存成功！"
    except Exception as e:
        return False, f"保存失败: {e}"