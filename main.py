# main.py

import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from downloader import download_video, get_video_formats
from history_manager import load_history, save_history
import re
import os
import threading
from tkinter.scrolledtext import ScrolledText

# 全局变量来保存视频信息
video_title = None
video_duration = None


def format_duration(seconds):
    """将秒数转换为 '分:秒' 格式"""
    if seconds is None:
        return "00:00"
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes:02d}:{seconds:02d}"


def extract_url(text):
    """从一段文字中提取出 URL"""
    url_pattern = re.compile(r'https?://[^\s]+')
    match = url_pattern.search(text)
    if match:
        return match.group(0)
    return None


def update_progress(d):
    """
    根据下载进度更新进度条和状态标签
    :param d: 包含下载状态信息的字典
    """
    if d['status'] == 'downloading':
        status_bar_label.config(text="正在下载...")
        progress_percentage_str = d.get('_percent_str')
        if progress_percentage_str:
            cleaned_progress_str = re.sub(r'[^\d.]', '', progress_percentage_str)
            try:
                progress_value = float(cleaned_progress_str)
                progress_bar['value'] = progress_value
                status_label.config(text=f"进度: {progress_percentage_str}")
            except ValueError:
                pass
    elif d['status'] == 'finished':
        status_bar_label.config(text="下载完成！")
        progress_bar['value'] = 100
        status_label.config(text="进度: 100%")
    elif d['status'] == 'error':
        status_bar_label.config(text="下载出错！")

    root.update_idletasks()


def parse_video():
    """解析视频链接并填充清晰度下拉菜单"""
    global video_title, video_duration

    user_input = url_entry.get()
    url = extract_url(user_input)

    if not url:
        status_label.config(text="请粘贴有效的视频链接！", fg="red")
        return

    status_label.config(text="正在解析视频...", fg="blue")
    root.update()

    formats, title, duration = get_video_formats(url)

    if not formats:
        status_label.config(text="解析失败，请检查链接或网络！", fg="red")
        video_title = None
        video_duration = None
    else:
        resolution_combobox['values'] = formats
        resolution_combobox.set(formats[0])
        status_label.config(text="解析完成，请选择清晰度！", fg="green")

        video_title = title
        video_duration = duration

    url_entry.delete(0, tk.END)
    url_entry.insert(0, url)


def start_download_thread():
    """在独立的线程中执行下载，避免界面卡死"""
    download_thread = threading.Thread(target=start_download)
    download_thread.start()


def start_download():
    """从界面获取信息并开始下载"""
    global video_title, video_duration

    url = url_entry.get()
    output_path = output_path_var.get()
    selected_res = resolution_combobox.get()
    audio_only = audio_only_var.get()

    if not url or not output_path or not selected_res:
        status_label.config(text="请先解析视频并选择清晰度及保存路径！", fg="red")
        return

    resolution = selected_res.strip('p') if not audio_only else ''

    status_bar_label.config(text="开始下载...")
    progress_bar.pack(pady=5)
    progress_bar['value'] = 0
    status_label.config(text="进度: 0%")
    root.update()

    success = download_video(url, output_path, resolution, audio_only, update_progress)

    progress_bar.pack_forget()

    if success:
        status_label.config(text="下载完成！", fg="green")
        if video_title and video_duration is not None:
            save_history(video_title, video_duration, url)
    else:
        if not audio_only:
            answer = messagebox.askyesno(
                "下载失败",
                f"当前清晰度 {selected_res} 下载失败，是否尝试下载低一级的清晰度？"
            )
            if answer:
                current_values = list(resolution_combobox['values'])
                current_index = current_values.index(selected_res)
                if current_index + 1 < len(current_values):
                    next_res = current_values[current_index + 1]
                    resolution_combobox.set(next_res)
                    start_download()
                else:
                    status_label.config(text="没有更低清晰度可选了。", fg="red")
            else:
                status_label.config(text="下载已取消。", fg="red")
        else:
            status_label.config(text="音频下载失败。", fg="red")


def select_folder():
    """打开文件夹选择对话框并更新路径显示"""
    folder_path = filedialog.askdirectory()
    if folder_path:
        output_path_var.set(folder_path)


def show_history_window():
    """创建并显示历史下载记录的新窗口"""
    history_window = tk.Toplevel(root)
    history_window.title("历史下载记录")
    history_window.geometry("600x400")

    tk.Label(history_window, text="历史下载记录", font=("Arial", 14, "bold")).pack(pady=10)

    history_text = ScrolledText(history_window, wrap=tk.WORD, state=tk.DISABLED)
    history_text.pack(expand=True, fill="both", padx=10, pady=10)

    history_data = load_history()
    history_text.config(state=tk.NORMAL)
    history_text.delete(1.0, tk.END)

    for entry in history_data:
        title = entry.get("title", "未知标题")
        duration = format_duration(entry.get("duration"))
        url = entry.get("url", "")
        formatted_entry = f"◎ {title} ({duration})\n链接: {url}\n\n"
        history_text.insert(tk.END, formatted_entry)

    history_text.config(state=tk.DISABLED)


# --- GUI 创建 ---
root = tk.Tk()
root.title("智能视频下载器")
root.geometry("500x450")
root.configure(bg="#f0f0f0")

# 链接输入框
tk.Label(root, text="视频链接:", bg="#f0f0f0").pack(pady=(10, 0))
url_entry = tk.Entry(root, width=50)
url_entry.pack(pady=5)

# 解析按钮
parse_button = tk.Button(root, text="解析视频", command=parse_video, bg="#FFA500", fg="white")
parse_button.pack(pady=5)

# 保存路径选择
tk.Label(root, text="保存路径:", bg="#f0f0f0").pack(pady=(10, 0))
output_path_var = tk.StringVar(root, os.getcwd())
output_path_label = tk.Label(root, textvariable=output_path_var, bg="white", width=40, relief="sunken")
output_path_label.pack(pady=5)
tk.Button(root, text="选择文件夹", command=select_folder).pack(pady=5)

# 清晰度选择
tk.Label(root, text="清晰度:", bg="#f0f0f0").pack(pady=(10, 0))
resolution_combobox = ttk.Combobox(root)
resolution_combobox.pack(pady=5)
resolution_combobox.set("请先解析视频")

# 音频复选框和历史记录按钮
audio_only_var = tk.BooleanVar()
button_frame = tk.Frame(root, bg="#f0f0f0")
button_frame.pack(pady=5)
tk.Checkbutton(button_frame, text="只下载音频", variable=audio_only_var, bg="#f0f0f0").pack(side=tk.LEFT, padx=(0, 20))
tk.Button(button_frame, text="历史下载", command=show_history_window).pack(side=tk.RIGHT)

# 下载按钮
tk.Button(root, text="开始下载", command=start_download_thread, bg="#4CAF50", fg="white").pack(pady=10)

# 进度条
status_bar_label = tk.Label(root, text="", bg="#f0f0f0", font=("Arial", 10, "bold"))
status_bar_label.pack(pady=(5, 0))
progress_bar = ttk.Progressbar(root, orient="horizontal", mode="determinate", length=400)
progress_bar.pack(pady=5)
progress_bar.pack_forget()

# 状态标签
status_label = tk.Label(root, text="", bg="#f0f0f0")
status_label.pack(pady=5)

# 启动主循环
root.mainloop()