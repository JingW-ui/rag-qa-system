# -*- coding: utf-8 -*-
"""
图片处理工具函数 — 用于 VLM 多模态输入。
"""

import os
from io import BytesIO
from PySide6.QtCore import QByteArray, QBuffer, Qt
from PySide6.QtGui import QPixmap, QImage


MAX_IMAGE_DIMENSION = 1568  # qwen-vl 推荐的最大边长（像素）
MAX_IMAGE_BYTES = 4 * 1024 * 1024  # 4MB 单张限制
JPEG_QUALITY = 85


def load_image_from_path(file_path: str) -> QPixmap:
    """从文件路径加载图片，返回 QPixmap。"""
    pixmap = QPixmap(file_path)
    if pixmap.isNull():
        raise ValueError(f"无法加载图片: {file_path}")
    return pixmap


def load_image_from_bytes(data: bytes) -> QPixmap:
    """从字节数据加载图片，返回 QPixmap。"""
    pixmap = QPixmap()
    if not pixmap.loadFromData(data):
        raise ValueError("无法从字节数据加载图片")
    return pixmap


def resize_pixmap(pixmap: QPixmap, max_dim: int = MAX_IMAGE_DIMENSION) -> QPixmap:
    """等比缩放，使最大边不超过 max_dim。"""
    w, h = pixmap.width(), pixmap.height()
    if w <= max_dim and h <= max_dim:
        return pixmap  # 不需要缩放
    scale = max_dim / max(w, h)
    new_w = int(w * scale)
    new_h = int(h * scale)
    return pixmap.scaled(new_w, new_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)


def pixmap_to_bytes(pixmap: QPixmap, quality: int = JPEG_QUALITY) -> bytes:
    """将 QPixmap 转为 JPEG 字节数据。"""
    # 转 QImage 以便 save 到 BytesIO
    image = pixmap.toImage()
    # 转 RGB888 去除 alpha 通道（JPEG 不支持透明）
    image = image.convertToFormat(QImage.Format_RGB888)
    byte_array = QByteArray()
    buffer = QBuffer(byte_array)
    buffer.open(QBuffer.WriteOnly)
    image.save(buffer, "JPEG", quality)
    buffer.close()
    return bytes(byte_array)


def prepare_image(file_path: str) -> bytes:
    """加载、缩放、压缩，返回 JPEG 字节。

    这是给 UI 层用的统一入口：从路径到可用的字节。
    """
    pixmap = load_image_from_path(file_path)
    pixmap = resize_pixmap(pixmap)
    return pixmap_to_bytes(pixmap)


def prepare_image_from_bytes(data: bytes) -> bytes:
    """从剪贴板/拖拽得到的字节数据，处理后返回 JPEG 字节。"""
    pixmap = load_image_from_bytes(data)
    pixmap = resize_pixmap(pixmap)
    return pixmap_to_bytes(pixmap)


def bytes_to_base64_url(data: bytes, mime: str = "image/jpeg") -> str:
    """将字节数据转为 data URL（base64 编码），用于 OpenAI Vision API。"""
    import base64
    b64 = base64.b64encode(data).decode("utf-8")
    return f"data:{mime};base64,{b64}"


def get_image_dimensions(data: bytes) -> tuple[int, int]:
    """从字节数据获取图片尺寸。"""
    pixmap = load_image_from_bytes(data)
    return pixmap.width(), pixmap.height()
