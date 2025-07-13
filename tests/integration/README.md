# 测试套件说明文档

## 测试文件结构

```
tests/
├── integration/
│   ├── __init__.py                    # 包初始化文件
│   ├── test_takeaway_platform.py     # 基础功能测试
│   ├── test_business_flow.py          # 完整业务流程测试
│   ├── test_web_interface.py          # Web界面功能测试
│   ├── test_store_platform.py        # 店铺平台配置测试
│   ├── test_data_generator.py         # 测试数据生成器
│   ├── run_all_tests.py              # 完整测试套件运行器
│   └── README.md                     # 本文档
├── test_user_admin.py                # 用户管理单元测试(pytest)
```

## 测试文件说明

### 1. test_takeaway_platform.py
**基础功能测试**
- 店铺配置检查
- 店铺查询逻辑验证
- 日报创建逻辑测试
- 数据库基础操作验证

### 2. test_business_flow.py
**完整业务流程测试**
- 模拟用户完整的营业额上报流程
- 测试开通外卖平台店铺的3步流程
- 测试未开通外卖平台店铺的2步流程
- 验证自动跳过逻辑和最终提交条件

### 3. test_web_interface.py
**Web界面功能测试**
- Flask服务器启动测试
- 页面访问状态验证
- 路由功能检查
- 认证重定向验证

### 4. test_store_platform.py
**店铺平台配置测试**
- 验证店铺模型中的third_party_platform字段
- 测试店铺查询和筛选功能
- 检查模型属性和条件判断逻辑
- 统计店铺配置分布

### 5. test_data_generator.py
**测试数据生成器**
- 创建测试用户
- 生成测试日报数据
- 数据统计功能
- 测试数据清理功能

### 6. run_all_tests.py
**完整测试套件运行器**
- 按顺序执行所有测试
- 生成详细测试报告
- 统计测试成功率
- 提供整体测试结果

## 使用方法

### 运行单个测试
```bash
# 激活虚拟环境
.\.venv\Scripts\activate

# 运行基础功能测试
python tests\integration\test_takeaway_platform.py

# 运行业务流程测试
python tests\integration\test_business_flow.py

# 运行店铺配置测试
python tests\integration\test_store_platform.py

# 运行Web界面测试
python tests\integration\test_web_interface.py

# 运行用户管理单元测试
python -m pytest tests\test_user_admin.py -v
```

### 运行完整测试套件
```bash
# 激活虚拟环境
.\.venv\Scripts\activate

# 运行所有测试
python tests\integration\run_all_tests.py
```

### 管理测试数据
```bash
# 创建测试数据
python tests\integration\test_data_generator.py

# 清理测试数据
python tests\integration\test_data_generator.py clean
```

## 测试覆盖范围

### 功能测试
- ✅ 第三方外卖平台条件逻辑
- ✅ 店铺配置检查机制
- ✅ 自动跳过逻辑验证
- ✅ 最终提交条件判断
- ✅ 数据库操作完整性

### 界面测试
- ✅ Flask应用启动
- ✅ 路由访问状态
- ✅ 页面渲染功能
- ✅ 认证机制验证

### 业务流程测试
- ✅ 完整的营业额上报流程
- ✅ 不同店铺类型的处理逻辑
- ✅ Tab切换和状态管理
- ✅ 表单提交和验证

## 预期测试结果

所有测试应该100%通过，表示：
1. Jinja2模板语法错误已修复
2. 第三方外卖平台条件逻辑工作正常
3. 自动跳过机制运行正确
4. Web界面功能完全正常
5. 系统准备投入使用

## 注意事项

1. **虚拟环境**: 所有测试必须在激活的虚拟环境中运行
2. **数据库**: 测试会创建和删除测试数据，不会影响生产数据
3. **服务器**: Web界面测试会启动临时Flask服务器
4. **依赖**: 确保所有依赖包已正确安装

## 故障排除

如果测试失败，检查：
1. 虚拟环境是否激活
2. 数据库连接是否正常
3. 依赖包是否完整安装
4. Flask应用配置是否正确
