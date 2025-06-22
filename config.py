"""
配置文件
支持从环境变量和.env文件读取配置
"""

import os
from typing import Dict, Optional
from pathlib import Path

# 尝试加载.env文件
def load_env_file():
    """加载.env文件中的环境变量"""
    env_file = Path('.env')
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # 移除引号
                    value = value.strip('\'"')
                    os.environ[key.strip()] = value

# 加载.env文件
load_env_file()

# Cookie配置
def get_bilibili_cookies() -> Optional[Dict[str, str]]:
    """
    获取B站Cookie配置
    优先级：环境变量 > .env文件
    """
    # 从环境变量获取Cookie字符串
    cookie_string = os.getenv('BILIBILI_COOKIES', '')
    
    # 如果没有Cookie字符串，尝试单独获取各个Cookie值
    if not cookie_string:
        sessdata = os.getenv('BILIBILI_SESSDATA', '')
        bili_jct = os.getenv('BILIBILI_BILI_JCT', '')
        buvid3 = os.getenv('BILIBILI_BUVID3', '')
        
        if sessdata and bili_jct:
            cookies = {
                'SESSDATA': sessdata,
                'bili_jct': bili_jct,
            }
            if buvid3:
                cookies['buvid3'] = buvid3
            return cookies
        return None
    
    # 解析Cookie字符串
    cookies = {}
    for item in cookie_string.split(';'):
        item = item.strip()
        if '=' in item:
            key, value = item.split('=', 1)
            cookies[key.strip()] = value.strip()
    
    return cookies if cookies else None

# API相关配置
API_CONFIG = {
    # 请求超时时间（秒）
    'timeout': int(os.getenv('API_TIMEOUT', '30')),
    
    # 请求重试次数
    'max_retries': int(os.getenv('API_MAX_RETRIES', '3')),
    
    # 请求间隔（秒）
    'request_interval': float(os.getenv('API_REQUEST_INTERVAL', '1')),
}

# User-Agent配置
USER_AGENT = os.getenv('USER_AGENT', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

# 支持的字幕格式
SUPPORTED_FORMATS = ['txt', 'srt', 'json']

# 默认输出格式
DEFAULT_FORMAT = os.getenv('DEFAULT_FORMAT', 'txt')

# Cookie配置
BILIBILI_COOKIES = get_bilibili_cookies()