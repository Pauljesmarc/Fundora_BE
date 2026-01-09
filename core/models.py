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
    market_growth_rate = models.DecimalField(max_digits=5, decimal_places=2)
    competitive_advantage = models.TextField()

class TeamMember(models.Model):
    deck = models.ForeignKey(Deck, on_delete=models.CASCADE, related_name='team_members')
    name = models.CharField(max_length=255)
    title = models.CharField(max_length=255)

class FinancialProjection(models.Model):
    deck = models.ForeignKey(Deck, on_delete=models.CASCADE, related_name='financials')
    valuation_multiple = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    current_valuation = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    projected_revenue_final_year = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    years_to_projection = models.PositiveIntegerField(null=True, blank=True)

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
    """Unified model for all startup data - combines financial and pitch deck startups"""
    
    # Existing owner relationship
    owner = models.ForeignKey(
        RegisteredUser, 
        on_delete=models.CASCADE, 
        related_name='startups',
        null=True,
        blank=True
    )
    
    # ===== 1. IDENTITY AND BASICS =====
    company_name = models.CharField(max_length=255)
    logo = models.ImageField(upload_to='startup_logos/', blank=True, null=True)
    tagline = models.CharField(max_length=255, blank=True, null=True)
    industry = models.CharField(max_length=255)
    headquarters = models.CharField(max_length=255, null=True, blank=True, help_text="City, Country")
    year_founded = models.IntegerField(null=True, blank=True)
    company_stage = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        choices=[
            ('idea', 'Idea'),
            ('mvp', 'MVP'),
            ('early_revenue', 'Early Revenue'),
            ('growth', 'Growth'),
            ('scale', 'Scale'),
        ]
    )
    company_description = models.TextField()
    website_url = models.URLField(null=True, blank=True)
    linkedin_url = models.URLField(null=True, blank=True)
    twitter_url = models.URLField(null=True, blank=True)
    facebook_url = models.URLField(null=True, blank=True)
    
    # ===== 2. PROBLEM, SOLUTION, AND PRODUCT =====
    problem_statement = models.TextField(null=True, blank=True)
    solution_description = models.TextField(null=True, blank=True)
    how_it_works = models.TextField(null=True, blank=True)
    key_features = models.TextField(null=True, blank=True, help_text="JSON array or bullet points")
    supported_platforms = models.CharField(max_length=255, null=True, blank=True, help_text="e.g., Web, iOS, Android")
    product_status = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        choices=[
            ('prototype', 'Prototype'),
            ('beta', 'Beta'),
            ('live', 'Live'),
            ('revenue_generating', 'Revenue Generating'),
        ]
    )
    
    # ===== 3. MARKET AND POSITIONING =====
    primary_market = models.CharField(max_length=255, null=True, blank=True)
    target_customer_segments = models.TextField(null=True, blank=True)
    target_geography = models.CharField(max_length=255, null=True, blank=True, help_text="e.g., PH, SEA, Global")
    market_size_tam = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, help_text="Total Addressable Market")
    market_size_sam = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, help_text="Serviceable Addressable Market")
    market_growth_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Percentage")
    competitors = models.TextField(null=True, blank=True)
    competitive_advantage = models.TextField(null=True, blank=True)
    go_to_market_strategy = models.TextField(null=True, blank=True)
    
    # ===== 4. TRACTION AND PERFORMANCE =====
    current_mrr_arr = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, help_text="Monthly/Annual Recurring Revenue")
    total_users = models.IntegerField(null=True, blank=True)
    paid_users = models.IntegerField(null=True, blank=True)
    key_traction_metrics = models.TextField(null=True, blank=True, help_text="GMV, MAU, retention, churn, NPS, etc.")
    major_milestones = models.TextField(null=True, blank=True)
    notable_customers = models.TextField(null=True, blank=True)
    
    # ===== 5. TEAM AND GOVERNANCE =====
    # Founder info (primary founder from RegisteredUser)
    additional_founders = models.TextField(null=True, blank=True, help_text="JSON array of founder objects")
    key_team_members = models.TextField(null=True, blank=True, help_text="JSON array of team member objects")
    advisors = models.TextField(null=True, blank=True, help_text="JSON array of advisor objects")
    team_size = models.IntegerField(null=True, blank=True, help_text="Number of full-time/part-time staff")
    
    # ===== 6. BUSINESS MODEL AND OPERATIONS =====
    business_model_type = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="e.g., SaaS, Marketplace, Transaction Fee, Hardware"
    )
    revenue_streams = models.TextField(null=True, blank=True)
    pricing_example = models.CharField(max_length=255, null=True, blank=True)
    key_partnerships = models.TextField(null=True, blank=True)
    operational_status = models.TextField(null=True, blank=True)
    
    # ===== 7. FINANCIALS =====
    reporting_period = models.CharField(max_length=50, null=True, blank=True)
    revenue = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    net_income = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    total_assets = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    total_liabilities = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    shareholder_equity = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    cash_flow = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    current_revenue = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    previous_revenue = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    investment_flow = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    financing_flow = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    
    # Additional financial fields for Altman Z-Score
    retained_earnings = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    ebit = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    current_assets = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    current_liabilities = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    
    # Unit economics
    cac = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, help_text="Customer Acquisition Cost")
    ltv = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, help_text="Lifetime Value")
    gross_margin = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Percentage")
    
    # ===== 8. RISK, RETURN, AND PROJECTIONS =====
    current_valuation = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    expected_future_valuation = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    years_to_future_valuation = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    time_between_periods = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    financial_projections = models.TextField(null=True, blank=True, help_text="JSON array of yearly projections")
    key_assumptions = models.TextField(null=True, blank=True)
    
    # Qualitative assessments
    team_strength = models.TextField(blank=True)
    market_position = models.TextField(blank=True)
    brand_reputation = models.TextField(blank=True)
    confidence_percentage = models.IntegerField(default=75)
    data_source_confidence = models.CharField(max_length=50, default='Medium')
    
    # ===== 9. FUNDING HISTORY AND CURRENT ROUND =====
    capital_raised_to_date = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    funding_history = models.TextField(null=True, blank=True, help_text="JSON array of past rounds")
    current_round_type = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        choices=[
            ('pre_seed', 'Pre-Seed'),
            ('seed', 'Seed'),
            ('series_a', 'Series A'),
            ('series_b', 'Series B'),
            ('series_c', 'Series C+'),
        ]
    )
    funding_ask = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    funding_usage = models.TextField(null=True, blank=True)
    target_valuation = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    expected_runway_months = models.IntegerField(null=True, blank=True)
    
    # ===== 10. IMPACT, IP, AND OTHER SIGNALS =====
    impact_statement = models.TextField(null=True, blank=True)
    sdg_alignment = models.TextField(null=True, blank=True, help_text="Sustainable Development Goals alignment")
    intellectual_property = models.TextField(null=True, blank=True, help_text="Patents, proprietary tech")
    regulatory_status = models.TextField(null=True, blank=True, help_text="Licenses, compliance status")
    awards_and_recognition = models.TextField(null=True, blank=True)
    
    # ===== 11. MEDIA AND DOCUMENTS =====
    demo_video_url = models.URLField(null=True, blank=True)
    pitch_video_url = models.URLField(null=True, blank=True)
    pitch_deck_pdf = models.FileField(upload_to='pitch_decks/', null=True, blank=True)
    one_pager_pdf = models.FileField(upload_to='one_pagers/', null=True, blank=True)
    data_room_url = models.URLField(null=True, blank=True)
    
    # ===== 12. CONTACT AND PREFERENCES =====
    primary_contact_name = models.CharField(max_length=255, null=True, blank=True)
    contact_email = models.EmailField(null=True, blank=True)
    contact_phone = models.CharField(max_length=20, null=True, blank=True)
    contact_whatsapp = models.CharField(max_length=20, null=True, blank=True)
    contact_telegram = models.CharField(max_length=100, null=True, blank=True)
    preferred_check_size_min = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    preferred_check_size_max = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    investor_preferences = models.TextField(null=True, blank=True)
    
    # ===== LEGACY FIELDS (Keep for backward compatibility) =====
    source_deck = models.ForeignKey(
        Deck, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='recommended_startups',
        help_text="DEPRECATED: Original deck reference for migration purposes"
    )
    
    # ===== METADATA =====
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company_name']),
            models.Index(fields=['industry']),
            models.Index(fields=['company_stage']),
            models.Index(fields=['current_round_type']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        if self.owner:
            return f"{self.company_name} - {self.owner.user.email}"
        return f"{self.company_name}"
    
    @property
    def is_deck_builder(self):
        """DEPRECATED: Check if originated from deck builder"""
        return self.source_deck is not None

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
