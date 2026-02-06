from __future__ import annotations

import ast
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
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


def _safe_eval_arithmetic(expr: str) -> Decimal:
    """Safely evaluate a simple arithmetic expression and return Decimal.

    Allowed:
        numbers, +, -, *, /, parentheses.

    Raises:
        ValidationError if expression contains anything else.
    """

    try:
        node = ast.parse(expr, mode="eval")
    except Exception as e:
        raise ValidationError(f"表达式格式错误：{expr!r}") from e

    def _eval(n: ast.AST) -> Decimal:
        if isinstance(n, ast.Expression):
            return _eval(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return Decimal(str(n.value))
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.UAdd, ast.USub)):
            v = _eval(n.operand)
            return v if isinstance(n.op, ast.UAdd) else -v
        if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
            a = _eval(n.left)
            b = _eval(n.right)
            if isinstance(n.op, ast.Add):
                return a + b
            if isinstance(n.op, ast.Sub):
                return a - b
            if isinstance(n.op, ast.Mult):
                return a * b
            if isinstance(n.op, ast.Div):
                return a / b
        raise ValidationError(f"不支持的表达式：{expr!r}")

    return _eval(node)


def parse_non_negative_decimal(value: Any, field_name: str, scale: int = 2) -> Decimal:
    """Parse a non-negative decimal.

    Excel/用户输入可能出现：
    - float (openpyxl 读出的数字类型)
    - 字符串包含千分位(1,234.56)
    - 不可见空格（\u00a0）
    - 小数位很多（168.3333333）

    我们允许上述情况，并按 scale（默认 2 位）四舍五入存储。
    """

    if value is None:
        raise ValidationError(f"{field_name}不能为空")

    # openpyxl 读到的数字通常是 int/float；float 直接 str() 有时会变科学计数法
    if isinstance(value, (int, float, Decimal)):
        s = format(value, ".15g")
    else:
        s = str(value)

    s = s.replace("\u00a0", " ").strip()
    if s == "":
        raise ValidationError(f"{field_name}不能为空")

    # 允许千分位
    s = s.replace(",", "")

    # 允许 Excel 公式样式的字符串，如："=1140/1"
    if s.startswith("="):
        expr = s.lstrip("=").strip()
        d = _safe_eval_arithmetic(expr)
    else:
        try:
            d = Decimal(s)
        except (InvalidOperation, ValueError) as e:
            raise ValidationError(f"{field_name}必须为数字（原始值={value!r}, 类型={type(value).__name__}）") from e

    if d < 0:
        raise ValidationError(f"{field_name}必须为非负数")

    q = Decimal("1." + "0" * scale)
    return d.quantize(q, rounding=ROUND_HALF_UP)


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
