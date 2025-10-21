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
    risk_level = serializers.SerializerMethodField()  # NEW: Financial risk calculation
    display_industry = serializers.SerializerMethodField()
    is_in_watchlist = serializers.SerializerMethodField()
    tagline = serializers.SerializerMethodField()

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
            'risk_level',  # NEW: Add to fields list
            'owner_email',
            'created_at',
            'updated_at',
            'is_in_watchlist',
        ]

    def get_tagline(self, obj):
        """Get tagline from source deck if this is a deck builder startup"""
        if obj.source_deck:
            return obj.source_deck.tagline
        return None

    def get_display_industry(self, obj):
        """Show tagline for pitch decks, industry for regular startups"""
        if obj.source_deck and obj.source_deck.tagline:
            return obj.source_deck.tagline
        if obj.industry and obj.industry != "—":
            return obj.industry
        return "—"

    def get_reward_potential(self, obj):
        """
        Calculate reward potential based on profit margin and other factors
        Returns a score from 1-5
        """
        try:
            revenue = float(obj.revenue or 0)
            net_income = float(obj.net_income or 0)
            assets = float(obj.total_assets or 0)
            liabilities = float(obj.total_liabilities or 0)
            
            if revenue <= 0 or assets <= 0:
                return None
            
            # Profit margin
            profit_margin = net_income / revenue
            
            # Return on Assets
            roa = net_income / assets
            
            # Debt ratio consideration
            debt_ratio = liabilities / assets if assets > 0 else 0
            
            # Weighted composite score
            base_score = (profit_margin * 3 + roa * 2) * 100
            base_score = max(min(base_score, 100), -100)
            
            # Adjust for debt (high debt reduces potential)
            debt_adjustment = 1.0 - min(debt_ratio, 1.0) * 0.3
            adjusted_score = base_score * debt_adjustment
            
            # Map to 1-5 scale
            if adjusted_score >= 60:
                return 5
            elif adjusted_score >= 40:
                return 4
            elif adjusted_score >= 20:
                return 3
            elif adjusted_score > 0:
                return 2
            else:
                return 1
                
        except Exception:
            return None

    def get_projected_return(self, obj):
        """
        Calculate projected return (ROE or ROA)
        ROE = Net Income / Shareholder Equity
        If equity unavailable, use ROA = Net Income / Total Assets
        """
        try:
            net_income = float(obj.net_income or 0)
            equity = float(obj.shareholder_equity or 0)
            assets = float(obj.total_assets or 0)
            
            # Prefer ROE (Return on Equity)
            if equity > 0:
                return round((net_income / equity) * 100, 2)
            # Fallback to ROA (Return on Assets)
            elif assets > 0:
                return round((net_income / assets) * 100, 2)
            
            return None
        except Exception:
            return None
    
    def get_risk_level(self, obj):
        """
        Calculate financial risk level based on multiple financial metrics:
        - Debt-to-Equity Ratio
        - Debt-to-Assets Ratio
        - Current Ratio (liquidity)
        - Profit Margin
        - Net Income status
        
        Returns: 'Low', 'Medium', or 'High'
        """
        try:
            # Extract financial data
            equity = float(obj.shareholder_equity or 0)
            liabilities = float(obj.total_liabilities or 0)
            assets = float(obj.total_assets or 0)
            revenue = float(obj.revenue or 0)
            net_income = float(obj.net_income or 0)
            
            # Estimate current assets/liabilities if not available
            # (In production, you'd want actual current assets/liabilities fields)
            current_assets = float(getattr(obj, 'current_assets', assets * 0.6) or 0)
            current_liabilities = float(getattr(obj, 'current_liabilities', liabilities * 0.5) or 0)
            
            risk_score = 0
            risk_factors = 0
            
            # 1. Debt-to-Equity Ratio (financial leverage)
            # Low risk: < 1.0, Medium: 1.0-2.0, High: > 2.0
            if equity > 0:
                debt_to_equity = liabilities / equity
                if debt_to_equity < 1.0:
                    risk_score += 1  # Low risk
                elif debt_to_equity < 2.0:
                    risk_score += 2  # Medium risk
                else:
                    risk_score += 3  # High risk
                risk_factors += 1
            
            # 2. Debt-to-Assets Ratio (solvency)
            # Low risk: < 0.4, Medium: 0.4-0.6, High: > 0.6
            if assets > 0:
                debt_to_assets = liabilities / assets
                if debt_to_assets < 0.4:
                    risk_score += 1
                elif debt_to_assets < 0.6:
                    risk_score += 2
                else:
                    risk_score += 3
                risk_factors += 1
            
            # 3. Current Ratio (liquidity)
            # Low risk: > 2.0, Medium: 1.0-2.0, High: < 1.0
            if current_liabilities > 0:
                current_ratio = current_assets / current_liabilities
                if current_ratio >= 2.0:
                    risk_score += 1
                elif current_ratio >= 1.0:
                    risk_score += 2
                else:
                    risk_score += 3
                risk_factors += 1
            
            # 4. Profit Margin
            # Low risk: > 10%, Medium: 0-10%, High: < 0%
            if revenue > 0:
                profit_margin = (net_income / revenue) * 100
                if profit_margin > 10:
                    risk_score += 1
                elif profit_margin >= 0:
                    risk_score += 2
                else:
                    risk_score += 3
                risk_factors += 1
            
            # 5. Net Income Status
            if net_income > 0:
                risk_score += 1  # Profitable = Low risk
            elif net_income == 0:
                risk_score += 2  # Break-even = Medium risk
            else:
                risk_score += 3  # Loss = High risk
            risk_factors += 1
            
            # Calculate average risk score
            if risk_factors == 0:
                return 'Medium'  # Default if no data available
            
            avg_risk = risk_score / risk_factors
            
            # Map to risk levels
            if avg_risk <= 1.5:
                return 'Low'
            elif avg_risk <= 2.3:
                return 'Medium'
            else:
                return 'High'
                
        except Exception as e:
            # If calculation fails, return Medium as safe default
            return 'Medium'
    
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