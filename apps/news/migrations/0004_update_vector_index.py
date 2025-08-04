# 这将创建类似 /apps/news/migrations/0004_update_vector_index.py 的文件

from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('news', '0003_alter_newsarticle_embedding_and_more'),  # 确保依赖于你最新的迁移
    ]

    operations = [
        # 删除旧的B-tree索引 (如果存在)
        migrations.RunSQL(
            "DROP INDEX IF EXISTS news_newsarticle_embedding_7808ff8a;",
            reverse_sql=migrations.RunSQL.noop  # 回滚时不做任何操作
        ),
        
        # 创建适合向量搜索的IVFFlat索引
        migrations.RunSQL(
            """
            CREATE INDEX IF NOT EXISTS news_newsarticle_embedding_ivfflat_idx 
            ON news_newsarticle USING ivfflat (embedding vector_l2_ops) 
            WITH (lists = 100);
            """,
            reverse_sql="DROP INDEX IF EXISTS news_newsarticle_embedding_ivfflat_idx;"
        ),
    ]