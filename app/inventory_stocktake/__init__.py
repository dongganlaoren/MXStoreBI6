"""inventory-stocktake（库存盘点）子系统。

约束对齐：
- 不提供对外 RESTful API（仅同站点页面+服务层内部调用）。
- 不提供导出。

蓝图路由以服务端渲染页面 + 表单提交为主。
"""

from flask import Blueprint

inventory_stocktake_bp = Blueprint(
    "inventory_stocktake",
    __name__,
    template_folder="templates",
    static_folder="static",
    url_prefix="/inventory-stocktake",
)

# 路由延迟导入：避免循环依赖
from . import views  # noqa: E402,F401
from . import api  # noqa: E402,F401
