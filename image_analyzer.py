import requests
import re
from urllib.parse import urlparse
from typing import List, Dict, Tuple
import logging
from exceptions import ImageAnalysisError

logger = logging.getLogger(__name__)

class ImageAnalyzer:
    """图片分析器 - 用于分析SVG代码中的图片并检测大小"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def extract_image_urls_from_svg(self, svg_content: str) -> List[str]:
        """从SVG代码中提取所有图片URL"""
        try:
            # 先处理HTML编码
            import html
            decoded_content = html.unescape(svg_content)
            
            # 匹配各种图片URL模式
            patterns = [
                # 传统图片扩展名结尾的URL
                r'src=["\']([^"\'>]+\.(jpg|jpeg|png|gif|webp|svg))["\']',  # src属性
                r'href=["\']([^"\'>]+\.(jpg|jpeg|png|gif|webp|svg))["\']',  # href属性
                r'url\(["\']?([^"\')>]+\.(jpg|jpeg|png|gif|webp|svg))["\']?\)',  # CSS url()
                r'background-image:[^;]*url\(["\']?([^"\')>]+\.(jpg|jpeg|png|gif|webp|svg))["\']?\)',  # background-image
                r'xlink:href=["\']([^"\'>]+\.(jpg|jpeg|png|gif|webp|svg))["\']',  # xlink:href
                
                # 微信公众号图床URL（支持各种属性和CSS样式）
                r'src=["\']([^"\'>]*(?:mmbiz\.qpic\.cn|mmecoa\.qpic\.cn)[^"\'>]*)["\']',  # src属性中的微信图床
                r'href=["\']([^"\'>]*(?:mmbiz\.qpic\.cn|mmecoa\.qpic\.cn)[^"\'>]*)["\']',  # href属性中的微信图床
                r'url\(["\']?([^"\')>]*(?:mmbiz\.qpic\.cn|mmecoa\.qpic\.cn)[^"\')>]*)["\']?\)',  # CSS url()中的微信图床
                r'background-image:[^;]*url\(["\']?([^"\')>]*(?:mmbiz\.qpic\.cn|mmecoa\.qpic\.cn)[^"\')>]*)["\']?\)',  # background-image中的微信图床
                r'xlink:href=["\']([^"\'>]*(?:mmbiz\.qpic\.cn|mmecoa\.qpic\.cn)[^"\'>]*)["\']',  # xlink:href中的微信图床
                
                # 其他常见图床URL（如oss.e2.cool等）
                r'src=["\']([^"\'>]*oss\.e2\.cool[^"\'>]*)["\']',
                r'href=["\']([^"\'>]*oss\.e2\.cool[^"\'>]*)["\']',
                r'url\(["\']?([^"\')>]*oss\.e2\.cool[^"\')>]*)["\']?\)',
                r'background-image:[^;]*url\(["\']?([^"\')>]*oss\.e2\.cool[^"\')>]*)["\']?\)',
                r'xlink:href=["\']([^"\'>]*oss\.e2\.cool[^"\'>]*)["\']',
            ]
            
            urls = set()
            for pattern in patterns:
                matches = re.findall(pattern, decoded_content, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        url = match[0]
                    else:
                        url = match
                    
                    # 验证URL格式
                    if self._is_valid_url(url):
                        urls.add(url)
            
            logger.info(f"从SVG代码中提取到 {len(urls)} 个图片URL")
            return list(urls)
            
        except Exception as e:
            logger.error(f"提取图片URL失败: {str(e)}")
            raise ImageAnalysisError(f"提取图片URL失败: {str(e)}")
    
    def _is_valid_url(self, url: str) -> bool:
        """验证URL是否有效"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    def get_image_size(self, url: str) -> Tuple[int, str]:
        """获取图片大小（字节）和格式化大小字符串"""
        try:
            # 发送HEAD请求获取Content-Length
            response = self.session.head(url, timeout=10, allow_redirects=True)
            
            if response.status_code == 200:
                content_length = response.headers.get('Content-Length')
                if content_length:
                    size_bytes = int(content_length)
                    size_str = self._format_size(size_bytes)
                    return size_bytes, size_str
            
            # 如果HEAD请求失败，尝试GET请求（只获取部分内容）
            response = self.session.get(url, timeout=10, stream=True)
            if response.status_code == 200:
                content_length = response.headers.get('Content-Length')
                if content_length:
                    size_bytes = int(content_length)
                    size_str = self._format_size(size_bytes)
                    return size_bytes, size_str
                
                # 如果没有Content-Length，下载部分内容估算
                chunk_size = 1024 * 1024  # 1MB
                downloaded = 0
                for chunk in response.iter_content(chunk_size=chunk_size):
                    downloaded += len(chunk)
                    if downloaded >= chunk_size:
                        break
                
                # 估算总大小（这只是一个粗略估计）
                estimated_size = downloaded
                size_str = f"~{self._format_size(estimated_size)}"
                return estimated_size, size_str
            
            return 0, "未知"
            
        except Exception as e:
            logger.warning(f"获取图片大小失败 {url}: {str(e)}")
            return 0, "获取失败"
    
    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes == 0:
            return "0 B"
        
        units = ['B', 'KB', 'MB', 'GB']
        size = float(size_bytes)
        unit_index = 0
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        if unit_index == 0:
            return f"{int(size)} {units[unit_index]}"
        else:
            return f"{size:.2f} {units[unit_index]}"
    
    def is_large_image(self, size_bytes: int) -> bool:
        """判断图片是否过大（超过3MB）"""
        return size_bytes > 3 * 1024 * 1024
    
    def get_size_category(self, size_bytes: int) -> str:
        """获取图片大小分类"""
        size_mb = size_bytes / (1024 * 1024)
        if size_mb >= 7:
            return 'red'  # 红色：7MB以上
        elif size_mb >= 5:
            return 'orange'  # 橙色：5-7MB
        elif size_mb >= 3:
            return 'yellow'  # 黄色：3-5MB
        else:
            return 'green'  # 绿色：3MB以下
    
    def analyze_svg_images(self, svg_content: str) -> List[Dict]:
        """分析SVG中的所有图片"""
        try:
            urls = self.extract_image_urls_from_svg(svg_content)
            results = []
            
            for i, url in enumerate(urls, 1):
                logger.info(f"分析图片 {i}/{len(urls)}: {url}")
                
                size_bytes, size_str = self.get_image_size(url)
                
                # 判断是否超过3MB
                is_large = size_bytes > 3 * 1024 * 1024  # 3MB
                
                # 获取大小分类
                size_category = self.get_size_category(size_bytes)
                
                result = {
                    'id': f'img_{i}',
                    'url': url,
                    'size_bytes': size_bytes,
                    'size_str': size_str,
                    'is_large': is_large,
                    'size_category': size_category,
                    'wechat_url': '',  # 用户手动输入的微信图床地址
                    'replaced': False  # 是否已替换
                }
                
                results.append(result)
            
            logger.info(f"图片分析完成，共 {len(results)} 张图片，其中 {sum(1 for r in results if r['is_large'])} 张超过3MB")
            return results
            
        except Exception as e:
            logger.error(f"分析SVG图片失败: {str(e)}")
            raise ImageAnalysisError(f"分析SVG图片失败: {str(e)}")
    
    def replace_url_in_svg(self, svg_content: str, old_url: str, new_url: str) -> str:
        """在SVG代码中替换指定的图片URL"""
        try:
            # 转义特殊字符
            escaped_old_url = re.escape(old_url)
            
            # 替换各种可能的URL格式
            patterns = [
                (f'src=["\']({escaped_old_url})["\']', f'src="{new_url}"'),
                (f'href=["\']({escaped_old_url})["\']', f'href="{new_url}"'),
                (f'url\(["\']?({escaped_old_url})["\']?\)', f'url("{new_url}")'),
                (f'xlink:href=["\']({escaped_old_url})["\']', f'xlink:href="{new_url}"'),
            ]
            
            updated_content = svg_content
            replaced_count = 0
            
            for pattern, replacement in patterns:
                new_content = re.sub(pattern, replacement, updated_content, flags=re.IGNORECASE)
                if new_content != updated_content:
                    replaced_count += 1
                    updated_content = new_content
            
            if replaced_count > 0:
                logger.info(f"成功替换URL: {old_url} -> {new_url}")
            else:
                logger.warning(f"未找到要替换的URL: {old_url}")
            
            return updated_content
            
        except Exception as e:
            logger.error(f"替换URL失败: {str(e)}")
            raise ImageAnalysisError(f"替换URL失败: {str(e)}")