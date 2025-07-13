#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试附件查看功能的脚本
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models import DailySales, Store
from app.models.attachment import DailySalesAttachments
from app.models.enums import AttachmentType
from datetime import date

def test_attachment_display():
    """测试附件显示功能"""
    from config import DevelopmentConfig
    app = create_app(DevelopmentConfig)
    
    with app.app_context():
        # 1. 查找一个有附件的日报
        daily_sales_with_attachments = DailySales.query.join(
            DailySalesAttachments
        ).first()
        
        if daily_sales_with_attachments:
            print(f"找到日报 ID: {daily_sales_with_attachments.report_id}")
            print(f"店铺: {daily_sales_with_attachments.store_id}")
            print(f"日期: {daily_sales_with_attachments.report_date}")
            
            # 查看附件
            attachments = daily_sales_with_attachments.attachments.all()
            print(f"附件数量: {len(attachments)}")
            
            for attachment in attachments:
                print(f"  - 类型: {attachment.attachment_type}")
                print(f"  - 路径: {attachment.file_path}")
                print(f"  - 创建时间: {attachment.created_at}")
                
            # 测试不同类型的附件过滤
            sales_slip_attachments = daily_sales_with_attachments.attachments.filter_by(
                attachment_type=AttachmentType.sales_slip
            ).all()
            print(f"POS机小票附件数量: {len(sales_slip_attachments)}")
            
            takeaway_attachments = daily_sales_with_attachments.attachments.filter_by(
                attachment_type=AttachmentType.takeaway_screenshot
            ).all()
            print(f"外卖凭证附件数量: {len(takeaway_attachments)}")
            
            bank_attachments = daily_sales_with_attachments.attachments.filter_by(
                attachment_type=AttachmentType.bank_receipt
            ).all()
            print(f"银行凭证附件数量: {len(bank_attachments)}")
            
            electronic_attachments = daily_sales_with_attachments.attachments.filter_by(
                attachment_type=AttachmentType.electronic_actual_arrival_receipt
            ).all()
            print(f"电子支付凭证附件数量: {len(electronic_attachments)}")
            
        else:
            print("没有找到包含附件的日报")
            
        # 2. 测试字段标签更新
        print("\n=== 测试字段标签 ===")
        from app.forms.sales_forms import SalesForm
        form = SalesForm()
        print(f"第三方外卖平台收入字段标签: {form.takeaway_platform_sales.label.text}")
        
        print("\n测试完成！")

if __name__ == '__main__':
    test_attachment_display()
