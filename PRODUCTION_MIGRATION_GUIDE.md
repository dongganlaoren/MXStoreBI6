# 生产环境迁移执行指南

**检查时间：** 2025-10-12  
**当前生产版本：** 7b4517cb3530 (更新表结构)  
**目标版本：** bbf3c1cae35a (增加了店铺整改模块)

---

## 🔍 实际情况分析

### 发现的问题

经过详细检查，之前报告中提到的多个迁移文件（c1d2e3f4a5b6、f5a6b7c8d9e0等）**实际并不存在**。

### 实际的迁移文件列表

生产服务器和代码仓库中实际存在的迁移文件：

```
1b4aa505d0ce_baseline.py                    ← 基线版本
2b5c8f9a1e3d_add_updated_at_to_testaaa.py   ← 测试表
3c7d9e4b5f6a_rename_updated_at_to_updated_in.py
4d5e6f7a8b9c_drop_testaaa_create_testb.py
5e6f7a8b9c0d_drop_test_tables.py            ← 清理测试表
bbf3c1cae35a_增加了店铺整改模块.py         ← 装修整改功能
7b4517cb3530_更新表结构.py                  ← 当前生产版本 ⭐
```

### 迁移依赖关系

```
1b4aa505d0ce (baseline)
    ↓
[测试表相关迁移 2b5c... → 5e6f...]
    ↓
bbf3c1cae35a (增加店铺整改模块) ← 应该在此
    ↓
7b4517cb3530 (更新表结构) ← 生产环境当前在此
```

---

## ⚠️ 关键发现

**生产数据库版本：** `7b4517cb3530`  
**生产数据库应该在：** `bbf3c1cae35a` 或更后

### 问题分析

根据迁移依赖关系：

- `7b4517cb3530` 的 `down_revision = 'bbf3c1cae35a'`
- 这说明 `7b4517cb3530` 是在 `bbf3c1cae35a` **之后**的版本

**结论：生产数据库已经是最新版本！无需执行额外迁移。**

---

## ✅ 验证步骤

为了确认生产环境状态，请在生产服务器执行以下命令：

### 1. 检查当前数据库版本

```bash
cd /var/www/MXStoreBI6
source venv/bin/activate
flask db current
```

**预期输出：** `7b4517cb3530`

### 2. 检查是否有待执行的迁移

```bash
flask db heads
```

**预期输出：** `7b4517cb3530` (如果这是最新的head)

### 3. 查看迁移历史

```bash
flask db history | head -20
```

### 4. 验证关键表是否存在

```bash
mysql -u rwmread -p MXStoreBI_Production -e "
SHOW TABLES LIKE 'renovation%';
SHOW TABLES LIKE 'notification%';
"
```

**预期应该看到：**

- `renovation_tasks` (店铺整改表)
- `renovation_expenses` (装修支出表)
- `renovation_incomes` (装修收入表)
- `renovation_expense_cc_recipients` (支出抄送人)
- `renovation_income_cc_recipients` (收入抄送人)
- `renovation_income_attachments` (收入附件)
- `notification_tasks` (通知任务表)

---

## 🎯 实际需要的操作

基于分析，生产环境**不需要执行数据库迁移**，但需要确认以下内容：

### 选项A：如果表已存在（推荐）

如果上述验证显示所有表都存在，说明数据库已经是最新的，只需：

```bash
# 1. 更新代码（已通过GitHub Actions完成）
cd /var/www/MXStoreBI6
git pull origin main

# 2. 重启服务
sudo supervisorctl restart MXStoreBI6

# 3. 验证功能
curl -I http://localhost:8000
```

### 选项B：如果发现表缺失（需要排查）

如果某些表不存在，可能是：

1. alembic_version表记录错误
2. 之前手动执行过某些DDL

需要执行：

```bash
# 检查alembic_version表
mysql -u rwmread -p MXStoreBI_Production -e "
SELECT * FROM alembic_version;
"

# 如果版本错误，可能需要手动修正或重新迁移
```

---

## 📋 生产环境更新检查清单

- [ ] **验证数据库版本** (`flask db current`)
- [ ] **验证关键表存在** (上述SQL查询)
- [ ] **更新代码** (git pull)
- [ ] **检查依赖** (pip list)
- [ ] **重启服务** (supervisorctl restart)
- [ ] **验证功能**
    - [ ] 登录功能
    - [ ] 装修收入模块
    - [ ] 装修支出模块
    - [ ] 装修业务报表
    - [ ] 店铺整改模块
- [ ] **检查日志** (无错误)

---

## 🚨 如果遇到问题

### 问题1：表不存在

```sql
-- 手动检查表结构
SHOW CREATE TABLE renovation_incomes;
SHOW CREATE TABLE renovation_expenses;
```

### 问题2：版本不匹配

```bash
# 查看alembic版本历史
flask db show 7b4517cb3530
flask db show bbf3c1cae35a
```

### 问题3：功能报错

```bash
# 查看应用日志
sudo supervisorctl tail -100 MXStoreBI6
tail -100 /var/www/MXStoreBI6/app.log
```

---

## 📞 执行命令汇总

在生产服务器上依次执行：

```bash
# 1. 切换到项目目录
cd /var/www/MXStoreBI6

# 2. 激活虚拟环境
source venv/bin/activate

# 3. 检查当前版本（确认）
flask db current

# 4. 验证表存在（确认）
mysql -u rwmread -p MXStoreBI_Production << EOF
SELECT TABLE_NAME 
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = 'MXStoreBI_Production' 
AND TABLE_NAME LIKE 'renovation%';
EOF

# 5. 如果一切正常，更新代码
git pull origin main

# 6. 安装/更新依赖（如果requirements.txt有变化）
pip install -r requirements.txt

# 7. 重启服务
sudo supervisorctl restart MXStoreBI6

# 8. 检查服务状态
sudo supervisorctl status MXStoreBI6

# 9. 验证应用响应
curl -I http://localhost:8000

# 10. 查看日志（确认无错误）
sudo supervisorctl tail -50 MXStoreBI6
```

---

## ✅ 预期结果

执行完成后：

- ✅ 服务正常运行
- ✅ 装修业务模块可访问
- ✅ 所有功能正常
- ✅ 无错误日志

---

## 📄 补充说明

### 关于之前的迁移飘移报告

之前的 `MIGRATION_DRIFT_CHECK_REPORT.md` 中提到的多个迁移版本是**误判**，实际情况是：

- 所有装修业务功能都在 `7b4517cb3530` 及之前的迁移中完成
- 不存在所谓的 c1d2e3f4、f5a6b7c8 等迁移文件
- 生产数据库版本正确，无需额外迁移

### 下次部署建议

1. 部署前先在测试环境验证迁移文件
2. 使用 `git ls-files migrations/versions/` 确认实际存在的迁移文件
3. 对比生产和代码库的实际文件列表

---

**报告生成时间：** 2025-10-12  
**状态：** 生产环境已是最新，无需迁移  
**下一步：** 更新代码并重启服务  

