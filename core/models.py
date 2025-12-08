from django.db import models
from django.contrib.auth.models import User


# MOD 1 AND 2
class Watchlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    startup = models.ForeignKey('Startup', on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)
    compared = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'startup')

    def __str__(self):
        return f"{self.user.username} - {self.startup.company_name}"
    
class Download(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    startup = models.ForeignKey('Startup', on_delete=models.CASCADE)
    download_type = models.CharField(max_length=50, default='company_profile')
    downloaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'startup', 'download_type']
    
    def __str__(self):
        return f"{self.user.username} - {self.startup.company_name} - {self.download_type}"
    
class ComparisonSet(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, blank=True)  # Optional name for the comparison
    created_at = models.DateTimeField(auto_now_add=True)
    startups = models.ManyToManyField('Startup', related_name='comparison_sets')
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        startup_names = [s.company_name for s in self.startups.all()[:3]]
        if len(startup_names) > 2:
            return f"{' vs '.join(startup_names[:2])} vs {startup_names[2]}"
        return ' vs '.join(startup_names)
    
    @property
    def startup_count(self):
        return self.startups.count()

class Deck(models.Model):
    owner = models.ForeignKey('RegisteredUser', on_delete=models.CASCADE, related_name='decks')
    company_name = models.CharField(max_length=255)
    tagline = models.CharField(max_length=255)
    logo = models.ImageField(upload_to='', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # One-to-one relationships for each section
    # These will be created/linked after the Deck is created

class Problem(models.Model):
    deck = models.OneToOneField(Deck, on_delete=models.CASCADE, related_name='problem')
    description = models.TextField()

class Solution(models.Model):
    deck = models.OneToOneField(Deck, on_delete=models.CASCADE, related_name='solution')
    description = models.TextField()

class MarketAnalysis(models.Model):
    deck = models.OneToOneField(Deck, on_delete=models.CASCADE, related_name='market_analysis')
    primary_market = models.CharField(max_length=255)
    target_audience = models.TextField()
    market_growth_rate = models.DecimalField(max_digits=5, decimal_places=2)  # e.g., 12.50%
    competitive_advantage = models.TextField()

class TeamMember(models.Model):
    deck = models.ForeignKey(Deck, on_delete=models.CASCADE, related_name='team_members')
    name = models.CharField(max_length=255)
    title = models.CharField(max_length=255)

class FinancialProjection(models.Model):
    deck = models.ForeignKey(Deck, on_delete=models.CASCADE, related_name='financials')
    year = models.PositiveIntegerField()
    revenue = models.DecimalField(max_digits=12, decimal_places=2)
    profit = models.DecimalField(max_digits=12, decimal_places=2)

class FundingAsk(models.Model):
    deck = models.OneToOneField(Deck, on_delete=models.CASCADE, related_name='ask')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    usage_description = models.TextField()


# Module 3 - Startup Registration

class RegisteredUser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', null=True)
    label = models.CharField(max_length=50, null=True, blank=True, default=None)

    # Contact
    contact_email = models.EmailField(null=True, blank=True)
    contact_phone = models.CharField(max_length=20, null=True, blank=True)
    website_url = models.URLField(null=True, blank=True)
    linkedin_url = models.URLField(null=True, blank=True)
    location = models.CharField(max_length=255, null=True, blank=True, help_text="City, Country")

    # Founder Info
    founder_name = models.CharField(max_length=255, null=True, blank=True)
    founder_title = models.CharField(max_length=100, null=True, blank=True)
    founder_linkedin = models.URLField(null=True, blank=True)

    #Additional Info
    year_founded = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} - {self.user.email}"


class Startup(models.Model):
    """Model to store startup company data submitted by users"""
    owner = models.ForeignKey(
        RegisteredUser, 
        on_delete=models.CASCADE, 
        related_name='startups',
        null=True,
        blank=True
    )
    company_name = models.CharField(max_length=255)
    industry = models.CharField(max_length=255)
    company_description = models.TextField()
    data_source_confidence = models.CharField(max_length=50, default='Medium')
    is_deck_builder = models.BooleanField(default=False)
    
    # Financial data
    revenue = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    net_income = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    total_assets = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    total_liabilities = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    shareholder_equity = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    cash_flow = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    # For CAGR Calculation (Projected Return)
    time_between_periods = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Number of years between previous and current revenue (e.g., 1.0 for annual)"
    )
    
    # For Altman Z-Score (Risk Level)
    retained_earnings = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Accumulated retained earnings from prior periods"
    )
    
    ebit = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Earnings Before Interest and Taxes"
    )
    
    current_assets = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Assets that can be converted to cash within one year"
    )
    
    current_liabilities = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Debts due within one year"
    )

    current_valuation = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Current market valuation of the company"
    )
    
    expected_future_valuation = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Expected future valuation at target date"
    )
    
    years_to_future_valuation = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Number of years until expected future valuation is reached"
    )
    
    # Additional Financial Data
    current_revenue = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    previous_revenue = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    investment_flow = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    financing_flow = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    reporting_period = models.CharField(max_length=50, null=True, blank=True)

    # Funding ask amount (from deck builder)
    funding_ask = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    funding_usage = models.TextField(null=True, blank=True)
    
    # Reference to original deck (if created from deck builder)
    source_deck = models.ForeignKey(Deck, on_delete=models.SET_NULL, null=True, blank=True, related_name='recommended_startups')
    
    # Qualitative data
    team_strength = models.TextField(blank=True)
    market_position = models.TextField(blank=True)
    brand_reputation = models.TextField(blank=True)
    
    confidence_percentage = models.IntegerField(default=75)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.company_name} - {self.owner.user.email}"

# Analytics tracking models
class StartupView(models.Model):
    """Track when users view startup profiles"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    startup = models.ForeignKey(Startup, on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)  # Optional for additional tracking
    
    class Meta:
        ordering = ['-viewed_at']
        indexes = [
            # Index for deduplication queries (user + startup + recent views)
            models.Index(fields=['user', 'startup', '-viewed_at'], name='view_dedup_idx'),
            # Index for startup analytics queries (total views per startup)
            models.Index(fields=['startup', '-viewed_at'], name='startup_views_idx'),
            # Index for user activity queries (user's view history)
            models.Index(fields=['user', '-viewed_at'], name='user_views_idx'),
        ]
    
    def __str__(self):
        return f"{self.user.email} viewed {self.startup.company_name} on {self.viewed_at.date()}"

class StartupComparison(models.Model):
    """Track when startups are included in comparisons"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    startup = models.ForeignKey(Startup, on_delete=models.CASCADE)
    compared_at = models.DateTimeField(auto_now_add=True)
    comparison_set_id = models.CharField(max_length=100, null=True, blank=True)  # To group comparisons
    
    class Meta:
        ordering = ['-compared_at']
        indexes = [
            # Index for user's comparison history
            models.Index(fields=['user', '-compared_at'], name='user_comp_idx'),
            # Index for startup comparison analytics
            models.Index(fields=['startup', '-compared_at'], name='startup_comp_idx'),
            # Index for comparison set queries
            models.Index(fields=['comparison_set_id', '-compared_at'], name='compset_idx'),
            # Composite index for deduplication checks
            models.Index(fields=['user', 'startup', '-compared_at'], name='comp_dedup_idx'),
        ]
    
    def __str__(self):
        return f"{self.user.email} compared {self.startup.company_name} on {self.compared_at.date()}"
