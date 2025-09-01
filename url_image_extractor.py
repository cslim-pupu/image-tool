#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网页图片抓取器
从指定URL抓取所有图片，获取图片信息和尺寸数据
"""

import requests
import re
from urllib.parse import urljoin, urlparse
from PIL import Image
import io
import os
import logging
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import hashlib
import time

logger = logging.getLogger(__name__)

class URLImageExtractor:
    """URL图片抓取器"""
    
    def __init__(self, download_folder='downloads'):
        self.download_folder = download_folder
        os.makedirs(download_folder, exist_ok=True)
        
        # 设置请求头，模拟浏览器
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def extract_images_from_url(self, url: str) -> List[Dict]:
        """从URL抓取所有图片信息"""
        try:
            logger.info(f"开始抓取URL: {url}")
            
            # 获取网页内容
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            # 解析HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 查找所有图片标签
            img_tags = soup.find_all('img')
            
            images = []
            for i, img in enumerate(img_tags):
                img_info = self._process_image_tag(img, url, i)
                if img_info:
                    images.append(img_info)
            
            logger.info(f"成功抓取到 {len(images)} 张图片")
            return images
            
        except requests.RequestException as e:
            logger.error(f"请求URL失败: {str(e)}")
            raise Exception(f"无法访问URL: {str(e)}")
        except Exception as e:
            logger.error(f"抓取图片失败: {str(e)}")
            raise Exception(f"抓取失败: {str(e)}")
    
    def _process_image_tag(self, img_tag, base_url: str, index: int) -> Optional[Dict]:
        """处理单个图片标签"""
        try:
            # 获取图片URL
            img_src = img_tag.get('src') or img_tag.get('data-src') or img_tag.get('data-original')
            if not img_src:
                return None
            
            # 转换为绝对URL
            img_url = urljoin(base_url, img_src)
            
            # 跳过base64图片和SVG
            if img_url.startswith('data:') or img_url.endswith('.svg'):
                return None
            
            # 获取图片信息
            img_info = self._get_image_info(img_url, index)
            
            # 添加额外信息
            img_info.update({
                'alt': img_tag.get('alt', ''),
                'title': img_tag.get('title', ''),
                'index': index
            })
            
            return img_info
            
        except Exception as e:
            logger.warning(f"处理图片标签失败: {str(e)}")
            return None
    
    def _get_image_info(self, img_url: str, index: int) -> Dict:
        """获取图片详细信息"""
        try:
            # 发送HEAD请求获取基本信息
            head_response = requests.head(img_url, headers=self.headers, timeout=5)
            
            # 如果HEAD请求失败，尝试GET请求
            if head_response.status_code != 200:
                response = requests.get(img_url, headers=self.headers, timeout=10, stream=True)
                response.raise_for_status()
            else:
                response = head_response
            
            # 获取文件大小
            content_length = response.headers.get('content-length')
            file_size = int(content_length) if content_length else 0
            
            # 获取文件类型
            content_type = response.headers.get('content-type', '')
            
            # 生成唯一ID
            img_id = hashlib.md5(f"{img_url}_{index}".encode()).hexdigest()[:8]
            
            img_info = {
                'id': img_id,
                'url': img_url,
                'size_bytes': file_size,
                'size_formatted': self._format_file_size(file_size),
                'content_type': content_type,
                'width': 0,
                'height': 0,
                'dimensions': '未知',
                'downloaded': False,
                'local_path': None
            }
            
            # 尝试获取图片尺寸（需要下载部分内容）
            try:
                if head_response.status_code == 200:
                    # 重新发送GET请求获取图片内容
                    img_response = requests.get(img_url, headers=self.headers, timeout=10)
                    img_response.raise_for_status()
                else:
                    img_response = response
                
                # 使用PIL获取图片尺寸
                img_data = io.BytesIO(img_response.content)
                with Image.open(img_data) as pil_img:
                    width, height = pil_img.size
                    img_info.update({
                        'width': width,
                        'height': height,
                        'dimensions': f'{width} × {height}',
                        'size_bytes': len(img_response.content)  # 更准确的文件大小
                    })
                    img_info['size_formatted'] = self._format_file_size(img_info['size_bytes'])
                    
            except Exception as e:
                logger.warning(f"获取图片尺寸失败: {str(e)}")
            
            return img_info
            
        except Exception as e:
            logger.warning(f"获取图片信息失败: {str(e)}")
            # 返回基本信息
            img_id = hashlib.md5(f"{img_url}_{index}".encode()).hexdigest()[:8]
            return {
                'id': img_id,
                'url': img_url,
                'size_bytes': 0,
                'size_formatted': '未知',
                'content_type': '未知',
                'width': 0,
                'height': 0,
                'dimensions': '未知',
                'downloaded': False,
                'local_path': None
            }
    
    def download_image(self, img_info: Dict) -> Dict:
        """下载单张图片"""
        try:
            img_url = img_info['url']
            img_id = img_info['id']
            
            logger.info(f"开始下载图片: {img_url}")
            
            # 发送请求下载图片
            response = requests.get(img_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            # 确定文件扩展名
            content_type = response.headers.get('content-type', '')
            if 'jpeg' in content_type or 'jpg' in content_type:
                ext = '.jpg'
            elif 'png' in content_type:
                ext = '.png'
            elif 'gif' in content_type:
                ext = '.gif'
            elif 'webp' in content_type:
                ext = '.webp'
            else:
                # 从URL推断扩展名
                parsed_url = urlparse(img_url)
                path = parsed_url.path.lower()
                if path.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                    ext = os.path.splitext(path)[1]
                else:
                    ext = '.jpg'  # 默认扩展名
            
            # 生成文件名
            filename = f"image_{img_id}{ext}"
            local_path = os.path.join(self.download_folder, filename)
            
            # 保存文件
            with open(local_path, 'wb') as f:
                f.write(response.content)
            
            # 更新图片信息
            img_info.update({
                'downloaded': True,
                'local_path': local_path,
                'filename': filename,
                'size_bytes': len(response.content)
            })
            img_info['size_formatted'] = self._format_file_size(img_info['size_bytes'])
            
            logger.info(f"图片下载成功: {filename}")
            return img_info
            
        except Exception as e:
            logger.error(f"下载图片失败: {str(e)}")
            raise Exception(f"下载失败: {str(e)}")
    
    def download_all_images(self, images: List[Dict]) -> List[Dict]:
        """批量下载所有图片"""
        downloaded_images = []
        
        for img_info in images:
            try:
                downloaded_img = self.download_image(img_info.copy())
                downloaded_images.append(downloaded_img)
                time.sleep(0.5)  # 避免请求过于频繁
            except Exception as e:
                logger.warning(f"跳过下载失败的图片: {img_info['url']} - {str(e)}")
                img_info['download_error'] = str(e)
                downloaded_images.append(img_info)
        
        return downloaded_images
    
    def _format_file_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes == 0:
            return "未知"
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def create_download_archive(self, images: List[Dict]) -> Dict:
        """创建下载压缩包"""
        import zipfile
        from datetime import datetime
        
        try:
            # 确保下载目录存在
            os.makedirs(self.download_folder, exist_ok=True)
            
            # 先下载所有图片
            downloaded_images = []
            for img_info in images:
                if not img_info.get('downloaded'):
                    try:
                        download_result = self.download_image(img_info.copy())
                        downloaded_images.append(download_result)
                    except Exception as e:
                        logger.warning(f"下载图片失败: {img_info['url']} - {str(e)}")
                        img_info['download_error'] = str(e)
                        downloaded_images.append(img_info)
                else:
                    downloaded_images.append(img_info)
            
            # 生成压缩包文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            archive_name = f"images_{timestamp}.zip"
            archive_path = os.path.join(self.download_folder, archive_name)
            
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for img_info in downloaded_images:
                    if img_info.get('downloaded') and img_info.get('local_path'):
                        local_path = img_info['local_path']
                        if os.path.exists(local_path):
                            # 使用原始文件名或生成的文件名
                            arcname = img_info.get('filename', os.path.basename(local_path))
                            zipf.write(local_path, arcname)
            
            logger.info(f"创建压缩包成功: {archive_name}")
            return {
                'success': True,
                'archive_name': archive_name,
                'archive_path': archive_path,
                'downloaded_count': len([img for img in downloaded_images if img.get('downloaded')])
            }
            
        except Exception as e:
            logger.error(f"创建压缩包失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }