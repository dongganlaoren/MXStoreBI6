-- inventory-stocktake 数据库脚本（手工/应急用）
-- 注意：项目以 Alembic migrations 为唯一可信的结构变更来源；此脚本仅用于需求文档要求的“SQL + 回滚语句”示例。
-- 适用：MySQL 8.0+

-- =========================
-- UP
-- =========================
-- 1) 新增 product_image 字段（若表存在且字段不存在则新增）
SET @tbl := 'mx_material_info';
SET @col := 'product_image';

SELECT COUNT(*) INTO @tbl_exists
FROM information_schema.tables
WHERE table_schema = DATABASE() AND table_name = @tbl;

SELECT COUNT(*) INTO @col_exists
FROM information_schema.columns
WHERE table_schema = DATABASE() AND table_name = @tbl AND column_name = @col;

SET @stmt := IF(
  @tbl_exists = 1 AND @col_exists = 0,
  'ALTER TABLE mx_material_info ADD COLUMN product_image VARCHAR(255) NULL COMMENT \'预留产品图片字段（文本路径/标识）\';',
  'SELECT \'SKIP: table/column already exists or table missing\' AS msg;'
);
PREPARE s FROM @stmt;
EXECUTE s;
DEALLOCATE PREPARE s;

-- =========================
-- DOWN（回滚）
-- =========================
-- 1) 删除 product_image 字段（若字段存在则删除）
SELECT COUNT(*) INTO @col_exists2
FROM information_schema.columns
WHERE table_schema = DATABASE() AND table_name = @tbl AND column_name = @col;

SET @stmt2 := IF(
  @tbl_exists = 1 AND @col_exists2 = 1,
  'ALTER TABLE mx_material_info DROP COLUMN product_image;',
  'SELECT \'SKIP: column not exists or table missing\' AS msg;'
);
PREPARE s2 FROM @stmt2;
EXECUTE s2;
DEALLOCATE PREPARE s2;
