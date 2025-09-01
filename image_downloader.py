# -*- coding: utf-8 -*-
"""
图片下载模块
"""

import os
import time
import logging
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

import requests
from PIL import Image
from tqdm import tqdm

import config
from utils import get_filename_from_url, sanitize_filename, format_file_size


class ImageDownloader:
    """图片下载器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # 创建下载目录
        os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)
    
    def download_single_image(self, url: str, custom_filename: Optional[str] = None) -> Dict:
        """下载单张图片
        
        Args:
            url: 图片URL
            custom_filename: 自定义文件名
            
        Returns:
            包含下载结果的字典
        """
        result = {
            'url': url,
            'success': False,
            'local_path': None,
            'error': None,
            'file_size': 0
        }
        
        try:
            # 获取文件名
            if custom_filename:
                filename = custom_filename
            else:
                filename = get_filename_from_url(url)
            
            filename = sanitize_filename(filename)
            local_path = os.path.join(config.DOWNLOAD_DIR, filename)
            
            # 如果文件已存在，添加序号
            counter = 1
            original_path = local_path
            while os.path.exists(local_path):
                name, ext = os.path.splitext(original_path)
                local_path = f"{name}_{counter}{ext}"
                counter += 1
            
            # 下载图片
            self.logger.info(f"开始下载图片: {url}")
            
            response = self.session.get(
                url, 
                timeout=config.REQUEST_TIMEOUT,
                stream=True
            )
            response.raise_for_status()
            
            # 检查内容类型
            content_type = response.headers.get('content-type', '').lower()
            if not content_type.startswith('image/'):
                raise ValueError(f"URL返回的不是图片内容: {content_type}")
            
            # 检查文件大小
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) > config.MAX_IMAGE_SIZE:
                raise ValueError(f"图片文件过大: {format_file_size(int(content_length))}")
            
            # 保存文件
            total_size = 0
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        total_size += len(chunk)
                        
                        # 检查下载过程中的文件大小
                        if total_size > config.MAX_IMAGE_SIZE:
                            f.close()
                            os.remove(local_path)
                            raise ValueError(f"图片文件过大: {format_file_size(total_size)}")
            
            # 验证图片文件
            try:
                with Image.open(local_path) as img:
                    img.verify()
            except Exception as e:
                os.remove(local_path)
                raise ValueError(f"图片文件损坏或格式不支持: {str(e)}")
            
            result.update({
                'success': True,
                'local_path': local_path,
                'file_size': total_size
            })
            
            self.logger.info(f"图片下载成功: {url} -> {local_path} ({format_file_size(total_size)})")
            
        except requests.exceptions.RequestException as e:
            error_msg = f"网络请求错误: {str(e)}"
            result['error'] = error_msg
            self.logger.error(f"下载失败 {url}: {error_msg}")
            
        except ValueError as e:
            result['error'] = str(e)
            self.logger.error(f"下载失败 {url}: {str(e)}")
            
        except Exception as e:
            error_msg = f"未知错误: {str(e)}"
            result['error'] = error_msg
            self.logger.error(f"下载失败 {url}: {error_msg}")
        
        return result
    
    def download_images_batch(self, urls: List[str], max_workers: int = 5) -> List[Dict]:
        """批量下载图片
        
        Args:
            urls: 图片URL列表
            max_workers: 最大并发数
            
        Returns:
            下载结果列表
        """
        if not urls:
            return []
        
        self.logger.info(f"开始批量下载 {len(urls)} 张图片")
        
        results = []
        
        # 使用线程池并发下载
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有下载任务
            future_to_url = {executor.submit(self.download_single_image, url): url for url in urls}
            
            # 使用进度条显示下载进度
            with tqdm(total=len(urls), desc="下载图片", unit="张") as pbar:
                for future in as_completed(future_to_url):
                    result = future.result()
                    results.append(result)
                    
                    # 更新进度条
                    if result['success']:
                        pbar.set_postfix(status="成功", file=os.path.basename(result['local_path']))
                    else:
                        pbar.set_postfix(status="失败", error=result['error'][:30])
                    
                    pbar.update(1)
        
        # 统计结果
        successful = sum(1 for r in results if r['success'])
        failed = len(results) - successful
        total_size = sum(r['file_size'] for r in results if r['success'])
        
        self.logger.info(f"批量下载完成: 成功 {successful} 张, 失败 {failed} 张, 总大小 {format_file_size(total_size)}")
        
        return results
    
    def retry_failed_downloads(self, failed_results: List[Dict], max_retries: int = None) -> List[Dict]:
        """重试失败的下载
        
        Args:
            failed_results: 失败的下载结果列表
            max_retries: 最大重试次数
            
        Returns:
            重试结果列表
        """
        if max_retries is None:
            max_retries = config.MAX_RETRIES
        
        failed_urls = [r['url'] for r in failed_results if not r['success']]
        if not failed_urls:
            return []
        
        self.logger.info(f"开始重试 {len(failed_urls)} 个失败的下载")
        
        retry_results = []
        
        for attempt in range(max_retries):
            if not failed_urls:
                break
            
            self.logger.info(f"第 {attempt + 1} 次重试，剩余 {len(failed_urls)} 个")
            
            # 重试下载
            current_results = self.download_images_batch(failed_urls)
            retry_results.extend(current_results)
            
            # 更新失败列表
            failed_urls = [r['url'] for r in current_results if not r['success']]
            
            # 如果还有失败的，等待一段时间再重试
            if failed_urls and attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 指数退避
        
        return retry_results
    
    def cleanup_downloads(self, keep_successful: bool = True):
        """清理下载目录
        
        Args:
            keep_successful: 是否保留成功下载的文件
        """
        if not os.path.exists(config.DOWNLOAD_DIR):
            return
        
        if not keep_successful:
            import shutil
            shutil.rmtree(config.DOWNLOAD_DIR)
            os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)
            self.logger.info("已清理所有下载文件")
        else:
            # 只清理可能的临时文件
            for filename in os.listdir(config.DOWNLOAD_DIR):
                if filename.startswith('temp_') or filename.endswith('.tmp'):
                    filepath = os.path.join(config.DOWNLOAD_DIR, filename)
                    try:
                        os.remove(filepath)
                        self.logger.info(f"清理临时文件: {filename}")
                    except Exception as e:
                        self.logger.warning(f"清理文件失败 {filename}: {str(e)}")
    
    def __del__(self):
        """析构函数，关闭会话"""
        if hasattr(self, 'session'):
            self.session.close()