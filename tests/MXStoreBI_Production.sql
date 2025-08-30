/*
 Navicat Premium Dump SQL

 Source Server         : 阿里云MySQL
 Source Server Type    : MySQL
 Source Server Version : 80043 (8.0.43-0ubuntu0.24.04.1)
 Source Host           : gothaieasy.fun:3306
 Source Schema         : MXStoreBI_Production

 Target Server Type    : MySQL
 Target Server Version : 80043 (8.0.43-0ubuntu0.24.04.1)
 File Encoding         : 65001

 Date: 30/08/2025 20:12:32
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for alembic_version
-- ----------------------------
DROP TABLE IF EXISTS `alembic_version`;
CREATE TABLE `alembic_version` (
  `version_num` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`version_num`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for bank_deposit_history
-- ----------------------------
DROP TABLE IF EXISTS `bank_deposit_history`;
CREATE TABLE `bank_deposit_history` (
  `id` int NOT NULL AUTO_INCREMENT,
  `report_id` int NOT NULL COMMENT '日报ID',
  `field_name` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '字段名',
  `old_value` float DEFAULT NULL COMMENT '原值',
  `new_value` float NOT NULL COMMENT '新值',
  `operator_id` int NOT NULL COMMENT '操作人ID',
  `operator_role` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '操作人角色',
  `remark` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '变更理由',
  `created_at` datetime DEFAULT NULL COMMENT '操作时间',
  PRIMARY KEY (`id`),
  KEY `operator_id` (`operator_id`),
  KEY `ix_bank_deposit_history_report_id` (`report_id`),
  CONSTRAINT `bank_deposit_history_ibfk_1` FOREIGN KEY (`operator_id`) REFERENCES `users` (`user_id`),
  CONSTRAINT `bank_deposit_history_ibfk_2` FOREIGN KEY (`report_id`) REFERENCES `daily_sales` (`report_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=69 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for daily_sales
-- ----------------------------
DROP TABLE IF EXISTS `daily_sales`;
CREATE TABLE `daily_sales` (
  `theoretical_total` float DEFAULT NULL COMMENT '理论营收(T2)=店铺理论营业额(T0)+第三方外卖平台收入(T1)-POS机小票里显示的代金券总金额-银行存款金额',
  `report_id` int NOT NULL AUTO_INCREMENT COMMENT '日报主键',
  `store_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '门店ID',
  `user_id` int NOT NULL COMMENT '上报人ID',
  `report_date` date NOT NULL COMMENT '营业日期',
  `cash_income` float DEFAULT NULL COMMENT '现金收入 (C)',
  `pos_income` float DEFAULT NULL COMMENT '电子支付收入 (P)',
  `day_pass_income` float DEFAULT NULL COMMENT '外卖收入 (D)',
  `voucher_amount` float DEFAULT NULL COMMENT '代金券使用金额 (R)',
  `pos_total` float DEFAULT NULL COMMENT '店铺理论营业额 (T0) = 现金收入 + 电子支付收入 + 外卖收入 + 代金券使用金额',
  `electronic_actual_arrival` float DEFAULT NULL COMMENT '电子支付实际入账金额 (EA)',
  `bank_deposit` float DEFAULT NULL COMMENT '银行存款金额 (BC)',
  `bank_fee` float DEFAULT NULL COMMENT '银行存款手续费 (BF)',
  `takeaway_amount` float NOT NULL COMMENT '第三方外卖平台收入 (T1)',
  `actual_sales` float DEFAULT NULL COMMENT '实际总营业额(S)=第三方外卖平台收入(T1)+外卖收入+电子支付实际入账金额+银行存款金额',
  `total_error` float DEFAULT NULL COMMENT '总误差(E)=电子支付实际入账金额+银行存款金额+银行存款手续费-POS机小票里显示的电子支付总金额-POS机小票里显示的现金总金额',
  `cash_difference` float NOT NULL COMMENT 'POS现金收入误差(A)，仅存储，默认0',
  `electronic_difference` float NOT NULL COMMENT 'POS电子支付误差(B)，仅存储，默认0',
  `remark` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '审核备注',
  `pos_info_completed` tinyint(1) NOT NULL COMMENT '第一步(POS)是否完成',
  `takeaway_info_completed` tinyint(1) NOT NULL COMMENT '第二步(外卖)是否完成',
  `actual_arrival_info_completed` tinyint(1) NOT NULL COMMENT '实际入账金额录入是否完成',
  `is_submitted` tinyint(1) NOT NULL COMMENT '是否已最终提交给财务',
  `financial_check_status` enum('PENDING','APPROVED') COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '财务核对状态（仅PENDING/APPROVED）',
  `created_at` datetime DEFAULT NULL COMMENT '创建时间',
  `updated_at` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`report_id`),
  KEY `ix_daily_sales_report_date` (`report_date`),
  KEY `ix_daily_sales_store_id` (`store_id`),
  KEY `ix_daily_sales_user_id` (`user_id`),
  CONSTRAINT `daily_sales_ibfk_1` FOREIGN KEY (`store_id`) REFERENCES `stores` (`store_id`),
  CONSTRAINT `daily_sales_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=194 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for daily_sales_attachments
-- ----------------------------
DROP TABLE IF EXISTS `daily_sales_attachments`;
CREATE TABLE `daily_sales_attachments` (
  `attachment_id` int NOT NULL AUTO_INCREMENT COMMENT '凭证ID',
  `report_id` int NOT NULL COMMENT '日报ID',
  `file_path` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '文件路径（本地磁盘，含user_id/store_id/report_date）',
  `attachment_type` enum('sales_slip','bank_receipt','takeaway_screenshot','electronic_actual_arrival_receipt','image','pdf') COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '附件类型（小票/银行/外卖/图片/PDF等）',
  `created_at` datetime DEFAULT NULL COMMENT '创建时间',
  PRIMARY KEY (`attachment_id`),
  KEY `report_id` (`report_id`),
  CONSTRAINT `daily_sales_attachments_ibfk_1` FOREIGN KEY (`report_id`) REFERENCES `daily_sales` (`report_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=631 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for email_report_config
-- ----------------------------
DROP TABLE IF EXISTS `email_report_config`;
CREATE TABLE `email_report_config` (
  `id` int NOT NULL AUTO_INCREMENT,
  `role` enum('ADMIN','HEAD_MANAGER','FINANCE','BRANCH_MANAGER','EMPLOYEE') COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '角色',
  `daily_enabled` tinyint(1) NOT NULL,
  `weekly_enabled` tinyint(1) NOT NULL,
  `monthly_enabled` tinyint(1) NOT NULL,
  `daily_time` varchar(8) COLLATE utf8mb4_unicode_ci NOT NULL,
  `weekly_time` varchar(8) COLLATE utf8mb4_unicode_ci NOT NULL,
  `monthly_time` varchar(8) COLLATE utf8mb4_unicode_ci NOT NULL,
  `weekly_day` varchar(2) COLLATE utf8mb4_unicode_ci NOT NULL,
  `monthly_day` varchar(2) COLLATE utf8mb4_unicode_ci NOT NULL,
  `emails` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`),
  UNIQUE KEY `role` (`role`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for email_task_log
-- ----------------------------
DROP TABLE IF EXISTS `email_task_log`;
CREATE TABLE `email_task_log` (
  `id` int NOT NULL AUTO_INCREMENT,
  `task_type` enum('daily','weekly','monthly') COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '任务类型',
  `start_date` date NOT NULL COMMENT '数据统计开始时间',
  `end_date` date NOT NULL COMMENT '数据统计结束时间',
  `recipients` text COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '收件人邮箱列表（逗号分隔）',
  `status` enum('success','partial_fail','fail') COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '发送结果状态',
  `success_count` int NOT NULL COMMENT '成功发送数量',
  `fail_count` int NOT NULL COMMENT '失败数量',
  `created_at` datetime NOT NULL COMMENT '创建时间',
  `updated_at` datetime NOT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for reimbursement_attachments
-- ----------------------------
DROP TABLE IF EXISTS `reimbursement_attachments`;
CREATE TABLE `reimbursement_attachments` (
  `attachment_id` int NOT NULL AUTO_INCREMENT COMMENT '附件ID',
  `request_id` int NOT NULL COMMENT '所属报销申请ID',
  `attachment_type` enum('SUBMISSION','APPROVAL') COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '附件类型（提交/审批）',
  `uploader_id` int NOT NULL COMMENT '上传人ID',
  `original_filename` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '原始文件名',
  `file_path` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '文件存储路径',
  `file_size` int NOT NULL COMMENT '文件大小（字节）',
  `mime_type` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '文件MIME类型',
  `uploaded_at` datetime NOT NULL COMMENT '上传时间',
  PRIMARY KEY (`attachment_id`),
  KEY `request_id` (`request_id`),
  KEY `uploader_id` (`uploader_id`),
  CONSTRAINT `reimbursement_attachments_ibfk_1` FOREIGN KEY (`request_id`) REFERENCES `reimbursement_requests` (`request_id`),
  CONSTRAINT `reimbursement_attachments_ibfk_2` FOREIGN KEY (`uploader_id`) REFERENCES `users` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=252 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for reimbursement_cc_recipients
-- ----------------------------
DROP TABLE IF EXISTS `reimbursement_cc_recipients`;
CREATE TABLE `reimbursement_cc_recipients` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '抄送记录ID',
  `request_id` int NOT NULL COMMENT '报销申请ID',
  `user_id` int NOT NULL COMMENT '抄送人用户ID',
  `created_at` datetime NOT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_request_user_cc` (`request_id`,`user_id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `reimbursement_cc_recipients_ibfk_1` FOREIGN KEY (`request_id`) REFERENCES `reimbursement_requests` (`request_id`),
  CONSTRAINT `reimbursement_cc_recipients_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=48 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for reimbursement_default_cc_recipients
-- ----------------------------
DROP TABLE IF EXISTS `reimbursement_default_cc_recipients`;
CREATE TABLE `reimbursement_default_cc_recipients` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '配置记录ID',
  `user_id` int NOT NULL COMMENT '默认抄送人用户ID',
  `is_active` tinyint(1) NOT NULL COMMENT '是否启用',
  `created_at` datetime NOT NULL COMMENT '创建时间',
  `created_by` int NOT NULL COMMENT '创建人ID',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_default_cc_user` (`user_id`),
  KEY `created_by` (`created_by`),
  CONSTRAINT `reimbursement_default_cc_recipients_ibfk_1` FOREIGN KEY (`created_by`) REFERENCES `users` (`user_id`),
  CONSTRAINT `reimbursement_default_cc_recipients_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for reimbursement_requests
-- ----------------------------
DROP TABLE IF EXISTS `reimbursement_requests`;
CREATE TABLE `reimbursement_requests` (
  `request_id` int NOT NULL AUTO_INCREMENT COMMENT '报销申请ID',
  `submitter_id` int NOT NULL COMMENT '申请人ID',
  `store_id` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '关联店铺ID',
  `primary_category` enum('SHARED_COST','STORE_COST') COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '一级分类',
  `secondary_category` enum('SHARED_REIMBURSEMENT','AGENCY_ACCOUNTING','TAXES','EMPLOYEE_SOCIAL_SECURITY','STORE_MANAGEMENT','OTHER_SHARED_COST','MIXTURE_MATERIAL','MATERIAL_TRANSPORT','FIXED_SALARY','TEMPORARY_SALARY','EXTERNAL_LEMON','STORE_PETTY_CASH','RENTAL_TAX','UTILITIES','STORE_RENT','WAREHOUSE_RENT','OTHER_COST') COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '二级分类',
  `amount` decimal(12,2) NOT NULL COMMENT '报销金额',
  `currency` varchar(8) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '货币单位',
  `description` text COLLATE utf8mb4_unicode_ci COMMENT '报销说明',
  `status` enum('PENDING','APPROVED','REJECTED','DRAFT') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'PENDING' COMMENT '审批状态',
  `approval_comments` text COLLATE utf8mb4_unicode_ci COMMENT '审批意见',
  `created_at` datetime NOT NULL COMMENT '创��时间',
  `updated_at` datetime NOT NULL COMMENT '更新时间',
  `approved_at` datetime DEFAULT NULL COMMENT '审批通过时间',
  `approver_id` int NOT NULL COMMENT '审批人ID',
  `check_status` enum('CHECKED','UNCHECKED') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'UNCHECKED' COMMENT '核对状态',
  PRIMARY KEY (`request_id`),
  KEY `approver_id` (`approver_id`),
  KEY `store_id` (`store_id`),
  KEY `submitter_id` (`submitter_id`),
  CONSTRAINT `reimbursement_requests_ibfk_1` FOREIGN KEY (`approver_id`) REFERENCES `users` (`user_id`),
  CONSTRAINT `reimbursement_requests_ibfk_2` FOREIGN KEY (`store_id`) REFERENCES `stores` (`store_id`),
  CONSTRAINT `reimbursement_requests_ibfk_3` FOREIGN KEY (`submitter_id`) REFERENCES `users` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=138 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for stores
-- ----------------------------
DROP TABLE IF EXISTS `stores`;
CREATE TABLE `stores` (
  `store_id` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '店铺唯一标识符',
  `store_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '店铺名称',
  `store_address` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '店铺地图地址链接',
  `third_party_platform` tinyint(1) DEFAULT NULL COMMENT '是否开启第三方外卖平台',
  PRIMARY KEY (`store_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for users
-- ----------------------------
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
  `employee_number` int DEFAULT NULL COMMENT '员工编号（店铺编号+三位序号）',
  `user_id` int NOT NULL AUTO_INCREMENT COMMENT '用户主键，自增 ID',
  `username` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '登录用户名',
  `password_hash` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '登录密码哈希',
  `user_status` int NOT NULL COMMENT '用户状态（1=活跃，0=禁用）',
  `last_login_time` datetime DEFAULT NULL COMMENT '最近一次登录时间',
  `created_at` datetime DEFAULT NULL COMMENT '创建时间',
  `updated_at` datetime DEFAULT NULL COMMENT '更新时间',
  `role` enum('ADMIN','HEAD_MANAGER','FINANCE','BRANCH_MANAGER','EMPLOYEE') COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '用户角色',
  `store_id` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '关联店铺ID (门店组用户专属)',
  `real_name` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '真实姓名',
  `id_card_number` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '身份证号',
  `bank_name` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '银行名称',
  `bank_account_number` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '银行账号',
  `is_primary_contact` tinyint(1) DEFAULT NULL COMMENT '是否为店铺主要联系人',
  `phone` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '联系电话',
  `line_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'LINE ID',
  `email` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '电子邮箱',
  `start_date` date DEFAULT NULL COMMENT '入职日期',
  `end_date` date DEFAULT NULL COMMENT '离职日期',
  `profile_completed` tinyint(1) DEFAULT NULL COMMENT '员工档案是否已完善（仅能一次性填写）',
  `id_card_copy` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '身份证复印件文件路径（受控访问，避免隐私泄露）',
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `username` (`username`),
  KEY `store_id` (`store_id`),
  CONSTRAINT `users_ibfk_1` FOREIGN KEY (`store_id`) REFERENCES `stores` (`store_id`)
) ENGINE=InnoDB AUTO_INCREMENT=41 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;
