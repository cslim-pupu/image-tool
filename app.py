#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片地址替换工具 - Web界面
提供用户友好的Web界面来处理文档和图片替换功能
"""

import os
import tempfile
import uuid
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, url_for
from werkzeug.utils import secure_filename
import json
import logging

# 导入现有的处理模块
from image_analyzer import ImageAnalyzer, ImageAnalysisError
from url_image_extractor import URLImageExtractor
from utils import setup_logging
from exceptions import ImageReplacementError

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# 初始化图片分析器和URL图片抓取器
image_analyzer = ImageAnalyzer()
url_extractor = URLImageExtractor()

# 设置上传文件夹
UPLOAD_FOLDER = 'uploads'
RESULT_FOLDER = 'results'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'txt', 'md', 'html', 'htm', 'docx'}

# 设置日志
setup_logging()
logger = logging.getLogger(__name__)

# 移除了文件上传相关的辅助函数

@app.route('/')
def home():
    """主页"""
    return render_template('home.html')

@app.route('/link-replacer')
def link_replacer():
    """图片链接替换工具页面"""
    return render_template('link_replacer.html')

@app.route('/image-extractor')
def image_extractor():
    """图片抓取工具页面"""
    return render_template('image_extractor.html')

@app.route('/analyze_svg', methods=['POST'])
def analyze_svg():
    """分析SVG代码中的图片"""
    try:
        data = request.get_json()
        if not data or 'svg_content' not in data:
            return jsonify({'error': 'SVG内容不能为空'}), 400
        
        svg_content = data['svg_content']
        logger.info("开始分析SVG代码中的图片")
        
        # 分析图片
        image_results = image_analyzer.analyze_svg_images(svg_content)
        
        return jsonify({
            'success': True,
            'images': image_results,
            'total_count': len(image_results),
            'large_count': sum(1 for img in image_results if img['is_large'])
        })
        
    except ImageAnalysisError as e:
        logger.error(f"SVG分析失败: {str(e)}")
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        logger.error(f"分析SVG时发生未知错误: {str(e)}")
        return jsonify({'error': f'分析失败: {str(e)}'}), 500

@app.route('/replace_url', methods=['POST'])
def replace_url():
    """替换单个图片URL"""
    try:
        data = request.get_json()
        required_fields = ['svg_content', 'old_url', 'new_url']
        
        for field in required_fields:
            if not data or field not in data:
                return jsonify({'error': f'缺少必要参数: {field}'}), 400
        
        svg_content = data['svg_content']
        old_url = data['old_url']
        new_url = data['new_url']
        
        logger.info(f"替换URL: {old_url} -> {new_url}")
        
        # 执行替换
        updated_content = image_analyzer.replace_url_in_svg(svg_content, old_url, new_url)
        
        return jsonify({
            'success': True,
            'updated_content': updated_content
        })
        
    except ImageAnalysisError as e:
        logger.error(f"URL替换失败: {str(e)}")
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        logger.error(f"替换URL时发生未知错误: {str(e)}")
        return jsonify({'error': f'替换失败: {str(e)}'}), 500

@app.route('/extract_images', methods=['POST'])
def extract_images():
    """从URL抓取图片"""
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'error': 'URL不能为空'}), 400
        
        url = data['url'].strip()
        if not url:
            return jsonify({'error': 'URL不能为空'}), 400
        
        logger.info(f"开始抓取URL图片: {url}")
        
        # 抓取图片
        images = url_extractor.extract_images_from_url(url)
        
        return jsonify({
            'success': True,
            'images': images,
            'total_count': len(images),
            'url': url
        })
        
    except Exception as e:
        logger.error(f"抓取图片失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/download_image', methods=['POST'])
def download_image():
    """下载单张图片"""
    try:
        data = request.get_json()
        if not data or 'image_info' not in data:
            return jsonify({'error': '图片信息不能为空'}), 400
        
        image_info = data['image_info']
        logger.info(f"开始下载图片: {image_info.get('url')}")
        
        # 下载图片
        downloaded_image = url_extractor.download_image(image_info)
        
        return jsonify({
            'success': True,
            'image': downloaded_image
        })
        
    except Exception as e:
        logger.error(f"下载图片失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/download_all_images', methods=['POST'])
def download_all_images():
    """批量下载所有图片"""
    try:
        data = request.get_json()
        if not data or 'images' not in data:
            return jsonify({'error': '图片列表不能为空'}), 400
        
        images = data['images']
        logger.info(f"开始批量下载 {len(images)} 张图片")
        
        # 批量下载图片
        downloaded_images = url_extractor.download_all_images(images)
        
        return jsonify({
            'success': True,
            'images': downloaded_images,
            'downloaded_count': sum(1 for img in downloaded_images if img.get('downloaded'))
        })
        
    except Exception as e:
        logger.error(f"批量下载失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/create_archive', methods=['POST'])
def create_archive():
    """创建下载压缩包"""
    try:
        data = request.get_json()
        if not data or 'images' not in data:
            return jsonify({'error': '图片列表不能为空'}), 400
        
        images = data['images']
        
        if not images:
            return jsonify({'error': '没有可打包的图片'}), 400
        
        logger.info(f"开始创建压缩包，包含 {len(images)} 张图片")
        
        # 创建压缩包
        result = url_extractor.create_download_archive(images)
        
        if result['success']:
            return jsonify({
                'success': True,
                'archive_name': result['archive_name'],
                'archive_path': result['archive_path'],
                'filename': result['archive_name'],
                'downloaded_count': result['downloaded_count']
            })
        else:
            return jsonify({'error': result['error']}), 500
        
    except Exception as e:
        logger.error(f"创建压缩包失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/download_file/<filename>')
def download_file(filename):
    """下载文件"""
    try:
        file_path = os.path.join(url_extractor.download_folder, filename)
        if not os.path.exists(file_path):
            return jsonify({'error': '文件不存在'}), 404
        
        return send_file(file_path, as_attachment=True, download_name=filename)
        
    except Exception as e:
        logger.error(f"下载文件失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

# 保留/process路由以防有其他地方调用，但简化功能
@app.route('/process', methods=['POST'])
def process_document():
    """简化的处理接口（已弃用，请使用新的SVG分析功能）"""
    return jsonify({
        'success': False,
        'error': '此功能已弃用，请使用新的SVG分析功能',
        'redirect': '/'
    }), 400

# 移除了自动微信上传功能相关代码

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': '文件太大，最大支持16MB'}), 413

@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': '服务器内部错误'}), 500

if __name__ == '__main__':
    print("🚀 图片地址替换工具 Web版本启动中...")
    print("📝 支持的文件格式: .txt, .md, .html, .htm, .docx")
    print("⚠️  请确保已正确配置微信公众号信息")
    
    # 获取端口号，优先使用环境变量（Render部署时需要）
    port = int(os.environ.get('PORT', 3000))
    print(f"🌐 访问地址: http://localhost:{port}")
    
    # 生产环境关闭debug模式
    debug_mode = os.environ.get('FLASK_ENV') != 'production'
    app.run(debug=debug_mode, host='0.0.0.0', port=port)