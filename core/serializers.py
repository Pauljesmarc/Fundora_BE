from rest_framework import serializers
from .models import RegisteredUser, Deck, Startup, Problem, Solution, MarketAnalysis, FundingAsk, TeamMember, FinancialProjection
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
    display_industry = serializers.SerializerMethodField()

    class Meta:
        model = Startup
        fields = [
            'id',
            'company_name',
            'industry',
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
            'owner_email',
            'created_at',
            'updated_at',
        ]

    def get_display_industry(self, obj):
        if obj.is_deck_builder and obj.industry:
            return obj.industry
        return "—"

    def get_reward_potential(self, obj):
        if obj.revenue and obj.net_income:
            try:
                revenue = float(obj.revenue)
                net_income = float(obj.net_income)
                if revenue == 0:
                    return None
                margin = net_income / revenue
                if margin > 0.3:
                    return 5
                elif margin > 0.2:
                    return 4
                elif margin > 0.1:
                    return 3
                elif margin > 0:
                    return 2
                else:
                    return 1
            except Exception:
                return None
        return None

    def get_projected_return(self, obj):
        if obj.revenue and obj.net_income:
            try:
                revenue = float(obj.revenue)
                net_income = float(obj.net_income)
                if revenue == 0:
                    return None
                return round((net_income / revenue) * 100, 2)
            except Exception:
                return None
        return None


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