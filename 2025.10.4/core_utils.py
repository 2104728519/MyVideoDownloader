# core_utils.py

import os
import sys
import json
import base64
import zlib
from PIL import Image
import struct  # 引入 struct 模块用于解析二进制数据


# --- 路径定义 ---
def get_base_path():
    """获取应用的基础路径，兼容打包和开发环境。"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


APP_DIR = get_base_path()
CARD_WORKSPACE = os.path.join(APP_DIR, "Character_Cards")
BOOK_WORKSPACE = os.path.join(APP_DIR, "World_Books")
CONFIG_FILE = os.path.join(APP_DIR, "config.json")


# --- 全新的、可靠的PNG块读取器 ---
def _read_png_chunks(file_path):
    """
    手动从PNG文件流中读取所有块，不依赖Pillow。
    这是一个生成器，会逐个yield (chunk_type, chunk_data)。
    """
    with open(file_path, 'rb') as f:
        # 验证PNG文件头
        png_signature = f.read(8)
        if png_signature != b'\x89PNG\r\n\x1a\n':
            raise ValueError("文件不是一个有效的PNG。")

        while True:
            # 读取块长度 (4 bytes, big-endian)
            chunk_length_bytes = f.read(4)
            if not chunk_length_bytes:
                break
            chunk_length = struct.unpack('>I', chunk_length_bytes)[0]

            # 读取块类型 (4 bytes)
            chunk_type = f.read(4)

            # 读取块数据
            chunk_data = f.read(chunk_length)

            # 读取CRC校验码 (4 bytes)，我们读取它只是为了让文件指针前进
            f.read(4)

            yield chunk_type, chunk_data

            # 如果是文件结束块，则停止
            if chunk_type == b'IEND':
                break


# --- 多格式角色卡读取函数 (最终版) ---
def extract_character_data_from_png(file_path):
    """
    尝试用多种已知标准从PNG文件中提取角色数据。
    返回一个元组: (数据字典, 格式类型字符串) 或 (None, None)
    """
    try:
        # --- 方案1: 手动二进制块扫描 (最可靠，支持V2/V3和zTXt) ---
        chara_v2_data = None
        chara_v3_data = None

        for chunk_type, chunk_data in _read_png_chunks(file_path):
            keyword = None
            decoded_text = None

            # --- 处理 tEXt 块 (未压缩) ---
            if chunk_type == b'tEXt':
                if b'\x00' in chunk_data:
                    keyword_bytes, text_bytes = chunk_data.split(b'\x00', 1)
                    keyword = keyword_bytes.decode('latin-1').lower()
                    if keyword in ['chara', 'ccv3']:
                        try:
                            decoded_text = base64.b64decode(text_bytes).decode('utf-8')
                        except Exception:
                            continue  # Base64解码失败，跳过

            # --- 处理 zTXt 块 (压缩) ---
            elif chunk_type == b'zTXt':
                if b'\x00' in chunk_data:
                    keyword_bytes, compressed_part = chunk_data.split(b'\x00', 1)
                    keyword = keyword_bytes.decode('latin-1').lower()
                    # zTXt 块的压缩部分包含一个字节的压缩方法，我们跳过它
                    if keyword in ['chara', 'ccv3'] and compressed_part[0] == 0:
                        try:
                            decompressed = zlib.decompress(compressed_part[1:])
                            decoded_text = base64.b64decode(decompressed).decode('utf-8')
                        except Exception:
                            continue  # 解压或解码失败，跳过

            if decoded_text:
                if keyword == 'chara':
                    chara_v2_data = decoded_text
                elif keyword == 'ccv3':
                    chara_v3_data = decoded_text

        # --- 优先返回 V3 数据 ---
        if chara_v3_data:
            return json.loads(chara_v3_data), "TavernAI V3"
        if chara_v2_data:
            return json.loads(chara_v2_data), "TavernAI V2"

        # --- 方案2: 如果手动扫描失败，回退到Pillow的info字典 (兼容旧格式) ---
        with Image.open(file_path) as img:
            img.load()
            info = img.info or {}

            # 尝试 NovelAI / V1 格式
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

            # 尝试 Stable Diffusion WebUI 格式
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
        # 对于无法打开的图片或非PNG文件
        return None, "Invalid Image"
    except Exception:
        # 捕捉所有其他可能的解析错误
        pass

    # 如果所有尝试都失败了
    return None, None


# --- 写入函数 (已优化) ---
def write_character_data_to_png(file_path, character_data):
    """将角色数据写入PNG文件，会跳过只读卡片。"""
    try:
        if character_data.get('data', {}).get('is_sd_card'):
            return False, "Stable Diffusion 卡片是只读的，不支持修改保存。"

        # --- 准备 V2 数据 ---
        v2_json_str = json.dumps(character_data, ensure_ascii=False)
        v2_b64_str = base64.b64encode(v2_json_str.encode('utf-8'))
        v2_chunk_content = b'chara\x00' + v2_b64_str

        # 读取原始数据并移除旧的角色块
        with open(file_path, 'rb') as f_in:
            original_data = f_in.read()

        if not original_data.startswith(b'\x89PNG\r\n\x1a\n'):
            raise ValueError("Invalid PNG")

        # 使用新的、可靠的方式重构PNG
        new_png_data = bytearray(b'\x89PNG\r\n\x1a\n')
        offset = 8

        while offset < len(original_data):
            length = struct.unpack('>I', original_data[offset:offset + 4])[0]
            chunk_type = original_data[offset + 4:offset + 8]

            # 如果是结束块，先缓存它，最后再写入
            if chunk_type == b'IEND':
                iend_chunk = original_data[offset: offset + 12 + length]
                break

            # 检查是否是我们的角色数据块，如果是则跳过，实现删除
            is_char_chunk = False
            if chunk_type in [b'tEXt', b'zTXt']:
                if b'\x00' in original_data[offset + 8:offset + 8 + length]:
                    keyword = original_data[offset + 8:offset + 8 + length].split(b'\x00', 1)[0]
                    if keyword.lower() in [b'chara', b'ccv3']:
                        is_char_chunk = True

            if not is_char_chunk:
                new_png_data.extend(original_data[offset: offset + 12 + length])

            offset += 12 + length

        # --- 在IEND之前插入新的V2数据块 ---
        chunk_type = b'tEXt'
        new_png_data.extend(struct.pack('>I', len(v2_chunk_content)))
        new_png_data.extend(chunk_type)
        new_png_data.extend(v2_chunk_content)
        new_png_data.extend(struct.pack('>I', zlib.crc32(chunk_type + v2_chunk_content)))

        # 写入结束块
        new_png_data.extend(iend_chunk)

        with open(file_path, 'wb') as f_out:
            f_out.write(new_png_data)

        return True, "保存成功！"
    except Exception as e:
        return False, f"保存失败: {e}"