# downloader.py

import yt_dlp
import os
import re


def get_video_formats(url):
    """
    解析视频链接，获取所有可用的视频清晰度信息。
    :param url: 视频链接
    :return: 包含所有清晰度选项的列表和视频元数据
    """
    try:
        ydl_opts = {}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # download=False 仅解析信息，不下载
            info = ydl.extract_info(url, download=False)
            formats = info.get('formats', [])

            resolutions = set()
            for f in formats:
                # 只获取视频流的清晰度
                if f.get('height') and f.get('vcodec') != 'none':
                    resolutions.add(f'{f["height"]}p')

            # 对清晰度进行排序
            sorted_resolutions = sorted([r for r in resolutions if r != 'audio'],
                                        key=lambda x: int(x.strip('p')),
                                        reverse=True)

            title = info.get('title', '未知标题')
            duration = info.get('duration', 0)

            return sorted_resolutions, title, duration

    except Exception as e:
        print("解析视频失败，错误信息：", e)
        return [], None, None


def download_video(url, output_path, resolution, audio_only, progress_hook):
    """
    下载视频或音频。
    :param url: 视频链接
    :param output_path: 保存文件的路径
    :param resolution: 下载的视频分辨率，例如 '1080p'
    :param audio_only: 是否只下载音频
    :param progress_hook: 进度回调函数
    """
    try:
        # 基础配置
        ydl_opts = {
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
            'progress_hooks': [progress_hook],
            'retries': 5,  # 增加自动重试次数
        }

        # 音频或视频下载配置
        if audio_only:
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
            ydl_opts['outtmpl'] = os.path.join(output_path, '%(title)s.mp3')
        else:
            ydl_opts['format'] = f'bestvideo[height<=?{resolution}]+bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4'
            }]

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        print(f"下载成功！文件已保存到: {output_path}")
        return True
    except Exception as e:
        print("下载失败，错误信息：", e)
        return False