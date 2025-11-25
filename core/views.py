from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, Http404
from django.template.loader import render_to_string
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password, check_password
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django.forms import ValidationError, inlineformset_factory
from django.db import transaction
from django.db.models import F, Value, FloatField, ExpressionWrapper, Case, When, Prefetch

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.generics import ListAPIView, RetrieveAPIView

from .models import Startup, Deck, FinancialProjection
from .serializers import (
    UserSerializer,
    DeckDetailSerializer,
    FinancialProjectionSerializer,
)
import uuid
import random
import math

class StartupFinancialsView(APIView):
    def get(self, request, startup_id):
        try:
            startup = Startup.objects.get(pk=startup_id)
        except Startup.DoesNotExist:
            return Response({'detail': 'Startup not found.'}, status=status.HTTP_404_NOT_FOUND)
        financials = FinancialProjection.objects.filter(deck=startup.source_deck)
        serializer = FinancialProjectionSerializer(financials, many=True)
        return Response(serializer.data)

    
# 3rd-party
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors

# Python standard
from io import BytesIO
import datetime
import json

# Project-specific
from .models import (
    FinancialProjection,
    Startup,
    Watchlist,
    Download,
    RegisteredUser,
    ComparisonSet,
    Deck,
    Problem,
    Solution,
    MarketAnalysis,
    FundingAsk,
    StartupView,
    StartupComparison,
)
from .forms import (
    RegistrationForm,
    LoginForm,
    DeckForm,
    FinancialProjectionFormSet,
    FundingAskForm,
    MarketAnalysisForm,
    ProblemForm,
    SolutionForm,
    TeamMemberFormSet,
)

from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.contrib.auth.hashers import make_password
from .models import RegisteredUser  # assuming your custom model
from django.contrib.auth.hashers import check_password
from .models import Startup, Watchlist, ComparisonSet, Download, StartupView, StartupComparison, Deck
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors
import datetime
import uuid
from django.contrib.auth import logout
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from .serializers import (
    InvestorRegistrationSerializer,
    StartupRegistrationSerializer,
    LoginSerializer,
    DeckSerializer,
    StartupSerializer,
    ProblemSerializer,
    SolutionSerializer,
    MarketAnalysisSerializer,
    FundingAskSerializer,
    TeamMemberSerializer,
    FinancialProjectionSerializer,
    DeckDetailSerializer,
    DeckReportSerializer,
)

def get_django_user_from_session(request):
    """
    Helper function to get Django User from session-based authentication
    Returns the Django User object or None if not logged in
    """
    if not request.session.get('user_id'):
        return None
    
    try:
        registration_user = RegisteredUser.objects.get(id=request.session['user_id'])
    except RegisteredUser.DoesNotExist:
        return None
    
    # Get or create corresponding Django User for backward compatibility
    django_user, created = User.objects.get_or_create(
        email=registration_user.email,
        defaults={
            'username': registration_user.email,
            'first_name': registration_user.first_name,
            'last_name': registration_user.last_name,
        }
    )
    return django_user


SECTION_CONFIG = {
    'cover-page': {
        'form_class': DeckForm,
        'template_key': 'form',
        'next_section': 'the-problem',
        'is_formset': False,
        'use_files': True,
        'create_deck': True,
    },
    'the-problem': {
        'form_class': ProblemForm,
        'template_key': 'form',
        'next_section': 'the-solution',
    },
    'the-solution': {
        'form_class': SolutionForm,
        'template_key': 'form',
        'next_section': 'market-analysis',
    },
    'market-analysis': {
        'form_class': MarketAnalysisForm,
        'template_key': 'form',
        'next_section': 'the-team',
    },

    'the-team': {
        'form_class': TeamMemberFormSet,
        'template_key': 'formset',
        'next_section': 'financials',
        'is_formset': True,
        'prefix': 'team',
    },
    'financials': {
        'form_class': FinancialProjectionFormSet,
        'template_key': 'formset',
        'next_section': 'the-ask',
        'is_formset': True,
        'prefix': 'financials',
    },
        'the-ask': {
        'form_class': FundingAskForm,
        'template_key': 'form',
        'next_section': 'deck_home',
    },
}

class section_list(APIView):
    # authentication_classes = [JWTAuthentication]
    # permission_classes = [IsAuthenticated]

    def get(self, request):
        sections = [
            {
                "key": key,
                "display_name": key.replace('-', ' ').title(),
                "next_section": config.get("next_section"),
                "template_key": config.get("template_key"),
                "is_formset": config.get("is_formset", False)
            }
            for key, config in SECTION_CONFIG.items()
        ]
        return Response(sections)

class index(APIView):
    def get(self, request):
        startup_user_id = request.session.get('startup_user_id')
        is_logged_in = bool(startup_user_id)
        startup_user_name = request.session.get('user_name', '') if is_logged_in else ''

        data = {
            'is_startup_logged_in': is_logged_in,
            'startup_user_name': startup_user_name
        }
        return Response(data, status=status.HTTP_200_OK)

class deck_builder(APIView):
    def get(self, request, section):
        if section not in SECTION_CONFIG:
            return Response({"error": "Section not found"}, status=status.HTTP_404_NOT_FOUND)

        config = SECTION_CONFIG[section]
        form_class = config['form_class']
        is_cover_page = config.get('create_deck', False)

        deck_id = request.query_params.get('deck_id')
        startup_user_id = request.user.id  # assuming token-based auth

        if is_cover_page and not startup_user_id:
            return Response({"error": "Login required to create deck"}, status=status.HTTP_403_FORBIDDEN)

        deck = get_object_or_404(Deck, id=deck_id, owner_id=startup_user_id) if deck_id else None
        form_kwargs = {'prefix': config.get('prefix')}

        if deck:
            form_kwargs['instance'] = getattr(deck, section.replace('-', '_'), None)

        form = form_class(**form_kwargs)
        return Response({"form": form.initial}, status=status.HTTP_200_OK)

    def post(self, request, section):
        if section not in SECTION_CONFIG:
            return Response({"error": "Section not found"}, status=status.HTTP_404_NOT_FOUND)

        config = SECTION_CONFIG[section]
        form_class = config['form_class']
        is_cover_page = config.get('create_deck', False)
        is_formset = config.get('is_formset', False)

        deck_id = request.data.get('deck_id')
        startup_user_id = request.user.id

        deck = get_object_or_404(Deck, id=deck_id, owner_id=startup_user_id) if deck_id else None
        form_kwargs = {
            'prefix': config.get('prefix'),
            'data': request.data,
            'files': request.FILES,
            'instance': getattr(deck, section.replace('-', '_'), None) if deck else None
        }

        form = form_class(**form_kwargs)

        if form.is_valid():
            with transaction.atomic():
                if is_cover_page and not deck:
                    deck = form.save(commit=False)
                    deck.owner_id = startup_user_id
                    deck.save()
                elif deck:
                    instance = form.save(commit=False)
                    instance.deck = deck
                    instance.save()
                else:
                    return Response({"error": "No active deck found"}, status=status.HTTP_400_BAD_REQUEST)

                # Create Startup entry linked to Deck, if not already existing
                from .models import Startup
                if not Startup.objects.filter(source_deck_id=deck.id).exists():
                    Startup.objects.create(
                        company_name=getattr(deck, "company_name", "Untitled Deck"),
                        company_description=getattr(deck, "description", ""),
                        industry=getattr(deck, "tagline", "—"),
                        data_source_confidence="Medium",
                        source_deck_id=deck.id,
                        is_deck_builder=True,
                        owner=RegisteredUser.objects.get(user=request.user)
                    )

            return Response(
                {"message": f"{section} saved successfully", "deck_id": deck.id},
                status=status.HTTP_200_OK
            )
        else:
            return Response({"errors": form.errors}, status=status.HTTP_400_BAD_REQUEST)

class investor_registration(APIView):
    def post(self, request):
        if not request.data.get('terms'):
            return Response(
                {"error": "You must agree to the Terms of Service and Privacy Policy."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = InvestorRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Investor account created successfully.'
            }, status=status.HTTP_201_CREATED)
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class login_view(APIView):
    """
    Unified login view for startups and investors.
    Returns JWT token and user info (id, name, email, label).
    """
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']

            # Ensure the user has a profile
            try:
                profile = user.profile  # RegisteredUser linked via OneToOneField related_name='profile'
            except Exception:
                return Response(
                    {'success': False, 'error': 'User profile not found.'},
                    status=status.HTTP_404_NOT_FOUND
                )

            tokens = get_tokens_for_user(user)
            return Response({
                "message": "Login successful",
                "token": tokens['access'],
                "user": {
                    "id": user.id,
                    "name": f"{user.first_name} {user.last_name}",
                    "email": user.email,
                    "label": profile.label
                }
            }, status=status.HTTP_200_OK)

        # Invalid login credentials
        return Response(
            {"success": False, "errors": serializer.errors},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
#session token
def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


# MOD 1
# TODO: UPDATE FILTERS TO MAKE THE RISK LEVEL WORK WITHOUT CLICKING THE STARTUP TYPE
class dashboard(APIView): 
    def get(self, request):
        industry = request.query_params.get('industry', '')
        risk = request.query_params.get('risk', '')
        min_return = request.query_params.get('min_return', '')
        sort_by = request.query_params.get('sort_by', 'recommended')

        startups = Startup.objects.select_related('owner__user', 'source_deck').all()

        # Apply industry filter
        if industry:
            startups = startups.filter(industry__iexact=industry)

        # Serialize and calculate metrics (including financial risk)
        serializer = StartupSerializer(startups, many=True, context={'request': request})
        startup_data = serializer.data

        # Apply risk filter based on calculated financial risk
        if risk:
            try:
                risk_value = int(risk)
                if risk_value <= 33:
                    # Conservative: Low risk only
                    startup_data = [s for s in startup_data if s.get('risk_level') == 'Low']
                elif risk_value <= 66:
                    # Balanced: Low and Medium risk
                    startup_data = [s for s in startup_data if s.get('risk_level') in ['Low', 'Medium']]
                # else: Aggressive: show all risk levels
            except ValueError:
                pass

        # Apply min_return filter (post-serialization)
        if min_return:
            try:
                min_ret_val = float(min_return)
                startup_data = [
                    s for s in startup_data
                    if s.get('projected_return') is not None 
                    and s.get('projected_return') >= min_ret_val
                ]
            except ValueError:
                pass

        # Apply sorting
        startup_data = sort_startups(startup_data, sort_by)

        return Response({
            "startups": startup_data,
            "count": len(startup_data),
        }, status=status.HTTP_200_OK)
    
# ========================================
# FINANCIAL RISK - USING ORIGINAL ALTMAN Z-SCORE
# ========================================
def calculate_financial_risk(startup):
    """
    Uses Original Altman Z-Score for comprehensive risk assessment
    Z = 1.2A + 1.4B + 3.3C + 0.6D + 1.0E
    
    Where:
    A = Working Capital / Total Assets
    B = Retained Earnings / Total Assets
    C = EBIT / Total Assets
    D = Book Value of Equity / Total Liabilities
    E = Sales (Revenue) / Total Assets
    
    Interpetation:
    - Z > 2.99 = Low Risk (Safe Zone)
    - 1.81 < Z < 2.99 = Medium Risk (Grey Zone)
    - Z < 1.81 = High Risk (Distress Zone)
    """
    try:
        total_assets = float(startup.total_assets or 0)
        total_liabilities = float(startup.total_liabilities or 0)
        shareholder_equity = float(startup.shareholder_equity or 0)
        retained_earnings = float(getattr(startup, 'retained_earnings', 0) or 0)
        ebit = float(getattr(startup, 'ebit', 0) or 0)
        current_assets = float(getattr(startup, 'current_assets', 0) or 0)
        current_liabilities = float(getattr(startup, 'current_liabilities', 0) or 0)
        revenue = float(startup.revenue or getattr(startup, 'current_revenue', 0) or 0)
        
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
            return 'Medium'   # Grey Zone
        else:
            return 'High'     # Distress Zone
            
    except Exception as e:
        # If calculation fails
        print(f"Risk calculation error: {e}")
        return 'Error'

# ========================================
# PROJECTED RETURN - USING CAGR WITH RISK ADJUSTMENT
# ========================================
def calculate_projected_return(startup):
    """
    Calculate projected return using Revenue CAGR with risk adjustment
    
    Step 1: Calculate CAGR
    CAGR = [(Current Revenue / Prior Revenue)^(1/Time Period) - 1] × 100
    
    Step 2: Apply Risk Adjustment Factor
    - Low Risk: CAGR × 1.00 (Aggressive - company is stable)
    - Medium Risk: CAGR × 0.85 (Moderate - some uncertainty)
    - High Risk: CAGR × 0.70 (Conservative - significant risk)
    Note:
    The risk adjustment isn't canon, it's just someting I added
    
    Step 3: Return Risk-Adjusted Growth Rate
    This represents the expected annual return percentage for investors
    """
    try:
        current_revenue = float(startup.revenue or getattr(startup, 'current_revenue', 0) or 0)
        previous_revenue = float(getattr(startup, 'previous_revenue', 0) or 0)
        time_between_periods = float(getattr(startup, 'time_between_periods', 1) or 1)
        
        # Validate data availability
        if current_revenue <= 0 or previous_revenue <= 0 or time_between_periods <= 0:
            # Fallback to simple profit margin if no revenue growth data
            net_income = float(startup.net_income or 0)
            if current_revenue > 0:
                profit_margin = (net_income / current_revenue) * 100
                return round(max(profit_margin, 0), 2)  # Return non-negative
            return 0.0
        
        # Step 1: Calculate CAGR
        revenue_ratio = current_revenue / previous_revenue
        cagr = (math.pow(revenue_ratio, 1 / time_between_periods) - 1) * 100
        
        # Cap CAGR at reasonable limits to avoid extreme outliers
        # Min: -50% (severe decline), Max: 100% (doubling year-over-year)
        cagr = max(min(cagr, 100), -50)
        
        # Step 2: Get Risk Level and Apply Adjustment Factor
        risk_level = calculate_financial_risk(startup)
        
        if risk_level == 'Low':
            adjustment_factor = 1.00  # Aggressive
        elif risk_level == 'Medium':
            adjustment_factor = 0.85  # Moderate
        else:  # High risk
            adjustment_factor = 0.70  # Conservative
        
        # Step 3: Calculate Risk-Adjusted Projected Return
        projected_return = cagr * adjustment_factor
        
        return round(projected_return, 2)
        
    except Exception as e:
        print(f"Projected return calculation error: {e}")
        return 0.0

# ========================================
# REWARD POTENTIAL - USING ROE (RETURN ON EQUITY)
# ========================================
def calculate_reward_potential(startup):
    """
    Uses Return on Equity (ROE) to measure profitability
    ROE = (Net Income / Shareholder Equity) × 100
    
    Converts ROE to 1-5 scale:
    - ROE < 5%: 1/5 (Low Reward)
    - ROE 5-10%: 2/5 (Below Average)
    - ROE 10-15%: 3/5 (Average)
    - ROE 15-20%: 4/5 (Good)
    - ROE > 20%: 5/5 (Excellent)
    
    Fallback to ROA if equity is not available:
    ROA = (Net Income / Total Assets) × 100
    """
    try:
        net_income = float(startup.net_income or 0)
        shareholder_equity = float(startup.shareholder_equity or 0)
        total_assets = float(startup.total_assets or 0)

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
                return 4.0  # Good
            elif roe_percentage >= 10:
                return 3.0  # Average
            elif roe_percentage >= 5:
                return 2.0  # Below Average
            else:
                return 1.0  # Low Reward
        
        # Fallback: Calculate ROA if equity not available
        elif total_assets > 0:
            roa_percentage = (net_income / total_assets) * 100
            
            # Convert ROA to 1-5 scale (ROA benchmarks are lower than ROE)
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
        
        # Default if no data
        return "N/A"
        
    except Exception as e:
        print(f"Reward potential calculation error: {e}")
        return "N/A"

# ========================================
# HELPER FUNCTION: Get Risk Score (1-5)
# ========================================
def get_risk_score(startup):
    """
    Converts risk level to numeric score (1-5)
    - Low Risk = 1/5
    - Medium Risk = 3/5
    - High Risk = 5/5
    """
    risk_level = calculate_financial_risk(startup)
    
    risk_mapping = {
        'Low': 1,
        'Medium': 3,
        'High': 5
    }
    
    return risk_mapping.get(risk_level, 3)

def sort_startups(startups, sort_by):
    """
    Sort startup list by various criteria
    Works with serialized data (dicts)
    """
    if sort_by == 'projected_return_desc':
        return sorted(startups, key=lambda x: x.get("projected_return") or -999999, reverse=True)
    elif sort_by == 'projected_return_asc':
        return sorted(startups, key=lambda x: x.get("projected_return") or 999999)
    elif sort_by == 'reward_potential_desc':
        return sorted(startups, key=lambda x: x.get("reward_potential") or 0, reverse=True)
    elif sort_by == 'confidence_desc':
        confidence_order = {'High': 3, 'Medium': 2, 'Low': 1}
        return sorted(startups, key=lambda x: confidence_order.get(x.get("data_source_confidence"), 0), reverse=True)
    elif sort_by == 'risk_asc':
        # Sort by financial risk (Low < Medium < High)
        risk_order = {'Low': 1, 'Medium': 2, 'High': 3}
        return sorted(startups, key=lambda x: risk_order.get(x.get("risk_level"), 2))
    elif sort_by == 'company_name':
        return sorted(startups, key=lambda x: x.get("company_name", "").lower())
    
    # Default: return as-is (already ordered by created_at desc from queryset)
    return startups

class StartupListView(ListAPIView):
    """
    API endpoint to list startups with filtering and sorting.
    Uses existing StartupSerializer which calculates metrics on-the-fly.
    """
    serializer_class = StartupSerializer
    
    def get_serializer_context(self):
        """Pass request to serializer for is_in_watchlist field"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def get_queryset(self):
        qs = Startup.objects.select_related(
            'owner__user',
            'source_deck'
        ).prefetch_related(
            Prefetch(
                'source_deck__market_analysis',
                queryset=MarketAnalysis.objects.all()
            )
        ).all()

        params = self.request.query_params

        # ---- FILTERS ----
        
        # Industry filter (case-insensitive)
        industry = params.get('industry')
        if industry:
            qs = qs.filter(industry__iexact=industry)

        # Minimum return filter - applied post-serialization
        min_return = params.get('min_return')
        self._min_return_filter = float(min_return) if min_return else None

        # Risk slider (0-100) - applied post-serialization based on calculated financial risk
        risk = params.get('risk')
        self._risk_filter = int(risk) if risk else None

        # ---- SORTING ----
        sort_by = params.get('sort_by')
        
        # For sorts that don't depend on calculated fields, use database ordering
        if sort_by == 'confidence_desc':
            # Sort by data source confidence: High > Medium > Low
            confidence_order = Case(
                When(data_source_confidence='High', then=Value(3)),
                When(data_source_confidence='Medium', then=Value(2)),
                When(data_source_confidence='Low', then=Value(1)),
                default=Value(0),
                output_field=FloatField()
            )
            qs = qs.annotate(confidence_order=confidence_order).order_by('-confidence_order')
        elif sort_by == 'company_name':
            qs = qs.order_by('company_name')
        else:
            # For projected_return, reward_potential, and risk_level sorting,
            # we'll sort after serialization since these are calculated fields
            # Default: newest first
            qs = qs.order_by('-created_at')
        
        # Store sort preference for post-serialization sorting
        self._sort_by = sort_by

        return qs
    
    def list(self, request, *args, **kwargs):
        """Override list to apply post-serialization filtering and sorting"""
        queryset = self.filter_queryset(self.get_queryset())
        
        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data
        
        # Apply financial risk filter (post-serialization)
        # IMPORTANT: Only filter financial startups, exclude pitch decks (risk_level = None)
        if hasattr(self, '_risk_filter') and self._risk_filter is not None:
            risk_value = self._risk_filter
            if risk_value <= 33:
                # Conservative: Low risk only (exclude pitch decks with None)
                data = [item for item in data if item.get('risk_level') == 'Low']
            elif risk_value <= 66:
                # Balanced: Low and Medium risk (exclude pitch decks with None)
                data = [item for item in data if item.get('risk_level') in ['Low', 'Medium']]
            # else: Aggressive: show all risk levels (including pitch decks)
        
        # Apply min_return filter (post-serialization)
        if hasattr(self, '_min_return_filter') and self._min_return_filter is not None:
            data = [
                item for item in data 
                if item.get('projected_return') is not None 
                and item.get('projected_return') >= self._min_return_filter
            ]
        
        # Apply sorting that requires calculated fields
        sort_by = getattr(self, '_sort_by', None)
        if sort_by == 'projected_return_desc':
            data = sorted(data, key=lambda x: x.get('projected_return') or -999999, reverse=True)
        elif sort_by == 'projected_return_asc':
            data = sorted(data, key=lambda x: x.get('projected_return') or 999999)
        elif sort_by == 'reward_potential_desc':
            data = sorted(data, key=lambda x: x.get('reward_potential') or 0, reverse=True)
        elif sort_by == 'risk_asc':
            # Sort by financial risk (Low < Medium < High)
            # Pitch decks (None) go to the end
            risk_order = {'Low': 1, 'Medium': 2, 'High': 3, None: 4}
            data = sorted(data, key=lambda x: risk_order.get(x.get('risk_level'), 4))
        
        return Response(data)
    
class StartupDetailView(RetrieveAPIView):
    queryset = Startup.objects.all()
    serializer_class = StartupSerializer

class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    
class StartupFinancialsView(APIView):
    def get(self, request, startup_id):
        try:
            startup = Startup.objects.get(id=startup_id)
        except Startup.DoesNotExist:
            return Response({'error': 'Startup not found'}, status=404)

        data = {
            'revenue': startup.revenue,
            'net_income': startup.net_income,
            'total_assets': startup.total_assets,
            'total_liabilities': startup.total_liabilities,
            'cash_flow': startup.cash_flow,
        }
        return Response(data)
    
class ProfileView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        try:
            registered_user = RegisteredUser.objects.get(user=user)
            label = registered_user.label
        except RegisteredUser.DoesNotExist:
            label = None
        
        # Get counts
        watchlist_count = Watchlist.objects.filter(user=user).count()
        views_count = StartupView.objects.filter(user=user).count()
        comparisons_count = ComparisonSet.objects.filter(user=user).count()
        
        # Get recent views (last 5)
        recent_views = StartupView.objects.filter(user=user).select_related('startup').order_by('-viewed_at')[:5]
        recent_views_data = [
            {
                'startup_name': view.startup.company_name,
                'startup_industry': view.startup.industry,
                'viewed_at': view.viewed_at.isoformat()
            }
            for view in recent_views
        ]
        
        # Get recent comparisons (last 5)
        recent_comparisons = ComparisonSet.objects.filter(user=user).prefetch_related('startups').order_by('-created_at')[:5]
        recent_comparisons_data = [
            {
                'name': comp.name or str(comp),
                'startup_count': comp.startup_count,
                'created_at': comp.created_at.isoformat()
            }
            for comp in recent_comparisons
        ]
        
        # Get downloads
        downloads = Download.objects.filter(user=user).select_related('startup').order_by('-downloaded_at')[:10]
        downloads_data = [
            {
                'startup_name': dl.startup.company_name,
                'download_type': dl.download_type,
                'downloaded_at': dl.downloaded_at.isoformat()
            }
            for dl in downloads
        ]
        
        return Response({
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'label': label,
            'watchlist_count': watchlist_count,
            'views_count': views_count,
            'comparisons_count': comparisons_count,
            'recent_views': recent_views_data,
            'recent_comparisons': recent_comparisons_data,
            'downloads': downloads_data
        })

class UpdateProfileView(APIView):
    permission_classes = [IsAuthenticated]
    
    def put(self, request):
        user = request.user
        data = request.data
        
        # Validate email uniqueness (if changed)
        new_email = data.get('email')
        if new_email and new_email != user.email:
            if User.objects.filter(email=new_email).exists():
                return Response(
                    {'error': 'Email is already in use'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Update user fields
        user.first_name = data.get('first_name', user.first_name)
        user.last_name = data.get('last_name', user.last_name)
        
        if new_email:
            user.email = new_email
            user.username = new_email  # Update username too if it's based on email
        
        user.save()
        
        return Response({
            'message': 'Profile updated successfully',
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email
        })
    
class StartupProfileAccountView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        try:
            registered_user = RegisteredUser.objects.get(user=user)
            
            # Verify this is a startup user
            if registered_user.label != 'startup':
                return Response(
                    {'error': 'This endpoint is only for startup users'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
        except RegisteredUser.DoesNotExist:
            return Response(
                {'error': 'User profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get startup's companies
        startups = Startup.objects.filter(owner=registered_user).order_by('-created_at')
        startups_count = startups.count()
        
        # Get startup's pitch decks
        decks = Deck.objects.filter(owner=registered_user).order_by('-created_at')
        decks_count = decks.count()
        
        # Get total views across all startups
        views_count = StartupView.objects.filter(
            startup__owner=registered_user
        ).count()
        
        # Prepare startups data
        startups_data = [
            {
                'id': startup.id,
                'company_name': startup.company_name,
                'industry': startup.industry,
                'created_at': startup.created_at.isoformat(),
                'is_deck_builder': startup.is_deck_builder
            }
            for startup in startups[:10]  # Limit to 10 most recent
        ]
        
        # Prepare decks data
        decks_data = [
            {
                'id': deck.id,
                'company_name': deck.company_name,
                'tagline': deck.tagline,
                'created_at': deck.created_at.isoformat()
            }
            for deck in decks[:10]  # Limit to 10 most recent
        ]
        
        # Get recent activity
        recent_activity = []
        
        # Add recent startup registrations
        for startup in startups[:5]:
            recent_activity.append({
                'type': 'startup',
                'description': f'Registered {startup.company_name}',
                'timestamp': startup.created_at.isoformat()
            })
        
        # Add recent deck creations
        for deck in decks[:5]:
            recent_activity.append({
                'type': 'deck',
                'description': f'Created pitch deck for {deck.company_name}',
                'timestamp': deck.created_at.isoformat()
            })
        
        # Add recent views on their startups
        recent_views = StartupView.objects.filter(
            startup__owner=registered_user
        ).select_related('startup', 'user').order_by('-viewed_at')[:5]
        
        for view in recent_views:
            recent_activity.append({
                'type': 'view',
                'description': f'{view.user.email} viewed {view.startup.company_name}',
                'timestamp': view.viewed_at.isoformat()
            })
        
        # Sort activity by timestamp (most recent first)
        recent_activity.sort(key=lambda x: x['timestamp'], reverse=True)
        recent_activity = recent_activity[:15]  # Limit to 15 most recent activities
        
        return Response({
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'label': registered_user.label,
            'startups_count': startups_count,
            'decks_count': decks_count,
            'views_count': views_count,
            'startups': startups_data,
            'decks': decks_data,
            'recent_activity': recent_activity
        })
    
class StartupProfileView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, startup_id):
        try:
            startup = Startup.objects.select_related("source_deck").get(pk=startup_id)
        except Startup.DoesNotExist:
            return Response({"detail": "Startup not found."}, status=404)

        deck = startup.source_deck
        if not deck:
            return Response({"detail": "No pitch deck linked to this startup."}, status=404)

        serialized = DeckDetailSerializer(deck).data
        response = {
            "company_name": deck.company_name,
            "company_description": deck.tagline or "",
            "problem": serialized.get("problem", {}).get("description"),
            "solution": serialized.get("solution", {}).get("description"),
            "primary_market": serialized.get("market_analysis", {}).get("primary_market"),
            "target_audience": serialized.get("market_analysis", {}).get("target_audience"),
            "market_growth": serialized.get("market_analysis", {}).get("market_growth_rate"),
            "competitive_advantage": serialized.get("market_analysis", {}).get("competitive_advantage"),
            "financials": serialized.get("financials", []),
            "funding_goal": serialized.get("ask", {}).get("amount"),
            "use_of_funds": serialized.get("ask", {}).get("usage_description"),
            "is_in_watchlist": False,
        }
        return Response(response)

class FinancialProjectionListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, startup_id):
        try:
            startup = Startup.objects.select_related("source_deck").get(pk=startup_id)
        except Startup.DoesNotExist:
            return Response([], status=200)

        if not startup.source_deck:
            return Response([], status=200)

        financials = FinancialProjection.objects.filter(deck=startup.source_deck)
        serializer = FinancialProjectionSerializer(financials, many=True)
        return Response(serializer.data)

class watchlist_view(APIView):
    def get(self, request):
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
        
        items = Watchlist.objects.filter(user=request.user).select_related('startup')
        data = [{
            "id": i.startup.id,
            "company_name": i.startup.company_name,
            "industry": i.startup.industry,
            "company_description": getattr(i.startup, 'company_description', ''),
        } for i in items]
        
        return Response({
            "results": data,
            "count": len(data)
        }, status=status.HTTP_200_OK)

class add_to_watchlist(APIView):
    def post(self, request, startup_id):
        if not request.user.is_authenticated:
            return Response({"success": False, "message": "Login required"}, status=status.HTTP_401_UNAUTHORIZED)
        
        startup = get_object_or_404(Startup, id=startup_id)
        obj, created = Watchlist.objects.get_or_create(user=request.user, startup=startup)
        
        return Response({
            "success": True,
            "added": created,
            "startup_id": startup.id,
            "message": (
                f"{startup.company_name} added to watchlist." if created 
                else f"{startup.company_name} already in watchlist."
            )
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

class remove_from_watchlist(APIView):
    def delete(self, request, startup_id):
        if not request.user.is_authenticated:
            return Response({"success": False, "message": "Login required"}, status=status.HTTP_401_UNAUTHORIZED)
        
        startup = get_object_or_404(Startup, id=startup_id)
        deleted, _ = Watchlist.objects.filter(user=request.user, startup=startup).delete()
        
        return Response({
            "success": deleted > 0,
            "startup_id": startup.id,
            "message": (
                f"{startup.company_name} removed from watchlist." if deleted 
                else f"{startup.company_name} not found in watchlist."
            )
        }, status=status.HTTP_200_OK)


# MOD 2
class SaveComparisonView(APIView):
    """Save a comparison set for the authenticated user"""
    def post(self, request):
        if not request.user.is_authenticated:
            return Response(
                {"error": "Authentication required"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        startup_ids = request.data.get('startup_ids', [])
        
        if not startup_ids or len(startup_ids) < 2:
            return Response(
                {"error": "At least 2 startups are required for comparison"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify all startups exist
        startups = Startup.objects.filter(id__in=startup_ids)
        if startups.count() != len(startup_ids):
            return Response(
                {"error": "One or more startups not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if this exact comparison already exists
        existing = ComparisonSet.objects.filter(user=request.user)
        for comp in existing:
            existing_ids = set(comp.startups.values_list('id', flat=True))
            if existing_ids == set(startup_ids):
                return Response({
                    "success": True,
                    "message": "This comparison already exists",
                    "id": comp.id,
                    "already_exists": True
                }, status=status.HTTP_200_OK)
        
        # Create new comparison set
        comparison = ComparisonSet.objects.create(user=request.user)
        comparison.startups.set(startups)
        
        return Response({
            "success": True,
            "message": "Comparison saved successfully",
            "id": comparison.id,
            "already_exists": False
        }, status=status.HTTP_201_CREATED)

class ListComparisonsView(APIView):
    """List all saved comparisons for the authenticated user"""
    def get(self, request):
        if not request.user.is_authenticated:
            return Response(
                {"error": "Authentication required"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        comparisons = ComparisonSet.objects.filter(user=request.user).prefetch_related('startups')
        
        results = []
        for comp in comparisons:
            startups_data = StartupSerializer(
                comp.startups.all(), 
                many=True,
                context={'request': request}
            ).data
            
            results.append({
                "id": comp.id,
                "startups": startups_data,
                "startup_count": comp.startup_count,
                "created_at": comp.created_at.isoformat(),
                "name": comp.name or str(comp)
            })
        
        return Response({
            "results": results,
            "count": len(results)
        }, status=status.HTTP_200_OK)

class DeleteComparisonSetView(APIView):
    """Delete a saved comparison set"""
    def delete(self, request, comparison_id):
        if not request.user.is_authenticated:
            return Response(
                {"error": "Authentication required"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        try:
            comparison = ComparisonSet.objects.get(id=comparison_id, user=request.user)
            comparison_name = str(comparison)
            comparison.delete()
            
            return Response({
                "success": True,
                "message": f"Comparison '{comparison_name}' removed successfully"
            }, status=status.HTTP_200_OK)
        except ComparisonSet.DoesNotExist:
            return Response(
                {"error": "Comparison not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )

def get_risk_level(confidence):
    """Helper function to get risk level based on confidence"""
    if confidence == 'High':
        return 'Low Risk'
    elif confidence == 'Medium':
        return 'Medium Risk'
    else:
        return 'High Risk'

def get_risk_color(confidence):
    """Helper function to get risk color class"""
    if confidence == 'High':
        return 'bg-green-100 text-green-800'
    elif confidence == 'Medium':
        return 'bg-yellow-100 text-yellow-800'
    else:
        return 'bg-red-100 text-red-800'

class company_profile(APIView):
    def get(self, request, startup_id):
        user = request.user
        if not user.is_authenticated:
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

        startup = get_object_or_404(Startup, id=startup_id)

        # Track view if not owner
        if user != startup.owner:
            ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR')
            StartupView.objects.create(user=user, startup=startup, ip_address=ip_address)

        is_in_watchlist = Watchlist.objects.filter(user=user, startup=startup).exists()

        # Deck-builder startup
        if startup.source_deck:
            deck = startup.source_deck
            return Response({
                "startup": {
                    "id": startup.id,
                    "company_name": startup.company_name,
                    "industry": startup.industry,
                    "is_deck_builder": True
                },
                "deck": {
                    "problem": getattr(deck, 'problem', None),
                    "solution": getattr(deck, 'solution', None),
                    "market_analysis": getattr(deck, 'market_analysis', None),
                    "ask": getattr(deck, 'ask', None),
                    "team_members": [member.name for member in deck.team_members.all()],
                    "financials": [
                        {"year": f.year, "revenue": f.revenue, "profit": f.profit}
                        for f in deck.financials.order_by('year')
                    ]
                },
                "is_in_watchlist": is_in_watchlist,
                "show_modal": True,
                "from_dashboard": True
            }, status=status.HTTP_200_OK)

        # Regular startup: calculate risk/reward
        revenue = float(startup.revenue or 0)
        net_income = float(startup.net_income or 0)
        risk_score, reward_score = 2.5, 3.0

        if revenue > 0:
            margin = net_income / revenue
            if margin > 0.2:
                risk_score, reward_score = 2.0, 4.5
            elif margin > 0.1:
                risk_score, reward_score = 2.5, 3.5
            elif margin > 0:
                risk_score, reward_score = 3.5, 2.5
            else:
                risk_score, reward_score = 4.5, 2.0

        confidence_adjustments = {'High': 0.0, 'Medium': 0.0, 'Low': 0.8}
        confidence = getattr(startup, 'data_source_confidence', 'Medium')
        risk_score += confidence_adjustments.get(confidence, 0.3)
        risk_score = min(risk_score, 5.0)

        return Response({
            "id": startup.id,
            "company_name": startup.company_name,
            "industry": startup.industry or "—",
            "company_description": startup.company_description or "",
            "revenue": startup.revenue or "N/A",
            "net_income": startup.net_income or "N/A",
            "total_assets": getattr(startup, 'total_assets', 'N/A'),
            "cash_flow": getattr(startup, 'cash_flow', 'N/A'),
            "team_strength": getattr(startup, 'team_strength', 'No data'),
            "market_position": getattr(startup, 'market_position', 'No data'),
            "brand_reputation": getattr(startup, 'brand_reputation', 'No data'),
            "risk_score": round(risk_score, 1),
            "reward_score": round(reward_score, 1),
            "data_source_confidence": getattr(startup, 'data_source_confidence', 'Medium'),
            "is_in_watchlist": is_in_watchlist
        }, status=status.HTTP_200_OK)

class compare_startups(APIView):
    def get(self, request):
        user = request.user
        if not user.is_authenticated:
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

        startups = Startup.objects.all()
        startup_data = []

        for s in startups:
            is_deck_builder = hasattr(s, 'source_deck') and s.source_deck is not None
            projected_return = calculate_projected_return(s)
            reward_potential, display_risk, _ = calculate_reward_potential(s)

            startup_data.append({
                "id": s.id,
                "company_name": s.company_name,
                "industry": s.industry,
                "is_deck_builder": is_deck_builder,
                "projected_return": projected_return,
                "reward_potential": reward_potential,
                "confidence": s.data_source_confidence,
                "display_risk": display_risk
            })

        return Response({"startups": startup_data}, status=status.HTTP_200_OK)

class startup_comparison(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        startup_ids = request.query_params.get('startups', '')
        if not startup_ids:
            return Response({'error': 'No startups selected'}, status=400)

        try:
            startup_ids = [int(id.strip()) for id in startup_ids.split(',') if id.strip()]
        except ValueError:
            return Response({'error': 'Invalid startup IDs'}, status=400)

        if len(startup_ids) < 2 or len(startup_ids) > 3:
            return Response({'error': 'Select 2–3 startups for comparison'}, status=400)

        startups = []
        for sid in startup_ids:
            try:
                startup = Startup.objects.get(id=sid)
                startup.projected_return = calculate_projected_return(startup)
                reward, display_risk, _ = calculate_reward_potential(startup)
                startup.reward_potential = reward

                # Risk score logic
                confidence = getattr(startup, 'data_source_confidence', 'Medium')
                if confidence == 'Low':
                    risk_score = 2.0
                else:
                    risk_score = 2.5
                    if startup.revenue and startup.net_income:
                        rev = float(startup.revenue or 0)
                        income = float(startup.net_income or 0)
                        if rev > 0:
                            margin = income / rev
                            if margin > 0.2:
                                risk_score = 2.0
                            elif margin > 0.1:
                                risk_score = 2.5
                            elif margin > 0:
                                risk_score = 3.5
                            else:
                                risk_score = 4.5
                        elif income < 0:
                            risk_score = 4.5

                startup.risk_score = round(max(min(risk_score, 5.0), 1.0), 1)
                startup.risk_level = get_risk_level(confidence)
                startup.risk_color = get_risk_color(confidence)

                startups.append(startup)
            except Startup.DoesNotExist:
                continue

        if len(startups) < 2:
            return Response({'error': 'Insufficient startups for comparison'}, status=400)

        # Create comparison session
        session_id = str(uuid.uuid4())
        for startup in startups:
            StartupComparison.objects.create(
                user=request.user,
                startup=startup,
                comparison_set_id=session_id
            )

        # Check for existing comparison set
        sorted_ids = sorted([s.id for s in startups])
        existing_set = None
        for comp_set in ComparisonSet.objects.filter(user=request.user):
            comp_ids = sorted(comp_set.startups.values_list('id', flat=True))
            if comp_ids == sorted_ids:
                existing_set = comp_set
                break

        if existing_set:
            comparison_set = existing_set
        else:
            comparison_set = ComparisonSet.objects.create(user=request.user)
            comparison_set.startups.set(startups)

        # Build response with all necessary fields
        startup_data = [{
            "id": s.id,
            "company_name": s.company_name,
            "industry": s.industry,
            "tagline": getattr(s, 'tagline', None),
            "projected_return": s.projected_return,
            "reward_potential": s.reward_potential,
            "risk_score": s.risk_score,
            "risk_level": s.risk_level,
            "risk_color": s.risk_color,
            "data_source_confidence": getattr(s, 'data_source_confidence', 'Medium'),
            "revenue": s.revenue,
            "net_income": getattr(s, 'net_income', None),
            "is_deck_builder": getattr(s, 'is_deck_builder', False),
            "source_deck_id": getattr(s, 'source_deck_id', None),
            "source_deck": getattr(s, 'source_deck', None),
        } for s in startups]

        return Response({
            "startups": startup_data,
            "startup_count": len(startups),
            "comparison_set_id": comparison_set.id
        }, status=200)

# Analytics helper functions
#TODO: MAKE THIS WORK
def get_startup_analytics(startup):
    """Get view and comparison analytics for a startup"""
    total_views = StartupView.objects.filter(startup=startup).count()
    unique_viewers = StartupView.objects.filter(startup=startup).values('user').distinct().count()
    total_comparisons = StartupComparison.objects.filter(startup=startup).count()
    unique_comparers = StartupComparison.objects.filter(startup=startup).values('user').distinct().count()
    
    # Get recent activity (last 30 days)
    from datetime import timedelta
    thirty_days_ago = timezone.now() - timedelta(days=30)
    
    recent_views = StartupView.objects.filter(
        startup=startup,
        viewed_at__gte=thirty_days_ago
    ).count()
    
    recent_comparisons = StartupComparison.objects.filter(
        startup=startup,
        compared_at__gte=thirty_days_ago
    ).count()
    
    return {
        'total_views': total_views,
        'unique_viewers': unique_viewers,
        'total_comparisons': total_comparisons,
        'unique_comparers': unique_comparers,
        'recent_views': recent_views,
        'recent_comparisons': recent_comparisons,
    }

def get_risk_level(confidence):
    """Helper function to get risk level based on confidence"""
    if confidence == 'High':
        return 'Low Risk'
    elif confidence == 'Medium':
        return 'Medium Risk'
    else:
        return 'High Risk'

def get_risk_color(confidence):
    """Helper function to get risk color class"""
    if confidence == 'High':
        return 'bg-green-100 text-green-800'
    elif confidence == 'Medium':
        return 'bg-yellow-100 text-yellow-800'
    else:
        return 'bg-red-100 text-red-800'

'''/* TODO: 
    USE FUTURE VALUE TO CALCULATE THE SIMULATION
    1. CALCULATE CAGR
    2. ASSESS RISK SCORE
    3. APPLY RISK ADJUSTMENT FACTOR
    4. CALCULATE FV
*/'''
class investment_simulation(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        startup_id = request.data.get('startup_id')
        investment_amount = request.data.get('investment_amount', 1000)
        duration_years = request.data.get('duration_years', 1)

        try:
            investment_amount = float(investment_amount)
            duration_years = int(duration_years)
            if investment_amount <= 0 or duration_years <= 0:
                raise ValueError("Invalid input values")
        except (ValueError, TypeError):
            return Response({"error": "Invalid investment amount or duration"}, status=400)

        selected_startup = None
        if startup_id:
            selected_startup = get_object_or_404(Startup, id=startup_id)

        # Use the projected_return directly (which is already CAGR with risk adjustment)
        if selected_startup:
            # projected_return is already calculated using CAGR with risk adjustment
            # from calculate_projected_return() function
            growth_rate = (selected_startup.projected_return or 7) / 100
            risk_level = selected_startup.risk_level or "Medium"
        else:
            growth_rate = 0.07
            risk_level = "Medium"

        # Canonical CAGR compound formula
        final_value = investment_amount * (1 + growth_rate) ** duration_years
        total_gain = final_value - investment_amount
        roi_percentage = (total_gain / investment_amount) * 100

        # Yearly breakdown (compound)
        yearly_breakdown = []
        current_value = investment_amount
        for year in range(1, duration_years + 1):
            growth = current_value * growth_rate
            ending = current_value + growth
            yearly_breakdown.append({
                "year": year,
                "starting_value": round(current_value, 2),
                "growth_amount": round(growth, 2),
                "ending_value": round(ending, 2)
            })
            current_value = ending

        # Chart data for plotting
        chart_data = [{"year": 0, "value": round(investment_amount, 2)}]
        temp_value = investment_amount
        for year in range(1, duration_years + 1):
            temp_value *= (1 + growth_rate)
            chart_data.append({"year": year, "value": round(temp_value, 2)})

        risk_colors = {
            "Low": "bg-green-100 text-green-800",
            "Medium": "bg-yellow-100 text-yellow-800",
            "High": "bg-red-100 text-red-800",
        }

        risk_color = risk_colors.get(risk_level if selected_startup else "Medium", "bg-gray-100 text-gray-800")

        return Response({
            "simulation_run": True,
            "investment_amount": round(investment_amount, 2),
            "duration_years": duration_years,
            "growth_rate": round(growth_rate * 100, 2),
            "final_value": round(final_value, 2),
            "total_gain": round(total_gain, 2),
            "roi_percentage": round(roi_percentage, 2),
            "yearly_breakdown": yearly_breakdown,
            "chart_data": chart_data,
            "risk_level": f"{risk_level} Risk" if selected_startup else "Medium Risk",
            "risk_color": risk_color,
            "calculation_method": "Revenue CAGR with Risk Adjustment",
            "startup": {
                "id": selected_startup.id,
                "name": selected_startup.company_name,
                "industry": selected_startup.industry,
                "projected_return": selected_startup.projected_return,
                "risk_level": selected_startup.risk_level,
            } if selected_startup else None,
        })

#TODO: UPDATE
class calculate_investment_api(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            startup_id = request.data.get('startup_id')
            investment_amount = float(request.data.get('investment_amount', 0))
            duration_years = int(request.data.get('duration_years', 1))

            if investment_amount <= 0 or duration_years <= 0:
                raise ValueError("Investment amount and duration must be positive")
        except (ValueError, TypeError) as e:
            return Response({'success': False, 'error': str(e)}, status=400)

        selected_startup = None
        if startup_id:
            selected_startup = get_object_or_404(Startup, id=startup_id)

        if selected_startup:
            growth_rate = (selected_startup.projected_return or 7) / 100
            risk_level = selected_startup.risk_level or 'Medium'
        else:
            growth_rate = float(request.data.get('growth_rate', 5)) / 100
            risk_level = 'Medium'

        final_value = investment_amount * (1 + growth_rate) ** duration_years
        total_gain = final_value - investment_amount
        roi_percentage = (total_gain / investment_amount) * 100

        yearly_breakdown = []
        current_value = investment_amount
        for year in range(1, duration_years + 1):
            growth_amount = current_value * growth_rate
            ending_value = current_value + growth_amount
            yearly_breakdown.append({
                'year': year,
                'starting_value': round(current_value, 2),
                'growth_amount': round(growth_amount, 2),
                'ending_value': round(ending_value, 2)
            })
            current_value = ending_value

        return Response({
            'success': True,
            'final_value': round(final_value, 2),
            'total_gain': round(total_gain, 2),
            'roi_percentage': round(roi_percentage, 2),
            'growth_rate': round(growth_rate * 100, 2),
            'yearly_breakdown': yearly_breakdown,
            'calculation_method': 'Revenue CAGR (Risk-Adjusted)' if selected_startup else 'Custom Rate',
            'startup_info': {
                'id': selected_startup.id,
                'name': selected_startup.company_name,
                'risk_level': selected_startup.risk_level
            } if selected_startup else None
        }, status=200)



# MOD 4
class deck_home(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            owner_instance = request.user.profile  # Access RegisteredUser via OneToOneField
        except RegisteredUser.DoesNotExist:
            return Response({'error': 'Startup profile not found.'}, status=403)

        if owner_instance.label != 'startup':
            return Response({'error': 'You must be logged in as a startup to view your decks.'}, status=403)

        decks = Deck.objects.filter(owner=owner_instance).order_by('-created_at')
        serializer = DeckSerializer(decks, many=True)

        return Response({'decks': serializer.data}, status=200)

class edit_deck(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, deck_id):
        startup_user_id = request.session.get('startup_user_id')
        if not startup_user_id:
            return Response({'error': 'Authentication required.'}, status=403)

        deck = get_object_or_404(Deck, id=deck_id, owner_id=startup_user_id)
        request.session['deck_id'] = deck_id

        return Response({
            'success': True,
            'message': 'Deck set for editing.',
            'deck_id': deck_id,
            'redirect_section': 'cover-page'
        }, status=200)

class delete_deck(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request, deck_id):
        try:
            owner = request.user.profile
            deck = get_object_or_404(Deck, id=deck_id, owner=owner)
            # 🔥 Delete any startup linked to this deck
            Startup.objects.filter(source_deck=deck).delete()
            # 🧹 Then delete the deck itself
            deck.delete()
            return Response({'success': True, 'message': 'Deck and linked startup deleted successfully.'}, status=200)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({'error': str(e)}, status=500)

class startup_registration(APIView):
    def post(self, request):
        if not request.data.get('terms'):
            return Response(
                {"error": "You must agree to the Terms of Service and Privacy Policy."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = StartupRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Startup account created successfully.'
            }, status=status.HTTP_201_CREATED)
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
def registration_success(request):
    return render(request, 'Module_3/registration_success.html')

# MOD 3
class added_startups(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = RegisteredUser.objects.get(user=request.user)
        except RegisteredUser.DoesNotExist:
            return Response({
                'error': 'User profile not found.',
                'detail': 'No RegisteredUser profile associated with this user.'
            }, status=status.HTTP_404_NOT_FOUND)
        try:
            # Base queryset
            if profile.label == 'startup':
                startups = Startup.objects.filter(owner=profile).order_by('-created_at')
            elif profile.label == 'investor':
                startups = Startup.objects.all().order_by('-created_at')
            else:
                return Response({
                    'error': 'Access denied.',
                    'detail': 'Only startup or investor users can access startups.'
                }, status=status.HTTP_403_FORBIDDEN)

            # Get all startups owned by this user
            startups = Startup.objects.filter(owner=profile).order_by('-created_at')

            # Prepare enriched data with analytics
            enriched_data = []
            for index, startup in enumerate(startups, 1):  # Start user-relative ID from 1
                try:
                    # Get analytics data
                    analytics = get_startup_analytics(startup)
                    
                    # Serialize startup data
                    serialized = StartupSerializer(startup).data
                    
                    # Add analytics
                    serialized['analytics'] = analytics
                    
                    # Add user-relative startup ID (1, 2, 3, etc.)
                    serialized['user_startup_id'] = index
                    
                    enriched_data.append(serialized)
                    
                except Exception as e:
                    # Log error but continue with other startups
                    print(f"Error processing startup {startup.id}: {e}")
                    # Still include the startup without analytics
                    serialized = StartupSerializer(startup).data
                    serialized['analytics'] = None
                    serialized['user_startup_id'] = index
                    enriched_data.append(serialized)

            return Response({
                'success': True,
                'count': len(enriched_data),
                'results': enriched_data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            import traceback
            print(f"Error in added_startups view: {e}")
            traceback.print_exc()
            return Response({
                'error': 'Internal server error',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class user_logout(APIView):
    def post(self, request):
        # Clear session-based authentication
        logout(request)

        # If you're using session auth, this flushes the session
        request.session.flush()

        return Response({
            'success': True,
            'message': 'You have been logged out successfully.'
        }, status=status.HTTP_200_OK)

class company_information_form(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        startup_user_id = request.session.get('startup_user_id')
        user_label = request.session.get('user_label')

        if not startup_user_id or user_label != 'startup':
            return Response({
                'error': 'Please log in as a startup to access this endpoint.'
            }, status=403)

        data = request.data

        # Helper function to safely parse numeric values
        def parse_numeric(value):
            if value is None or value == '':
                return None
            try:
                return float(value)
            except (ValueError, TypeError):
                return None

        company_data = {
            # Basic Information
            'company_name': data.get('company_name', '').strip(),
            'industry': data.get('industry', '').strip(),
            'company_description': data.get('company_description', '').strip(),
            
            # Financial Data - Income Statement
            'time_between_periods': parse_numeric(data.get('time_between_periods')),
            'previous_revenue': parse_numeric(data.get('previous_revenue')),
            'current_revenue': parse_numeric(data.get('current_revenue')),
            'revenue': parse_numeric(data.get('revenue')),  # Duplicate field for compatibility
            'net_income': parse_numeric(data.get('net_income')),
            'ebit': parse_numeric(data.get('ebit')),
            
            # Financial Data - Balance Sheet
            'total_assets': parse_numeric(data.get('total_assets')),
            'current_assets': parse_numeric(data.get('current_assets')),
            'total_liabilities': parse_numeric(data.get('total_liabilities')),
            'current_liabilities': parse_numeric(data.get('current_liabilities')),
            'retained_earnings': parse_numeric(data.get('retained_earnings')),
            'shareholder_equity': parse_numeric(data.get('shareholder_equity')),
            'working_capital': parse_numeric(data.get('working_capital')),
            
            # Financial Data - Cash Flow
            'cash_flow': parse_numeric(data.get('cash_flow')),
            
            # Qualitative Assessment
            'team_strength': data.get('team_strength', '').strip(),
            'market_position': data.get('market_position', '').strip(),
            'brand_reputation': data.get('brand_reputation', '').strip(),
            
            # Confidence Metrics
            'data_source_confidence': data.get('data_source_confidence', 'Medium').strip(),
            'confidence_percentage': parse_numeric(data.get('confidence_percentage')),
        }

        # Validate required fields
        if not company_data['company_name'] or not company_data['industry']:
            return Response({
                'success': False,
                'error': 'Company name and industry are required fields.',
                'errors': {
                    'company_name': ['This field is required.'] if not company_data['company_name'] else [],
                    'industry': ['This field is required.'] if not company_data['industry'] else []
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        # Store in session
        request.session['company_data'] = company_data
        request.session.modified = True

        return Response({
            'success': True,
            'message': 'Company information saved successfully.',
            'startup_id': startup_user_id,
            'data': company_data,
            'next_step': 'health_report_page'
        }, status=status.HTTP_200_OK)

class health_report_page(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        startup_user_id = request.session.get('startup_user_id')
        user_label = request.session.get('user_label')

        if not startup_user_id or user_label != 'startup':
            return Response({'error': 'Please log in as a startup to access this page.'}, status=403)

        company_data = request.session.get('company_data', {})
        edit_startup_id = request.session.get('edit_startup_id')

        if not company_data.get('company_name'):
            return Response({'error': 'No company data found. Please fill out the company information form first.'}, status=400)

        return Response({
            'company_data': company_data,
            'edit_startup_id': edit_startup_id
        }, status=200)

@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
@csrf_exempt
def add_startup(request):
    """
    DRF-compliant view to add a new startup using StartupSerializer
    """
    # Get the authenticated user from JWT token
    user = request.user
    
    try:
        # Get the RegisteredUser profile
        registered_user = RegisteredUser.objects.get(user=user)
        
        # Check if user is a startup
        if registered_user.label != 'startup':
            return Response({
                'success': False, 
                'error': 'Only startup users can add company information'
            }, status=status.HTTP_403_FORBIDDEN)
            
    except RegisteredUser.DoesNotExist:
        return Response({
            'success': False, 
            'error': 'User profile not found'
        }, status=status.HTTP_404_NOT_FOUND)

    # Prepare data for serializer - add the owner
    startup_data = request.data.copy()
    
    # Create serializer instance with the data
    serializer = StartupSerializer(data=startup_data)
    
    if serializer.is_valid():
        # Save the startup with the owner (not included in serializer)
        startup = serializer.save(owner=registered_user)
        
        return Response({
            'success': True,
            'message': 'Startup added successfully!',
            'startup_id': startup.id,
            'data': StartupSerializer(startup).data
        }, status=status.HTTP_201_CREATED)
    else:
        # Return validation errors
        return Response({
            'success': False,
            'error': 'Validation failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class delete_startup(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request, startup_id):
        try:
            # Get the authenticated user from JWT token
            user = request.user
            
            # Get the RegisteredUser profile associated with the authenticated user
            try:
                user_profile = RegisteredUser.objects.get(user=user)
            except RegisteredUser.DoesNotExist:
                return Response({
                    'success': False, 
                    'error': 'User profile not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Find the startup owned by this user
            startup = get_object_or_404(Startup, id=startup_id, owner=user_profile)
            startup_name = startup.company_name
            
            # Delete the startup
            startup.delete()

            return Response({
                'success': True,
                'message': f'Startup "{startup_name}" deleted successfully!'
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'success': False, 
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class edit_startup(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, startup_id):
        # Use JWT authentication - get owner from request.user.profile
        owner = request.user.profile
        startup = get_object_or_404(Startup, id=startup_id, owner=owner)

        # Check if startup is from pitch deck (should not be editable)
        if startup.source_deck:
            return Response({
                'error': 'Pitch deck startups cannot be edited through this form.',
                'startup_type': 'pitch-deck'
            }, status=400)

        # Return all fields that the frontend expects
        form_data = {
            'id': startup.id,
            'company_name': startup.company_name,
            'industry': startup.industry,
            'company_description': startup.company_description,
            'data_source_confidence': startup.data_source_confidence,
            'reporting_period': startup.reporting_period or '',
            'previous_revenue': float(startup.previous_revenue) if startup.previous_revenue else None,
            'current_revenue': float(startup.current_revenue) if startup.current_revenue else None,
            'revenue': float(startup.revenue) if startup.revenue else None,
            'net_income': float(startup.net_income) if startup.net_income else None,
            'total_assets': float(startup.total_assets) if startup.total_assets else None,
            'total_liabilities': float(startup.total_liabilities) if startup.total_liabilities else None,
            'shareholder_equity': float(startup.shareholder_equity) if startup.shareholder_equity else None,
            'cash_flow': float(startup.cash_flow) if startup.cash_flow else None,
            'investment_flow': float(startup.investment_flow) if startup.investment_flow else None,
            'financing_flow': float(startup.financing_flow) if startup.financing_flow else None,
            'team_strength': startup.team_strength or '',
            'market_position': startup.market_position or '',
            'brand_reputation': startup.brand_reputation or '',
            'confidence_percentage': startup.confidence_percentage,
        }

        return Response(form_data, status=200)

    def put(self, request, startup_id):
        # Use JWT authentication - get owner from request.user.profile
        owner = request.user.profile
        startup = get_object_or_404(Startup, id=startup_id, owner=owner)

        # Check if startup is from pitch deck (should not be editable)
        if startup.source_deck:
            return Response({
                'error': 'Pitch deck startups cannot be edited through this form.',
                'startup_type': 'pitch-deck'
            }, status=400)

        data = request.data

        def to_decimal(value):
            try:
                return float(str(value).strip()) if value and str(value).strip() else None
            except (ValueError, TypeError):
                return None

        confidence_level = data.get('data_source_confidence', 'Medium')
        confidence_percentage = {'High': 75, 'Medium': 50, 'Low': 30}.get(confidence_level, 50)

        # Update all fields
        startup.company_name = data.get('company_name', '')
        startup.industry = data.get('industry', '')
        startup.company_description = data.get('company_description', '')
        startup.data_source_confidence = confidence_level
        startup.confidence_percentage = confidence_percentage
        
        # Financial data - Income Statement
        startup.reporting_period = data.get('reporting_period', '')
        startup.previous_revenue = to_decimal(data.get('previous_revenue'))
        startup.current_revenue = to_decimal(data.get('current_revenue'))
        startup.revenue = to_decimal(data.get('current_revenue'))  # Keep revenue in sync with current_revenue
        startup.net_income = to_decimal(data.get('net_income'))
        
        # Financial data - Balance Sheet
        startup.total_assets = to_decimal(data.get('total_assets'))
        startup.total_liabilities = to_decimal(data.get('total_liabilities'))
        # Shareholder equity is calculated on frontend, but we can store it
        startup.shareholder_equity = to_decimal(data.get('shareholder_equity'))
        
        # Financial data - Cash Flow
        startup.cash_flow = to_decimal(data.get('cash_flow'))
        startup.investment_flow = to_decimal(data.get('investment_flow'))
        startup.financing_flow = to_decimal(data.get('financing_flow'))
        
        # Qualitative data
        startup.team_strength = data.get('team_strength', '')
        startup.market_position = data.get('market_position', '')
        startup.brand_reputation = data.get('brand_reputation', '')

        startup.save()

        return Response({
            'success': True, 
            'message': f'Startup "{startup.company_name}" updated successfully!',
            'startup': {
                'id': startup.id,
                'company_name': startup.company_name,
                'industry': startup.industry
            }
        }, status=200)

class view_startup_report(APIView):
    """
    DRF-compliant view to get detailed startup report for authenticated users
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, startup_id):
        try:
            # Get the RegisteredUser profile from the authenticated user
            profile = RegisteredUser.objects.select_related('user').get(user=request.user)
        except RegisteredUser.DoesNotExist:
            return Response({
                'success': False,
                'error': 'User profile not found.',
                'detail': 'No RegisteredUser profile associated with this user.'
            }, status=status.HTTP_404_NOT_FOUND)

        # Check if user is a startup
        if profile.label != 'startup':
            return Response({
                'success': False,
                'error': 'Access denied.',
                'detail': 'Only startup users can access startup reports.'
            }, status=status.HTTP_403_FORBIDDEN)

        # Get the startup - ensure it's owned by this user
        try:
            startup = Startup.objects.select_related('owner', 'source_deck').get(id=startup_id, owner=profile)
        except Startup.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Startup not found.',
                'detail': 'Startup not found or you do not have permission to access it.'
            }, status=status.HTTP_404_NOT_FOUND)

        # ✅ Track view
        try:
            StartupView.objects.create(
                user=request.user,
                startup=startup,
                viewed_at=timezone.now(),
                ip_address=request.META.get('REMOTE_ADDR')
            )
        except Exception as e:
            # Log error but don't fail the request
            print(f"Error tracking startup view: {e}")

        # Return startup report data
        company_data = {
            'success': True,
            'startup': {
                'id': startup.id,
                'company_name': startup.company_name,
                'industry': startup.industry,
                'company_description': startup.company_description,
                'data_source_confidence': startup.data_source_confidence,
                'confidence_percentage': startup.confidence_percentage,
                'reporting_period': startup.reporting_period,
                'created_at': startup.created_at.isoformat() if startup.created_at else None,
                'updated_at': startup.updated_at.isoformat() if startup.updated_at else None
            },
            'financials': {
                'income_statement': {
                    'previous_revenue': float(startup.previous_revenue) if startup.previous_revenue else None,
                    'current_revenue': float(startup.current_revenue) if startup.current_revenue else None,
                    'revenue': float(startup.revenue) if startup.revenue else None,
                    'net_income': float(startup.net_income) if startup.net_income else None
                },
                'balance_sheet': {
                    'total_assets': float(startup.total_assets) if startup.total_assets else None,
                    'total_liabilities': float(startup.total_liabilities) if startup.total_liabilities else None,
                    'shareholder_equity': float(startup.shareholder_equity) if startup.shareholder_equity else None
                },
                'cash_flow': {
                    'operations': float(startup.cash_flow) if startup.cash_flow else None,
                    'investment_flow': float(startup.investment_flow) if startup.investment_flow else None,
                    'financing_flow': float(startup.financing_flow) if startup.financing_flow else None
                }
            },
            'qualitative': {
                'team_strength': startup.team_strength or '',
                'market_position': startup.market_position or '',
                'brand_reputation': startup.brand_reputation or ''
            }
        }
        return Response(company_data, status=status.HTTP_200_OK)

class create_deck(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data

        try:
            with transaction.atomic():
                # Create deck
                deck_serializer = DeckSerializer(data=data.get('deck'))
                deck_serializer.is_valid(raise_exception=True)
                deck = deck_serializer.save(owner=request.user)

                # Create one-to-one components
                for key, serializer_class in {
                    'problem': ProblemSerializer,
                    'solution': SolutionSerializer,
                    'market_analysis': MarketAnalysisSerializer,
                    'ask': FundingAskSerializer
                }.items():
                    section_data = data.get(key)
                    if section_data:
                        section_data['deck'] = deck.id
                        serializer = serializer_class(data=section_data)
                        serializer.is_valid(raise_exception=True)
                        serializer.save()

                # Create team members
                team_data = data.get('team_members', [])
                for member in team_data:
                    member['deck'] = deck.id
                    serializer = TeamMemberSerializer(data=member)
                    serializer.is_valid(raise_exception=True)
                    serializer.save()

                # Create financial projections
                financial_data = data.get('financials', [])
                for projection in financial_data:
                    projection['deck'] = deck.id
                    serializer = FinancialProjectionSerializer(data=projection)
                    serializer.is_valid(raise_exception=True)
                    serializer.save()

            return Response({
                'success': True,
                'message': 'Deck created successfully!',
                'deck_id': deck.id
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class add_deck_to_recommended(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        startup_user_id = request.session.get('startup_user_id')
        deck_id = request.session.get('deck_id')

        if not startup_user_id:
            return Response({'success': False, 'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        if not deck_id:
            return Response({'success': False, 'error': 'No active deck found'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = RegisteredUser.objects.get(id=startup_user_id)
            deck = get_object_or_404(Deck, id=deck_id, owner=user)

            # Check for duplicate startup
            if Startup.objects.filter(owner=user, company_name=deck.company_name).exists():
                return Response({
                    'success': False,
                    'error': f'Startup "{deck.company_name}" already exists in your added startups'
                }, status=status.HTTP_409_CONFLICT)

            # Extract financials
            financials = deck.financials.order_by('year')
            total_revenue = sum(f.revenue for f in financials if f.revenue) if financials.exists() else None
            total_profit = sum(f.profit for f in financials if f.profit) if financials.exists() else None

            # Market and ask
            market = getattr(deck, 'market_analysis', None)
            ask = getattr(deck, 'ask', None)
            funding_ask_amount = ask.amount if ask and hasattr(ask, 'amount') else None
            funding_ask_text = f"Seeking {ask.amount} funding" if funding_ask_amount else ""

            # Description
            problem = getattr(deck, 'problem', None)
            solution = getattr(deck, 'solution', None)
            description_parts = []
            if problem and problem.description:
                description_parts.append(f"Problem: {problem.description}")
            if solution and solution.description:
                description_parts.append(f"Solution: {solution.description}")
            company_description = " | ".join(description_parts) if description_parts else "No description available"

            # Industry
            industry = market.primary_market if market and market.primary_market else "Technology"

            # Create startup
            startup = Startup.objects.create(
                owner=user,
                company_name=deck.company_name,
                industry=industry,
                company_description=company_description,
                data_source_confidence='High',
                confidence_percentage=85,
                revenue=total_revenue,
                net_income=total_profit,
                funding_ask=funding_ask_amount,
                source_deck=deck,
                total_assets=None,
                total_liabilities=None,
                cash_flow=None,
                team_strength=f"Team size: {deck.team_members.count()} members" if deck.team_members.exists() else "",
                market_position=market.competitive_advantage if market and market.competitive_advantage else "",
                brand_reputation=funding_ask_text
            )

            return Response({
                'success': True,
                'message': f'"{deck.company_name}" has been added to your startup recommendations!',
                'startup_id': startup.id
            }, status=status.HTTP_201_CREATED)

        except RegisteredUser.DoesNotExist:
            return Response({'success': False, 'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            import traceback
            print(f"Error in AddDeckToRecommendedView: {str(e)}")
            print(traceback.format_exc())
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class debug_session(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        session_data = {
            'startup_user_id': request.session.get('startup_user_id'),
            'deck_id': request.session.get('deck_id'),
            'session_keys': list(request.session.keys())
        }
        return Response(session_data, status=200)

class create_new_deck(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            owner_instance = request.user.profile  # Comes from JWT

            deck = Deck.objects.create(
                owner=owner_instance,
                company_name="Untitled Deck",
                tagline=""
            )

            print(f"DEBUG: Created fresh new deck {deck.id} for user {owner_instance.id}")

            return Response({
                'success': True,
                'message': 'New deck created successfully.',
                'deck_id': deck.id,
                'next_section': 'cover-page'
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({
                'error': f'An error occurred while creating a new deck: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class create_cover(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        owner = request.user.profile
        deck_id = request.data.get('deck_id')

        if not deck_id:
            return Response({'error': 'Missing deck_id.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            deck = Deck.objects.get(id=deck_id, owner=owner)

            deck_data = {
                'company_name': request.data.get('company_name'),
                'tagline': request.data.get('tagline'),
            }

            if 'logo' in request.FILES:
                deck_data['logo'] = request.FILES['logo']

            serializer = DeckSerializer(deck, data=deck_data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            # 🔄 Sync Startup if one is linked to this deck
            Startup.objects.filter(source_deck=deck).update(
                company_name=deck.company_name,
                company_description=deck.tagline
            )

            return Response({
                'success': True,
                'message': 'Cover page updated successfully.',
                'deck_id': deck.id
            }, status=status.HTTP_200_OK)

        except Deck.DoesNotExist:
            return Response({'error': 'Deck not found or unauthorized.'}, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as ve:
            return Response({'success': False, 'errors': ve.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request):
        deck_id = request.query_params.get('deck_id')
        if not deck_id:
            return Response({'error': 'Missing deck_id.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            owner = request.user.profile
            deck = Deck.objects.get(id=deck_id, owner=owner)

            return Response({
                'company_name': deck.company_name,
                'tagline': deck.tagline,
                'logo_url': deck.logo.url if deck.logo else None
            }, status=status.HTTP_200_OK)

        except Deck.DoesNotExist:
            return Response({'error': 'Deck not found or unauthorized.'}, status=status.HTTP_404_NOT_FOUND)
        
class create_problem(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        owner = request.user.profile
        deck_id = request.data.get('deck_id')

        if not deck_id:
            return Response({'error': 'Missing deck_id.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            deck = Deck.objects.get(id=deck_id, owner=owner)
            problem_instance = getattr(deck, 'problem', None)

            serializer = ProblemSerializer(
                instance=problem_instance,
                data={'deck': deck.id, 'description': request.data.get('description')},
                partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()

            return Response({
                'success': True,
                'message': 'Problem section saved successfully.',
                'deck_id': deck.id
            }, status=status.HTTP_200_OK)

        except Deck.DoesNotExist:
            return Response({'error': 'Deck not found or unauthorized.'}, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as ve:
            return Response({'success': False, 'errors': ve.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request):
        deck_id = request.query_params.get('deck_id')
        if not deck_id:
            return Response({'error': 'Missing deck_id.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            owner = request.user.profile
            deck = Deck.objects.get(id=deck_id, owner=owner)
            problem_instance = getattr(deck, 'problem', None)

            if not problem_instance:
                return Response({'description': ''}, status=status.HTTP_200_OK)

            return Response({
                'description': problem_instance.description
            }, status=status.HTTP_200_OK)

        except Deck.DoesNotExist:
            return Response({'error': 'Deck not found or unauthorized.'}, status=status.HTTP_404_NOT_FOUND)    
        
class create_solution(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        owner = request.user.profile
        deck_id = request.data.get('deck_id')

        if not deck_id:
            return Response({'error': 'Missing deck_id.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            deck = Deck.objects.get(id=deck_id, owner=owner)
            solution_instance = getattr(deck, 'solution', None)

            serializer = SolutionSerializer(
                instance=solution_instance,
                data={'deck': deck.id, 'description': request.data.get('description')},
                partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()

            return Response({
                'success': True,
                'message': 'Solution section saved successfully.',
                'deck_id': deck.id
            }, status=status.HTTP_200_OK)

        except Deck.DoesNotExist:
            return Response({'error': 'Deck not found or unauthorized.'}, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as ve:
            return Response({'success': False, 'errors': ve.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request):
        deck_id = request.query_params.get('deck_id')
        if not deck_id:
            return Response({'error': 'Missing deck_id.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            owner = request.user.profile
            deck = Deck.objects.get(id=deck_id, owner=owner)
            solution_instance = getattr(deck, 'solution', None)

            if not solution_instance:
                return Response({'description': ''}, status=status.HTTP_200_OK)

            return Response({
                'description': solution_instance.description
            }, status=status.HTTP_200_OK)

        except Deck.DoesNotExist:
            return Response({'error': 'Deck not found or unauthorized.'}, status=status.HTTP_404_NOT_FOUND)
        
class create_market_analysis(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        owner = request.user.profile
        deck_id = request.data.get('deck_id')

        if not deck_id:
            return Response({'error': 'Missing deck_id.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            deck = Deck.objects.get(id=deck_id, owner=owner)
            market_instance = getattr(deck, 'market_analysis', None)

            serializer = MarketAnalysisSerializer(
                instance=market_instance,
                data={
                    'deck': deck.id,
                    'primary_market': request.data.get('primary_market'),
                    'target_audience': request.data.get('target_audience'),
                    'market_growth_rate': request.data.get('market_growth_rate'),
                    'competitive_advantage': request.data.get('competitive_advantage')
                },
                partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()

            return Response({
                'success': True,
                'message': 'Market analysis section saved successfully.',
                'deck_id': deck.id
            }, status=status.HTTP_200_OK)

        except Deck.DoesNotExist:
            return Response({'error': 'Deck not found or unauthorized.'}, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as ve:
            return Response({'success': False, 'errors': ve.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request):
        deck_id = request.query_params.get('deck_id')
        if not deck_id:
            return Response({'error': 'Missing deck_id.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            owner = request.user.profile
            deck = Deck.objects.get(id=deck_id, owner=owner)
            market_instance = getattr(deck, 'market_analysis', None)

            if not market_instance:
                return Response({
                    'primary_market': '',
                    'target_audience': '',
                    'market_growth_rate': '',
                    'competitive_advantage': ''
                }, status=status.HTTP_200_OK)

            return Response({
                'primary_market': market_instance.primary_market,
                'target_audience': market_instance.target_audience,
                'market_growth_rate': market_instance.market_growth_rate,
                'competitive_advantage': market_instance.competitive_advantage
            }, status=status.HTTP_200_OK)

        except Deck.DoesNotExist:
            return Response({'error': 'Deck not found or unauthorized.'}, status=status.HTTP_404_NOT_FOUND)

class create_team(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        owner = request.user.profile
        deck_id = request.data.get('deck_id')
        members = request.data.get('members', [])

        if not deck_id:
            return Response({'error': 'Missing deck_id.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            deck = Deck.objects.get(id=deck_id, owner=owner)

            # Clear existing team members (optional)
            deck.team_members.all().delete()

            # Validate and create new members
            created = []
            for member in members:
                serializer = TeamMemberSerializer(data={
                    'deck': deck.id,
                    'name': member.get('name'),
                    'title': member.get('title')
                })
                serializer.is_valid(raise_exception=True)
                created.append(serializer.save())

            # 🔄 Sync Startup if linked to this deck
            team_text = "\n".join([f"{m.name} - {m.title}" for m in deck.team_members.all()])

            return Response({
                'success': True,
                'message': 'Team members saved successfully.',
                'deck_id': deck.id,
                'members': TeamMemberSerializer(created, many=True).data
            }, status=status.HTTP_200_OK)

        except Deck.DoesNotExist:
            return Response({'error': 'Deck not found or unauthorized.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request):
        deck_id = request.query_params.get('deck_id')
        if not deck_id:
            return Response({'error': 'Missing deck_id.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            owner = request.user.profile
            deck = Deck.objects.get(id=deck_id, owner=owner)
            members = deck.team_members.all()

            return Response({
                'members': TeamMemberSerializer(members, many=True).data
            }, status=status.HTTP_200_OK)

        except Deck.DoesNotExist:
            return Response({'error': 'Deck not found or unauthorized.'}, status=status.HTTP_404_NOT_FOUND)
        
class create_financial(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        owner = request.user.profile
        deck_id = request.data.get('deck_id')
        projections = request.data.get('financials', [])

        if not deck_id:
            return Response({'error': 'Missing deck_id.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            deck = Deck.objects.get(id=deck_id, owner=owner)

            # Clear existing financials
            deck.financials.all().delete()

            created = []
            for item in projections:
                serializer = FinancialProjectionSerializer(data={
                    'deck': deck.id,
                    'year': item.get('year'),
                    'revenue': item.get('revenue'),
                    'profit': item.get('profit')
                })
                serializer.is_valid(raise_exception=True)
                created.append(serializer.save())

            return Response({
                'success': True,
                'message': 'Financial projections saved successfully.',
                'deck_id': deck.id,
                'projections': FinancialProjectionSerializer(created, many=True).data
            }, status=status.HTTP_200_OK)

        except Deck.DoesNotExist:
            return Response({'error': 'Deck not found or unauthorized.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request):
        deck_id = request.query_params.get('deck_id')
        if not deck_id:
            return Response({'error': 'Missing deck_id.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            owner = request.user.profile
            deck = Deck.objects.get(id=deck_id, owner=owner)
            projections = deck.financials.all().order_by('year')

            return Response(FinancialProjectionSerializer(projections, many=True).data, status=status.HTTP_200_OK)

        except Deck.DoesNotExist:
            return Response({'error': 'Deck not found or unauthorized.'}, status=status.HTTP_404_NOT_FOUND)
        
class create_ask(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        owner = request.user.profile
        deck_id = request.data.get('deck_id')

        if not deck_id:
            return Response({'error': 'Missing deck_id.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            deck = Deck.objects.get(id=deck_id, owner=owner)
            ask_instance = getattr(deck, 'ask', None)

            serializer = FundingAskSerializer(
                instance=ask_instance,
                data={
                    'deck': deck.id,
                    'amount': request.data.get('amount'),
                    'usage_description': request.data.get('usage_description')
                },
                partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()

            # 🔄 Sync funding ask if Startup already exists
            Startup.objects.filter(source_deck=deck).update(
                funding_ask=serializer.instance.amount
            )

            # ✅ Create Startup shell if not already linked
            if not Startup.objects.filter(source_deck=deck).exists():
                Startup.objects.create(
                    owner=owner,  # assuming profile.user is the RegisteredUser
                    company_name=deck.company_name,
                    industry='—',  # optional: prompt later or infer from deck
                    company_description=deck.tagline or '',
                    data_source_confidence='Medium',
                    confidence_percentage=50,
                    funding_ask=serializer.instance.amount,
                    source_deck=deck,
                )

            return Response({
                'success': True,
                'message': 'Funding ask saved and startup created.',
                'deck_id': deck.id
            }, status=status.HTTP_200_OK)

        except Deck.DoesNotExist:
            return Response({'error': 'Deck not found or unauthorized.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request):
        deck_id = request.query_params.get('deck_id')
        if not deck_id:
            return Response({'error': 'Missing deck_id.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            owner = request.user.profile
            deck = Deck.objects.get(id=deck_id, owner=owner)
            ask_instance = getattr(deck, 'ask', None)

            if not ask_instance:
                return Response({
                    'amount': '',
                    'usage_description': ''
                }, status=status.HTTP_200_OK)

            return Response({
                'amount': ask_instance.amount,
                'usage_description': ask_instance.usage_description
            }, status=status.HTTP_200_OK)

        except Deck.DoesNotExist:
            return Response({'error': 'Deck not found or unauthorized.'}, status=status.HTTP_404_NOT_FOUND)
        
class UserDeckListView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        owner = request.user.profile
        decks = Deck.objects.filter(owner=owner).order_by('-created_at')  # optional ordering
        serializer = DeckDetailSerializer(decks, many=True)
        return Response({
            'success': True,
            'count': len(decks),
            'decks': serializer.data
        }, status=status.HTTP_200_OK)

class FinancialsView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        deck_id = request.query_params.get('deck_id')
        financials = FinancialProjection.objects.filter(deck_id=deck_id).order_by('year')
        serializer = FinancialProjectionSerializer(financials, many=True)
        return Response(serializer.data)
    
class DeckReportView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, deck_id):  # <-- deck_id comes from the URL
        try:
            registered_user = RegisteredUser.objects.get(user=request.user)
        except RegisteredUser.DoesNotExist:
            return Response({'detail': 'RegisteredUser not found'}, status=404)

        try:
            deck = Deck.objects.get(id=deck_id, owner=registered_user)
        except Deck.DoesNotExist:
            return Response({'detail': 'Deck not found'}, status=404)

        serializer = DeckReportSerializer(deck)
        return Response(serializer.data)

class startup_detail(APIView):
    """
    DRF-compliant view to get and update a single startup owned by the authenticated user
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, startup_id):
        try:
            # Get the RegisteredUser profile from the authenticated user - optimized with select_related
            profile = RegisteredUser.objects.select_related('user').get(user=request.user)
        except RegisteredUser.DoesNotExist:
            return Response({
                'error': 'User profile not found.',
                'detail': 'No RegisteredUser profile associated with this user.'
            }, status=status.HTTP_404_NOT_FOUND)

        # Check if user is a startup
        if profile.label != 'startup':
            return Response({
                'error': 'Access denied.',
                'detail': 'Only startup users can access their startup details.'
            }, status=status.HTTP_403_FORBIDDEN)

        try:
            # Get the startup owned by this user - optimized with select_related
            startup = Startup.objects.select_related('owner', 'source_deck').get(id=startup_id, owner=profile)
        except Startup.DoesNotExist:
            return Response({
                'error': 'Startup not found.',
                'detail': 'Startup not found or you do not have permission to access it.'
            }, status=status.HTTP_404_NOT_FOUND)

        # Serialize the startup data
        serializer = StartupSerializer(startup)
        
        return Response({
            'success': True,
            'startup': serializer.data
        }, status=status.HTTP_200_OK)

    def put(self, request, startup_id):
        try:
            # Get the RegisteredUser profile from the authenticated user - optimized
            profile = RegisteredUser.objects.select_related('user').get(user=request.user)
        except RegisteredUser.DoesNotExist:
            return Response({
                'error': 'User profile not found.',
                'detail': 'No RegisteredUser profile associated with this user.'
            }, status=status.HTTP_404_NOT_FOUND)

        # Check if user is a startup
        if profile.label != 'startup':
            return Response({
                'error': 'Access denied.',
                'detail': 'Only startup users can update their startup details.'
            }, status=status.HTTP_403_FORBIDDEN)

        try:
            # Get the startup owned by this user - optimized
            startup = Startup.objects.select_related('owner', 'source_deck').get(id=startup_id, owner=profile)
        except Startup.DoesNotExist:
            return Response({
                'error': 'Startup not found.',
                'detail': 'Startup not found or you do not have permission to update it.'
            }, status=status.HTTP_404_NOT_FOUND)

        # Update the startup with the provided data
        serializer = StartupSerializer(startup, data=request.data, partial=True)
        
        if serializer.is_valid():
            try:
                updated_startup = serializer.save(updated_at=timezone.now())
                
                return Response({
                    'success': True,
                    'message': 'Startup information updated successfully.',
                    'startup': StartupSerializer(updated_startup).data
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                return Response({
                    'success': False,
                    'error': f'Failed to update startup: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response({
                'success': False,
                'error': 'Validation failed.',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, startup_id):
        """
        Delete a startup owned by the authenticated user
        """
        try:
            # Get the RegisteredUser profile from the authenticated user
            profile = RegisteredUser.objects.get(user=request.user)
        except RegisteredUser.DoesNotExist:
            return Response({
                'success': False,
                'error': 'User profile not found.',
                'detail': 'No RegisteredUser profile associated with this user.'
            }, status=status.HTTP_404_NOT_FOUND)

        # Check if user is a startup
        if profile.label != 'startup':
            return Response({
                'success': False,
                'error': 'Access denied.',
                'detail': 'Only startup users can delete their startup details.'
            }, status=status.HTTP_403_FORBIDDEN)

        try:
            # Get the startup owned by this user
            startup = Startup.objects.get(id=startup_id, owner=profile)
        except Startup.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Startup not found.',
                'detail': 'Startup not found or you do not have permission to delete it.'
            }, status=status.HTTP_404_NOT_FOUND)

        # Store startup name for response message
        startup_name = startup.company_name
        
        # Delete the startup
        startup.delete()

        return Response({
            'success': True,
            'message': f'Startup "{startup_name}" deleted successfully!'
        }, status=status.HTTP_200_OK)

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

class TestAPI(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"message": "API is working!"})