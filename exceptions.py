# -*- coding: utf-8 -*-
"""
自定义异常类
"""


class ImageReplacementError(Exception):
    """图片替换工具基础异常类"""
    pass


class ConfigurationError(ImageReplacementError):
    """配置错误"""
    pass


class DocumentProcessingError(ImageReplacementError):
    """文档处理错误"""
    pass


class ImageDownloadError(ImageReplacementError):
    """图片下载错误"""
    pass


class WeChatUploadError(ImageReplacementError):
    """微信上传错误"""
    pass


class URLReplacementError(ImageReplacementError):
    """URL替换错误"""
    pass


class NetworkError(ImageReplacementError):
    """网络错误"""
    pass


class FileOperationError(ImageReplacementError):
    """文件操作错误"""
    pass


class ValidationError(ImageReplacementError):
    """验证错误"""
    pass


class ImageAnalysisError(ImageReplacementError):
    """图片分析错误"""
    pass