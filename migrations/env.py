import logging
from logging.config import fileConfig

from alembic import context
from flask import current_app

# Alembic 配置对象
config = context.config

# 设置日志
fileConfig(config.config_file_name)
logger = logging.getLogger('alembic.env')

# 目标 metadata
# 确保导入项目所有 models，这样 Alembic 才能检测表结构
from app import models  # 你的模型模块路径

target_metadata = models.db.metadata  # SQLAlchemy db 对象的 metadata


# 线上/开发数据库引擎获取
def get_engine():
    try:
        return current_app.extensions['migrate'].db.get_engine()
    except (TypeError, AttributeError):
        return current_app.extensions['migrate'].db.engine


# 数据库 URL 配置
def get_engine_url():
    try:
        return str(get_engine().url).replace('%', '%%')
    except AttributeError:
        return str(get_engine().url).replace('%', '%%')


config.set_main_option('sqlalchemy.url', get_engine_url())


# Offline 模式
def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# Online 模式
def run_migrations_online():
    def process_revision_directives(context, revision, directives):
        if getattr(config.cmd_opts, 'autogenerate', False):
            script = directives[0]
            if script.upgrade_ops.is_empty():
                directives[:] = []
                logger.info('No changes in schema detected.')

    conf_args = current_app.extensions['migrate'].configure_args
    if conf_args.get("process_revision_directives") is None:
        conf_args["process_revision_directives"] = process_revision_directives

    connectable = get_engine()
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            **conf_args
        )
        with context.begin_transaction():
            context.run_migrations()


# 根据模式执行
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
