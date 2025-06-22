#!/usr/bin/env python3
"""
Bilibili字幕获取工具示例
"""

import sys
import os
import re
import argparse
from config import BILIBILI_COOKIES


def sanitize_filename(filename: str) -> str:
    """清理文件名，移除不合法字符"""
    # 替换Windows和Unix系统都不支持的文件名字符
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # 移除前后的空格和点
    filename = filename.strip('. ')
    # 如果文件名为空，返回默认名称
    return filename or 'untitled'


def save_content(video_title: str, content_type: str, content: str) -> str:
    """保存内容到指定目录
    
    Args:
        video_title: 视频标题
        content_type: 内容类型 ('srt' 或 'article')
        content: 要保存的内容
        
    Returns:
        str: 保存的文件路径
    """
    # 清理视频标题作为目录名
    safe_title = sanitize_filename(video_title)
    
    # 创建保存目录
    save_dir = os.path.join('docs', safe_title)
    os.makedirs(save_dir, exist_ok=True)
    
    # 确定文件名
    extension = 'txt' if content_type == 'article' else content_type
    filename = f"{content_type}.{extension}"
    file_path = os.path.join(save_dir, filename)
    
    # 保存文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return file_path


def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='获取Bilibili视频字幕')
    parser.add_argument('url', help='视频URL')
    parser.add_argument('-l', '--list-languages', action='store_true', help='只列出可用的字幕语言')
    parser.add_argument('--lang', dest='language', help='指定字幕语言代码(例如: zh-CN)')
    parser.add_argument('--with-timestamp', action='store_true', help='在文章格式中包含时间戳')
    args = parser.parse_args()
    
    try:
        from bilibili_subtitle_service import BilibiliSubtitleService
        service = BilibiliSubtitleService()
        
        # 获取视频信息
        print(f"🔍 正在获取视频信息: {args.url}")
        video_info = service.get_video_info(args.url)
        print(f"📺 视频标题: {video_info['title']}")
        print(f"👤 视频作者: {video_info['author']}")
        print(f"🆔 视频ID: {video_info['aid']}")
        print()
        
        # 获取字幕列表
        print("📋 正在获取字幕列表...")
        subtitle_list = service.get_subtitle_list(video_info['aid'], video_info['cid'])
        
        if not subtitle_list:
            print("❌ 该视频没有可用的字幕")
            return
        
        print("✅ 可用的字幕语言:")
        for i, subtitle in enumerate(subtitle_list, 1):
            print(f"  {i}. {subtitle['lan']}: {subtitle['lan_doc']}")
        print()
        
        # 如果只是列出语言
        if args.list_languages:
            return
        
        # 选择字幕语言
        selected_subtitle = None
        if args.language:
            for subtitle in subtitle_list:
                if subtitle['lan'] == args.language:
                    selected_subtitle = subtitle
                    break
            if not selected_subtitle:
                print(f"❌ 未找到指定语言的字幕: {args.language}")
                print("可用的字幕语言:")
                for subtitle in subtitle_list:
                    print(f"  - {subtitle['lan']}: {subtitle['lan_doc']}")
                return
        else:
            selected_subtitle = subtitle_list[0]
        
        print(f"📥 正在获取字幕内容: {selected_subtitle['lan_doc']}")
        
        # 获取字幕内容
        subtitle_content = service.get_subtitle_content(selected_subtitle['subtitle_url'])
        
        print("🔄 正在处理字幕格式...")
        
        # 始终获取并保存SRT格式和文章格式
        srt_content = service.format_subtitle(subtitle_content, "srt")
        article_content = service.format_as_article(subtitle_content, args.with_timestamp)
        
        print("💾 正在保存文件...")
        
        # 保存文件
        srt_path = save_content(video_info['title'], 'srt', srt_content)
        article_path = save_content(video_info['title'], 'article', article_content)
        
        print("\n✅ 文件已成功保存:")
        print(f"📝 SRT字幕文件: {srt_path}")
        print(f"📖 文章格式文件: {article_path}")
        
        # 显示统计信息
        srt_lines = len(srt_content.split('\n\n'))
        article_chars = len(article_content)
        print(f"\n📊 处理统计:")
        print(f"   字幕条数: {srt_lines}")
        print(f"   文章字数: {article_chars}")
        
        print("\n🎉 处理完成！")
        
    except Exception as e:
        print(f"❌ 错误: {e}", file=sys.stderr)
        if "获取字幕列表失败" in str(e) and not BILIBILI_COOKIES:
            print("\n💡 可能的解决方案:")
            print("1. 检查Cookie是否有效（可能已过期）")
            print("2. 重新获取Cookie并更新 .env 文件")
            print("3. 确保Cookie包含SESSDATA和bili_jct字段")


if __name__ == '__main__':
    main()