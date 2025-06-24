# MXStoreBI/app/utils/helpers.py

import os

from flask import current_app
from flask_login import current_user
from werkzeug.utils import secure_filename

# 定义允许上传的文件扩展名集合
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename):
    """
    功能：检查上传的文件名，判断其扩展名是否在允许的范围内。
    参数：
        filename (str): 用户上传的文件名。
    返回：
        bool: 如果文件扩展名合法，返回 True，否则返回 False。
    """
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_upload_file(file, report_id, attachment_type):
    """
    功能：保存用户上传的文件，并返回一个用于存入数据库的相对路径。
    核心修正：此函数解决了之前将整数 report_id 直接用于路径拼接的错误。
    参数：
        file: 从请求中获取的文件对象。
        report_id (int): 关联的报告ID，将用于创建文件夹。
        attachment_type: 附件类型（暂时未使用，但保留以备将来扩展）。
    返回：
        str: 如果保存成功，返回文件的相对路径。
        None: 如果文件不符合要求或保存失败，返回 None。
    """
    # 检查文件对象是否存在，并且文件名是否合法
    if file and allowed_file(file.filename):
        # 使用 werkzeug 提供的函数来确保文件名是安全的，防止路径注入等攻击
        filename = secure_filename(file.filename)

        # 从 Flask 的应用配置中获取上传文件夹的根目录名，例如 'uploads'
        upload_folder = current_app.config['UPLOAD_FOLDER']

        # 【关键修复】构建用于存储的相对目录路径：<user_id>/<report_id>
        # 我们在这里使用 str() 将整数类型的 user_id 和 report_id 转换成字符串，
        # 这是解决您遇到的“无法保存凭证”问题的核心所在。
        relative_dir = os.path.join(str(current_user.user_id), str(report_id))

        # 构建用于存入数据库的完整相对路径：<user_id>/<report_id>/<filename>
        relative_path = os.path.join(relative_dir, filename)

        # 构建用于在服务器上保存文件的绝对物理路径
        # app.root_path 指的是 app 包所在的目录
        absolute_dir = os.path.join(current_app.root_path, upload_folder, relative_dir)

        # 在保存文件之前，检查目标文件夹是否存在，如果不存在，则创建它
        # exist_ok=True 表示如果文件夹已存在，不要抛出错误
        os.makedirs(absolute_dir, exist_ok=True)

        # 拼接出文件的绝对保存路径
        absolute_path = os.path.join(absolute_dir, filename)

        try:
            # 执行保存操作
            file.save(absolute_path)
            # 文件保存成功后，返回相对路径，这个路径将被存入数据库
            return relative_path
        except Exception as e:
            # 如果保存过程中出现任何异常，记录错误日志，并返回 None
            current_app.logger.error(f"文件保存失败: {e}")
            return None

    # 如果文件对象不存在或文件名不合法，也返回 None
    return None