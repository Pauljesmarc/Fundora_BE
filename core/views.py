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
from django.db.models import Value, FloatField, Case, When, Prefetch

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import ListAPIView, RetrieveAPIView
from django.conf import settings
import requests

from .models import Startup, Deck, FinancialProjection
from .serializers import (
    UserSerializer,
    DeckDetailSerializer,
    FinancialProjectionSerializer,
    StartupViewSerializer,
    RecordViewResponseSerializer,
    StartupSerializer,
)
import uuid
import math
from datetime import timedelta

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
    StartupViewSerializer,
    RecordViewResponseSerializer,
    StartupComparisonSerializer,
    RecordComparisonResponseSerializer,
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
                    market = getattr(deck, 'market_analysis', None)
                    market_growth_rate = market.market_growth_rate if market and hasattr(market, 'market_growth_rate') else None
                    
                    Startup.objects.create(
                        company_name=getattr(deck, "company_name", "Untitled Deck"),
                        company_description=getattr(deck, "description", ""),
                        industry=getattr(deck, "tagline", "—"),
                        data_source_confidence="Medium",
                        source_deck_id=deck.id,
                        is_deck_builder=True,
                        funding_ask=getattr(deck.ask, 'amount', None) if hasattr(deck, 'ask') else None,
                        market_growth_rate=market_growth_rate,
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

        # ---- STARTUP TYPE FILTER ----
        startup_type = params.get('startup_type')
        if startup_type == 'pitch_deck':
            # Only show pitch decks (source_deck is not null)
            qs = qs.filter(source_deck__isnull=False)
        elif startup_type == 'financial':
            # Only show regular startups (source_deck is null)
            qs = qs.filter(source_deck__isnull=True)
        # If no startup_type specified, show all

        # ---- FILTERS ----
        
        # Industry filter (case-insensitive)
        industry = params.get('industry')
        if industry:
            qs = qs.filter(industry__iexact=industry)

        # Risk tolerance filter (Low/Medium/High) - applied post-serialization
        risk_tolerance = params.get('risk_tolerance')
        self._risk_tolerance_filter = risk_tolerance if risk_tolerance else None

        # Risk slider (0-100) - applied post-serialization based on calculated financial risk
        risk = params.get('risk')
        self._risk_filter = int(risk) if risk else None

        # Minimum growth rate filter - only for financial startups, not pitch decks
        min_growth_rate = params.get('min_growth_rate')
        if min_growth_rate and startup_type != 'pitch_deck':
            self._min_growth_rate_filter = float(min_growth_rate)
        else:
            self._min_growth_rate_filter = None

        # Pitch Deck Filters
        funding_ask_range = params.get('funding_ask_range')
        self._funding_ask_range = funding_ask_range

        market_growth_filter = params.get('market_growth_filter')
        self._market_growth_filter = market_growth_filter

        min_market_growth = params.get('min_market_growth')
        self._min_market_growth = float(min_market_growth) if min_market_growth else None

        # ---- SORTING ----
        sort_by = params.get('sort_by')
        deck_sort_by = params.get('deck_sort_by')
        
        # Use deck_sort_by if it exists, otherwise use sort_by
        effective_sort = deck_sort_by or sort_by
        
        if effective_sort == 'growth_rate_desc':
            effective_sort = 'projected_return_desc'
        elif effective_sort == 'growth_rate_asc':
            effective_sort = 'projected_return_asc'
        
        # For sorts that don't depend on calculated fields, use database ordering
        if effective_sort == 'confidence_desc':
            confidence_order = Case(
                When(data_source_confidence='High', then=Value(3)),
                When(data_source_confidence='Medium', then=Value(2)),
                When(data_source_confidence='Low', then=Value(1)),
                default=Value(0),
                output_field=FloatField()
            )
            qs = qs.annotate(confidence_order=confidence_order).order_by('-confidence_order')
        elif effective_sort == 'company_name':
            qs = qs.order_by('company_name')
        elif effective_sort == 'funding_ask_desc':
            qs = qs.order_by('-funding_ask')
        elif effective_sort == 'funding_ask_asc':
            qs = qs.order_by('funding_ask')
        else:
            qs = qs.order_by('-created_at')
        
        # Store sort preference for post-serialization sorting
        self._sort_by = effective_sort

        return qs
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data
        
        # Only filters financial startups, excludes pitch decks
        if hasattr(self, '_risk_tolerance_filter') and self._risk_tolerance_filter:
            risk_tolerance = self._risk_tolerance_filter
            if risk_tolerance == 'Low':
                # Show only Low risk financial startups
                data = [item for item in data if item.get('risk_level') == 'Low']
            elif risk_tolerance == 'Medium':
                # Show only Medium risk financial startups
                data = [item for item in data if item.get('risk_level') == 'Medium']
            elif risk_tolerance == 'High':
                # Show only High risk financial startups
                data = [item for item in data if item.get('risk_level') == 'High']
        
        # Apply financial risk filter (slider 0-100) - post-serialization
        elif hasattr(self, '_risk_filter') and self._risk_filter is not None:
            risk_value = self._risk_filter
            if risk_value <= 33:
                # Conservative: Low risk only with minimum 5% growth (exclude pitch decks)
                data = [item for item in data 
                    if item.get('risk_level') == 'Low'
                    and item.get('estimated_growth_rate') is not None
                    and item.get('estimated_growth_rate') >= 5]
            elif risk_value <= 66:
                # Balanced: Low (5%+) and Medium (15%+) risk (exclude pitch decks)
                data = [item for item in data 
                    if (item.get('risk_level') == 'Low' 
                        and item.get('estimated_growth_rate') is not None
                        and item.get('estimated_growth_rate') >= 5)
                    or (item.get('risk_level') == 'Medium'
                        and item.get('estimated_growth_rate') is not None
                        and item.get('estimated_growth_rate') >= 15)]
            else:
                # Aggressive: show all risk levels with their respective minimums (exclude pitch decks)
                data = [item for item in data 
                    if (item.get('risk_level') == 'Low' 
                        and item.get('estimated_growth_rate') is not None
                        and item.get('estimated_growth_rate') >= 5)
                    or (item.get('risk_level') == 'Medium'
                        and item.get('estimated_growth_rate') is not None
                        and item.get('estimated_growth_rate') >= 15)
                    or (item.get('risk_level') == 'High'
                        and item.get('estimated_growth_rate') is not None
                        and item.get('estimated_growth_rate') >= 30)]
        
        if hasattr(self, '_min_growth_rate_filter') and self._min_growth_rate_filter is not None:
            data = [
                item for item in data
                if item.get('estimated_growth_rate') is not None
                and item.get('estimated_growth_rate') >= self._min_growth_rate_filter
            ]
        
        # Apply funding ask range filter for pitch decks
        if hasattr(self, '_funding_ask_range') and self._funding_ask_range:
            funding_range = self._funding_ask_range
            if funding_range == '0-100000':
                data = [item for item in data if item.get('funding_ask') and float(item['funding_ask']) <= 100000]
            elif funding_range == '100000-500000':
                data = [item for item in data if item.get('funding_ask') and 100000 < float(item['funding_ask']) <= 500000]
            elif funding_range == '500000-1000000':
                data = [item for item in data if item.get('funding_ask') and 500000 < float(item['funding_ask']) <= 1000000]
            elif funding_range == '1000000-5000000':
                data = [item for item in data if item.get('funding_ask') and 1000000 < float(item['funding_ask']) <= 5000000]
            elif funding_range == '5000000+':
                data = [item for item in data if item.get('funding_ask') and float(item['funding_ask']) > 5000000]
        
        # Apply market growth filter
        if hasattr(self, '_market_growth_filter') and self._market_growth_filter:
            growth_filter = self._market_growth_filter
            if growth_filter == 'Low':
                data = [item for item in data if item.get('market_growth_rate') and 0 <= float(item['market_growth_rate']) < 10]
            elif growth_filter == 'Medium':
                data = [item for item in data if item.get('market_growth_rate') and 10 <= float(item['market_growth_rate']) < 30]
            elif growth_filter == 'High':
                data = [item for item in data if item.get('market_growth_rate') and float(item['market_growth_rate']) >= 30]
        
        # Apply min market growth filter
        if hasattr(self, '_min_market_growth') and self._min_market_growth is not None:
            data = [
                item for item in data
                if item.get('market_growth_rate') is not None
                and float(item['market_growth_rate']) >= self._min_market_growth
            ]
        
        # Apply sorting that requires calculated fields
        sort_by = getattr(self, '_sort_by', None)
        if sort_by == 'projected_return_desc':
            data = sorted(data, key=lambda x: x.get('estimated_growth_rate') or -999999, reverse=True)
        elif sort_by == 'projected_return_asc':
            data = sorted(data, key=lambda x: x.get('estimated_growth_rate') or 999999)
        elif sort_by == 'reward_potential_desc':
            data = sorted(data, key=lambda x: x.get('reward_potential') or 0, reverse=True)
        elif sort_by == 'risk_asc':
            # Sort by financial risk (Low < Medium < High)
            # Pitch decks (None) go to the end
            risk_order = {'Low': 1, 'Medium': 2, 'High': 3, None: 4}
            data = sorted(data, key=lambda x: risk_order.get(x.get('risk_level'), 4))
        elif sort_by == 'market_growth_desc':
            data = sorted(data, key=lambda x: float(x.get('market_growth_rate') or -999999), reverse=True)
        elif sort_by == 'market_growth_asc':
            data = sorted(data, key=lambda x: float(x.get('market_growth_rate') or 999999))
        
        return Response(data)
    
class AIRecommendationsView(APIView):
    permission_classes = []
    
    def get(self, request):
        if request.user.is_authenticated:
            user_id = request.user.id
        else:
            user_id = int(request.query_params.get('user_id', 1))
        
        n_recommendations = int(request.query_params.get('n', 10))
        
        try:
            ml_service_url = "http://localhost:8001"
            response = requests.post(
                f"{ml_service_url}/api/recommendations",
                json={
                    "user_id": user_id,
                    "n_recommendations": n_recommendations,
                    "exclude_viewed": False # change for now to see all recom
                },
                timeout=5
            )
            
            if response.status_code == 200:
                ml_data = response.json()
                
                # DEBUG: Print what ML service returned
                print("=== ML SERVICE RESPONSE ===")
                print(f"ML Data: {ml_data}")
                print(f"Recommendations: {ml_data.get('recommendations', [])}")
                
                startup_ids = [rec['startup_id'] for rec in ml_data['recommendations']]
                print(f"Startup IDs to fetch: {startup_ids}")
                
                # Fetch full startup details from database
                startups = Startup.objects.filter(id__in=startup_ids)
                print(f"Found {len(startups)} startups in database")
                print(f"Startup IDs found: {[s.id for s in startups]}")
                
                # Preserve the order from ML recommendations
                startup_dict = {s.id: s for s in startups}
                ordered_startups = [startup_dict[sid] for sid in startup_ids if sid in startup_dict]
                
                serializer = StartupSerializer(
                    ordered_startups, 
                    many=True, 
                    context={'request': request}
                )
                
                return Response({
                    'recommendations': serializer.data,
                    'model_version': ml_data.get('model_version', 'v1.0'),
                    'ai_powered': True,
                    'count': len(serializer.data),
                    'user_id': user_id
                })
            else:
                # Fallback to popular startups
                return self._fallback_recommendations(request, n_recommendations)
                
        except requests.exceptions.RequestException as e:
            print(f"ML Service error: {e}")
            # Fallback to popular startups
            return self._fallback_recommendations(request, n_recommendations)
    
    def _fallback_recommendations(self, request, n=10):
        """Fallback to simple popularity-based recommendations"""
        from django.db.models import Count
        
        # Get most viewed startups
        popular_startups = Startup.objects.annotate(
            view_count=Count('startupview')
        ).order_by('-view_count')[:n]
        
        serializer = StartupSerializer(
            popular_startups, 
            many=True, 
            context={'request': request}
        )
        
        return Response({
            'recommendations': serializer.data,
            'ai_powered': False,
            'fallback': True,
            'count': len(serializer.data)
        })

    
class StartupDetailView(RetrieveAPIView):
    queryset = Startup.objects.all()
    serializer_class = StartupSerializer
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [AllowAny]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        record_startup_view(request.user, instance, request=request)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

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
            for startup in startups[:10]
        ]
        
        # Prepare decks data
        decks_data = [
            {
                'id': deck.id,
                'company_name': deck.company_name,
                'tagline': deck.tagline,
                'created_at': deck.created_at.isoformat()
            }
            for deck in decks[:10]
        ]
        
        # Get recent activity
        recent_activity = []
        
        for startup in startups[:5]:
            recent_activity.append({
                'type': 'startup',
                'description': f'Registered {startup.company_name}',
                'timestamp': startup.created_at.isoformat()
            })
        
        for deck in decks[:5]:
            recent_activity.append({
                'type': 'deck',
                'description': f'Created pitch deck for {deck.company_name}',
                'timestamp': deck.created_at.isoformat()
            })
        
        recent_views = StartupView.objects.filter(
            startup__owner=registered_user
        ).select_related('startup', 'user').order_by('-viewed_at')[:5]
        
        for view in recent_views:
            recent_activity.append({
                'type': 'view',
                'description': f'{view.user.email} viewed {view.startup.company_name}',
                'timestamp': view.viewed_at.isoformat()
            })
        
        recent_activity.sort(key=lambda x: x['timestamp'], reverse=True)
        recent_activity = recent_activity[:15]
        
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
            'recent_activity': recent_activity,
            'contact_email': registered_user.contact_email or '',
            'contact_phone': registered_user.contact_phone or '',
            'website_url': registered_user.website_url or '',
            'linkedin_url': registered_user.linkedin_url or '',
            'location': registered_user.location or '',
            'founder_name': registered_user.founder_name or '',
            'founder_title': registered_user.founder_title or '',
            'founder_linkedin': registered_user.founder_linkedin or '',
        })
    
class UpdateStartupProfileView(APIView):
    permission_classes = [IsAuthenticated]
    
    def put(self, request):
        user = request.user
        
        try:
            registered_user = RegisteredUser.objects.get(user=user)
            
            if registered_user.label != 'startup':
                return Response({
                    'error': 'This endpoint is only accessible to startup users.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Update user fields
            user.first_name = request.data.get('first_name', user.first_name)
            user.last_name = request.data.get('last_name', user.last_name)
            user.save()
            
            # Update RegisteredUser contact fields
            registered_user.contact_email = request.data.get('contact_email', registered_user.contact_email)
            registered_user.contact_phone = request.data.get('contact_phone', registered_user.contact_phone)
            registered_user.website_url = request.data.get('website_url', registered_user.website_url)
            registered_user.linkedin_url = request.data.get('linkedin_url', registered_user.linkedin_url)
            registered_user.location = request.data.get('location', registered_user.location)
            registered_user.founder_name = request.data.get('founder_name', registered_user.founder_name)
            registered_user.founder_title = request.data.get('founder_title', registered_user.founder_title)
            registered_user.founder_linkedin = request.data.get('founder_linkedin', registered_user.founder_linkedin)
            registered_user.save()
            
            return Response({
                'success': True,
                'message': 'Profile updated successfully'
            }, status=status.HTTP_200_OK)
            
        except RegisteredUser.DoesNotExist:
            return Response({
                'error': 'User profile not found.'
            }, status=status.HTTP_404_NOT_FOUND)
    
class StartupProfileView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, startup_id):
        try:
            startup = Startup.objects.select_related(
                'owner__user', 
                'source_deck__problem',
                'source_deck__solution', 
                'source_deck__market_analysis',
                'source_deck__ask'
            ).prefetch_related(
                'source_deck__team_members',
                'source_deck__financials'
            ).get(pk=startup_id)
        except Startup.DoesNotExist:
            return Response({'detail': 'Startup not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Track view if user is authenticated
        if request.user.is_authenticated and startup.owner and request.user != startup.owner.user:
            try:
                ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR')
                StartupView.objects.create(user=request.user, startup=startup, ip_address=ip_address)
            except Exception as e:
                print(f"Error tracking view: {e}")

        serializer = StartupSerializer(startup, context={'request': request})
        data = serializer.data
        
        # If this is a deck-builder startup, add deck details
        if startup.source_deck:
            deck = startup.source_deck
            data['report_type'] = 'deck'
            data['deck_info'] = {
                'company_name': deck.company_name,
                'tagline': deck.tagline
            }
            
            # Problem section
            try:
                data['problem'] = {
                    'description': deck.problem.description
                }
            except Exception:
                data['problem'] = None
            
            # Solution section
            try:
                data['solution'] = {
                    'description': deck.solution.description
                }
            except Exception:
                data['solution'] = None
            
            # Market Analysis section
            try:
                data['market_analysis'] = {
                    'primary_market': deck.market_analysis.primary_market,
                    'target_audience': deck.market_analysis.target_audience,
                    'market_growth_rate': float(deck.market_analysis.market_growth_rate),
                    'competitive_advantage': deck.market_analysis.competitive_advantage
                }
            except Exception:
                data['market_analysis'] = None
            
            # Funding Ask section
            try:
                data['ask'] = {
                    'amount': float(deck.ask.amount),
                    'usage_description': deck.ask.usage_description
                }
            except Exception:
                data['ask'] = None
            
            # Team Members
            data['team_members'] = [
                {'name': member.name, 'title': member.title} 
                for member in deck.team_members.all()
            ]
            
            # Financial Projections
            financials_list = []
            for f in deck.financials.all():
                financial_data = {
                    'valuation_multiple': float(f.valuation_multiple) if f.valuation_multiple else None,
                    'current_valuation': float(f.current_valuation) if f.current_valuation else None,
                    'projected_revenue_final_year': float(f.projected_revenue_final_year) if f.projected_revenue_final_year else None,
                    'years_to_projection': f.years_to_projection if f.years_to_projection else None
                }
                financials_list.append(financial_data)
            
            data['financials'] = financials_list
        else:
            data['report_type'] = 'regular'
        
        return Response(data, status=status.HTTP_200_OK)

class FinancialProjectionListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, startup_id):
        try:
            startup = Startup.objects.select_related("source_deck").get(pk=startup_id)
        except Startup.DoesNotExist:
            return Response([], status=status.HTTP_200_OK)

        if not startup.source_deck:
            return Response([], status=status.HTTP_200_OK)

        financials = FinancialProjection.objects.filter(deck=startup.source_deck).order_by('year')
        serializer = FinancialProjectionSerializer(financials, many=True)
        return Response(serializer.data)
    
class RecordStartupComparisonAPI(APIView):
    """API endpoint to record when a user compares startups"""
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    
    def post(self, request):
        # Get startup IDs from request
        startup_ids = request.data.get('startup_ids', [])
        
        if not startup_ids or not isinstance(startup_ids, list):
            return Response(
                {'detail': 'startup_ids must be a non-empty list'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(startup_ids) < 2:
            return Response(
                {'detail': 'At least 2 startups required for comparison'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Fetch startups
        startups = []
        for startup_id in startup_ids:
            try:
                startup = Startup.objects.get(pk=startup_id)
                startups.append(startup)
            except Startup.DoesNotExist:
                return Response(
                    {'detail': f'Startup with id {startup_id} not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Record the comparison
        record_result = record_startup_comparison(request.user, startups, request=request)
        
        # Determine response details based on record status
        status_map = {
            'recorded': (
                f'Comparison of {len(startups)} startups recorded successfully',
                status.HTTP_201_CREATED,
                record_result['comparisons'][0].compared_at if record_result['comparisons'] else timezone.now()
            ),
            'duplicate': (
                'Comparison already recorded recently',
                status.HTTP_200_OK,
                record_result['comparisons'][0].compared_at if record_result['comparisons'] else timezone.now()
            ),
            'insufficient_startups': (
                'At least 2 startups required for comparison',
                status.HTTP_400_BAD_REQUEST,
                timezone.now()
            ),
            'unauthenticated': (
                'Authentication required',
                status.HTTP_401_UNAUTHORIZED,
                timezone.now()
            ),
            'error': (
                'Failed to record comparison',
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                timezone.now()
            ),
        }
        
        message, response_status, compared_at = status_map.get(
            record_result['status'],
            ('Comparison status unknown', status.HTTP_400_BAD_REQUEST, timezone.now())
        )
        
        # Get analytics for each startup
        total_comparisons = {}
        unique_comparers = {}
        
        for startup in startups:
            total_comparisons[startup.id] = StartupComparison.objects.filter(startup=startup).count()
            unique_comparers[startup.id] = (
                StartupComparison.objects
                .filter(startup=startup)
                .values('user')
                .distinct()
                .count()
            )
        
        response_data = {
            'message': message,
            'startup_ids': [s.id for s in startups],
            'comparison_set_id': record_result.get('comparison_set_id', ''),
            'total_comparisons': total_comparisons,
            'unique_comparers': unique_comparers,
            'compared_at': compared_at
        }
        
        serializer = RecordComparisonResponseSerializer(data=response_data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=response_status)
    
def record_startup_comparison(user, startups, request=None, dedupe_minutes=5):
    """
    Utility to record a startup comparison with optional deduplication.
    
    Args:
        user: The user performing the comparison
        startups: List of Startup objects being compared
        request: The HTTP request object (optional, for IP tracking)
        dedupe_minutes: Minutes to check for duplicate comparisons
    
    Returns:
        dict with 'status', 'comparison_set_id', and 'comparisons'
    """
    if not user or not getattr(user, 'is_authenticated', False):
        return {'status': 'unauthenticated', 'comparison_set_id': None, 'comparisons': []}
    
    if not startups or len(startups) < 2:
        return {'status': 'insufficient_startups', 'comparison_set_id': None, 'comparisons': []}
    
    # Generate a unique comparison set ID
    comparison_set_id = str(uuid.uuid4())
    
    # Sort startup IDs for consistent comparison
    sorted_startup_ids = sorted([s.id for s in startups])
    
    # Check for duplicate comparisons (same set of startups within time window)
    cutoff = timezone.now() - timedelta(minutes=dedupe_minutes)
    
    # Find recent comparisons by this user
    recent_comparisons = (
        StartupComparison.objects
        .filter(user=user, compared_at__gte=cutoff)
        .values_list('comparison_set_id', flat=True)
        .distinct()
    )
    
    # Check if any recent comparison set matches the current startup set
    for recent_set_id in recent_comparisons:
        if recent_set_id:
            recent_startup_ids = sorted(
                StartupComparison.objects
                .filter(comparison_set_id=recent_set_id)
                .values_list('startup_id', flat=True)
            )
            if recent_startup_ids == sorted_startup_ids:
                # Found a duplicate comparison
                existing_comparisons = StartupComparison.objects.filter(
                    comparison_set_id=recent_set_id
                ).order_by('compared_at')
                return {
                    'status': 'duplicate',
                    'comparison_set_id': recent_set_id,
                    'comparisons': list(existing_comparisons)
                }
    
    # Create new comparison records
    comparisons = []
    try:
        for startup in startups:
            comparison = StartupComparison.objects.create(
                user=user,
                startup=startup,
                comparison_set_id=comparison_set_id
            )
            comparisons.append(comparison)
    except Exception as exc:
        print(f"Error recording startup comparison: {exc}")
        return {'status': 'error', 'comparison_set_id': None, 'comparisons': []}
    
    return {
        'status': 'recorded',
        'comparison_set_id': comparison_set_id,
        'comparisons': comparisons
    }

class RecordStartupViewAPI(APIView):
    """API endpoint to record when a user views a startup profile"""
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication, SessionAuthentication]

    def post(self, request, startup_id):
        # Get startup or return 404
        startup = get_object_or_404(Startup, pk=startup_id)

        record_result = record_startup_view(request.user, startup, request=request)

        # Determine response details based on record status
        status_map = {
            'recorded': (
                'View recorded successfully',
                status.HTTP_201_CREATED,
                record_result['view'].viewed_at if record_result['view'] else timezone.now()
            ),
            'duplicate': (
                'View already recorded recently',
                status.HTTP_200_OK,
                record_result['view'].viewed_at if record_result['view'] else timezone.now()
            ),
            'owner_skipped': (
                'View not recorded (own startup)',
                status.HTTP_200_OK,
                timezone.now()
            ),
            'unauthenticated': (
                'Authentication required',
                status.HTTP_401_UNAUTHORIZED,
                timezone.now()
            ),
            'error': (
                'Failed to record view',
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                timezone.now()
            ),
        }

        message, response_status, viewed_at = status_map.get(
            record_result['status'],
            ('View status unknown', status.HTTP_400_BAD_REQUEST, timezone.now())
        )

        total_views = StartupView.objects.filter(startup=startup).count()
        unique_viewers = StartupView.objects.filter(startup=startup).values('user').distinct().count()

        response_data = {
            'message': message,
            'startup_id': startup_id,
            'company_name': startup.company_name,
            'total_views': total_views,
            'unique_viewers': unique_viewers,
            'viewed_at': viewed_at
        }

        serializer = RecordViewResponseSerializer(data=response_data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=response_status)


class RecordStartupComparisonAPI(APIView):
    """API endpoint to record when a user compares startups"""
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication, SessionAuthentication]

    def post(self, request, *args, **kwargs):
        """
        Record a startup comparison and update analytics.
        
        Request body:
            {
                "startup_ids": [1, 2, 3]  // List of startup IDs being compared
            }
        
        Returns:
            {
                "message": "Comparison recorded successfully",
                "startup_ids": [1, 2, 3],
                "comparison_set_id": "uuid-string",
                "total_comparisons": {"1": 5, "2": 3, "3": 7},
                "unique_comparers": {"1": 3, "2": 2, "3": 4},
                "compared_at": "2025-12-08T10:30:00Z"
            }
        """
        try:
            # Get startup IDs from request
            startup_ids = request.data.get('startup_ids', [])

            # Validate input
            if not startup_ids or not isinstance(startup_ids, list):
                return Response(
                    {
                        'error': 'Invalid request',
                        'detail': 'startup_ids must be a non-empty list'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            if len(startup_ids) < 2:
                return Response(
                    {
                        'error': 'Insufficient startups',
                        'detail': 'At least 2 startups required for comparison'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Fetch startups and validate they exist
            startups = []
            for startup_id in startup_ids:
                try:
                    startup = Startup.objects.get(pk=startup_id)
                    startups.append(startup)
                except Startup.DoesNotExist:
                    return Response(
                        {
                            'error': 'Startup not found',
                            'detail': f'Startup with id {startup_id} does not exist'
                        },
                        status=status.HTTP_404_NOT_FOUND
                    )
                except (ValueError, TypeError):
                    return Response(
                        {
                            'error': 'Invalid startup ID',
                            'detail': f'Invalid startup ID: {startup_id}'
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # Record the comparison
            record_result = record_startup_comparison(request.user, startups, request=request)

            # Determine response details based on record status
            if record_result['status'] == 'recorded':
                message = f'Comparison of {len(startups)} startups recorded successfully'
                response_status = status.HTTP_201_CREATED
                compared_at = record_result['comparisons'][0].compared_at if record_result['comparisons'] else timezone.now()
            elif record_result['status'] == 'duplicate':
                message = 'Comparison already recorded recently'
                response_status = status.HTTP_200_OK
                compared_at = record_result['comparisons'][0].compared_at if record_result['comparisons'] else timezone.now()
            elif record_result['status'] == 'insufficient_startups':
                return Response(
                    {
                        'error': 'Insufficient startups',
                        'detail': 'At least 2 startups required for comparison'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            elif record_result['status'] == 'unauthenticated':
                return Response(
                    {
                        'error': 'Authentication required',
                        'detail': 'You must be authenticated to record comparisons'
                    },
                    status=status.HTTP_401_UNAUTHORIZED
                )
            elif record_result['status'] == 'error':
                return Response(
                    {
                        'error': 'Server error',
                        'detail': 'Failed to record comparison. Please try again.'
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            else:
                return Response(
                    {
                        'error': 'Unknown status',
                        'detail': 'Comparison status unknown'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get updated analytics for each startup
            total_comparisons = {}
            unique_comparers = {}

            for startup in startups:
                total_comparisons[str(startup.id)] = StartupComparison.objects.filter(startup=startup).count()
                unique_comparers[str(startup.id)] = (
                    StartupComparison.objects
                    .filter(startup=startup)
                    .values('user')
                    .distinct()
                    .count()
                )

            # Prepare response data
            response_data = {
                'message': message,
                'startup_ids': [s.id for s in startups],
                'comparison_set_id': str(record_result.get('comparison_set_id', '')),
                'total_comparisons': total_comparisons,
                'unique_comparers': unique_comparers,
                'compared_at': compared_at
            }

            # Validate response with serializer
            serializer = RecordComparisonResponseSerializer(data=response_data)
            serializer.is_valid(raise_exception=True)

            return Response(serializer.data, status=response_status)

        except Exception as e:
            # Log the error for debugging
            print(f"Error in RecordStartupComparisonAPI: {str(e)}")
            import traceback
            traceback.print_exc()

            return Response(
                {
                    'error': 'Server error',
                    'detail': 'An unexpected error occurred while recording the comparison'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
def record_startup_view(user, startup, request=None, dedupe_minutes=5, allow_owner=False):
    """Utility to record a startup view with optional deduplication."""
    if not user or not getattr(user, 'is_authenticated', False):
        return {'status': 'unauthenticated', 'view': None}

    is_owner = bool(startup.owner and startup.owner.user == user)
    if is_owner and not allow_owner:
        return {'status': 'owner_skipped', 'view': None}

    cutoff = timezone.now() - timedelta(minutes=dedupe_minutes)
    existing = (
        StartupView.objects
        .filter(user=user, startup=startup, viewed_at__gte=cutoff)
        .order_by('-viewed_at')
        .first()
    )

    if existing:
        return {'status': 'duplicate', 'view': existing}

    ip_address = None
    if request is not None:
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
        if forwarded:
            ip_address = forwarded.split(',')[0].strip()
        elif request.META.get('REMOTE_ADDR'):
            ip_address = request.META.get('REMOTE_ADDR')

    try:
        view_record = StartupView.objects.create(
            user=user,
            startup=startup,
            ip_address=ip_address
        )
    except Exception as exc:
        print(f"Error recording startup view for startup {startup.id}: {exc}")
        return {'status': 'error', 'view': None}

    return {'status': 'recorded', 'view': view_record}


def record_startup_comparison(user, startups, request=None, dedupe_minutes=5):
    """
    Utility to record a startup comparison with optional deduplication.
    
    Args:
        user: The user performing the comparison
        startups: List of Startup objects being compared
        request: The HTTP request object (optional, for IP tracking)
        dedupe_minutes: Minutes to check for duplicate comparisons
    
    Returns:
        dict with 'status', 'comparison_set_id', and 'comparisons'
    """
    if not user or not getattr(user, 'is_authenticated', False):
        return {'status': 'unauthenticated', 'comparison_set_id': None, 'comparisons': []}

    if not startups or len(startups) < 2:
        return {'status': 'insufficient_startups', 'comparison_set_id': None, 'comparisons': []}

    # Generate a unique comparison set ID
    comparison_set_id = str(uuid.uuid4())

    # Sort startup IDs for consistent comparison
    sorted_startup_ids = sorted([s.id for s in startups])

    # Check for duplicate comparisons (same set of startups within time window)
    cutoff = timezone.now() - timedelta(minutes=dedupe_minutes)

    # Find recent comparisons by this user
    recent_comparisons = (
        StartupComparison.objects
        .filter(user=user, compared_at__gte=cutoff)
        .values_list('comparison_set_id', flat=True)
        .distinct()
    )

    # Check if any recent comparison set matches the current startup set
    for recent_set_id in recent_comparisons:
        if recent_set_id:
            recent_startup_ids = sorted(
                StartupComparison.objects
                .filter(comparison_set_id=recent_set_id)
                .values_list('startup_id', flat=True)
            )
            if recent_startup_ids == sorted_startup_ids:
                # Found a duplicate comparison
                existing_comparisons = StartupComparison.objects.filter(
                    comparison_set_id=recent_set_id
                ).order_by('compared_at')
                return {
                    'status': 'duplicate',
                    'comparison_set_id': recent_set_id,
                    'comparisons': list(existing_comparisons)
                }

    # Create new comparison records
    comparisons = []
    try:
        for startup in startups:
            comparison = StartupComparison.objects.create(
                user=user,
                startup=startup,
                comparison_set_id=comparison_set_id
            )
            comparisons.append(comparison)
    except Exception as exc:
        print(f"Error recording startup comparison: {exc}")
        return {'status': 'error', 'comparison_set_id': None, 'comparisons': []}

    return {
        'status': 'recorded',
        'comparison_set_id': comparison_set_id,
        'comparisons': comparisons
    }

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
    def post(self, request, startup_id):
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

def get_risk_level(self, obj):
    """
    Uses Altman Z-Score Formula for Private Companies (Z')
    Maps to 3 risk categories: Low, Medium, High
    
    Z' = 0.717 x (Working Capital / Total Assets) 
         + 0.847 x (Retained Earnings / Total Assets) 
         + 3.107 x (EBIT / Total Assets) 
         + 0.420 x (Book Value of Equity / Total Liabilities) 
         + 0.998 x (Sales / Total Assets)
    
    Risk Mapping:
    - Z' > 2.9: Low Risk (Excellent/Good)
    - Z' 1.8-2.9: Medium Risk (Average)
    - Z' < 1.8: High Risk (Risky/Very Risky)
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
        
        # Map to Low/Medium/High categories
        if z_prime > 2.9:
            return 'Low'
        elif z_prime > 1.8:
            return 'Medium'
        else:
            return 'High'
            
    except Exception as e:
        print(f"Risk calculation error: {e}")
        return None

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
        if startup.owner and user != startup.owner.user:
            ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR')
            StartupView.objects.create(user=user, startup=startup, ip_address=ip_address)

        is_in_watchlist = Watchlist.objects.filter(user=user, startup=startup).exists()

        # Use serializer for the startup
        serializer = StartupSerializer(startup, context={'request': request})
        startup_data = serializer.data
        startup_data['is_in_watchlist'] = is_in_watchlist
        
        # If this is a deck-builder startup, add deck details
        if startup.source_deck:
            deck = startup.source_deck
            startup_data['report_type'] = 'deck'
            startup_data['deck_info'] = {
                'company_name': deck.company_name,
                'tagline': deck.tagline
            }
            startup_data['problem'] = {
                'description': deck.problem.description
            } if hasattr(deck, 'problem') else None
            startup_data['solution'] = {
                'description': deck.solution.description
            } if hasattr(deck, 'solution') else None
            startup_data['market_analysis'] = {
                'primary_market': deck.market_analysis.primary_market,
                'target_audience': deck.market_analysis.target_audience,
                'market_growth_rate': float(deck.market_analysis.market_growth_rate),
                'competitive_advantage': deck.market_analysis.competitive_advantage
            } if hasattr(deck, 'market_analysis') else None
            startup_data['ask'] = {
                'amount': float(deck.ask.amount),
                'usage_description': deck.ask.usage_description
            } if hasattr(deck, 'ask') else None
            startup_data['team_members'] = [
                {'name': member.name, 'title': member.title} 
                for member in deck.team_members.all()
            ]
            startup_data['financials'] = [
                {
                    'current_valuation': float(f.current_valuation) if f.current_valuation else 0,
                    'projected_revenue_final_year': float(f.projected_revenue_final_year) if f.projected_revenue_final_year else 0,
                    'valuation_multiple': float(f.valuation_multiple) if f.valuation_multiple else 0,
                    'years_to_projection': int(f.years_to_projection) if f.years_to_projection else 0
                }
                for f in deck.financials.all()
            ]

        return Response(startup_data, status=status.HTTP_200_OK)

class compare_startups(APIView):
    def get(self, request):
        user = request.user
        if not user.is_authenticated:
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

        startups = Startup.objects.select_related('owner__user', 'source_deck').filter(
            source_deck__isnull=True, 
            is_deck_builder=False
        )
        
        serializer = StartupSerializer(startups, many=True, context={'request': request})
        startup_data = serializer.data

        investor_view_data = []
        for item in startup_data:
            investor_view_data.append({
                "id": item.get("id"),
                "company_name": item.get("company_name"),
                "industry": item.get("industry"),
                "company_description": item.get("company_description"),
                "risk_level": item.get("risk_level"),
                "risk_score": item.get("risk_score"),
                "reward_potential": item.get("reward_potential"),
                "projected_return": item.get("projected_return"),
                "estimated_growth_rate": item.get("estimated_growth_rate"),
            })

        return Response({"startups": investor_view_data}, status=status.HTTP_200_OK)

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

        # Fetch startups
        startups = []
        for sid in startup_ids:
            try:
                startup = Startup.objects.get(id=sid)
                startups.append(startup)
            except Startup.DoesNotExist:
                continue

        if len(startups) < 2:
            return Response({'error': 'Insufficient startups for comparison'}, status=400)

        # Create comparison session for tracking
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

        # Use serializer to get all calculated metrics
        serializer = StartupSerializer(startups, many=True, context={'request': request})
        startup_data = serializer.data

        # Add risk color for frontend display
        for item in startup_data:
            risk_level = item.get('risk_level')
            if risk_level == 'Low':
                item['risk_color'] = 'bg-green-100 text-green-800'
            elif risk_level == 'Medium':
                item['risk_color'] = 'bg-yellow-100 text-yellow-800'
            elif risk_level == 'High':
                item['risk_color'] = 'bg-red-100 text-red-800'
            else:
                item['risk_color'] = 'bg-gray-100 text-gray-800'

        return Response({
            "startups": startup_data,
            "startup_count": len(startups),
            "comparison_set_id": comparison_set.id
        }, status=200)

# Analytics helper functions
def get_startup_analytics(startup):
    """Get view and comparison analytics for a startup"""
    from datetime import timedelta
    
    total_views = StartupView.objects.filter(startup=startup).count()
    unique_viewers = StartupView.objects.filter(startup=startup).values('user').distinct().count()
    
    # Get comparisons via ComparisonSet relationship (use startup_id if available)
    total_comparisons = StartupComparison.objects.filter(startup=startup).count()
    unique_comparers = StartupComparison.objects.filter(startup=startup).values('user').distinct().count()
    
    # Get watchlist count
    watchlist_count = Watchlist.objects.filter(startup=startup).count()
    
    # Get recent activity (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    
    recent_views = StartupView.objects.filter(
        startup=startup,
        viewed_at__gte=thirty_days_ago
    ).count()
    
    recent_comparisons = StartupComparison.objects.filter(
        startup=startup,
        compared_at__gte=thirty_days_ago
    ).count()
    
    recent_watchlist = Watchlist.objects.filter(
        startup=startup,
        added_at__gte=thirty_days_ago
    ).count()
    
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

def get_risk_color(confidence):
    """Helper function to get risk color class"""
    if confidence == 'High':
        return 'bg-green-100 text-green-800'
    elif confidence == 'Medium':
        return 'bg-yellow-100 text-yellow-800'
    else:
        return 'bg-red-100 text-red-800'

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
        projected_return = None
        risk_level = None

        if startup_id:
            selected_startup = get_object_or_404(Startup, id=startup_id)
            
            serializer = StartupSerializer(selected_startup, context={'request': request})
            startup_data = serializer.data
            
            is_pitch_deck = startup_data.get('is_deck_builder', False)

            # Select correct IRR field based on startup type
            if is_pitch_deck:
                # Pitch Deck IRR: (Future Val / Current Val)^(1/years) - 1
                # Where Future Val = Projected Revenue × Industry Multiple
                projected_return = startup_data.get('pitch_deck_projected_return')
                calculation_source = "pitch_deck_projected_return (IRR from revenue projections)"
            else:
                # Normal Startup IRR: (Expected Future Val / Current Val)^(1/years) - 1
                # Uses explicit valuation fields
                projected_return = startup_data.get('projected_return')
                calculation_source = "projected_return (IRR from valuations)"

            risk_level = startup_data.get('risk_level')

            if projected_return is None:
                error_detail = (
                    "This pitch deck does not have complete financial projections. "
                    "Required: projected_revenue_final_year, valuation_multiple, current_valuation, years_to_projection"
                    if is_pitch_deck else
                    "This startup does not have complete valuation data. "
                    "Required: current_valuation, expected_future_valuation, years_to_future_valuation"
                )
                return Response({
                    "error": "Insufficient financial data to run simulation",
                    "detail": error_detail,
                    "missing": {
                        "is_pitch_deck": is_pitch_deck,
                        "has_projected_return": False,
                        "has_risk_level": risk_level is not None
                    }
                }, status=400)
        else:
            return Response({
                "error": "No startup selected",
                "detail": "Please select a startup to run investment simulation"
            }, status=400)

        # Risk Multiplier: ONLY applied to normal startups
        # High = 0.50, Medium = 0.75, Low = 1.00
        risk_multipliers = {
            'Low': 1.00,
            'Medium': 0.75,
            'High': 0.50
        }
        
        # Apply risk adjustment based on startup type
        if is_pitch_deck:
            risk_multiplier = 1.00
            risk_adjusted_return_percent = projected_return
            risk_adjustment_applied = False
        else:
            # Normal startups: Apply risk adjustment based on Altman Z-Score
            risk_multiplier = risk_multipliers.get(risk_level, 0.75) if risk_level else 0.75
            risk_adjusted_return_percent = projected_return * risk_multiplier
            risk_adjustment_applied = True
        
        # Convert percentage to decimal
        growth_rate = risk_adjusted_return_percent / 100  
        
        # Investment Simulation Formula:
        # Pitch Deck: FV = Investment × (1 + IRR)^Years
        # Normal Startup: FV = Investment × (1 + RiskAdjustedIRR)^Years
        final_value = investment_amount * math.pow(1 + growth_rate, duration_years)
        total_gain = final_value - investment_amount
        roi_percentage = (total_gain / investment_amount) * 100

        # Yearly breakdown
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

        # Chart data
        chart_data = [{"year": 0, "value": round(investment_amount, 2)}]
        temp_value = investment_amount
        for year in range(1, duration_years + 1):
            temp_value *= (1 + growth_rate)
            chart_data.append({"year": year, "value": round(temp_value, 2)})

        # Risk color mapping
        risk_colors = {
            "Low": "bg-green-100 text-green-800",
            "Medium": "bg-yellow-100 text-yellow-800",
            "High": "bg-red-100 text-red-800",
        }
        risk_color = risk_colors.get(risk_level, "bg-gray-100 text-gray-800") if risk_level else "bg-gray-100 text-gray-800"

        response_data = {
            "simulation_run": True,
            "is_pitch_deck": is_pitch_deck,
            "investment_amount": round(investment_amount, 2),
            "duration_years": duration_years,
            "base_projected_return": round(projected_return, 2),
            "risk_multiplier": risk_multiplier,
            "risk_adjusted_return": round(risk_adjusted_return_percent, 2),
            "risk_adjustment_applied": risk_adjustment_applied,
            "final_value": round(final_value, 2),
            "total_gain": round(total_gain, 2),
            "roi_percentage": round(roi_percentage, 2),
            "yearly_breakdown": yearly_breakdown,
            "chart_data": chart_data,
            "risk_level": risk_level if not is_pitch_deck else "N/A (Pitch Deck)",
            "risk_color": risk_color,
            "calculation_method": "IRR with Risk Adjustment" if risk_adjustment_applied else "IRR (No Risk Adjustment)",
            "calculation_source": calculation_source
        }

        response_data["startup"] = {
            "id": selected_startup.id,
            "name": selected_startup.company_name,
            "industry": selected_startup.industry,
            "base_return": projected_return,
            "adjusted_return": risk_adjusted_return_percent,
            "risk_level": risk_level,
        }

        return Response(response_data, status=200)


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
        user = request.user
        
        try:
            registered_user = RegisteredUser.objects.get(user=user)
            
            if registered_user.label != 'startup':
                return Response({
                    'error': 'Only startup users can submit company information.'
                }, status=status.HTTP_403_FORBIDDEN)
        except RegisteredUser.DoesNotExist:
            return Response({
                'error': 'User profile not found.'
            }, status=status.HTTP_404_NOT_FOUND)

        data = request.data

        # Helper function to safely parse numeric values
        def parse_numeric(value):
            if value is None or value == '':
                return None
            try:
                return float(value)
            except (ValueError, TypeError):
                return None

        # Validate required fields
        if not data.get('company_name') or not data.get('industry'):
            return Response({
                'success': False,
                'error': 'Company name and industry are required fields.',
                'errors': {
                    'company_name': ['This field is required.'] if not data.get('company_name') else [],
                    'industry': ['This field is required.'] if not data.get('industry') else []
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        # Create the startup with financial data
        startup = Startup.objects.create(
            owner=registered_user,
            company_name=data.get('company_name', '').strip(),
            industry=data.get('industry', '').strip(),
            company_description=data.get('company_description', '').strip(),
            
            # Financial Data
            time_between_periods=parse_numeric(data.get('time_between_periods')),
            previous_revenue=parse_numeric(data.get('previous_revenue')),
            current_revenue=parse_numeric(data.get('current_revenue')),
            revenue=parse_numeric(data.get('current_revenue')),
            net_income=parse_numeric(data.get('net_income')),
            ebit=parse_numeric(data.get('ebit')),
            total_assets=parse_numeric(data.get('total_assets')),
            current_assets=parse_numeric(data.get('current_assets')),
            total_liabilities=parse_numeric(data.get('total_liabilities')),
            current_liabilities=parse_numeric(data.get('current_liabilities')),
            retained_earnings=parse_numeric(data.get('retained_earnings')),
            shareholder_equity=parse_numeric(data.get('shareholder_equity')),
            cash_flow=parse_numeric(data.get('cash_flow')),
            current_valuation=parse_numeric(data.get('current_valuation')),
            expected_future_valuation=parse_numeric(data.get('expected_future_valuation')),
            years_to_future_valuation=parse_numeric(data.get('years_to_future_valuation')),
            
            # Qualitative Data
            team_strength=data.get('team_strength', '').strip(),
            market_position=data.get('market_position', '').strip(),
            brand_reputation=data.get('brand_reputation', '').strip(),
            
            # Inherit contact and founder info from user profile
            contact_email=registered_user.contact_email,
            contact_phone=registered_user.contact_phone,
            website_url=registered_user.website_url,
            linkedin_url=registered_user.linkedin_url,
            location=registered_user.location,
            founder_name=registered_user.founder_name,
            founder_title=registered_user.founder_title,
            founder_linkedin=registered_user.founder_linkedin,
            
            # Year founded
            year_founded=parse_numeric(data.get('year_founded')),
            
            # Confidence Metrics
            data_source_confidence=data.get('data_source_confidence', 'Medium').strip(),
            confidence_percentage=int(parse_numeric(data.get('confidence_percentage')) or 50),
        )

        return Response({
            'success': True,
            'message': 'Company information saved successfully.',
            'startup_id': startup.id,
            'company_name': startup.company_name
        }, status=status.HTTP_201_CREATED)

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

    # Prepare data for serializer
    startup_data = request.data.copy()
    
    # Create serializer instance with the data
    serializer = StartupSerializer(data=startup_data, context={'request': request})
    
    if serializer.is_valid():
        try:
            # Save the startup with the owner (passed as kwarg, not in data)
            startup = serializer.save(owner=registered_user)
            
            return Response({
                'success': True,
                'message': 'Startup added successfully!',
                'startup_id': startup.id,
                'data': StartupSerializer(startup, context={'request': request}).data
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            # Log the actual error for debugging
            import traceback
            print(f"Error saving startup: {e}")
            traceback.print_exc()
            
            return Response({
                'success': False,
                'error': f'Failed to save startup: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
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

        record_startup_view(
            request.user,
            startup,
            request=request,
            allow_owner=True
        )

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
                brand_reputation=funding_ask_text,
                is_deck_builder=True,
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
        
class save_pitch_deck_financials(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        deck_id = request.data.get('deck_id')
        current_valuation = request.data.get('current_valuation')
        industry_multiple = request.data.get('industry_multiple')
        years_to_projection = request.data.get('years_to_projection')
        projected_revenue = request.data.get('projected_revenue')

        if not deck_id:
            return Response({'error': 'deck_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            startup_user_id = request.session.get('startup_user_id')
            user = RegisteredUser.objects.get(id=startup_user_id)
            deck = get_object_or_404(Deck, id=deck_id, owner=user)

            # Save to market_analysis for valuation multiple
            market_analysis, created = MarketAnalysis.objects.get_or_create(deck=deck)
            market_analysis.valuation_multiple = industry_multiple
            market_analysis.save()

            # Create or update the financial projection record for the final year
            FinancialProjection.objects.update_or_create(
                deck=deck,
                year=years_to_projection,
                defaults={
                    'revenue': projected_revenue,
                    'profit': None  # Can be calculated later if needed
                }
            )

            # Also update the FundingAsk with current valuation
            FundingAsk.objects.update_or_create(
                deck=deck,
                defaults={'amount': current_valuation}
            )

            return Response({
                'success': True,
                'message': 'Financial projections saved successfully'
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
        
        # Get IRR calculation fields
        current_valuation = request.data.get('current_valuation')
        industry_multiple = request.data.get('industry_valuation_multiple')
        years_to_projection = request.data.get('years_to_projection')
        projected_revenue = request.data.get('projected_revenue')

        if not deck_id:
            return Response({'error': 'Missing deck_id.'}, status=status.HTTP_400_BAD_REQUEST)

        # Validate required fields
        if not all([current_valuation, industry_multiple, years_to_projection, projected_revenue]):
            return Response({
                'error': 'Missing required fields: current_valuation, industry_valuation_multiple, years_to_projection, projected_revenue'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            deck = Deck.objects.get(id=deck_id, owner=owner)

            # Clear existing financials
            deck.financials.all().delete()
            
            # Create the financial projection with all the IRR fields
            financial_projection = FinancialProjection.objects.create(
                deck=deck,
                current_valuation=float(current_valuation),
                valuation_multiple=float(industry_multiple),
                projected_revenue_final_year=float(projected_revenue),
                years_to_projection=int(years_to_projection)
            )

            return Response({
                'success': True,
                'message': 'Financial projections saved successfully.',
                'deck_id': deck.id,
                'financial_projection': FinancialProjectionSerializer(financial_projection).data
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
            
            # Return financial projection data with IRR fields
            financial = deck.financials.first()
            if financial:
                return Response({
                    'current_valuation': financial.current_valuation,
                    'valuation_multiple': financial.valuation_multiple,
                    'projected_revenue_final_year': financial.projected_revenue_final_year,
                    'years_to_projection': financial.years_to_projection
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'current_valuation': None,
                    'valuation_multiple': None,
                    'projected_revenue_final_year': None,
                    'years_to_projection': None
                }, status=status.HTTP_200_OK)

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

            if not Startup.objects.filter(source_deck=deck).exists():
                market = getattr(deck, 'market_analysis', None)
                Startup.objects.create(
                    owner=owner,
                    company_name=deck.company_name,
                    industry='—',
                    company_description=deck.tagline or '',
                    data_source_confidence='Medium',
                    confidence_percentage=50,
                    funding_ask=serializer.instance.amount,
                    source_deck=deck,
                    is_deck_builder=True,
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
