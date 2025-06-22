"""
Bilibili字幕获取服务
基于bilibili-subtitle浏览器扩展项目的API调用方式实现
"""

import re
import json
import requests
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urlparse, parse_qs

from config import BILIBILI_COOKIES, USER_AGENT, API_CONFIG


class BilibiliSubtitleService:
    """Bilibili字幕获取服务类"""
    
    def __init__(self, cookies: Optional[Dict[str, str]] = None):
        self.session = requests.Session()
        # 设置User-Agent以避免被识别为爬虫
        self.session.headers.update({
            'User-Agent': USER_AGENT,
            'Referer': 'https://www.bilibili.com/',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })
        
        # 设置请求超时
        self.session.timeout = API_CONFIG['timeout']
        
        # 设置cookies - 优先使用传入的cookies，否则使用配置文件中的
        cookies_to_use = cookies or BILIBILI_COOKIES
        if cookies_to_use:
            self.session.cookies.update(cookies_to_use)
        
        self.has_cookies = cookies_to_use is not None
    
    def extract_video_id(self, url: str) -> Dict[str, Any]:
        """
        从Bilibili URL中提取视频ID
        支持格式:
        - https://www.bilibili.com/video/BV1bK411W7t8
        - https://www.bilibili.com/video/av12345
        - https://www.bilibili.com/list/watchlater?bvid=BV1bK411W7t8&oid=123
        """
        parsed_url = urlparse(url)
        
        # 处理稍后再看的URL
        if '/list/watchlater' in parsed_url.path:
            query_params = parse_qs(parsed_url.query)
            if 'bvid' in query_params:
                return {'type': 'bvid', 'id': query_params['bvid'][0]}
            elif 'aid' in query_params:
                return {'type': 'aid', 'id': int(query_params['aid'][0])}
        
        # 处理普通视频URL
        path = parsed_url.path
        if path.endswith('/'):
            path = path[:-1]
        
        path_parts = path.split('/')
        video_id = path_parts[-1]
        
        if video_id.lower().startswith('av'):
            # av号格式
            aid = int(video_id[2:])
            return {'type': 'aid', 'id': aid}
        elif video_id.lower().startswith('bv'):
            # BV号格式
            return {'type': 'bvid', 'id': video_id}
        else:
            raise ValueError(f"无法识别的视频ID格式: {video_id}")
    
    def get_video_info(self, url: str) -> Dict[str, Any]:
        """获取视频基本信息"""
        video_id_info = self.extract_video_id(url)
        
        if video_id_info['type'] == 'aid':
            # 使用aid获取信息
            aid = video_id_info['id']
            api_url = f"https://api.bilibili.com/x/player/pagelist?aid={aid}"
            
            response = self.session.get(api_url)
            response.raise_for_status()
            data = response.json()
            
            if data['code'] != 0:
                raise Exception(f"获取视频信息失败: {data['message']}")
            
            pages = data['data']
            if not pages:
                raise Exception("视频信息为空")
            
            first_page = pages[0]
            return {
                'aid': aid,
                'cid': first_page['cid'],
                'title': first_page['part'],
                'author': first_page.get('owner', {}).get('name', '未知'),
                'ctime': first_page.get('ctime'),
                'pages': pages
            }
        
        else:  # bvid
            bvid = video_id_info['id']
            api_url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
            
            response = self.session.get(api_url)
            response.raise_for_status()
            data = response.json()
            
            if data['code'] != 0:
                raise Exception(f"获取视频信息失败: {data['message']}")
            
            video_data = data['data']
            return {
                'aid': video_data['aid'],
                'cid': video_data['cid'],
                'title': video_data['title'],
                'author': video_data['owner']['name'],
                'ctime': video_data['ctime'],
                'pages': video_data['pages']
            }
    
    def get_subtitle_list(self, aid: int, cid: int) -> List[Dict[str, Any]]:
        """
        获取字幕列表
        参考bilibili-subtitle扩展的实现方式
        """
        api_url = f"https://api.bilibili.com/x/player/wbi/v2?aid={aid}&cid={cid}"
        
        response = self.session.get(api_url)
        response.raise_for_status()
        data = response.json()
        
        if data['code'] != 0:
            error_msg = f"获取字幕列表失败: {data['message']}"
            if not self.has_cookies and data['code'] == -101:
                error_msg += " (可能需要登录Cookie)"
            raise Exception(error_msg)
        
        subtitle_data = data['data'].get('subtitle', {})
        subtitles = subtitle_data.get('subtitles', [])
        
        # 过滤掉没有subtitle_url的字幕（参考扩展的实现）
        valid_subtitles = [
            subtitle for subtitle in subtitles 
            if subtitle.get('subtitle_url')
        ]
        
        return valid_subtitles
    
    def get_subtitle_content(self, subtitle_url: str) -> Dict[str, Any]:
        """
        获取字幕内容
        参考bilibili-subtitle扩展的实现方式
        """
        # 确保使用HTTPS（参考扩展的实现）
        if subtitle_url.startswith('http://'):
            subtitle_url = subtitle_url.replace('http://', 'https://')
        elif subtitle_url.startswith('//'):
            subtitle_url = 'https:' + subtitle_url
        
        response = self.session.get(subtitle_url)
        response.raise_for_status()
        
        try:
            return response.json()
        except json.JSONDecodeError as e:
            raise Exception(f"解析字幕JSON失败: {e}")
    
    def format_subtitle(self, subtitle_data: Dict[str, Any], format_type: str = "txt") -> str:
        """格式化字幕输出"""
        body = subtitle_data.get('body', [])
        
        if not body:
            return "字幕内容为空"
        
        if format_type == "json":
            return json.dumps(subtitle_data, ensure_ascii=False, indent=2)
        
        elif format_type == "srt":
            # SRT格式
            srt_content = []
            for i, item in enumerate(body, 1):
                start_time = self._seconds_to_srt_time(item['from'])
                end_time = self._seconds_to_srt_time(item['to'])
                content = item['content'].strip()
                
                srt_content.append(f"{i}")
                srt_content.append(f"{start_time} --> {end_time}")
                srt_content.append(content)
                srt_content.append("")  # 空行分隔
            
            return "\n".join(srt_content)
        
        else:  # txt格式
            txt_content = []
            for item in body:
                start_time = self._seconds_to_readable_time(item['from'])
                end_time = self._seconds_to_readable_time(item['to'])
                content = item['content'].strip()
                
                txt_content.append(f"[{start_time} - {end_time}] {content}")
            
            return "\n".join(txt_content)
    
    def _seconds_to_srt_time(self, seconds: float) -> str:
        """将秒数转换为SRT时间格式 (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"
    
    def _seconds_to_readable_time(self, seconds: float) -> str:
        """将秒数转换为可读时间格式 (MM:SS)"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        
        return f"{minutes:02d}:{secs:02d}"

    def _is_sentence_end(self, text: str) -> bool:
        """判断文本是否是一个完整句子的结尾"""
        # 中文句子结尾标点
        end_punctuations = ['。', '！', '？', '…', '~', '.', '!', '?']
        return any(text.strip().endswith(p) for p in end_punctuations)

    def _add_punctuation(self, text: str) -> str:
        """为文本添加合适的标点符号"""
        if not text:
            return text
        
        text = text.strip()
        if not text:
            return text
        
        # 如果已经有标点符号，直接返回
        if self._is_sentence_end(text):
            return text
        
        # 检查是否是疑问句
        question_words = ['什么', '为什么', '怎么', '如何', '哪里', '哪个', '谁', '吗', '呢']
        if any(word in text for word in question_words):
            return text + '？'
        
        # 检查是否是感叹句
        exclamation_words = ['太', '非常', '真的', '居然', '竟然', '哇', '啊', '呀']
        if any(word in text for word in exclamation_words):
            return text + '！'
        
        # 默认添加句号
        return text + '。'

    def _merge_subtitle_segments(self, body: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """将字幕分段合并成更有意义的段落"""
        if not body:
            return []

        merged_segments = []
        current_segment = {
            'from': body[0]['from'],
            'to': body[0]['to'],
            'content': body[0]['content'].strip(),
        }

        for item in body[1:]:
            current_text = current_segment['content']
            next_text = item['content'].strip()
            time_gap = item['from'] - current_segment['to']

            # 判断是否需要合并
            # 1. 如果当前文本不是完整句子结尾
            # 2. 如果时间间隔小于3秒
            # 3. 如果下一句以标点开始或当前句以标点结束
            if (not self._is_sentence_end(current_text) or 
                time_gap < 3.0 or 
                (next_text and next_text[0] in '，,、')):
                # 合并内容，添加适当的连接
                if current_text and not current_text.endswith(('，', ',', '、')):
                    if next_text and not next_text[0] in '，,、。！？':
                        current_text += '，'
                current_segment['to'] = item['to']
                current_segment['content'] = f"{current_text}{next_text}"
            else:
                # 创建新段落前，为当前段落添加标点
                current_segment['content'] = self._add_punctuation(current_segment['content'])
                merged_segments.append(current_segment)
                current_segment = {
                    'from': item['from'],
                    'to': item['to'],
                    'content': next_text
                }

        # 添加最后一个段落
        current_segment['content'] = self._add_punctuation(current_segment['content'])
        merged_segments.append(current_segment)
        return merged_segments

    def _group_segments_into_paragraphs(self, segments: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """将段落分组成更大的章节"""
        if not segments:
            return []

        paragraphs = []
        current_paragraph = []
        
        for segment in segments:
            current_paragraph.append(segment)
            
            # 如果遇到明显的段落结束标志，开始新的段落
            if (len(current_paragraph) >= 5 and  # 最小段落长度
                self._is_sentence_end(segment['content']) and
                len(segment['content']) > 10):  # 避免太短的句子
                paragraphs.append(current_paragraph)
                current_paragraph = []

        # 添加最后一个段落
        if current_paragraph:
            paragraphs.append(current_paragraph)

        return paragraphs

    def format_as_article(self, subtitle_data: Dict[str, Any], include_timestamp: bool = False) -> str:
        """将字幕格式化为文章格式
        
        Args:
            subtitle_data: 字幕数据
            include_timestamp: 是否在每个段落包含时间戳
            
        Returns:
            str: 格式化后的文章文本
        """
        body = subtitle_data.get('body', [])
        if not body:
            return "字幕内容为空"

        # 1. 合并相邻的字幕片段
        merged_segments = self._merge_subtitle_segments(body)
        
        # 2. 将片段分组成段落
        paragraphs = self._group_segments_into_paragraphs(merged_segments)
        
        # 3. 格式化文章
        article_parts = []
        
        for i, paragraph in enumerate(paragraphs):
            paragraph_lines = []
            
            # 添加时间戳（如果需要）
            if include_timestamp:
                start_time = self._seconds_to_readable_time(paragraph[0]['from'])
                end_time = self._seconds_to_readable_time(paragraph[-1]['to'])
                paragraph_lines.append(f"[{start_time} - {end_time}]")
            
            # 添加段落内容
            paragraph_text = ''.join(segment['content'] for segment in paragraph)
            # 确保段落文本有合适的标点符号
            paragraph_text = self._add_punctuation(paragraph_text)
            paragraph_lines.append(paragraph_text)
            
            # 合并段落内容
            article_parts.append('\n'.join(paragraph_lines))
        
        # 用两个换行符分隔段落
        return '\n\n'.join(article_parts)

    def get_subtitle_with_article(self, url: str) -> Tuple[str, str]:
        """获取视频的字幕和文章格式
        
        Args:
            url: 视频URL
            
        Returns:
            Tuple[str, str]: (SRT格式字幕, 文章格式文本)
        """
        # 获取视频信息
        video_info = self.get_video_info(url)
        
        # 获取字幕列表
        subtitle_list = self.get_subtitle_list(video_info['aid'], video_info['cid'])
        if not subtitle_list:
            raise Exception("该视频没有可用的字幕")
            
        # 使用第一个可用的字幕
        selected_subtitle = subtitle_list[0]
        
        # 获取字幕内容
        subtitle_content = self.get_subtitle_content(selected_subtitle['subtitle_url'])
        
        # 生成两种格式
        srt_format = self.format_subtitle(subtitle_content, "srt")
        article_format = self.format_as_article(subtitle_content)
        
        return srt_format, article_format