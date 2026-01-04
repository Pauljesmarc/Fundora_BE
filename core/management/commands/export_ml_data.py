from django.core.management.base import BaseCommand
import pandas as pd
from datetime import datetime
from core.models import Startup, StartupView, Watchlist, StartupComparison, RegisteredUser
from django.contrib.auth.models import User
import os

class Command(BaseCommand):
    help = 'Export data for ML training'

    def handle(self, *args, **options):
        self.stdout.write('Exporting ML training data...')
        
        # Export startups
        startups = Startup.objects.all().values(
            'id', 'company_name', 'industry', 'data_source_confidence',
            'revenue', 'net_income', 'total_assets', 'total_liabilities',
            'current_revenue', 'previous_revenue', 'confidence_percentage',
            'is_deck_builder', 'current_valuation', 'expected_future_valuation',
            'years_to_future_valuation', 'current_assets', 'current_liabilities',
            'retained_earnings', 'ebit', 'created_at'
        )
        startups_df = pd.DataFrame(list(startups))
        
        # Export interactions
        interactions = StartupView.objects.all().values(
            'user_id', 'startup_id', 'viewed_at'
        )
        interactions_df = pd.DataFrame(list(interactions))
        
        # Add engagement levels
        if not interactions_df.empty:
            interactions_df['engagement_level'] = 1  # Default: view
            
            # Mark comparisons
            comparisons = set(StartupComparison.objects.values_list('user_id', 'startup_id'))
            interactions_df.loc[
                interactions_df.apply(lambda x: (x['user_id'], x['startup_id']) in comparisons, axis=1),
                'engagement_level'
            ] = 2
            
            # Mark watchlist
            watchlist = set(Watchlist.objects.values_list('user_id', 'startup_id'))
            interactions_df.loc[
                interactions_df.apply(lambda x: (x['user_id'], x['startup_id']) in watchlist, axis=1),
                'engagement_level'
            ] = 3
        
        # Export users
        users = User.objects.all().values('id', 'email', 'date_joined')
        users_df = pd.DataFrame(list(users))
        
        # Add user labels
        try:
            user_labels = RegisteredUser.objects.all().values('user_id', 'label')
            user_labels_df = pd.DataFrame(list(user_labels))
            if not user_labels_df.empty:
                users_df = users_df.merge(user_labels_df, left_on='id', right_on='user_id', how='left')
        except:
            pass
        
        # Save to CSV
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = os.path.join('..', 'fundora-ml-service-1', 'data', 'raw')
        os.makedirs(output_dir, exist_ok=True)
        
        startups_df.to_csv(os.path.join(output_dir, f'startups_{timestamp}.csv'), index=False)
        interactions_df.to_csv(os.path.join(output_dir, f'interactions_{timestamp}.csv'), index=False)
        users_df.to_csv(os.path.join(output_dir, f'users_{timestamp}.csv'), index=False)
        
        self.stdout.write(self.style.SUCCESS(
            f'✅ Exported:\n'
            f'   - {len(startups_df)} startups\n'
            f'   - {len(interactions_df)} interactions\n'
            f'   - {len(users_df)} users\n'
            f'To: {output_dir}'
        ))