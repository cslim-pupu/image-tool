# -*- coding: utf-8 -*-
"""
文档处理模块
"""

import os
import re
import logging
from typing import List, Dict, Tuple, Optional
from pathlib import Path

from bs4 import BeautifulSoup

from utils import extract_image_urls_from_text, is_valid_image_url


class DocumentProcessor:
    """文档处理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 支持的文档格式
        self.supported_formats = {
            '.txt': self._process_text_file,
            '.md': self._process_markdown_file,
            '.html': self._process_html_file,
            '.htm': self._process_html_file,
        }
    
    def extract_images_from_file(self, file_path: str) -> Dict:
        """从文件中提取图片URL
        
        Args:
            file_path: 文件路径
            
        Returns:
            提取结果字典
        """
        result = {
            'file_path': file_path,
            'success': False,
            'image_urls': [],
            'total_images': 0,
            'error': None,
            'file_type': None
        }
        
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"文件不存在: {file_path}")
            
            # 获取文件扩展名
            file_ext = Path(file_path).suffix.lower()
            result['file_type'] = file_ext
            
            if file_ext not in self.supported_formats:
                raise ValueError(f"不支持的文件格式: {file_ext}")
            
            self.logger.info(f"开始处理文件: {file_path}")
            
            # 调用对应的处理函数
            processor = self.supported_formats[file_ext]
            image_urls = processor(file_path)
            
            # 去重并验证URL
            unique_urls = list(set(image_urls))
            valid_urls = [url for url in unique_urls if is_valid_image_url(url)]
            
            result.update({
                'success': True,
                'image_urls': valid_urls,
                'total_images': len(valid_urls)
            })
            
            self.logger.info(f"文件处理完成: {file_path}, 找到 {len(valid_urls)} 个有效图片URL")
            
        except FileNotFoundError as e:
            result['error'] = str(e)
            self.logger.error(f"文件处理失败 {file_path}: {str(e)}")
            
        except Exception as e:
            result['error'] = str(e)
            self.logger.error(f"文件处理失败 {file_path}: {str(e)}")
        
        return result
    
    def _process_text_file(self, file_path: str) -> List[str]:
        """处理纯文本文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            图片URL列表
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # 尝试其他编码
            encodings = ['gbk', 'gb2312', 'latin1']
            content = None
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    break
                except UnicodeDecodeError:
                    continue
            
            if content is None:
                raise ValueError("无法解码文件内容")
        
        return extract_image_urls_from_text(content)
    
    def _process_markdown_file(self, file_path: str) -> List[str]:
        """处理Markdown文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            图片URL列表
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        image_urls = []
        
        # 提取Markdown图片语法: ![alt](url)
        md_image_pattern = r'!\[.*?\]\((https?://[^\s\)]+)\)'
        md_urls = re.findall(md_image_pattern, content, re.IGNORECASE)
        # 过滤出图片URL
        for url in md_urls:
            if any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']) or '?' in url:
                image_urls.append(url)
        
        # 提取HTML img标签
        html_urls = self._extract_html_images(content)
        image_urls.extend(html_urls)
        
        # 提取普通URL
        text_urls = extract_image_urls_from_text(content)
        image_urls.extend(text_urls)
        
        return image_urls
    
    def _process_html_file(self, file_path: str) -> List[str]:
        """处理HTML文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            图片URL列表
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return self._extract_html_images(content)
    
    def _extract_html_images(self, html_content: str) -> List[str]:
        """从HTML内容中提取图片URL
        
        Args:
            html_content: HTML内容
            
        Returns:
            图片URL列表
        """
        image_urls = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 提取img标签的src属性
            img_tags = soup.find_all('img')
            for img in img_tags:
                src = img.get('src')
                if src and src.startswith(('http://', 'https://')):
                    image_urls.append(src)
                
                # 也检查data-src属性（懒加载图片）
                data_src = img.get('data-src')
                if data_src and data_src.startswith(('http://', 'https://')):
                    image_urls.append(data_src)
            
            # 提取CSS背景图片
            style_pattern = r'background-image:\s*url\(["\']?(https?://[^"\')\s]+)["\']?\)'
            css_urls = re.findall(style_pattern, html_content, re.IGNORECASE)
            image_urls.extend(css_urls)
            
        except Exception as e:
            self.logger.warning(f"HTML解析失败，使用正则表达式: {str(e)}")
            
            # 备用方案：使用正则表达式
            img_pattern = r'<img[^>]+src=["\']?(https?://[^"\'>\s]+)["\']?[^>]*>'
            regex_urls = re.findall(img_pattern, html_content, re.IGNORECASE)
            image_urls.extend(regex_urls)
        
        return image_urls
    
    def extract_images_from_directory(self, directory_path: str, recursive: bool = True) -> List[Dict]:
        """从目录中的所有支持文件提取图片URL
        
        Args:
            directory_path: 目录路径
            recursive: 是否递归处理子目录
            
        Returns:
            提取结果列表
        """
        if not os.path.exists(directory_path):
            raise FileNotFoundError(f"目录不存在: {directory_path}")
        
        if not os.path.isdir(directory_path):
            raise ValueError(f"路径不是目录: {directory_path}")
        
        self.logger.info(f"开始处理目录: {directory_path} (递归: {recursive})")
        
        results = []
        file_count = 0
        
        # 遍历目录
        if recursive:
            for root, dirs, files in os.walk(directory_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    if Path(file_path).suffix.lower() in self.supported_formats:
                        result = self.extract_images_from_file(file_path)
                        results.append(result)
                        file_count += 1
        else:
            for file in os.listdir(directory_path):
                file_path = os.path.join(directory_path, file)
                if os.path.isfile(file_path) and Path(file_path).suffix.lower() in self.supported_formats:
                    result = self.extract_images_from_file(file_path)
                    results.append(result)
                    file_count += 1
        
        # 统计结果
        successful_files = sum(1 for r in results if r['success'])
        total_images = sum(r['total_images'] for r in results if r['success'])
        
        self.logger.info(f"目录处理完成: 处理了 {file_count} 个文件，成功 {successful_files} 个，共找到 {total_images} 个图片URL")
        
        return results
    
    def extract_images_from_text(self, text: str) -> List[str]:
        """从纯文本中提取图片URL
        
        Args:
            text: 文本内容
            
        Returns:
            图片URL列表
        """
        return extract_image_urls_from_text(text)
    
    def get_all_unique_urls(self, results: List[Dict]) -> List[str]:
        """从提取结果中获取所有唯一的图片URL
        
        Args:
            results: 提取结果列表
            
        Returns:
            唯一图片URL列表
        """
        all_urls = []
        for result in results:
            if result['success']:
                all_urls.extend(result['image_urls'])
        
        # 去重并保持顺序
        unique_urls = []
        seen = set()
        for url in all_urls:
            if url not in seen:
                unique_urls.append(url)
                seen.add(url)
        
        return unique_urls
    
    def create_url_mapping(self, original_urls: List[str], new_urls: List[str]) -> Dict[str, str]:
        """创建原始URL到新URL的映射
        
        Args:
            original_urls: 原始URL列表
            new_urls: 新URL列表
            
        Returns:
            URL映射字典
        """
        if len(original_urls) != len(new_urls):
            self.logger.warning(f"URL数量不匹配: 原始 {len(original_urls)}, 新 {len(new_urls)}")
        
        mapping = {}
        for i, original_url in enumerate(original_urls):
            if i < len(new_urls):
                mapping[original_url] = new_urls[i]
            else:
                self.logger.warning(f"没有对应的新URL: {original_url}")
        
        return mapping
    
    def get_supported_formats(self) -> List[str]:
        """获取支持的文件格式列表
        
        Returns:
            支持的文件格式列表
        """
        return list(self.supported_formats.keys())
    
    def is_supported_file(self, file_path: str) -> bool:
        """检查文件是否为支持的格式
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否支持
        """
        file_ext = Path(file_path).suffix.lower()
        return file_ext in self.supported_formats