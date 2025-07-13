# 🔧 外卖平台Tab显示问题修复说明

## 问题描述
在营业信息上报页面，用户补全第三方外卖平台数据并保存后，系统正常提示是否最终提交，但页面中看不到"第三方外卖平台"Tab，只能看到"店内营业信息"和"实际入账"两个Tab。

## 问题原因
Jinja2模板中的变量作用域问题。在"已有日报数据"的情况下，`show_takeaway` 变量在 `{% if %}` 块内部设置，导致其作用域不能正确传播到后续的模板部分。

## 修复内容
将 `show_takeaway` 变量的设置移到更合适的位置，确保其作用域覆盖整个Tab导航和内容区域。

### 修复前的代码结构：
```jinja2
<li class="nav-item">...</li>
{% set show_takeaway = false %}
{% if current_store and current_store.third_party_platform %}
    {% set show_takeaway = true %}
{% endif %}
{% if show_takeaway %}
<li class="nav-item">外卖平台Tab</li>
{% endif %}
```

### 修复后的代码结构：
```jinja2
{# 首先设置外卖平台显示变量 #}
{% set show_takeaway = current_store and current_store.third_party_platform %}

<li class="nav-item">...</li>
{% if show_takeaway %}
<li class="nav-item">外卖平台Tab</li>
{% endif %}
```

## 如何验证修复

### 方法1：浏览器验证
1. 在浏览器中清除缓存或强制刷新页面 (Ctrl+F5)
2. 登录系统并进入营业信息上报页面
3. 选择一个开通了第三方外卖平台的店铺
4. 应该能看到三个Tab：
   - 店内营业信息
   - 外卖平台 ← 这个应该现在可以看到了
   - 实际入账

### 方法2：运行测试验证
```bash
# 激活虚拟环境
.\.venv\Scripts\activate

# 运行外卖平台功能测试
python run_tests.py store

# 或运行完整测试套件
python run_tests.py all
```

### 方法3：开发者工具验证
1. 在浏览器中按F12打开开发者工具
2. 查看页面HTML源代码
3. 搜索 `takeaway-tab` 或 `外卖平台`
4. 应该能找到相关的HTML元素

## 预期结果

修复后，对于开通了第三方外卖平台的店铺：
- ✅ 外卖平台Tab应该显示在Tab导航中
- ✅ 点击外卖平台Tab应该能看到外卖相关的表单字段
- ✅ 完成所有必需步骤后应该能看到"最终提交"按钮

对于未开通第三方外卖平台的店铺：
- ✅ 外卖平台Tab不显示（正常行为）
- ✅ 只需要完成"店内营业信息"和"实际入账"两个步骤

## 技术细节

修复涉及的文件：
- `app/templates/sales/report.html` - 主要修复文件

修复的具体位置：
1. 行233-237：已有数据情况下的Tab导航部分
2. 行53-57：新建数据情况下的Tab导航部分

## 测试确认

运行以下命令确认修复有效：
```bash
python tests\integration\test_template_logic.py
```

预期输出应该显示：
```
✅ 外卖平台Tab应该显示
外卖Tab启用状态: True
→ 可以最终提交: True
```

## 如果问题仍然存在

如果修复后问题仍然存在，请检查：
1. 是否已清除浏览器缓存
2. 确认选择的店铺确实开通了第三方外卖平台
3. 查看浏览器开发者工具中是否有JavaScript错误
4. 确认Flask应用已重启
