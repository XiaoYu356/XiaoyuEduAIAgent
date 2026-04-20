"""
数据库迁移脚本：为 knowledge_gaps 表添加 kb_id 字段并更新外键约束
运行方式: cd backend && python migrate_add_kb_id.py
"""
import asyncio
import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import asyncpg
except ImportError:
    print("请先安装 asyncpg: pip install asyncpg")
    sys.exit(1)


async def migrate():
    conn_params = {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", "5432")),
        "user": os.getenv("POSTGRES_USER", "xiaoyu"),
        "password": os.getenv("POSTGRES_PASSWORD", "xiaoyu_password"),
        "database": os.getenv("POSTGRES_DB", "xiaoyu_edu"),
    }

    print(f"连接数据库: {conn_params['host']}:{conn_params['port']}/{conn_params['database']}")

    try:
        conn = await asyncpg.connect(**conn_params)
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        sys.exit(1)

    try:
        print("\n开始迁移...")

        print("1. 添加 kb_id 字段...")
        await conn.execute("""
            ALTER TABLE knowledge_gaps 
            ADD COLUMN IF NOT EXISTS kb_id INTEGER REFERENCES knowledge_bases(id)
        """)
        print("   ✅ 添加 kb_id 字段成功")

        print("2. 创建索引...")
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS ix_knowledge_gaps_kb_id ON knowledge_gaps(kb_id)
        """)
        print("   ✅ 创建索引成功")

        print("3. 删除旧外键约束...")
        await conn.execute("""
            ALTER TABLE knowledge_gaps 
            DROP CONSTRAINT IF EXISTS knowledge_gaps_source_conversation_id_fkey
        """)
        print("   ✅ 删除旧外键约束成功")

        print("4. 添加新外键约束 (ON DELETE SET NULL)...")
        await conn.execute("""
            ALTER TABLE knowledge_gaps 
            ADD CONSTRAINT knowledge_gaps_source_conversation_id_fkey 
            FOREIGN KEY (source_conversation_id) REFERENCES conversations(id) ON DELETE SET NULL
        """)
        print("   ✅ 添加新外键约束成功")

        print("\n🎉 迁移完成！")

        result = await conn.fetch("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'knowledge_gaps' AND column_name = 'kb_id'
        """)
        if result:
            print(f"\n验证: kb_id 字段已存在，类型为 {result[0]['data_type']}")

    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        sys.exit(1)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(migrate())
