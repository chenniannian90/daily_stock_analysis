# -*- coding: utf-8 -*-
"""
自选股数据迁移脚本

将旧的自选股表结构迁移到新的多分组支持结构。

旧表:
- watchlist_stocks -> watchlist_items (group_id=0)
- watchlist_groups -> watchlist_groups_new
- watchlist_tags -> user_tags
- watchlist_stock_tags -> stock_user_tags

新表:
- watchlist_items (支持一股多分组)
- watchlist_groups_new
- watchlist_sorts
- user_tags
- stock_user_tags

用法:
    python scripts/migrate_watchlist.py [--dry-run]
"""

import argparse
import logging
import sys
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_config

logger = logging.getLogger(__name__)


def get_old_table_names():
    """返回旧表名列表"""
    return [
        'watchlist_stocks',
        'watchlist_groups',
        'watchlist_tags',
        'watchlist_stock_tags',
    ]


def get_new_table_names():
    """返回新表名列表"""
    return [
        'watchlist_items',
        'watchlist_groups_new',
        'watchlist_sorts',
        'user_tags',
        'stock_user_tags',
    ]


def check_old_tables_exist(conn) -> bool:
    """检查旧表是否存在"""
    for table in get_old_table_names():
        result = conn.execute(text(
            f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'"
        ))
        if result.fetchone() is None:
            return False
    return True


def check_new_tables_exist(conn) -> bool:
    """检查新表是否存在"""
    for table in get_new_table_names():
        result = conn.execute(text(
            f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'"
        ))
        if result.fetchone() is None:
            return False
    return True


def migrate_data(conn, dry_run: bool = False):
    """迁移数据"""
    migrated_counts = {}

    # 1. 迁移分组
    logger.info("迁移分组...")
    result = conn.execute(text("""
        INSERT INTO watchlist_groups_new (user_id, name, created_at)
        SELECT user_id, name, created_at
        FROM watchlist_groups
        WHERE NOT EXISTS (
            SELECT 1 FROM watchlist_groups_new
            WHERE watchlist_groups_new.user_id = watchlist_groups.user_id
            AND watchlist_groups_new.name = watchlist_groups.name
        )
    """))
    migrated_counts['groups'] = result.rowcount
    logger.info(f"  迁移了 {result.rowcount} 个分组")

    # 2. 迁移标签
    logger.info("迁移标签...")
    result = conn.execute(text("""
        INSERT INTO user_tags (user_id, name, created_at)
        SELECT user_id, name, created_at
        FROM watchlist_tags
        WHERE NOT EXISTS (
            SELECT 1 FROM user_tags
            WHERE user_tags.user_id = watchlist_tags.user_id
            AND user_tags.name = watchlist_tags.name
        )
    """))
    migrated_counts['tags'] = result.rowcount
    logger.info(f"  迁移了 {result.rowcount} 个标签")

    # 3. 迁移自选股条目 (group_id=0 表示未分组)
    logger.info("迁移自选股条目...")
    result = conn.execute(text("""
        INSERT INTO watchlist_items (user_id, watch_type, group_id, ts_code, sort_num, created_at)
        SELECT user_id, 'stock', 0, code, 0, created_at
        FROM watchlist_stocks
        WHERE NOT EXISTS (
            SELECT 1 FROM watchlist_items
            WHERE watchlist_items.user_id = watchlist_stocks.user_id
            AND watchlist_items.ts_code = watchlist_stocks.code
            AND watchlist_items.group_id = 0
        )
    """))
    migrated_counts['items'] = result.rowcount
    logger.info(f"  迁移了 {result.rowcount} 个自选股条目")

    # 4. 迁移股票标签关联
    logger.info("迁移股票标签关联...")
    result = conn.execute(text("""
        INSERT INTO stock_user_tags (user_id, ts_code, tag_id)
        SELECT wst.user_id, ws.code, wt.id
        FROM watchlist_stock_tags wst
        JOIN watchlist_stocks ws ON wst.stock_id = ws.id
        JOIN user_tags wt ON wt.name = (
            SELECT name FROM watchlist_tags WHERE id = wst.tag_id
        ) AND wt.user_id = wst.user_id
        WHERE NOT EXISTS (
            SELECT 1 FROM stock_user_tags
            WHERE stock_user_tags.user_id = wst.user_id
            AND stock_user_tags.ts_code = ws.code
            AND stock_user_tags.tag_id = wt.id
        )
    """))
    migrated_counts['stock_tags'] = result.rowcount
    logger.info(f"  迁移了 {result.rowcount} 个股票标签关联")

    return migrated_counts


def run_migration(dry_run: bool = False):
    """执行迁移"""
    config = get_config()
    db_url = config.database_url

    logger.info(f"连接数据库: {db_url}")
    engine = create_engine(db_url)

    with engine.connect() as conn:
        # 检查旧表
        if not check_old_tables_exist(conn):
            logger.info("旧表不存在，无需迁移")
            return

        # 检查新表
        if not check_new_tables_exist(conn):
            logger.error("新表不存在，请先启动应用创建新表")
            sys.exit(1)

        logger.info("开始数据迁移...")

        if dry_run:
            logger.info("[DRY RUN] 不会实际修改数据")
            # 查询旧数据数量
            for table in get_old_table_names():
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                logger.info(f"  {table}: {count} 条记录")
        else:
            counts = migrate_data(conn, dry_run)
            conn.commit()
            logger.info(f"迁移完成: {counts}")


def main():
    parser = argparse.ArgumentParser(description='自选股数据迁移脚本')
    parser.add_argument('--dry-run', action='store_true', help='只检查，不实际迁移')
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    run_migration(dry_run=args.dry_run)


if __name__ == '__main__':
    main()
