# Generated migration for optimizing StartupView queries

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_remove_startup_contact_email_and_more'),  # Update to your latest migration
    ]

    operations = [
        # Index for deduplication queries (user + startup + recent views)
        migrations.AddIndex(
            model_name='startupview',
            index=models.Index(
                fields=['user', 'startup', '-viewed_at'],
                name='view_dedup_idx'
            ),
        ),
        
        # Index for startup analytics queries (total views per startup)
        migrations.AddIndex(
            model_name='startupview',
            index=models.Index(
                fields=['startup', '-viewed_at'],
                name='startup_views_idx'
            ),
        ),
        
        # Index for user activity queries (user's view history)
        migrations.AddIndex(
            model_name='startupview',
            index=models.Index(
                fields=['user', '-viewed_at'],
                name='user_views_idx'
            ),
        ),
    ]
