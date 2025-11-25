from rest_framework import serializers
from .models import RegisteredUser, Deck, Startup, Problem, Solution, MarketAnalysis, FundingAsk, TeamMember, FinancialProjection, Watchlist
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

    reward_potential = serializers.SerializerMethodField()
    projected_return = serializers.SerializerMethodField()
    risk_level = serializers.SerializerMethodField()
    display_industry = serializers.SerializerMethodField()
    is_in_watchlist = serializers.SerializerMethodField()
    tagline = serializers.SerializerMethodField()
    market_growth_rate = serializers.SerializerMethodField()


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
            'projected_return',
            'risk_level',
            'owner_email',
            'created_at',
            'updated_at',
            'is_in_watchlist',
            'market_growth_rate',
            'current_revenue',
            'previous_revenue',
            'time_between_periods',
            'retained_earnings',
            'ebit',
            'current_assets',
            'current_liabilities',
        ]

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
            # Access the OneToOne relationship - will raise DoesNotExist if not present
            market_analysis = obj.source_deck.market_analysis
            if market_analysis and market_analysis.market_growth_rate is not None:
                return float(market_analysis.market_growth_rate)
        except Exception:
            # Handle all exceptions (DoesNotExist, AttributeError, etc.)
            return None
        
        return None

    def get_reward_potential(self, obj):
        """
        Uses Return on Equity (ROE) to measure profitability
        ROE = (Net Income / Shareholder Equity) × 100
        Matches calculate_reward_potential() function in views.py
        """
        try:
            net_income = float(obj.net_income or 0)
            shareholder_equity = float(obj.shareholder_equity or 0)
            total_assets = float(obj.total_assets or 0)

            # Check if we have ANY usable data
            if shareholder_equity <= 0 and total_assets <= 0:
                return "N/A"
            
            # Primary: Calculate ROE
            if shareholder_equity > 0:
                roe_percentage = (net_income / shareholder_equity) * 100    
                
                # Convert ROE to 1-5 scale
                if roe_percentage >= 20:
                    return 5.0  # Excellent
                elif roe_percentage >= 15:
                    return 4.0  # Good ← Your 18.75% should hit here
                elif roe_percentage >= 10:
                    return 3.0  # Average
                elif roe_percentage >= 5:
                    return 2.0  # Below Average
                else:
                    return 1.0  # Low Reward
            
            # Fallback: Calculate ROA if equity not available
            elif total_assets > 0:
                roa_percentage = (net_income / total_assets) * 100
                
                # Convert ROA to 1-5 scale
                if roa_percentage >= 15:
                    return 5.0
                elif roa_percentage >= 10:
                    return 4.0
                elif roa_percentage >= 5:
                    return 3.0
                elif roa_percentage >= 2:
                    return 2.0
                else:
                    return 1.0
            
            return "N/A"
            
        except Exception as e:
            print(f"Reward potential calculation error: {e}")
            return "N/A"

    def get_projected_return(self, obj):
        """
        Calculate projected return using Revenue CAGR with risk adjustment
        Matches calculate_projected_return() function in views.py
        """
        try:
            current_revenue = float(obj.revenue or getattr(obj, 'current_revenue', 0) or 0)
            previous_revenue = float(getattr(obj, 'previous_revenue', 0) or 0)
            time_between_periods = float(getattr(obj, 'time_between_periods', 1) or 1)
            
            # Validate data availability
            if current_revenue <= 0 or previous_revenue <= 0 or time_between_periods <= 0:
                # Fallback to simple profit margin if no revenue growth data
                net_income = float(obj.net_income or 0)
                if current_revenue > 0:
                    profit_margin = (net_income / current_revenue) * 100
                    return round(max(profit_margin, 0), 2)
                return 0.0
            
            # Step 1: Calculate CAGR
            revenue_ratio = current_revenue / previous_revenue
            cagr = (math.pow(revenue_ratio, 1 / time_between_periods) - 1) * 100
            
            # Cap CAGR at reasonable limits
            cagr = max(min(cagr, 100), -50)
            
            # Step 2: Get Risk Level and Apply Adjustment Factor
            risk_level = self.get_risk_level(obj)
            
            if risk_level == 'Low':
                adjustment_factor = 1.00  # Aggressive
            elif risk_level == 'Medium':
                adjustment_factor = 0.85  # Moderate
            else:  # High risk or None
                adjustment_factor = 0.70  # Conservative
            
            # Step 3: Calculate Risk-Adjusted Projected Return
            projected_return = cagr * adjustment_factor
            
            return round(projected_return, 2)
            
        except Exception as e:
            print(f"Projected return calculation error: {e}")
            return 0.0
    
    def get_risk_level(self, obj):
        """
        Uses Original Altman Z-Score for comprehensive risk assessment
        Z = 1.2A + 1.4B + 3.3C + 0.6D + 1.0E
        Matches calculate_financial_risk() function in views.py
        
        Returns: 'Low', 'Medium', 'High', 'No Data', or 'Error'
        """
        try:
            total_assets = float(obj.total_assets or 0)
            total_liabilities = float(obj.total_liabilities or 0)
            shareholder_equity = float(obj.shareholder_equity or 0)
            retained_earnings = float(getattr(obj, 'retained_earnings', 0) or 0)
            ebit = float(getattr(obj, 'ebit', 0) or 0)
            current_assets = float(getattr(obj, 'current_assets', 0) or 0)
            current_liabilities = float(getattr(obj, 'current_liabilities', 0) or 0)
            revenue = float(obj.revenue or getattr(obj, 'current_revenue', 0) or 0)
            
            # Validate minimum data requirements
            if total_assets <= 0:
                return 'No Data'
            
            # Calculate Working Capital
            working_capital = current_assets - current_liabilities
            
            # Calculate Z-Score components
            A = working_capital / total_assets
            B = retained_earnings / total_assets
            C = ebit / total_assets
            D = shareholder_equity / total_liabilities if total_liabilities > 0 else 1.0
            E = revenue / total_assets
            
            # Calculate Altman Z-Score
            z_score = (1.2 * A) + (1.4 * B) + (3.3 * C) + (0.6 * D) + (1.0 * E)
            
            # Interpret Z-Score
            if z_score > 2.99:
                return 'Low'      # Safe Zone
            elif z_score > 1.81:
                return 'Medium'   # Grey Zone ← Your 1.93 should be here
            else:
                return 'High'     # Distress Zone
                
        except Exception as e:
            print(f"Risk calculation error: {e}")
            return 'Error'
    
    def get_is_in_watchlist(self, obj):
        """Check if the startup is in the current user's watchlist"""
        request = self.context.get('request')
        
        if not request or not request.user.is_authenticated:
            return False
        
        return Watchlist.objects.filter(
            user=request.user,
            startup=obj
        ).exists()

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