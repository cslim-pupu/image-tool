#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片地址替换工具 - 主程序

这个工具可以：
1. 从文档中提取图片URL
2. 下载图片到本地
3. 上传图片到微信公众号
4. 替换文档中的图片地址为公众号地址
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Optional

import click
from colorama import init, Fore, Style
from tqdm import tqdm

# 初始化colorama
init()

# 导入自定义模块
from utils import setup_logging, create_directories
from document_processor import DocumentProcessor
from image_downloader import ImageDownloader
from wechat_uploader import WeChatUploader
from url_replacer import URLReplacer
import config


class ImageReplacementTool:
    """图片地址替换工具主类"""
    
    def __init__(self):
        self.logger = setup_logging()
        create_directories()
        
        self.doc_processor = DocumentProcessor()
        self.downloader = ImageDownloader()
        self.uploader = None  # 延迟初始化
        self.replacer = URLReplacer()
        
        self.logger.info("图片地址替换工具已启动")
    
    def initialize_wechat_uploader(self, appid: str = None, secret: str = None) -> bool:
        """初始化微信上传器
        
        Args:
            appid: 微信公众号AppID
            secret: 微信公众号AppSecret
            
        Returns:
            是否初始化成功
        """
        try:
            self.uploader = WeChatUploader(appid, secret)
            # 测试获取访问令牌
            self.uploader.get_access_token()
            self.logger.info("微信上传器初始化成功")
            return True
        except Exception as e:
            self.logger.error(f"微信上传器初始化失败: {str(e)}")
            return False
    
    def extract_images_from_source(self, source_path: str, recursive: bool = True) -> List[str]:
        """从源文件或目录提取图片URL
        
        Args:
            source_path: 源文件或目录路径
            recursive: 是否递归处理目录
            
        Returns:
            图片URL列表
        """
        self.logger.info(f"开始提取图片URL: {source_path}")
        
        if os.path.isfile(source_path):
            # 处理单个文件
            result = self.doc_processor.extract_images_from_file(source_path)
            if result['success']:
                return result['image_urls']
            else:
                self.logger.error(f"提取失败: {result['error']}")
                return []
        
        elif os.path.isdir(source_path):
            # 处理目录
            results = self.doc_processor.extract_images_from_directory(source_path, recursive)
            return self.doc_processor.get_all_unique_urls(results)
        
        else:
            self.logger.error(f"路径不存在: {source_path}")
            return []
    
    def download_images(self, image_urls: List[str], max_workers: int = 5) -> Dict[str, str]:
        """下载图片并返回URL到本地路径的映射
        
        Args:
            image_urls: 图片URL列表
            max_workers: 最大并发数
            
        Returns:
            URL到本地路径的映射字典
        """
        if not image_urls:
            self.logger.warning("没有图片URL需要下载")
            return {}
        
        self.logger.info(f"开始下载 {len(image_urls)} 张图片")
        
        # 批量下载
        results = self.downloader.download_images_batch(image_urls, max_workers)
        
        # 重试失败的下载
        failed_results = [r for r in results if not r['success']]
        if failed_results:
            self.logger.info(f"重试 {len(failed_results)} 个失败的下载")
            retry_results = self.downloader.retry_failed_downloads(failed_results)
            results.extend(retry_results)
        
        # 创建URL到本地路径的映射
        url_to_path = {}
        for result in results:
            if result['success']:
                url_to_path[result['url']] = result['local_path']
        
        successful_count = len(url_to_path)
        self.logger.info(f"图片下载完成: 成功 {successful_count}/{len(image_urls)} 张")
        
        return url_to_path
    
    def upload_images_to_wechat(self, local_paths: List[str], permanent: bool = True) -> Dict[str, str]:
        """上传图片到微信公众号
        
        Args:
            local_paths: 本地图片路径列表
            permanent: 是否上传为永久素材
            
        Returns:
            本地路径到微信URL的映射字典
        """
        if not self.uploader:
            raise ValueError("微信上传器未初始化")
        
        if not local_paths:
            self.logger.warning("没有图片需要上传")
            return {}
        
        self.logger.info(f"开始上传 {len(local_paths)} 张图片到微信公众号")
        
        # 批量上传
        results = self.uploader.upload_images_batch(local_paths, permanent)
        
        # 重试失败的上传
        failed_results = [r for r in results if not r['success']]
        if failed_results:
            self.logger.info(f"重试 {len(failed_results)} 个失败的上传")
            retry_results = self.uploader.retry_failed_uploads(failed_results, permanent)
            results.extend(retry_results)
        
        # 创建本地路径到微信URL的映射
        path_to_wechat_url = {}
        for result in results:
            if result['success']:
                wechat_url = result.get('media_url') or f"https://mmbiz.qpic.cn/mmbiz_jpg/{result['media_id']}/0"
                path_to_wechat_url[result['local_path']] = wechat_url
        
        successful_count = len(path_to_wechat_url)
        self.logger.info(f"图片上传完成: 成功 {successful_count}/{len(local_paths)} 张")
        
        return path_to_wechat_url
    
    def replace_urls_in_documents(self, source_path: str, url_mapping: Dict[str, str],
                                output_path: str = None, backup: bool = True) -> List[Dict]:
        """替换文档中的图片URL
        
        Args:
            source_path: 源文件或目录路径
            url_mapping: URL映射字典
            output_path: 输出路径
            backup: 是否备份原文件
            
        Returns:
            替换结果列表
        """
        if not url_mapping:
            self.logger.warning("没有URL映射，跳过替换")
            return []
        
        self.logger.info(f"开始替换文档中的图片URL: {source_path}")
        
        if os.path.isfile(source_path):
            # 处理单个文件
            result = self.replacer.replace_urls_in_file(source_path, url_mapping, output_path, backup)
            return [result]
        
        elif os.path.isdir(source_path):
            # 处理目录
            return self.replacer.replace_urls_in_directory(source_path, url_mapping, output_path, True, backup)
        
        else:
            self.logger.error(f"路径不存在: {source_path}")
            return []
    
    def run_complete_workflow(self, source_path: str, output_path: str = None,
                            appid: str = None, secret: str = None,
                            max_workers: int = 5, backup: bool = True,
                            permanent: bool = True, save_mapping: bool = True) -> bool:
        """运行完整的工作流程
        
        Args:
            source_path: 源文件或目录路径
            output_path: 输出路径
            appid: 微信公众号AppID
            secret: 微信公众号AppSecret
            max_workers: 最大并发数
            backup: 是否备份原文件
            permanent: 是否上传为永久素材
            save_mapping: 是否保存URL映射
            
        Returns:
            是否成功完成
        """
        try:
            # 1. 初始化微信上传器
            if not self.initialize_wechat_uploader(appid, secret):
                return False
            
            # 2. 提取图片URL
            click.echo(f"{Fore.CYAN}步骤 1/5: 提取图片URL...{Style.RESET_ALL}")
            image_urls = self.extract_images_from_source(source_path)
            if not image_urls:
                click.echo(f"{Fore.YELLOW}没有找到图片URL{Style.RESET_ALL}")
                return True
            
            click.echo(f"{Fore.GREEN}找到 {len(image_urls)} 个图片URL{Style.RESET_ALL}")
            
            # 3. 下载图片
            click.echo(f"{Fore.CYAN}步骤 2/5: 下载图片...{Style.RESET_ALL}")
            url_to_path = self.download_images(image_urls, max_workers)
            if not url_to_path:
                click.echo(f"{Fore.RED}没有成功下载任何图片{Style.RESET_ALL}")
                return False
            
            # 4. 上传到微信公众号
            click.echo(f"{Fore.CYAN}步骤 3/5: 上传到微信公众号...{Style.RESET_ALL}")
            local_paths = list(url_to_path.values())
            path_to_wechat_url = self.upload_images_to_wechat(local_paths, permanent)
            if not path_to_wechat_url:
                click.echo(f"{Fore.RED}没有成功上传任何图片{Style.RESET_ALL}")
                return False
            
            # 5. 创建URL映射
            click.echo(f"{Fore.CYAN}步骤 4/5: 创建URL映射...{Style.RESET_ALL}")
            url_mapping = {}
            for original_url, local_path in url_to_path.items():
                if local_path in path_to_wechat_url:
                    url_mapping[original_url] = path_to_wechat_url[local_path]
            
            if save_mapping:
                mapping_file = 'url_mapping.json'
                with open(mapping_file, 'w', encoding='utf-8') as f:
                    json.dump(url_mapping, f, ensure_ascii=False, indent=2)
                click.echo(f"{Fore.GREEN}URL映射已保存到: {mapping_file}{Style.RESET_ALL}")
            
            # 6. 替换文档中的URL
            click.echo(f"{Fore.CYAN}步骤 5/5: 替换文档中的URL...{Style.RESET_ALL}")
            replace_results = self.replace_urls_in_documents(source_path, url_mapping, output_path, backup)
            
            # 生成报告
            report = self.replacer.create_replacement_report(replace_results)
            click.echo(f"{Fore.GREEN}\n{report}{Style.RESET_ALL}")
            
            # 保存报告
            report_file = 'replacement_report.txt'
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)
            click.echo(f"{Fore.GREEN}详细报告已保存到: {report_file}{Style.RESET_ALL}")
            
            click.echo(f"{Fore.GREEN}\n✅ 工作流程完成！{Style.RESET_ALL}")
            return True
            
        except Exception as e:
            self.logger.error(f"工作流程执行失败: {str(e)}")
            click.echo(f"{Fore.RED}❌ 工作流程失败: {str(e)}{Style.RESET_ALL}")
            return False


# CLI命令定义
@click.group()
@click.version_option(version='1.0.0')
def cli():
    """图片地址替换工具 - 将文档中的图片地址替换为微信公众号地址"""
    pass


@cli.command()
@click.argument('source_path', type=click.Path(exists=True))
@click.option('--output', '-o', help='输出路径')
@click.option('--appid', help='微信公众号AppID')
@click.option('--secret', help='微信公众号AppSecret')
@click.option('--workers', '-w', default=5, help='最大并发数')
@click.option('--no-backup', is_flag=True, help='不备份原文件')
@click.option('--temporary', is_flag=True, help='上传为临时素材')
@click.option('--no-save-mapping', is_flag=True, help='不保存URL映射')
def run(source_path, output, appid, secret, workers, no_backup, temporary, no_save_mapping):
    """运行完整的图片地址替换流程"""
    tool = ImageReplacementTool()
    
    success = tool.run_complete_workflow(
        source_path=source_path,
        output_path=output,
        appid=appid,
        secret=secret,
        max_workers=workers,
        backup=not no_backup,
        permanent=not temporary,
        save_mapping=not no_save_mapping
    )
    
    sys.exit(0 if success else 1)


@cli.command()
@click.argument('source_path', type=click.Path(exists=True))
def extract(source_path):
    """从文档中提取图片URL"""
    tool = ImageReplacementTool()
    
    image_urls = tool.extract_images_from_source(source_path)
    
    if image_urls:
        click.echo(f"{Fore.GREEN}找到 {len(image_urls)} 个图片URL:{Style.RESET_ALL}")
        for i, url in enumerate(image_urls, 1):
            click.echo(f"{i:3d}. {url}")
        
        # 保存到文件
        output_file = 'extracted_urls.txt'
        with open(output_file, 'w', encoding='utf-8') as f:
            for url in image_urls:
                f.write(url + '\n')
        click.echo(f"{Fore.GREEN}\nURL列表已保存到: {output_file}{Style.RESET_ALL}")
    else:
        click.echo(f"{Fore.YELLOW}没有找到图片URL{Style.RESET_ALL}")


@cli.command()
@click.argument('urls_file', type=click.Path(exists=True))
@click.option('--workers', '-w', default=5, help='最大并发数')
def download(urls_file, workers):
    """从文件中读取URL并下载图片"""
    tool = ImageReplacementTool()
    
    # 读取URL列表
    with open(urls_file, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip()]
    
    if not urls:
        click.echo(f"{Fore.YELLOW}文件中没有找到URL{Style.RESET_ALL}")
        return
    
    click.echo(f"{Fore.CYAN}开始下载 {len(urls)} 张图片...{Style.RESET_ALL}")
    url_to_path = tool.download_images(urls, workers)
    
    if url_to_path:
        click.echo(f"{Fore.GREEN}成功下载 {len(url_to_path)} 张图片{Style.RESET_ALL}")
        
        # 保存映射
        mapping_file = 'download_mapping.json'
        with open(mapping_file, 'w', encoding='utf-8') as f:
            json.dump(url_to_path, f, ensure_ascii=False, indent=2)
        click.echo(f"{Fore.GREEN}下载映射已保存到: {mapping_file}{Style.RESET_ALL}")
    else:
        click.echo(f"{Fore.RED}没有成功下载任何图片{Style.RESET_ALL}")


@cli.command()
@click.argument('images_dir', type=click.Path(exists=True))
@click.option('--appid', help='微信公众号AppID')
@click.option('--secret', help='微信公众号AppSecret')
@click.option('--temporary', is_flag=True, help='上传为临时素材')
def upload(images_dir, appid, secret, temporary):
    """上传图片到微信公众号"""
    tool = ImageReplacementTool()
    
    if not tool.initialize_wechat_uploader(appid, secret):
        click.echo(f"{Fore.RED}微信上传器初始化失败{Style.RESET_ALL}")
        return
    
    # 获取图片文件列表
    image_files = []
    for ext in config.SUPPORTED_FORMATS:
        pattern = f"*{ext}"
        image_files.extend(Path(images_dir).glob(pattern))
    
    local_paths = [str(p) for p in image_files]
    
    if not local_paths:
        click.echo(f"{Fore.YELLOW}目录中没有找到图片文件{Style.RESET_ALL}")
        return
    
    click.echo(f"{Fore.CYAN}开始上传 {len(local_paths)} 张图片...{Style.RESET_ALL}")
    path_to_wechat_url = tool.upload_images_to_wechat(local_paths, not temporary)
    
    if path_to_wechat_url:
        click.echo(f"{Fore.GREEN}成功上传 {len(path_to_wechat_url)} 张图片{Style.RESET_ALL}")
        
        # 保存映射
        mapping_file = 'upload_mapping.json'
        with open(mapping_file, 'w', encoding='utf-8') as f:
            json.dump(path_to_wechat_url, f, ensure_ascii=False, indent=2)
        click.echo(f"{Fore.GREEN}上传映射已保存到: {mapping_file}{Style.RESET_ALL}")
    else:
        click.echo(f"{Fore.RED}没有成功上传任何图片{Style.RESET_ALL}")


@cli.command()
@click.argument('source_path', type=click.Path(exists=True))
@click.argument('mapping_file', type=click.Path(exists=True))
@click.option('--output', '-o', help='输出路径')
@click.option('--no-backup', is_flag=True, help='不备份原文件')
def replace(source_path, mapping_file, output, no_backup):
    """使用映射文件替换文档中的URL"""
    tool = ImageReplacementTool()
    
    # 读取URL映射
    with open(mapping_file, 'r', encoding='utf-8') as f:
        url_mapping = json.load(f)
    
    if not url_mapping:
        click.echo(f"{Fore.YELLOW}映射文件为空{Style.RESET_ALL}")
        return
    
    click.echo(f"{Fore.CYAN}开始替换URL，共 {len(url_mapping)} 个映射...{Style.RESET_ALL}")
    results = tool.replace_urls_in_documents(source_path, url_mapping, output, not no_backup)
    
    # 生成报告
    report = tool.replacer.create_replacement_report(results)
    click.echo(f"{Fore.GREEN}\n{report}{Style.RESET_ALL}")


if __name__ == '__main__':
    cli()