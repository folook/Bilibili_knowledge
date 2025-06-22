#!/usr/bin/env python3
"""
Web界面服务
提供简单的前端界面来使用Bilibili字幕获取功能
"""

import os
import json
from flask import Flask, render_template, request, jsonify, send_file
from bilibili_subtitle_service import BilibiliSubtitleService
from config import BILIBILI_COOKIES
import zipfile
import tempfile
from datetime import datetime
from typing import List, Dict, Optional

app = Flask(__name__)

def sanitize_filename(filename: str) -> str:
    """清理文件名，移除不合法字符"""
    import re
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    filename = filename.strip('. ')
    return filename or 'untitled'

def save_content(video_title: str, content_type: str, content: str) -> str:
    """保存内容到指定目录"""
    safe_title = sanitize_filename(video_title)
    save_dir = os.path.join('docs', safe_title)
    os.makedirs(save_dir, exist_ok=True)
    
    extension = 'txt' if content_type == 'article' else content_type
    filename = f"{content_type}.{extension}"
    file_path = os.path.join(save_dir, filename)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return file_path

def extract_video_id_from_url(video_title: str) -> Optional[str]:
    """从保存的文件中提取视频ID"""
    safe_title = sanitize_filename(video_title)
    video_dir = os.path.join('docs', safe_title)
    
    if not os.path.exists(video_dir):
        return None
    
    # 查找可能包含视频信息的文件
    try:
        for file in os.listdir(video_dir):
            if file.endswith('.txt') or file.endswith('.srt'):
                file_path = os.path.join(video_dir, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # 尝试从内容中提取BV号或其他视频标识
                        import re
                        bv_match = re.search(r'BV[a-zA-Z0-9]+', content)
                        if bv_match:
                            return f"https://www.bilibili.com/video/{bv_match.group()}"
                except:
                    continue
    except OSError:
        pass
    
    return None

@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')

@app.route('/api/videos')
def get_video_list():
    """获取docs文件夹中的视频列表"""
    try:
        docs_dir = 'docs'
        if not os.path.exists(docs_dir):
            return jsonify({'success': True, 'videos': []})
        
        videos = []
        for item in os.listdir(docs_dir):
            item_path = os.path.join(docs_dir, item)
            if os.path.isdir(item_path):
                # 检查文件夹中是否有文章或字幕文件
                has_article = os.path.exists(os.path.join(item_path, 'article.txt'))
                has_subtitle = os.path.exists(os.path.join(item_path, 'srt.srt'))
                
                if has_article or has_subtitle:
                    # 尝试获取视频链接
                    video_url = extract_video_id_from_url(item)
                    
                    videos.append({
                        'title': item,
                        'has_article': has_article,
                        'has_subtitle': has_subtitle,
                        'video_url': video_url
                    })
        
        return jsonify({'success': True, 'videos': videos})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/video_content/<video_title>/<content_type>')
def get_video_content(video_title: str, content_type: str):
    """获取指定视频的内容"""
    try:
        safe_title = sanitize_filename(video_title)
        video_dir = os.path.join('docs', safe_title)
        
        if not os.path.exists(video_dir):
            return jsonify({'success': False, 'error': '视频文件夹不存在'})
        
        filename = 'article.txt' if content_type == 'article' else 'srt.srt'
        file_path = os.path.join(video_dir, filename)
        
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'error': f'{content_type}文件不存在'})
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return jsonify({
            'success': True,
            'content': content,
            'content_type': content_type,
            'video_title': video_title
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/process', methods=['POST'])
def process_video():
    """处理视频字幕获取请求"""
    try:
        data = request.get_json()
        url = data.get('url', '').strip()
        with_timestamp = data.get('with_timestamp', False)
        
        if not url:
            return jsonify({'success': False, 'error': '请输入有效的视频链接'})
        
        # 检查Cookie配置
        if not BILIBILI_COOKIES:
            return jsonify({
                'success': False, 
                'error': '未配置Cookie，请在.env文件中配置BILIBILI_COOKIES'
            })
        
        service = BilibiliSubtitleService()
        
        # 获取视频信息
        video_info = service.get_video_info(url)
        
        # 获取字幕列表
        subtitle_list = service.get_subtitle_list(video_info['aid'], video_info['cid'])
        
        if not subtitle_list:
            return jsonify({
                'success': False,
                'error': '该视频没有可用的字幕'
            })
        
        # 使用第一个可用字幕
        selected_subtitle = subtitle_list[0]
        
        # 获取字幕内容
        subtitle_content = service.get_subtitle_content(selected_subtitle['subtitle_url'])
        
        # 生成两种格式
        srt_content = service.format_subtitle(subtitle_content, "srt")
        article_content = service.format_as_article(subtitle_content, with_timestamp)
        
        # 在字幕内容中添加视频链接信息（用于后续提取）
        srt_content_with_url = f"# Video URL: {url}\n{srt_content}"
        article_content_with_url = f"# Video URL: {url}\n# Video Title: {video_info['title']}\n\n{article_content}"
        
        # 保存文件
        srt_path = save_content(video_info['title'], 'srt', srt_content_with_url)
        article_path = save_content(video_info['title'], 'article', article_content_with_url)
        
        return jsonify({
            'success': True,
            'video_info': {
                'title': video_info['title'],
                'author': video_info['author'],
                'aid': video_info['aid']
            },
            'subtitle_info': {
                'language': selected_subtitle['lan_doc'],
                'subtitle_count': len(subtitle_content.get('body', [])),
                'article_length': len(article_content)
            },
            'files': {
                'srt_path': srt_path,
                'article_path': article_path
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/download/<path:filename>')
def download_file(filename):
    """下载文件"""
    try:
        file_path = os.path.join(os.getcwd(), filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return jsonify({'error': '文件不存在'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download_all/<video_title>')
def download_all_files(video_title):
    """下载所有文件（打包为ZIP）"""
    try:
        safe_title = sanitize_filename(video_title)
        video_dir = os.path.join('docs', safe_title)
        
        if not os.path.exists(video_dir):
            return jsonify({'error': '文件夹不存在'}), 404
        
        # 创建临时ZIP文件
        temp_dir = tempfile.gettempdir()
        zip_filename = f"{safe_title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        zip_path = os.path.join(temp_dir, zip_filename)
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(video_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, video_dir)
                    zipf.write(file_path, arcname)
        
        return send_file(zip_path, as_attachment=True, download_name=zip_filename)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete/<video_title>', methods=['DELETE'])
def delete_video(video_title: str):
    """删除指定视频的字幕文件"""
    try:
        safe_title = sanitize_filename(video_title)
        video_dir = os.path.join('docs', safe_title)
        
        if not os.path.exists(video_dir):
            return jsonify({'success': False, 'error': '视频文件夹不存在'})
        
        # 删除整个文件夹
        import shutil
        shutil.rmtree(video_dir)
        
        return jsonify({
            'success': True,
            'message': f'已成功删除视频"{video_title}"的所有文件'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    # 确保docs目录存在
    os.makedirs('docs', exist_ok=True)
    
    # 确保templates目录存在
    os.makedirs('templates', exist_ok=True)
    
    print("🚀 启动Web界面服务...")
    print("📱 访问地址: http://localhost:8080")
    print("⚠️  请确保已配置Cookie信息")
    
    app.run(debug=True, host='0.0.0.0', port=8080) 