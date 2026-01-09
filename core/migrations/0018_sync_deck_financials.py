from django.db import migrations


def sync_deck_financials_to_startup(apps, schema_editor):
    """Sync existing pitch deck financial projections to Startup fields"""
    Startup = apps.get_model('core', 'Startup')
    FinancialProjection = apps.get_model('core', 'FinancialProjection')
    
    pitch_deck_startups = Startup.objects.filter(source_deck__isnull=False)
    
    synced_count = 0
    skipped_count = 0
    
    for startup in pitch_deck_startups:
        try:
            financial = FinancialProjection.objects.filter(deck=startup.source_deck).first()
            
            if financial and all([
                financial.current_valuation,
                financial.projected_revenue_final_year,
                financial.valuation_multiple,
                financial.years_to_projection
            ]):
                # Calculate future valuation: Projected Revenue × Industry Multiple
                future_valuation = float(financial.projected_revenue_final_year) * float(financial.valuation_multiple)
                
                # Update Startup with valuation-based IRR fields
                startup.current_valuation = financial.current_valuation
                startup.expected_future_valuation = future_valuation
                startup.years_to_future_valuation = financial.years_to_projection
                startup.save()
                
                synced_count += 1
                print(f"✅ Synced Startup {startup.id}: {startup.company_name}")
            else:
                skipped_count += 1
                print(f"⏭️  Skipped Startup {startup.id}: Missing financial projection data")
                
        except Exception as e:
            print(f"⚠️  Error syncing Startup {startup.id}: {e}")
            skipped_count += 1
    
    print(f"\n✅ Migration complete!")
    print(f"   - Synced: {synced_count} startups")
    print(f"   - Skipped: {skipped_count} startups (missing data)")


def reverse_sync(apps, schema_editor):
    """Reverse migration - clear synced valuation fields"""
    Startup = apps.get_model('core', 'Startup')
    
    pitch_deck_startups = Startup.objects.filter(source_deck__isnull=False)
    count = pitch_deck_startups.update(
        current_valuation=None,
        expected_future_valuation=None,
        years_to_future_valuation=None
    )
    print(f"✅ Reversed: Cleared valuation fields for {count} pitch deck startups")


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0017_remove_financialprojection_profit_and_more'),
    ]

    operations = [
        migrations.RunPython(sync_deck_financials_to_startup, reverse_sync),
    ]