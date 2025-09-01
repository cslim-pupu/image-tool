# -*- coding: utf-8 -*-
"""
微信公众号图片上传模块
"""

import os
import time
import json
import logging
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin

import requests
from tqdm import tqdm

import config
from utils import format_file_size


class WeChatUploader:
    """微信公众号图片上传器"""
    
    # 微信API端点
    TOKEN_URL = "https://api.weixin.qq.com/cgi-bin/token"
    UPLOAD_URL = "https://api.weixin.qq.com/cgi-bin/media/upload"
    UPLOAD_IMG_URL = "https://api.weixin.qq.com/cgi-bin/media/uploadimg"
    
    def __init__(self, appid: str = None, secret: str = None):
        """初始化上传器
        
        Args:
            appid: 微信公众号AppID
            secret: 微信公众号AppSecret
        """
        self.logger = logging.getLogger(__name__)
        
        # 使用传入的参数或配置文件中的参数
        self.appid = appid or config.WECHAT_APPID
        self.secret = secret or config.WECHAT_SECRET
        
        if not self.appid or not self.secret:
            raise ValueError("微信公众号AppID和AppSecret不能为空，请在.env文件中配置或传入参数")
        
        self.access_token = None
        self.token_expires_at = 0
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'WeChat-Image-Uploader/1.0'
        })
    
    def get_access_token(self, force_refresh: bool = False) -> str:
        """获取访问令牌
        
        Args:
            force_refresh: 是否强制刷新令牌
            
        Returns:
            访问令牌
        """
        current_time = time.time()
        
        # 如果令牌未过期且不强制刷新，直接返回
        if (not force_refresh and 
            self.access_token and 
            current_time < self.token_expires_at):
            return self.access_token
        
        self.logger.info("获取微信访问令牌")
        
        try:
            params = {
                'grant_type': 'client_credential',
                'appid': self.appid,
                'secret': self.secret
            }
            
            response = self.session.get(
                self.TOKEN_URL,
                params=params,
                timeout=config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            
            data = response.json()
            
            if 'access_token' not in data:
                error_msg = data.get('errmsg', '未知错误')
                error_code = data.get('errcode', -1)
                raise Exception(f"获取访问令牌失败: [{error_code}] {error_msg}")
            
            self.access_token = data['access_token']
            expires_in = data.get('expires_in', 7200)  # 默认2小时
            self.token_expires_at = current_time + expires_in - 300  # 提前5分钟过期
            
            self.logger.info(f"访问令牌获取成功，有效期: {expires_in} 秒")
            return self.access_token
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"网络请求失败: {str(e)}")
        except json.JSONDecodeError as e:
            raise Exception(f"响应解析失败: {str(e)}")
        except Exception as e:
            self.logger.error(f"获取访问令牌失败: {str(e)}")
            raise
    
    def upload_image(self, image_path: str, media_type: str = 'image') -> Dict:
        """上传单张图片到微信公众号
        
        Args:
            image_path: 图片本地路径
            media_type: 媒体类型，'image' 或 'thumb'
            
        Returns:
            上传结果字典
        """
        result = {
            'local_path': image_path,
            'success': False,
            'media_id': None,
            'media_url': None,
            'error': None
        }
        
        try:
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"图片文件不存在: {image_path}")
            
            # 检查文件大小
            file_size = os.path.getsize(image_path)
            if file_size > config.MAX_IMAGE_SIZE:
                raise ValueError(f"图片文件过大: {format_file_size(file_size)}")
            
            # 获取访问令牌
            access_token = self.get_access_token()
            
            self.logger.info(f"开始上传图片: {image_path} ({format_file_size(file_size)})")
            
            # 准备上传参数
            params = {
                'access_token': access_token,
                'type': media_type
            }
            
            # 准备文件数据
            filename = os.path.basename(image_path)
            with open(image_path, 'rb') as f:
                files = {
                    'media': (filename, f, 'image/jpeg')
                }
                
                # 上传图片
                response = self.session.post(
                    self.UPLOAD_URL,
                    params=params,
                    files=files,
                    timeout=config.REQUEST_TIMEOUT * 2  # 上传时间可能较长
                )
                response.raise_for_status()
            
            data = response.json()
            
            if 'media_id' not in data:
                error_msg = data.get('errmsg', '未知错误')
                error_code = data.get('errcode', -1)
                raise Exception(f"上传失败: [{error_code}] {error_msg}")
            
            result.update({
                'success': True,
                'media_id': data['media_id'],
                'media_url': data.get('url', ''),  # 有些接口返回URL
                'created_at': data.get('created_at', int(time.time()))
            })
            
            self.logger.info(f"图片上传成功: {image_path} -> {data['media_id']}")
            
        except FileNotFoundError as e:
            result['error'] = str(e)
            self.logger.error(f"上传失败 {image_path}: {str(e)}")
            
        except requests.exceptions.RequestException as e:
            error_msg = f"网络请求错误: {str(e)}"
            result['error'] = error_msg
            self.logger.error(f"上传失败 {image_path}: {error_msg}")
            
        except Exception as e:
            result['error'] = str(e)
            self.logger.error(f"上传失败 {image_path}: {str(e)}")
        
        return result
    
    def upload_permanent_image(self, image_path: str) -> Dict:
        """上传永久图片素材
        
        Args:
            image_path: 图片本地路径
            
        Returns:
            上传结果字典
        """
        result = {
            'local_path': image_path,
            'success': False,
            'media_id': None,
            'media_url': None,
            'error': None
        }
        
        try:
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"图片文件不存在: {image_path}")
            
            # 获取访问令牌
            access_token = self.get_access_token()
            
            file_size = os.path.getsize(image_path)
            self.logger.info(f"开始上传永久图片: {image_path} ({format_file_size(file_size)})")
            
            # 使用uploadimg接口上传永久图片
            params = {
                'access_token': access_token
            }
            
            filename = os.path.basename(image_path)
            with open(image_path, 'rb') as f:
                files = {
                    'media': (filename, f, 'image/jpeg')
                }
                
                response = self.session.post(
                    self.UPLOAD_IMG_URL,
                    params=params,
                    files=files,
                    timeout=config.REQUEST_TIMEOUT * 2
                )
                response.raise_for_status()
            
            data = response.json()
            
            if 'url' not in data:
                error_msg = data.get('errmsg', '未知错误')
                error_code = data.get('errcode', -1)
                raise Exception(f"上传失败: [{error_code}] {error_msg}")
            
            result.update({
                'success': True,
                'media_url': data['url'],
                'media_id': data.get('media_id', ''),
            })
            
            self.logger.info(f"永久图片上传成功: {image_path} -> {data['url']}")
            
        except Exception as e:
            result['error'] = str(e)
            self.logger.error(f"永久图片上传失败 {image_path}: {str(e)}")
        
        return result
    
    def upload_images_batch(self, image_paths: List[str], permanent: bool = True) -> List[Dict]:
        """批量上传图片
        
        Args:
            image_paths: 图片路径列表
            permanent: 是否上传为永久素材
            
        Returns:
            上传结果列表
        """
        if not image_paths:
            return []
        
        self.logger.info(f"开始批量上传 {len(image_paths)} 张图片 ({'永久' if permanent else '临时'}素材)")
        
        results = []
        
        # 使用进度条显示上传进度
        with tqdm(total=len(image_paths), desc="上传图片", unit="张") as pbar:
            for image_path in image_paths:
                if permanent:
                    result = self.upload_permanent_image(image_path)
                else:
                    result = self.upload_image(image_path)
                
                results.append(result)
                
                # 更新进度条
                if result['success']:
                    pbar.set_postfix(status="成功", file=os.path.basename(image_path))
                else:
                    pbar.set_postfix(status="失败", error=result['error'][:30])
                
                pbar.update(1)
                
                # 避免请求过于频繁
                time.sleep(0.1)
        
        # 统计结果
        successful = sum(1 for r in results if r['success'])
        failed = len(results) - successful
        
        self.logger.info(f"批量上传完成: 成功 {successful} 张, 失败 {failed} 张")
        
        return results
    
    def retry_failed_uploads(self, failed_results: List[Dict], permanent: bool = True, max_retries: int = None) -> List[Dict]:
        """重试失败的上传
        
        Args:
            failed_results: 失败的上传结果列表
            permanent: 是否上传为永久素材
            max_retries: 最大重试次数
            
        Returns:
            重试结果列表
        """
        if max_retries is None:
            max_retries = config.MAX_RETRIES
        
        failed_paths = [r['local_path'] for r in failed_results if not r['success']]
        if not failed_paths:
            return []
        
        self.logger.info(f"开始重试 {len(failed_paths)} 个失败的上传")
        
        retry_results = []
        
        for attempt in range(max_retries):
            if not failed_paths:
                break
            
            self.logger.info(f"第 {attempt + 1} 次重试，剩余 {len(failed_paths)} 个")
            
            # 重试上传
            current_results = self.upload_images_batch(failed_paths, permanent)
            retry_results.extend(current_results)
            
            # 更新失败列表
            failed_paths = [r['local_path'] for r in current_results if not r['success']]
            
            # 如果还有失败的，等待一段时间再重试
            if failed_paths and attempt < max_retries - 1:
                wait_time = 2 ** attempt
                self.logger.info(f"等待 {wait_time} 秒后重试")
                time.sleep(wait_time)
        
        return retry_results
    
    def get_media_info(self, media_id: str) -> Dict:
        """获取媒体文件信息
        
        Args:
            media_id: 媒体文件ID
            
        Returns:
            媒体文件信息
        """
        try:
            access_token = self.get_access_token()
            
            params = {
                'access_token': access_token,
                'media_id': media_id
            }
            
            response = self.session.get(
                "https://api.weixin.qq.com/cgi-bin/media/get",
                params=params,
                timeout=config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            
            # 如果返回的是JSON，说明有错误
            if response.headers.get('content-type', '').startswith('application/json'):
                data = response.json()
                error_msg = data.get('errmsg', '未知错误')
                error_code = data.get('errcode', -1)
                raise Exception(f"获取媒体信息失败: [{error_code}] {error_msg}")
            
            return {
                'success': True,
                'content_type': response.headers.get('content-type'),
                'content_length': response.headers.get('content-length'),
                'content': response.content
            }
            
        except Exception as e:
            self.logger.error(f"获取媒体信息失败 {media_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def __del__(self):
        """析构函数，关闭会话"""
        if hasattr(self, 'session'):
            self.session.close()