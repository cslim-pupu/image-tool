# -*- coding: utf-8 -*-
"""
工具函数模块
"""

import os
import re
import logging
from urllib.parse import urlparse, urljoin
from pathlib import Path
from typing import List, Optional

import config


def setup_logging():
    """设置日志配置"""
    # 创建日志目录
    os.makedirs(config.LOG_DIR, exist_ok=True)
    
    # 配置日志
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format=config.LOG_FORMAT,
        handlers=[
            logging.FileHandler(os.path.join(config.LOG_DIR, 'app.log'), encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)


def create_directories():
    """创建必要的目录"""
    directories = [config.DOWNLOAD_DIR, config.LOG_DIR]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)


def is_valid_image_url(url: str) -> bool:
    """检查是否为有效的图片URL"""
    if not url or not isinstance(url, str):
        return False
    
    # 检查URL格式
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False
    except Exception:
        return False
    
    # 检查文件扩展名或者是否包含图片相关的查询参数
    path = parsed.path.lower()
    url_lower = url.lower()
    
    # 检查路径中的扩展名
    if any(path.endswith(ext) for ext in config.SUPPORTED_FORMATS):
        return True
    
    # 检查URL中是否包含图片格式关键词（适用于动态图片URL）
    if any(ext.replace('.', '') in url_lower for ext in config.SUPPORTED_FORMATS):
        return True
    
    # 检查是否为图片服务（如picsum.photos）
    if 'picsum.photos' in parsed.netloc or 'image' in url_lower:
        return True
    
    return False


def extract_image_urls_from_text(text: str) -> List[str]:
    """从文本中提取图片URL"""
    # 匹配HTTP/HTTPS图片链接的正则表达式
    url_pattern = r'https?://[^\s<>"\'{}},|\\^`\[\]]+\.(?:jpg|jpeg|png|gif|bmp|webp)(?:\?[^\s<>"\'{}},|\\^`\[\]]*)?'
    
    # 直接查找完整的URL
    full_urls = re.findall(url_pattern, text, re.IGNORECASE)
    
    # 去重并验证
    valid_urls = []
    for url in set(full_urls):
        if is_valid_image_url(url):
            valid_urls.append(url)
    
    return valid_urls


def get_filename_from_url(url: str) -> str:
    """从URL中提取文件名"""
    parsed = urlparse(url)
    filename = os.path.basename(parsed.path)
    
    # 如果没有文件名，生成一个
    if not filename or '.' not in filename:
        import hashlib
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        filename = f"image_{url_hash}.jpg"
    
    return filename


def sanitize_filename(filename: str) -> str:
    """清理文件名，移除非法字符"""
    # 移除或替换非法字符
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # 限制长度
    if len(filename) > 100:
        name, ext = os.path.splitext(filename)
        filename = name[:95] + ext
    
    return filename


def format_file_size(size_bytes: int) -> str:
    """格式化文件大小显示"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    
    return f"{s} {size_names[i]}"