# 生产环境迁移执行指南

**检查时间：** 2026-01-30  \
**当前生产版本（旧）：** 7b4517cb3530 (更新表结构)  \
**目标版本（新）：** 8c4a2dd7a1b0 (补齐整改模块外键，当前 head)

---

## 🔍 实际情况分析

### 这次变更解决什么问题？

历史原因：仓库早期迁移链只包含“整改模块/通知模块”，但 model 层还定义了 users/stores/daily_sales/reimbursement 等核心业务表；这会导致
**新环境空库无法仅靠 migrations 初始化出完整 schema**。

本次新增了两步迁移（不改历史）：

- `6d52051b9c5f_create_core_business_tables.py`：创建缺失的核心业务表（stores/users/daily_sales/...）
- `8c4a2dd7a1b0_add_fk_to_renovation_tables.py`：为整改模块补齐指向 users/stores 的外键（可重复执行：若 FK 已存在则跳过）

---

## ✅ 迁移文件列表（当前应该存在）

```
1b4aa505d0ce_baseline.py
2b5c8f9a1e3d_add_updated_at_to_testaaa.py
3c7d9e4b5f6a_rename_updated_at_to_updated_in.py
4d5e6f7a8b9c_drop_testaaa_create_testb.py
5e6f7a8b9c0d_drop_test_tables.py
bbf3c1cae35a_增加了店铺整改模块.py
7b4517cb3530_更新表结构.py
6d52051b9c5f_create_core_business_tables.py
8c4a2dd7a1b0_add_fk_to_renovation_tables.py  ← 当前 head ⭐
```

---

## ✅ 生产/开发（MySQL）执行前必做检查（强烈建议）

### 0) 先确认当前版本

```bash
flask db current --verbose
flask db heads --verbose
```

### 1) 如果你要执行到 `6d52051b9c5f`

这一步主要是 **新建缺失表**，一般风险较低。

建议先检查目标 tables 是否已存在：

```sql
-- 任选几张核心表作为哨兵
SHOW TABLES LIKE 'stores';
SHOW TABLES LIKE 'users';
SHOW TABLES LIKE 'daily_sales';
SHOW TABLES LIKE 'reimbursement_requests';
```

### 2) 如果你要执行到 `8c4a2dd7a1b0`（新增外键）

加外键是“最容易在生产失败”的步骤：如果整改表里已有脏数据（比如 store_id 指向不存在的 stores.store_id），MySQL 会直接报错并中止迁移。

**建议在执行前先跑下面的“孤儿数据预检 SQL”**：

```sql
-- 1) renovation_tasks.store_id 是否存在于 stores
SELECT COUNT(*) AS orphan_store_id
FROM renovation_tasks t
LEFT JOIN stores s ON s.store_id = t.store_id
WHERE s.store_id IS NULL;

-- 2) renovation_tasks.created_by / assigned_to / verifier_id 是否存在于 users
SELECT COUNT(*) AS orphan_created_by
FROM renovation_tasks t
LEFT JOIN users u ON u.user_id = t.created_by
WHERE u.user_id IS NULL;

SELECT COUNT(*) AS orphan_assigned_to
FROM renovation_tasks t
LEFT JOIN users u ON u.user_id = t.assigned_to
WHERE t.assigned_to IS NOT NULL AND u.user_id IS NULL;

SELECT COUNT(*) AS orphan_verifier_id
FROM renovation_tasks t
LEFT JOIN users u ON u.user_id = t.verifier_id
WHERE t.verifier_id IS NOT NULL AND u.user_id IS NULL;

-- 3) renovation_records.operator_id 是否存在于 users
SELECT COUNT(*) AS orphan_operator_id
FROM renovation_records r
LEFT JOIN users u ON u.user_id = r.operator_id
WHERE u.user_id IS NULL;

-- 4) renovation_attachments.uploaded_by 是否存在于 users
SELECT COUNT(*) AS orphan_uploaded_by
FROM renovation_attachments a
LEFT JOIN users u ON u.user_id = a.uploaded_by
WHERE u.user_id IS NULL;
```

**预期：以上 orphan_* 全部为 0。**

如果不为 0：请先修复数据（补齐 users/stores、或修正/置空相关字段），再执行迁移。

---

## 🎯 标准生产部署流程（建议顺序）

1) 更新代码
2) 激活虚拟环境
3) `flask db current --verbose` 确认当前 revision
4) （可选）执行上面的孤儿数据预检 SQL
5) `flask db upgrade` 执行迁移
6) `flask db current --verbose` 再确认 revision 已到 head
7) 重启服务
8) 看日志确认无错误

---

## ✅ 本地/测试环境推荐的一键验证

仓库提供了一个 SQLite 验证脚本，可用于 CI/本地预检：

```bash
.venv/bin/python tools/verify_migrations.py
```

它会在 instance/ 下创建一个全新 sqlite 文件库，执行 `flask db upgrade`，并检查“迁移后的表集合”是否覆盖 model 层表集合。

---

## 如果遇到迁移失败怎么办？

- 失败在 `6d52051b9c5f`：多半是权限/字符集/DATABASE_URL 指向错误
- 失败在 `8c4a2dd7a1b0`：优先怀疑“数据不满足外键约束”（先跑孤儿数据预检 SQL）

---

（以下为历史内容，已过时但保留备查）

````
