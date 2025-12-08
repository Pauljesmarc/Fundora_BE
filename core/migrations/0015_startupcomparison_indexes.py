# Generated migration for optimizing StartupComparison queries

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_startupview_indexes'),  # Update to your latest migration
    ]

    operations = [
        # Index for user's comparison history
        migrations.AddIndex(
            model_name='startupcomparison',
            index=models.Index(
                fields=['user', '-compared_at'],
                name='user_comp_idx'
            ),
        ),
        
        # Index for startup comparison analytics
        migrations.AddIndex(
            model_name='startupcomparison',
            index=models.Index(
                fields=['startup', '-compared_at'],
                name='startup_comp_idx'
            ),
        ),
        
        # Index for comparison set queries
        migrations.AddIndex(
            model_name='startupcomparison',
            index=models.Index(
                fields=['comparison_set_id', '-compared_at'],
                name='compset_idx'
            ),
        ),
        
        # Composite index for deduplication checks
        migrations.AddIndex(
            model_name='startupcomparison',
            index=models.Index(
                fields=['user', 'startup', '-compared_at'],
                name='comp_dedup_idx'
            ),
        ),
    ]
