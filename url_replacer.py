# -*- coding: utf-8 -*-
"""
URL替换模块
"""

import os
import re
import logging
import shutil
from typing import Dict, List, Optional
from pathlib import Path

from bs4 import BeautifulSoup


class URLReplacer:
    """URL替换器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def replace_urls_in_file(self, file_path: str, url_mapping: Dict[str, str], 
                           output_path: Optional[str] = None, backup: bool = True) -> Dict:
        """替换文件中的图片URL
        
        Args:
            file_path: 原文件路径
            url_mapping: URL映射字典 {原始URL: 新URL}
            output_path: 输出文件路径，如果为None则覆盖原文件
            backup: 是否备份原文件
            
        Returns:
            替换结果字典
        """
        result = {
            'file_path': file_path,
            'output_path': output_path or file_path,
            'success': False,
            'replacements': 0,
            'backup_path': None,
            'error': None
        }
        
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"文件不存在: {file_path}")
            
            if not url_mapping:
                raise ValueError("URL映射不能为空")
            
            # 创建备份
            if backup and (output_path is None or output_path == file_path):
                backup_path = f"{file_path}.backup"
                shutil.copy2(file_path, backup_path)
                result['backup_path'] = backup_path
                self.logger.info(f"已创建备份文件: {backup_path}")
            
            # 读取文件内容
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
            
            # 获取文件扩展名以确定处理方式
            file_ext = Path(file_path).suffix.lower()
            
            # 执行替换
            if file_ext in ['.html', '.htm']:
                new_content, replacements = self._replace_urls_in_html(content, url_mapping)
            elif file_ext == '.md':
                new_content, replacements = self._replace_urls_in_markdown(content, url_mapping)
            else:
                new_content, replacements = self._replace_urls_in_text(content, url_mapping)
            
            # 写入新内容
            output_file = output_path or file_path
            
            # 确保输出目录存在
            os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            result.update({
                'success': True,
                'replacements': replacements
            })
            
            self.logger.info(f"URL替换完成: {file_path} -> {output_file}, 替换了 {replacements} 个URL")
            
        except Exception as e:
            result['error'] = str(e)
            self.logger.error(f"URL替换失败 {file_path}: {str(e)}")
        
        return result
    
    def _replace_urls_in_text(self, content: str, url_mapping: Dict[str, str]) -> tuple:
        """在纯文本中替换URL
        
        Args:
            content: 文本内容
            url_mapping: URL映射字典
            
        Returns:
            (新内容, 替换次数)
        """
        new_content = content
        replacements = 0
        
        for old_url, new_url in url_mapping.items():
            # 精确匹配URL
            if old_url in new_content:
                new_content = new_content.replace(old_url, new_url)
                replacements += content.count(old_url)
        
        return new_content, replacements
    
    def _replace_urls_in_markdown(self, content: str, url_mapping: Dict[str, str]) -> tuple:
        """在Markdown中替换URL
        
        Args:
            content: Markdown内容
            url_mapping: URL映射字典
            
        Returns:
            (新内容, 替换次数)
        """
        new_content = content
        replacements = 0
        
        for old_url, new_url in url_mapping.items():
            # 替换Markdown图片语法中的URL
            md_pattern = r'(!\[.*?\]\()' + re.escape(old_url) + r'(\))'
            matches = re.findall(md_pattern, new_content)
            if matches:
                new_content = re.sub(md_pattern, r'\1' + new_url + r'\2', new_content)
                replacements += len(matches)
            
            # 替换HTML img标签中的URL
            img_pattern = r'(<img[^>]+src=["\']?)' + re.escape(old_url) + r'(["\']?[^>]*>)'
            matches = re.findall(img_pattern, new_content, re.IGNORECASE)
            if matches:
                new_content = re.sub(img_pattern, r'\1' + new_url + r'\2', new_content, flags=re.IGNORECASE)
                replacements += len(matches)
            
            # 替换普通URL
            if old_url in new_content:
                count = new_content.count(old_url)
                new_content = new_content.replace(old_url, new_url)
                replacements += count
        
        return new_content, replacements
    
    def _replace_urls_in_html(self, content: str, url_mapping: Dict[str, str]) -> tuple:
        """在HTML中替换URL
        
        Args:
            content: HTML内容
            url_mapping: URL映射字典
            
        Returns:
            (新内容, 替换次数)
        """
        replacements = 0
        
        try:
            soup = BeautifulSoup(content, 'html.parser')
            
            # 替换img标签的src属性
            img_tags = soup.find_all('img')
            for img in img_tags:
                src = img.get('src')
                if src and src in url_mapping:
                    img['src'] = url_mapping[src]
                    replacements += 1
                
                # 替换data-src属性（懒加载图片）
                data_src = img.get('data-src')
                if data_src and data_src in url_mapping:
                    img['data-src'] = url_mapping[data_src]
                    replacements += 1
            
            # 替换CSS背景图片
            style_tags = soup.find_all(['style', 'link'])
            for tag in style_tags:
                if tag.name == 'style' and tag.string:
                    new_css = tag.string
                    for old_url, new_url in url_mapping.items():
                        if old_url in new_css:
                            new_css = new_css.replace(old_url, new_url)
                            replacements += 1
                    tag.string = new_css
            
            # 替换内联样式
            elements_with_style = soup.find_all(attrs={'style': True})
            for element in elements_with_style:
                style = element.get('style', '')
                new_style = style
                for old_url, new_url in url_mapping.items():
                    if old_url in new_style:
                        new_style = new_style.replace(old_url, new_url)
                        replacements += 1
                if new_style != style:
                    element['style'] = new_style
            
            new_content = str(soup)
            
        except Exception as e:
            self.logger.warning(f"HTML解析失败，使用文本替换: {str(e)}")
            # 备用方案：使用文本替换
            new_content, replacements = self._replace_urls_in_text(content, url_mapping)
        
        return new_content, replacements
    
    def replace_urls_in_directory(self, directory_path: str, url_mapping: Dict[str, str],
                                output_directory: Optional[str] = None, 
                                recursive: bool = True, backup: bool = True) -> List[Dict]:
        """替换目录中所有文件的URL
        
        Args:
            directory_path: 源目录路径
            url_mapping: URL映射字典
            output_directory: 输出目录路径，如果为None则覆盖原文件
            recursive: 是否递归处理子目录
            backup: 是否备份原文件
            
        Returns:
            替换结果列表
        """
        if not os.path.exists(directory_path):
            raise FileNotFoundError(f"目录不存在: {directory_path}")
        
        if not os.path.isdir(directory_path):
            raise ValueError(f"路径不是目录: {directory_path}")
        
        self.logger.info(f"开始替换目录中的URL: {directory_path}")
        
        results = []
        supported_formats = ['.txt', '.md', '.html', '.htm']
        
        # 遍历目录
        if recursive:
            for root, dirs, files in os.walk(directory_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    if Path(file_path).suffix.lower() in supported_formats:
                        # 计算输出路径
                        if output_directory:
                            rel_path = os.path.relpath(file_path, directory_path)
                            output_path = os.path.join(output_directory, rel_path)
                        else:
                            output_path = None
                        
                        result = self.replace_urls_in_file(file_path, url_mapping, output_path, backup)
                        results.append(result)
        else:
            for file in os.listdir(directory_path):
                file_path = os.path.join(directory_path, file)
                if os.path.isfile(file_path) and Path(file_path).suffix.lower() in supported_formats:
                    # 计算输出路径
                    if output_directory:
                        output_path = os.path.join(output_directory, file)
                    else:
                        output_path = None
                    
                    result = self.replace_urls_in_file(file_path, url_mapping, output_path, backup)
                    results.append(result)
        
        # 统计结果
        successful_files = sum(1 for r in results if r['success'])
        total_replacements = sum(r['replacements'] for r in results if r['success'])
        
        self.logger.info(f"目录URL替换完成: 处理了 {len(results)} 个文件，成功 {successful_files} 个，共替换 {total_replacements} 个URL")
        
        return results
    
    def create_replacement_report(self, results: List[Dict]) -> str:
        """创建替换报告
        
        Args:
            results: 替换结果列表
            
        Returns:
            报告文本
        """
        successful_files = [r for r in results if r['success']]
        failed_files = [r for r in results if not r['success']]
        
        total_replacements = sum(r['replacements'] for r in successful_files)
        
        report = []
        report.append("=" * 50)
        report.append("URL替换报告")
        report.append("=" * 50)
        report.append(f"总文件数: {len(results)}")
        report.append(f"成功处理: {len(successful_files)}")
        report.append(f"处理失败: {len(failed_files)}")
        report.append(f"总替换次数: {total_replacements}")
        report.append("")
        
        if successful_files:
            report.append("成功处理的文件:")
            report.append("-" * 30)
            for result in successful_files:
                report.append(f"  {result['file_path']} -> 替换 {result['replacements']} 个URL")
                if result['backup_path']:
                    report.append(f"    备份: {result['backup_path']}")
            report.append("")
        
        if failed_files:
            report.append("处理失败的文件:")
            report.append("-" * 30)
            for result in failed_files:
                report.append(f"  {result['file_path']} - 错误: {result['error']}")
            report.append("")
        
        report.append("=" * 50)
        
        return "\n".join(report)
    
    def validate_url_mapping(self, url_mapping: Dict[str, str]) -> Dict:
        """验证URL映射
        
        Args:
            url_mapping: URL映射字典
            
        Returns:
            验证结果字典
        """
        result = {
            'valid': True,
            'total_mappings': len(url_mapping),
            'valid_mappings': 0,
            'invalid_mappings': [],
            'warnings': []
        }
        
        for old_url, new_url in url_mapping.items():
            is_valid = True
            
            # 检查URL格式
            if not old_url or not isinstance(old_url, str):
                result['invalid_mappings'].append((old_url, new_url, "原始URL无效"))
                is_valid = False
            
            if not new_url or not isinstance(new_url, str):
                result['invalid_mappings'].append((old_url, new_url, "新URL无效"))
                is_valid = False
            
            if is_valid:
                result['valid_mappings'] += 1
                
                # 检查URL是否相同
                if old_url == new_url:
                    result['warnings'].append(f"URL相同，无需替换: {old_url}")
        
        if result['invalid_mappings']:
            result['valid'] = False
        
        return result
    
    def restore_from_backup(self, file_path: str) -> bool:
        """从备份恢复文件
        
        Args:
            file_path: 原文件路径
            
        Returns:
            是否成功恢复
        """
        backup_path = f"{file_path}.backup"
        
        try:
            if not os.path.exists(backup_path):
                self.logger.error(f"备份文件不存在: {backup_path}")
                return False
            
            shutil.copy2(backup_path, file_path)
            self.logger.info(f"已从备份恢复文件: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"恢复文件失败 {file_path}: {str(e)}")
            return False
    
    def cleanup_backups(self, directory_path: str, recursive: bool = True):
        """清理备份文件
        
        Args:
            directory_path: 目录路径
            recursive: 是否递归清理
        """
        self.logger.info(f"开始清理备份文件: {directory_path}")
        
        cleaned_count = 0
        
        if recursive:
            for root, dirs, files in os.walk(directory_path):
                for file in files:
                    if file.endswith('.backup'):
                        backup_path = os.path.join(root, file)
                        try:
                            os.remove(backup_path)
                            cleaned_count += 1
                            self.logger.debug(f"已删除备份文件: {backup_path}")
                        except Exception as e:
                            self.logger.warning(f"删除备份文件失败 {backup_path}: {str(e)}")
        else:
            for file in os.listdir(directory_path):
                if file.endswith('.backup'):
                    backup_path = os.path.join(directory_path, file)
                    if os.path.isfile(backup_path):
                        try:
                            os.remove(backup_path)
                            cleaned_count += 1
                            self.logger.debug(f"已删除备份文件: {backup_path}")
                        except Exception as e:
                            self.logger.warning(f"删除备份文件失败 {backup_path}: {str(e)}")
        
        self.logger.info(f"备份文件清理完成，共清理 {cleaned_count} 个文件")