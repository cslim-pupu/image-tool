# -*- coding: utf-8 -*-
"""
配置文件
"""

import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 微信公众号配置
WECHAT_APPID = os.getenv('WECHAT_APPID', '')
WECHAT_SECRET = os.getenv('WECHAT_SECRET', '')

# 文件路径配置
DOWNLOAD_DIR = 'downloads'  # 图片下载目录
LOG_DIR = 'logs'  # 日志目录

# 图片配置
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 最大图片大小 10MB
SUPPORTED_FORMATS = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']

# 请求配置
REQUEST_TIMEOUT = 30  # 请求超时时间
MAX_RETRIES = 3  # 最大重试次数

# 日志配置
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'