import math
from rest_framework import serializers
from .models import RegisteredUser, Deck, Startup, Problem, Solution, MarketAnalysis, FundingAsk, TeamMember, FinancialProjection, Watchlist, StartupView, StartupComparison
from datetime import timedelta
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.hashers import make_password
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import User
from django.contrib.auth import authenticate


User = get_user_model()

class BaseRegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    label = serializers.CharField(required=False)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email is already registered.")
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        password = validated_data.pop('password')
        label = validated_data.pop('label', None)

        user = User.objects.create_user(
            username=validated_data['email'],
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            password=password
        )

        RegisteredUser.objects.create(user=user, label=label)
        return user

class StartupRegistrationSerializer(BaseRegistrationSerializer):
    def validate(self, attrs):
        attrs = super().validate(attrs)
        attrs['label'] = 'startup'
        return attrs

class InvestorRegistrationSerializer(BaseRegistrationSerializer):
    def validate(self, attrs):
        attrs = super().validate(attrs)
        attrs['label'] = 'investor'
        return attrs

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        try:
            user_obj = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid email or password.")

        user = authenticate(username=user_obj.username, password=password)
        if not user:
            raise serializers.ValidationError("Invalid email or password.")

        attrs['user'] = user
        return attrs
    
class RegisteredUserProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    
    class Meta:
        model = RegisteredUser
        fields = [
            'email', 'first_name', 'last_name',
            'contact_email', 'contact_phone', 'website_url', 'linkedin_url', 'location',
            'founder_name', 'founder_title', 'founder_linkedin'
        ]
    
    def update(self, instance, validated_data):
        # Update User fields
        user_data = validated_data.pop('user', {})
        if 'first_name' in user_data:
            instance.user.first_name = user_data['first_name']
        if 'last_name' in user_data:
            instance.user.last_name = user_data['last_name']
        instance.user.save()
        
        # Update RegisteredUser fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        return instance

class DeckSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deck
        fields = ['id', 'company_name', 'tagline', 'logo', 'created_at']
        extra_kwargs = {
            'tagline': {'required': False, 'allow_blank': True},
            'logo': {'required': False, 'allow_null': True}
        }

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class StartupSerializer(serializers.ModelSerializer):
    owner_email = serializers.EmailField(source='owner.user.email', read_only=True)
    source_deck_id = serializers.IntegerField(source='source_deck.id', read_only=True)

    contact_email = serializers.SerializerMethodField()
    contact_phone = serializers.SerializerMethodField()
    website_url = serializers.SerializerMethodField()
    linkedin_url = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()
    founder_name = serializers.SerializerMethodField()
    founder_title = serializers.SerializerMethodField()
    founder_linkedin = serializers.SerializerMethodField()
    year_founded = serializers.SerializerMethodField()

    risk_level = serializers.SerializerMethodField()
    risk_score = serializers.SerializerMethodField()
    reward_potential = serializers.SerializerMethodField()
    projected_return = serializers.SerializerMethodField()
    pitch_deck_projected_return = serializers.SerializerMethodField()
    estimated_growth_rate = serializers.SerializerMethodField()
    display_industry = serializers.SerializerMethodField()
    is_in_watchlist = serializers.SerializerMethodField()
    tagline = serializers.SerializerMethodField()
    market_growth_rate = serializers.SerializerMethodField()
    analytics = serializers.SerializerMethodField()


    class Meta:
        model = Startup
        fields = [
            'id',
            'company_name',
            'industry',
            'tagline',
            'display_industry',
            'company_description',
            'data_source_confidence',
            'revenue',
            'net_income',
            'total_assets',
            'total_liabilities',
            'shareholder_equity',
            'cash_flow',
            'current_revenue',
            'previous_revenue',
            'investment_flow',
            'financing_flow',
            'reporting_period',
            'funding_ask',
            'source_deck_id',
            'is_deck_builder',
            'team_strength',
            'market_position',
            'brand_reputation',
            'confidence_percentage',
            'reward_potential',
            'estimated_growth_rate',
            'projected_return',
            'pitch_deck_projected_return',
            'risk_level',
            'risk_score',
            'owner_email',
            'created_at',
            'updated_at',
            'is_in_watchlist',
            'market_growth_rate',
            'analytics',
            'current_revenue',
            'previous_revenue',
            'time_between_periods',
            'retained_earnings',
            'ebit',
            'current_assets',
            'current_liabilities',
            'current_valuation',
            'expected_future_valuation',
            'years_to_future_valuation',
            'contact_email',
            'contact_phone',
            'website_url',
            'linkedin_url',
            'location',
            'founder_name',
            'founder_title',
            'founder_linkedin',
            'year_founded',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'owner_email', 'source_deck_id']

    def create(self, validated_data):
        """
        Override create to handle owner properly
        Owner should be passed via save(owner=...) not in validated_data
        """
        return super().create(validated_data)
    
    def get_contact_email(self, obj):
        """Get owner's contact email"""
        if obj.owner:
            return obj.owner.contact_email
        return None
    
    def get_contact_phone(self, obj):
        """Get owner's contact phone"""
        if obj.owner:
            return obj.owner.contact_phone
        return None
    
    def get_website_url(self, obj):
        """Get owner's website URL"""
        if obj.owner:
            return obj.owner.website_url
        return None
    
    def get_linkedin_url(self, obj):
        """Get owner's LinkedIn URL"""
        if obj.owner:
            return obj.owner.linkedin_url
        return None
    
    def get_location(self, obj):
        """Get owner's location"""
        if obj.owner:
            return obj.owner.location
        return None
    
    def get_founder_name(self, obj):
        """Get owner's founder name"""
        if obj.owner:
            return obj.owner.founder_name
        return None
    
    def get_founder_title(self, obj):
        """Get owner's founder title"""
        if obj.owner:
            return obj.owner.founder_title
        return None
    
    def get_founder_linkedin(self, obj):
        """Get owner's founder LinkedIn"""
        if obj.owner:
            return obj.owner.founder_linkedin
        return None
    
    def get_year_founded(self, obj):
        """Get owner's year founded"""
        if obj.owner:
            return obj.owner.year_founded
        return None

    def get_tagline(self, obj):
        """Get tagline from source deck if this is a deck builder startup"""
        if obj.source_deck:
            return obj.source_deck.tagline
        return None
    
    def get_owner_email(self, obj):
        """Get owner email, handle null owner"""
        if obj.owner and obj.owner.user:
            return obj.owner.user.email
        return None

    def get_display_industry(self, obj):
        """Show tagline for pitch decks, industry for regular startups"""
        if obj.source_deck and obj.source_deck.tagline:
            return obj.source_deck.tagline
        if obj.industry and obj.industry != "—":
            return obj.industry
        return "—"
    
    def get_market_growth_rate(self, obj):
        """Get market growth rate from source deck if available"""
        if not obj.source_deck:
            return None
        
        try:
            market_analysis = obj.source_deck.market_analysis
            if market_analysis and market_analysis.market_growth_rate is not None:
                return float(market_analysis.market_growth_rate)
        except Exception:
            return None
        
        return None

    def get_risk_level(self, obj):
        """
        Uses Altman Z-Score Formula for Private Companies (Z')
        Z' = 0.717 x (Working Capital / Total Assets) 
             + 0.847 x (Retained Earnings / Total Assets) 
             + 3.107 x (EBIT / Total Assets) 
             + 0.420 x (Book Value of Equity / Total Liabilities) 
             + 0.998 x (Sales / Total Assets)
        
        Where:
        - Working Capital = Current Assets - Current Liabilities
        - Book Value of Equity = Total Assets - Total Liabilities
        - Sales = Revenue
        
        Risk Assessment (mapped to Low/Medium/High only):
        - Z' < 1.23:  Very Risky → High
        - 1.23 - 1.8: Risky → High
        - 1.8 - 2.9: Average → Medium
        - 2.9 - 3.5: Good → Low
        - Z' > 3.5:  Excellent → Low
        """
        try:
            total_assets = float(obj.total_assets or 0)
            total_liabilities = float(obj.total_liabilities or 0)
            retained_earnings = float(getattr(obj, 'retained_earnings', 0) or 0)
            ebit = float(getattr(obj, 'ebit', 0) or 0)
            current_assets = float(getattr(obj, 'current_assets', 0) or 0)
            current_liabilities = float(getattr(obj, 'current_liabilities', 0) or 0)
            sales = float(obj.revenue or getattr(obj, 'current_revenue', 0) or 0)
            
            if total_assets <= 0:
                return None
            
            # Calculate components
            working_capital = current_assets - current_liabilities
            book_value_of_equity = total_assets - total_liabilities
            
            # Apply Altman Z' Formula for Private Companies
            x1 = 0.717 * (working_capital / total_assets)
            x2 = 0.847 * (retained_earnings / total_assets)
            x3 = 3.107 * (ebit / total_assets)
            x4 = 0.420 * (book_value_of_equity / total_liabilities) if total_liabilities > 0 else 0
            x5 = 0.998 * (sales / total_assets)
            
            z_prime = x1 + x2 + x3 + x4 + x5
            
            if z_prime > 2.9:
                return 'Low'
            elif z_prime > 1.8:
                return 'Medium'
            else:
                return 'High'
                
        except Exception as e:
            print(f"Risk calculation error: {e}")
            return None
        
    def get_risk_score(self, obj):
        """
        Convert Z' score to numeric score (1-5) for more granularity
        While risk_level remains as 3 categories (Low, Medium, High)
        
        Mapping:
        - Z' > 3.5: Score 1 (Excellent)
        - Z' 2.9-3.5: Score 2 (Good)
        - Z' 1.8-2.9: Score 3 (Average)
        - Z' 1.23-1.8: Score 4 (Risky)
        - Z' < 1.23: Score 5 (Very Risky)
        """
        try:
            total_assets = float(obj.total_assets or 0)
            total_liabilities = float(obj.total_liabilities or 0)
            retained_earnings = float(getattr(obj, 'retained_earnings', 0) or 0)
            ebit = float(getattr(obj, 'ebit', 0) or 0)
            current_assets = float(getattr(obj, 'current_assets', 0) or 0)
            current_liabilities = float(getattr(obj, 'current_liabilities', 0) or 0)
            sales = float(obj.revenue or getattr(obj, 'current_revenue', 0) or 0)
            
            if total_assets <= 0:
                return None
            
            # Calculate Z' score components
            working_capital = current_assets - current_liabilities
            book_value_of_equity = total_assets - total_liabilities
            
            x1 = 0.717 * (working_capital / total_assets)
            x2 = 0.847 * (retained_earnings / total_assets)
            x3 = 3.107 * (ebit / total_assets)
            x4 = 0.420 * (book_value_of_equity / total_liabilities) if total_liabilities > 0 else 0
            x5 = 0.998 * (sales / total_assets)
            
            z_prime = x1 + x2 + x3 + x4 + x5
            
            if z_prime > 3.5:
                return 1
            elif z_prime > 2.9:
                return 2
            elif z_prime > 1.8:
                return 3
            elif z_prime > 1.23:
                return 4
            else:
                return 5
                
        except Exception as e:
            print(f"Risk score calculation error: {e}")
            return None
    
    def get_reward_potential(self, obj):
        """
        Uses Return on Equity (ROE) to measure profitability
        ROE = Net Income / Equity
        where Equity = Total Assets - Total Liabilities
        """
        try:
            net_income = float(obj.net_income or 0)
            total_assets = float(obj.total_assets or 0)
            total_liabilities = float(obj.total_liabilities or 0)

            # Calculate equity from total assets and liabilities
            equity = total_assets - total_liabilities

            # Check if we have usable data
            if equity <= 0:
                return "N/A"
            
            roe_percentage = (net_income / equity) * 100    
            
            # Convert ROE to 1-5 scale
            if roe_percentage >= 20:
                return 5.0
            elif roe_percentage >= 15:
                return 4.0
            elif roe_percentage >= 10:
                return 3.0
            elif roe_percentage >= 5:
                return 2.0
            else:
                return 1.0
            
        except Exception as e:
            print(f"Reward potential calculation error: {e}")
            return "N/A"
        
    def get_projected_return(self, obj):
        """
        Calculate Projected Return ONLY for normal startups using IRR formula
        Uses explicit valuation fields: current_valuation, expected_future_valuation, years_to_future_valuation
        
        Formula: IRR = (Expected Future Valuation / Current Valuation)^(1/years) - 1
        Returns as percentage. Pure calculation without risk adjustment.
        
        For pitch decks, use get_pitch_deck_projected_return() instead
        """
        try:
            current_valuation = float(getattr(obj, 'current_valuation', 0) or 0)
            expected_future_valuation = float(getattr(obj, 'expected_future_valuation', 0) or 0)
            years_to_future_valuation = float(getattr(obj, 'years_to_future_valuation', 1) or 1)
            
            if current_valuation > 0 and expected_future_valuation > 0 and years_to_future_valuation > 0:
                # IRR = (Expected Future Valuation / Current Valuation)^(1/years) - 1
                irr = (math.pow(expected_future_valuation / current_valuation, 1 / years_to_future_valuation) - 1) * 100
                return round(max(min(irr, 200), -100), 2)
            
            return None
            
        except Exception as e:
            print(f"Projected return calculation error: {e}")
            return None
    
    def get_pitch_deck_projected_return(self, obj):
        """
        Uses pitch deck data: current_valuation, projected_revenue, industry_multiple, years_to_projection
        
        Formula:
        Future Valuation = Projected Revenue × Industry Multiple
        IRR = (Future Valuation / Current Valuation)^(1/years) - 1
        """
        try:
            if not obj.source_deck:
                return None
            
            try:
                current_valuation = float(getattr(obj.source_deck.ask, 'amount', 0) or 0) if obj.source_deck.ask else 0
            except:
                current_valuation = 0
            
            try:
                financials = obj.source_deck.financials.all().order_by('year')
                market_analysis = obj.source_deck.market_analysis
                
                if financials.count() >= 1 and market_analysis:
                    latest_financial = financials.last()
                    projected_revenue = float(latest_financial.revenue or 0)
                    industry_multiple = float(getattr(market_analysis, 'valuation_multiple', 0) or 0)
                    
                    # Calculate years from earliest to latest projection
                    earliest_financial = financials.first()
                    years_to_projection = latest_financial.year - earliest_financial.year
                    
                    # Verify all required values
                    if current_valuation > 0 and projected_revenue > 0 and industry_multiple > 0 and years_to_projection > 0:
                        # Future Valuation = Projected Revenue × Industry Multiple
                        future_valuation = projected_revenue * industry_multiple
                        
                        # IRR = (Future Valuation / Current Valuation)^(1/years) - 1
                        irr = (math.pow(future_valuation / current_valuation, 1 / years_to_projection) - 1) * 100
                        return round(max(min(irr, 200), -100), 2)
            except:
                pass
            
            return None
            
        except Exception as e:
            print(f"Pitch deck projected return calculation error: {e}")
            return None

    def get_estimated_growth_rate(self, obj):
        """
        Calculate Estimated Growth Rate using CAGR formula
        CAGR = (Current Revenue / Prior Revenue)^(1/years) - 1
        Returns as percentage
        """
        try:
            if obj.source_deck:
                financials = obj.source_deck.financials.all().order_by('year')
                
                if financials.count() >= 2:
                    earliest = financials.first()
                    latest = financials.last()
                    
                    earliest_revenue = float(earliest.revenue)
                    latest_revenue = float(latest.revenue)
                    number_of_years = latest.year - earliest.year
                    
                    if earliest_revenue > 0 and latest_revenue > 0 and number_of_years > 0:
                        # CAGR = [(Latest / Earliest)^(1/years) - 1] × 100
                        cagr = (math.pow(latest_revenue / earliest_revenue, 1 / number_of_years) - 1) * 100
                        return round(max(min(cagr, 200), -100), 2)
                
                return None
            
            # Regular startup calculation
            current_revenue = float(obj.revenue or getattr(obj, 'current_revenue', 0) or 0)
            previous_revenue = float(getattr(obj, 'previous_revenue', 0) or 0)
            time_between_periods = float(getattr(obj, 'time_between_periods', 1) or 1)
            
            if current_revenue <= 0 or previous_revenue <= 0 or time_between_periods <= 0:
                return None
            
            # CAGR = (Current / Prior)^(1/years) - 1
            revenue_ratio = current_revenue / previous_revenue
            cagr = (math.pow(revenue_ratio, 1 / time_between_periods) - 1) * 100
            cagr = max(min(cagr, 200), -100)
            
            return round(cagr, 2)
            
        except Exception as e:
            print(f"Estimated growth rate calculation error: {e}")
            return None
    
    def get_is_in_watchlist(self, obj):
        """Check if the startup is in the current user's watchlist"""
        request = self.context.get('request')
        
        if not request or not request.user.is_authenticated:
            return False
        
        return Watchlist.objects.filter(
            user=request.user,
            startup=obj
        ).exists()
    
    def get_analytics(self, obj):
        """Get view and comparison analytics for this startup"""
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        try:
            total_views = StartupView.objects.filter(startup=obj).count()
            unique_viewers = StartupView.objects.filter(startup=obj).values('user').distinct().count()
            total_comparisons = StartupComparison.objects.filter(startup=obj).count()
            unique_comparers = StartupComparison.objects.filter(startup=obj).values('user').distinct().count()
            watchlist_count = Watchlist.objects.filter(startup=obj).count()
            recent_views = StartupView.objects.filter(startup=obj, viewed_at__gte=thirty_days_ago).count()
            recent_comparisons = StartupComparison.objects.filter(startup=obj, compared_at__gte=thirty_days_ago).count()
            recent_watchlist = Watchlist.objects.filter(startup=obj, added_at__gte=thirty_days_ago).count()
            
            return {
                'total_views': total_views,
                'unique_viewers': unique_viewers,
                'total_comparisons': total_comparisons,
                'unique_comparers': unique_comparers,
                'watchlist_count': watchlist_count,
                'recent_views': recent_views,
                'recent_comparisons': recent_comparisons,
                'recent_watchlist': recent_watchlist,
            }
        except Exception as e:
            print(f"Analytics error for startup {obj.id}: {e}")
            return {
                'total_views': 0,
                'unique_viewers': 0,
                'total_comparisons': 0,
                'unique_comparers': 0,
                'watchlist_count': 0,
                'recent_views': 0,
                'recent_comparisons': 0,
                'recent_watchlist': 0,
            }

class ProblemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Problem
        fields = ['id', 'deck', 'description']

class SolutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Solution
        fields = ['id', 'deck', 'description']

class MarketAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketAnalysis
        fields = [
            'id',
            'deck',
            'primary_market',
            'target_audience',
            'market_growth_rate',
            'competitive_advantage'
        ]

class FundingAskSerializer(serializers.ModelSerializer):
    class Meta:
        model = FundingAsk
        fields = ['id', 'deck', 'amount', 'usage_description']

class TeamMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeamMember
        fields = ['id', 'deck', 'name', 'title']

class FinancialProjectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialProjection
        fields = ['id', 'deck', 'year', 'revenue', 'profit']

class DeckDetailSerializer(serializers.ModelSerializer):
    problem = ProblemSerializer(read_only=True)
    solution = SolutionSerializer(read_only=True)
    market_analysis = MarketAnalysisSerializer(read_only=True)
    team_members = TeamMemberSerializer(many=True, read_only=True)
    financials = FinancialProjectionSerializer(many=True, read_only=True)
    ask = FundingAskSerializer(read_only=True)

    class Meta:
        model = Deck
        fields = [
            'id', 'company_name', 'tagline', 'logo',
            'team_members', 'financials', 'ask', 'problem', 'solution', 'market_analysis','created_at'
        ]

class DeckReportSerializer(serializers.ModelSerializer):
    problem = serializers.SerializerMethodField()
    solution = serializers.SerializerMethodField()
    market_analysis = serializers.SerializerMethodField()
    financials = FinancialProjectionSerializer(many=True)
    ask = serializers.SerializerMethodField()

    class Meta:
        model = Deck
        fields = ['company_name', 'tagline', 'problem', 'solution', 'market_analysis', 'financials', 'ask','created_at']

    def get_problem(self, obj):
        return {'description': obj.problem.description} if obj.problem else {}

    def get_solution(self, obj):
        return {'description': obj.solution.description} if obj.solution else {}

    def get_market_analysis(self, obj):
        if obj.market_analysis:
            return {
                'primary_market': obj.market_analysis.primary_market,
                'target_audience': obj.market_analysis.target_audience,
                'market_growth_rate': obj.market_analysis.market_growth_rate,
                'competitive_advantage': obj.market_analysis.competitive_advantage
            }
        return {}

    def get_ask(self, obj):
        return {
            'amount': obj.ask.amount,
            'usage_description': obj.ask.usage_description
        } if obj.ask else {}