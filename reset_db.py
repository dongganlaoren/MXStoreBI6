import os
import re

import pymysql
from dotenv import load_dotenv


def parse_mysql_url(url):
    # 只支持 mysql+pymysql://user:pass@host:port/dbname
    pattern = r"mysql\+pymysql://([^:]+):([^@]+)@([^:/]+):(\d+)/(\w+)"
    match = re.match(pattern, url)
    if not match:
        raise ValueError(
            "DATABASE_URL 格式不正确，仅支持 mysql+pymysql://user:pass@host:port/dbname"
        )
    user, password, host, port, dbname = match.groups()
    return user, password, host, int(port), dbname


if __name__ == "__main__":
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("未检测到 DATABASE_URL，请检查 .env 文件")
        exit(1)
    try:
        user, password, host, port, dbname = parse_mysql_url(db_url)
    except Exception as e:
        print(f"数据库连接字符串解析失败: {e}")
        exit(1)
    print(f"正在连接数据库: {host}:{port}, 用户: {user}, 数据库: {dbname}")
    try:
        conn = pymysql.connect(
            host=host, port=port, user=user, password=password
        )
        with conn.cursor() as cursor:
            cursor.execute(f"DROP DATABASE IF EXISTS {dbname};")
            cursor.execute(
                f"CREATE DATABASE {dbname} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
            )
        conn.close()
        print(f"数据库 {dbname} 已重建。")
    except Exception as e:
        print(f"数据库操作失败: {e}")
        exit(1)
