#!/usr/bin/env python3
"""
测试脚本
用于测试BilibiliSubtitleService的各个功能
"""

from bilibili_subtitle_service import BilibiliSubtitleService


def test_extract_video_id():
    """测试视频ID提取功能"""
    service = BilibiliSubtitleService()
    
    test_cases = [
        ("https://www.bilibili.com/video/BV1bK411W7t8", {'type': 'bvid', 'id': 'BV1bK411W7t8'}),
        ("https://www.bilibili.com/video/av12345", {'type': 'aid', 'id': 12345}),
        ("https://www.bilibili.com/list/watchlater?bvid=BV1bK411W7t8&oid=123", {'type': 'bvid', 'id': 'BV1bK411W7t8'}),
    ]
    
    print("测试视频ID提取功能:")
    for url, expected in test_cases:
        try:
            result = service.extract_video_id(url)
            status = "✅" if result == expected else "❌"
            print(f"  {status} {url} -> {result}")
        except Exception as e:
            print(f"  ❌ {url} -> 错误: {e}")
    print()


def test_time_conversion():
    """测试时间转换功能"""
    service = BilibiliSubtitleService()
    
    test_cases = [
        (0, "00:00:00,000", "00:00"),
        (61.5, "00:01:01,500", "01:01"),
        (3661.123, "01:01:01,123", "61:01"),
    ]
    
    print("测试时间转换功能:")
    for seconds, expected_srt, expected_readable in test_cases:
        srt_result = service._seconds_to_srt_time(seconds)
        readable_result = service._seconds_to_readable_time(seconds)
        
        srt_status = "✅" if srt_result == expected_srt else "❌"
        readable_status = "✅" if readable_result == expected_readable else "❌"
        
        print(f"  {srt_status} {seconds}s -> SRT: {srt_result} (期望: {expected_srt})")
        print(f"  {readable_status} {seconds}s -> 可读: {readable_result} (期望: {expected_readable})")
    print()


def test_real_video():
    """测试真实视频（需要网络连接）"""
    service = BilibiliSubtitleService()
    
    # 使用一个知名的有字幕的视频进行测试
    test_url = "https://www.bilibili.com/video/BV1GJ411x7h7"  # 这是一个经典的测试视频
    
    print(f"测试真实视频: {test_url}")
    try:
        # 获取视频信息
        video_info = service.get_video_info(test_url)
        print(f"  ✅ 视频标题: {video_info['title']}")
        print(f"  ✅ 视频作者: {video_info['author']}")
        print(f"  ✅ 视频ID: {video_info['aid']}")
        
        # 获取字幕列表
        subtitle_list = service.get_subtitle_list(video_info['aid'], video_info['cid'])
        if subtitle_list:
            print(f"  ✅ 找到 {len(subtitle_list)} 个字幕:")
            for subtitle in subtitle_list:
                print(f"    - {subtitle['lan']}: {subtitle['lan_doc']}")
            
            # 获取第一个字幕的内容
            first_subtitle = subtitle_list[0]
            subtitle_content = service.get_subtitle_content(first_subtitle['subtitle_url'])
            
            if subtitle_content.get('body'):
                print(f"  ✅ 字幕内容获取成功，共 {len(subtitle_content['body'])} 条")
                
                # 测试格式化
                txt_format = service.format_subtitle(subtitle_content, "txt")
                srt_format = service.format_subtitle(subtitle_content, "srt")
                
                print(f"  ✅ TXT格式化成功，长度: {len(txt_format)}")
                print(f"  ✅ SRT格式化成功，长度: {len(srt_format)}")
            else:
                print("  ❌ 字幕内容为空")
        else:
            print("  ⚠️  该视频没有字幕")
            
    except Exception as e:
        print(f"  ❌ 错误: {e}")
    print()


if __name__ == "__main__":
    print("开始测试 BilibiliSubtitleService")
    print("=" * 50)
    
    test_extract_video_id()
    test_time_conversion()
    
    print("注意: 以下测试需要网络连接")
    test_real_video()
    
    print("测试完成!")