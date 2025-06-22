#!/usr/bin/env python3
"""
Web服务启动脚本
"""

import os
import sys
from web_interface import app

def main():
    print("🚀 启动 Bilibili 字幕获取 Web 服务")
    print("=" * 50)
    
    # 检查Cookie配置
    from config import BILIBILI_COOKIES
    if not BILIBILI_COOKIES:
        print("⚠️  警告: 未配置Cookie，请在.env文件中配置BILIBILI_COOKIES")
        print("   参考 COOKIE_SETUP.md 了解如何获取Cookie")
    else:
        print("✅ Cookie配置已加载")
    
    print()
    print("📱 Web界面地址: http://localhost:8080")
    print("🛑 按 Ctrl+C 停止服务")
    print("=" * 50)
    
    # 确保必要目录存在
    os.makedirs('docs', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    
    try:
        app.run(debug=True, host='0.0.0.0', port=8080)
    except KeyboardInterrupt:
        print("\n🛑 服务已停止")
        sys.exit(0)

if __name__ == '__main__':
    main() 