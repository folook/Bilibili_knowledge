#!/usr/bin/env python3
"""
Bilibili字幕获取服务
基于bilibili-subtitle浏览器扩展项目的API调用方式实现的Python后端服务
"""

import argparse
import sys
import os
import re
from typing import Optional

from bilibili_subtitle_service import BilibiliSubtitleService
from config import BILIBILI_COOKIES, DEFAULT_FORMAT


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


def main() -> None:
    """主函数"""
    parser = argparse.ArgumentParser(
        description="获取Bilibili视频字幕",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python main.py "https://www.bilibili.com/video/BV1bK411W7t8"
  python main.py "https://www.bilibili.com/video/av12345"
  python main.py --list-languages "https://www.bilibili.com/video/BV1bK411W7t8"
  
配置Cookie:
  1. 复制 .env.example 为 .env
  2. 在 .env 文件中设置你的Cookie信息
  3. 或者设置环境变量 BILIBILI_COOKIES

注意: 由于B站的政策变化，现在获取字幕需要登录状态，请在配置文件中提供有效的Cookie。
        """
    )
    
    parser.add_argument(
        "url",
        help="Bilibili视频链接"
    )
    
    parser.add_argument(
        "--language", "-l",
        help="指定字幕语言 (例如: zh-CN, en, ja)，不指定则使用第一个可用字幕",
        default=None
    )
    
    parser.add_argument(
        "--list-languages",
        action="store_true",
        help="仅列出可用的字幕语言，不下载字幕内容"
    )
    
    parser.add_argument(
        "--with-timestamp",
        action="store_true",
        help="在文章格式中包含时间戳"
    )
    
    args = parser.parse_args()
    
    try:
        # 检查Cookie配置
        if not BILIBILI_COOKIES:
            print("⚠️  警告: 未配置Cookie，可能无法获取字幕内容")
            print("   请在 .env 文件中配置Cookie或设置环境变量")
            print("   参考 .env.example 文件了解配置方法")
            print()
        
        service = BilibiliSubtitleService()
        
        # 获取视频信息和字幕列表
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
            print("❌ 该视频没有可用的字幕", file=sys.stderr)
            if not BILIBILI_COOKIES:
                print("   这可能是因为未配置有效的Cookie导致的", file=sys.stderr)
                print("   请在 .env 文件中配置Cookie", file=sys.stderr)
            sys.exit(1)
        
        print("✅ 可用的字幕语言:")
        for i, subtitle in enumerate(subtitle_list, 1):
            print(f"  {i}. {subtitle['lan']}: {subtitle['lan_doc']}")
        print()
        
        # 如果只是列出语言
        if args.list_languages:
            return
        
        # 选择字幕语言
        selected_subtitle: Optional[dict] = None
        if args.language:
            for subtitle in subtitle_list:
                if subtitle['lan'] == args.language:
                    selected_subtitle = subtitle
                    break
            if not selected_subtitle:
                print(f"❌ 未找到指定语言的字幕: {args.language}", file=sys.stderr)
                print("可用的字幕语言:")
                for subtitle in subtitle_list:
                    print(f"  - {subtitle['lan']}: {subtitle['lan_doc']}")
                sys.exit(1)
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
            print("   提示: 这可能是因为未配置有效的Cookie导致的", file=sys.stderr)
            print("   请在 .env 文件中配置Cookie", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()