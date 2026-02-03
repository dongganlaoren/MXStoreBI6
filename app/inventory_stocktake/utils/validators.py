from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Optional

ALLOWED_OPERATION_TYPES = {"新增", "更新"}
ALLOWED_STATUS = {"启用", "禁用"}


class ValidationError(ValueError):
    """用于在页面友好展示的校验异常。"""


def require_non_empty(value: Any, field_name: str) -> str:
    if value is None:
        raise ValidationError(f"{field_name}不能为空")
    s = str(value).strip()
    if not s:
        raise ValidationError(f"{field_name}不能为空")
    return s


def parse_non_negative_int(value: Any, field_name: str) -> int:
    if value is None or str(value).strip() == "":
        raise ValidationError(f"{field_name}不能为空")
    try:
        i = int(str(value).strip())
    except Exception as e:
        raise ValidationError(f"{field_name}必须为整数") from e
    if i < 0:
        raise ValidationError(f"{field_name}必须为非负整数")
    return i


def parse_non_negative_decimal(value: Any, field_name: str, scale: int = 2) -> Decimal:
    if value is None or str(value).strip() == "":
        raise ValidationError(f"{field_name}不能为空")
    try:
        d = Decimal(str(value).strip())
    except (InvalidOperation, ValueError) as e:
        raise ValidationError(f"{field_name}必须为数字") from e
    if d < 0:
        raise ValidationError(f"{field_name}必须为非负数")
    q = Decimal("1." + "0" * scale)
    return d.quantize(q)


def validate_operation_type(value: Any) -> str:
    v = require_non_empty(value, "操作类型")
    if v not in ALLOWED_OPERATION_TYPES:
        raise ValidationError(f"操作类型必须为：{' / '.join(sorted(ALLOWED_OPERATION_TYPES))}")
    return v


def validate_status(value: Any) -> str:
    v = require_non_empty(value, "状态")
    if v not in ALLOWED_STATUS:
        raise ValidationError(f"状态必须为：{' / '.join(sorted(ALLOWED_STATUS))}")
    return v


def validate_product_image(value: Any) -> Optional[str]:
    """产品图片字段预留：仅校验为文本，长度不超过 255。"""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    if len(s) > 255:
        raise ValidationError("产品图片长度不能超过255")
    return s
