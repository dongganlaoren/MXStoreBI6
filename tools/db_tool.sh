#!/bin/bash
# ============================================
# 数据库管理工具 db_tool.sh
# 功能: 备份/恢复/删除数据库 + 日志管理 + 安全保护 + 过期备份清理
# ============================================

BACKUP_DIR="/var/backups/mysql"
LOG_FILE="/var/log/db_tool.log"
PROTECT_DB="MXStoreBI_Production"
RETENTION_DAYS=7   # 保留备份天数

mkdir -p "$BACKUP_DIR"
mkdir -p "$(dirname $LOG_FILE)"

# 颜色定义
RED="\033[31m"
GREEN="\033[32m"
YELLOW="\033[33m"
BLUE="\033[34m"
NC="\033[0m"

# ====== 清理过期备份 ======
function cleanup_old_backups() {
    echo -e "${YELLOW}[INFO] 清理 ${RETENTION_DAYS} 天前的旧备份文件...${NC}"
    OLD_FILES=$(find "$BACKUP_DIR" -type f -name "*.sql.gz" -mtime +$RETENTION_DAYS)
    if [[ -z "$OLD_FILES" ]]; then
        echo "[INFO] 没有需要清理的旧备份文件。"
        return
    fi
    echo "将删除以下旧备份文件："
    echo "$OLD_FILES"
    read -p "确认删除？(yes/no): " CONFIRM
    if [[ "$CONFIRM" == "yes" ]]; then
        echo "$OLD_FILES" | xargs rm -f
        echo "[SUCCESS] 已删除过期备份文件。" | tee -a "$LOG_FILE"
    else
        echo "[INFO] 取消清理操作。"
    fi
}

# ====== 备份数据库（交互式选择） ======
function backup_db() {
    cleanup_old_backups
    echo -e "${BLUE}========== 数据库备份 ==========${NC}"

    # 获取可备份数据库列表（包括生产库）
    DB_LIST=($(mysql -u root -N -e "SHOW DATABASES;" | grep -Ev "(information_schema|performance_schema|mysql|sys)"))

    if [ ${#DB_LIST[@]} -eq 0 ]; then
        echo -e "${RED}[ERROR] 没有可备份的数据库！${NC}"
        return
    fi

    echo -e "${YELLOW}[INFO] 可备份的数据库列表:${NC}"
    select DB_NAME in "${DB_LIST[@]}"; do
        if [[ -n "$DB_NAME" ]]; then
            if [[ "$DB_NAME" == "$PROTECT_DB" ]]; then
                echo -e "${YELLOW}[INFO] 你选择的是生产数据库: $DB_NAME${NC}"
            fi
            TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
            BACKUP_FILE="$BACKUP_DIR/db_backup_${DB_NAME}_${TIMESTAMP}.sql.gz"
            echo -e "${YELLOW}[INFO] 正在备份数据库 $DB_NAME ...${NC}"
            mysqldump -u root "$DB_NAME" 2>>"$LOG_FILE" | gzip > "$BACKUP_FILE"

            if [[ $? -eq 0 ]]; then
                echo -e "${GREEN}[SUCCESS] 数据库 $DB_NAME 备份成功: $BACKUP_FILE${NC}" | tee -a "$LOG_FILE"
                echo "$(date '+%Y-%m-%d %H:%M:%S') | BACKUP | DB: $DB_NAME | File: $BACKUP_FILE" >> "$LOG_FILE"
            else
                echo -e "${RED}[ERROR] 数据库备份失败！${NC}" | tee -a "$LOG_FILE"
            fi
            break
        else
            echo -e "${RED}无效选择，请重新选择！${NC}"
        fi
    done
}

# ====== 恢复数据库 ======
function restore_db() {
    echo -e "${BLUE}========== 数据库恢复 ==========${NC}"

    echo -e "${YELLOW}[INFO] 当前数据库列表:${NC}"
    mysql -u root -e "SHOW DATABASES;" | grep -Ev "(Database|information_schema|performance_schema|mysql|sys)"

    echo -e "${YELLOW}[INFO] 可用备份文件:${NC}"
    FILES=($(ls -1t ${BACKUP_DIR}/*.sql.gz 2>/dev/null))
    if [ ${#FILES[@]} -eq 0 ]; then
        echo -e "${RED}[ERROR] 没有找到备份文件！${NC}"
        return
    fi

    select BACKUP_FILE in "${FILES[@]}"; do
        if [[ -f "$BACKUP_FILE" ]]; then
            echo -e "${GREEN}已选择备份文件: $BACKUP_FILE${NC}"
            break
        else
            echo -e "${RED}无效选择，请重试！${NC}"
        fi
    done

    read -p "请输入要恢复到的数据库名称: " DB_NAME
    if [[ "$DB_NAME" == "$PROTECT_DB" ]]; then
        echo -e "${RED}[ERROR] 禁止恢复到生产数据库！${NC}" | tee -a "$LOG_FILE"
        return
    fi

    DB_EXIST=$(mysql -u root -e "SHOW DATABASES LIKE '${DB_NAME}';" | grep "${DB_NAME}" | wc -l)
    if [[ $DB_EXIST -eq 1 ]]; then
        echo -e "${YELLOW}[WARNING] 数据库 $DB_NAME 已存在，将被清空！${NC}"
        read -p "确认清空并继续恢复？(yes/no): " CONFIRM
        if [[ "$CONFIRM" != "yes" ]]; then
            echo "[INFO] 操作取消。" | tee -a "$LOG_FILE"
            return
        fi
        mysql -u root -e "DROP DATABASE ${DB_NAME}; CREATE DATABASE ${DB_NAME};"
    else
        mysql -u root -e "CREATE DATABASE ${DB_NAME};"
        echo -e "${YELLOW}[INFO] 数据库 $DB_NAME 不存在，已创建新库。${NC}"
    fi

    TABLES_BEFORE=$(mysql -u root -N -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='${DB_NAME}';")

    echo -e "${YELLOW}[INFO] 正在恢复数据库，请稍候...${NC}"
    gunzip < "$BACKUP_FILE" | mysql -u root "$DB_NAME"

    if [[ $? -eq 0 ]]; then
        echo -e "${GREEN}[SUCCESS] 数据库 $DB_NAME 恢复完成。${NC}" | tee -a "$LOG_FILE"
    else
        echo -e "${RED}[ERROR] 数据库恢复失败！${NC}" | tee -a "$LOG_FILE"
        return
    fi

    TABLES_AFTER=$(mysql -u root -N -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='${DB_NAME}';")
    echo -e "${YELLOW}[INFO] 数据库表数量: ${TABLES_BEFORE} → ${TABLES_AFTER}${NC}"
    echo "$(date '+%Y-%m-%d %H:%M:%S') | RESTORE | DB: $DB_NAME | File: $BACKUP_FILE | Tables: $TABLES_AFTER" >> "$LOG_FILE"
}

# ====== 删除数据库（交互式选择） ======
function delete_db() {
    echo -e "${BLUE}========== 删除数据库 ==========${NC}"

    # 获取可删除数据库列表（排除系统库和生产库）
    DB_LIST=($(mysql -u root -N -e "SHOW DATABASES;" | grep -Ev "(information_schema|performance_schema|mysql|sys|${PROTECT_DB})"))

    if [ ${#DB_LIST[@]} -eq 0 ]; then
        echo -e "${YELLOW}[INFO] 没有可删除的数据库。${NC}"
        return
    fi

    echo -e "${YELLOW}[INFO] 可删除的数据库列表:${NC}"
    select DB_NAME in "${DB_LIST[@]}"; do
        if [[ -n "$DB_NAME" ]]; then
            echo -e "${YELLOW}[WARNING] 你选择删除数据库: $DB_NAME${NC}"
            read -p "确认删除数据库 $DB_NAME？(yes/no): " CONFIRM
            if [[ "$CONFIRM" != "yes" ]]; then
                echo "[INFO] 操作取消。" | tee -a "$LOG_FILE"
                return
            fi

            mysql -u root -e "DROP DATABASE ${DB_NAME};"
            if [[ $? -eq 0 ]]; then
                echo -e "${GREEN}[SUCCESS] 数据库 $DB_NAME 已删除。${NC}" | tee -a "$LOG_FILE"
                echo "$(date '+%Y-%m-%d %H:%M:%S') | DELETE | DB: $DB_NAME" >> "$LOG_FILE"
            else
                echo -e "${RED}[ERROR] 删除数据库 $DB_NAME 失败！${NC}" | tee -a "$LOG_FILE"
            fi
            break
        else
            echo -e "${RED}无效选择，请重新选择！${NC}"
        fi
    done
}

# ====== 查看日志 ======
function view_log() {
    echo -e "${BLUE}========== 数据库操作日志 ==========${NC}"
    if [[ -f "$LOG_FILE" ]]; then
        tail -n 50 "$LOG_FILE"
    else
        echo "[INFO] 日志文件不存在。"
    fi
}

# ====== 主菜单 ======
while true; do
    echo -e "\n${BLUE}===== 数据库管理工具 =====${NC}"
    echo "1) 备份数据库"
    echo "2) 恢复数据库"
    echo "3) 查看日志"
    echo "4) 清理过期备份"
    echo "5) 删除数据库"
    echo "6) 退出"
    read -p "请选择操作 [1-6]: " CHOICE
    case "$CHOICE" in
        1) backup_db ;;
        2) restore_db ;;
        3) view_log ;;
        4) cleanup_old_backups ;;
        5) delete_db ;;
        6) exit 0 ;;
        *) echo -e "${RED}无效选择，请输入1-6${NC}" ;;
    esac
done
