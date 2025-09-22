from django.contrib import admin

# Register your models here.
from .models import (
    Deck, Problem, Solution, MarketAnalysis, TeamMember, 
    FinancialProjection, FundingAsk, StartupView, StartupComparison,
    Startup, RegisteredUser, Watchlist, ComparisonSet, Download
)

admin.site.register(Deck)
admin.site.register(Problem)
admin.site.register(Solution)
admin.site.register(MarketAnalysis)
admin.site.register(TeamMember)
admin.site.register(FinancialProjection)
admin.site.register(FundingAsk)
admin.site.register(Startup)
admin.site.register(RegisteredUser)
admin.site.register(Watchlist)
admin.site.register(ComparisonSet)
admin.site.register(Download)

# Analytics models with custom admin
@admin.register(StartupView)
class StartupViewAdmin(admin.ModelAdmin):
    list_display = ('user', 'startup', 'viewed_at', 'ip_address')
    list_filter = ('viewed_at', 'startup')
    search_fields = ('user__email', 'startup__company_name')
    date_hierarchy = 'viewed_at'

@admin.register(StartupComparison)
class StartupComparisonAdmin(admin.ModelAdmin):
    list_display = ('user', 'startup', 'compared_at', 'comparison_set_id')
    list_filter = ('compared_at', 'startup')
    search_fields = ('user__email', 'startup__company_name', 'comparison_set_id')
    date_hierarchy = 'compared_at'