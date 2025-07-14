"""
销售相关上传文件视图
"""
import os
from flask import current_app

def save_attachment(form_field, report_id, attachment_type):
    """
    辅助函数：保存上传的文件并创建 DailySalesAttachments 记录。
    1. 上传文件保存到 static/uploads 目录下
    2. 若 static/uploads 不存在则自动创建
    3. 数据库存储相对路径，便于前端展示
    支持多文件上传：form_field.data 可能为 FileStorage 或 list[FileStorage]
    """
    files = form_field.data
    if not files:
        return
    if not isinstance(files, list):
        files = [files]
    upload_folder = os.path.join(current_app.static_folder, 'uploads')
    os.makedirs(upload_folder, exist_ok=True)
    for file in files:
        # 这里应有实际的文件保存逻辑，略
        pass
