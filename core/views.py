from django.utils import timezone 
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, Http404
from django.template.loader import render_to_string
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password, check_password
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
from django.forms import ValidationError, inlineformset_factory
from django.db import transaction
import uuid

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
# def index(request):
#     startup_user_id = request.session.get('startup_user_id')
#     context = {
#         'is_startup_logged_in': bool(startup_user_id),
#         'startup_user_name': request.session.get('user_name', '') if startup_user_id else ''
#     }
#     return render(request, 'index.html', context)

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

# def deck_builder(request, section='cover-page'):
#     print(f"DEBUG: deck_builder called with section={section}, method={request.method}")  # Debug line
    
#     if section not in SECTION_CONFIG:
#         raise Http404("Section not found.")

#     config = SECTION_CONFIG[section]
#     form_class = config['form_class']
#     is_formset = config.get('is_formset', False)
#     is_cover_page = config.get('create_deck', False)

#     startup_user_id = request.session.get('startup_user_id')
    
#     if is_cover_page and not startup_user_id:
#         messages.error(request, "You need to be logged in as a startup to create a pitch deck.")
#         return redirect('startup_login')

#     context = {
#         'sections': SECTION_CONFIG.keys(),
#         'current_section': section,
#     }

#     deck = None
#     form_kwargs = {
#         'prefix': config.get('prefix'),
#         'data': request.POST or None,
#     }

#     if is_cover_page:
#         form_kwargs['files'] = request.FILES or None
#         # Get or create a draft deck for editing
#         deck_id = request.session.get('deck_id')
#         if deck_id:
#             try:
#                 deck = get_object_or_404(Deck, id=deck_id, owner_id=startup_user_id)
#                 if not request.POST:  # Only pre-populate on GET requests
#                     form_kwargs['instance'] = deck
#             except:
#                 # Deck not found or access denied, clear session and create new draft
#                 request.session.pop('deck_id', None)
#                 deck_id = None
        
#         if not deck_id:
#             # No deck in session - this shouldn't happen for cover page since create_new_deck handles this
#             messages.error(request, "No deck found. Please create a new deck first.")
#             return redirect('deck_home')
#     else:
#         deck_id = request.session.get('deck_id')
#         if not deck_id:
#             # No deck in session - redirect to create a new deck first
#             messages.info(request, "Please create a new deck first to access this section.")
#             return redirect('deck_create')
#         else:
#             try:
#                 deck = get_object_or_404(Deck, id=deck_id)
#                 print(f"DEBUG: Found deck {deck_id} for section {section}")  # Debug line
#             except:
#                 print(f"DEBUG: Deck {deck_id} not found, clearing session")  # Debug line
#                 request.session.pop('deck_id', None)
#                 # Recursively call this function to create a new draft deck
#                 return deck_builder(request, section)
        
#         # For non-cover-page sections, populate with existing data if it exists
#         if not request.POST:  # Only pre-populate on GET requests
#             if section == 'the-problem':
#                 try:
#                     form_kwargs['instance'] = deck.problem
#                 except Problem.DoesNotExist:
#                     pass
#             elif section == 'the-solution':
#                 try:
#                     form_kwargs['instance'] = deck.solution
#                 except Solution.DoesNotExist:
#                     pass
#             elif section == 'market-analysis':
#                 try:
#                     form_kwargs['instance'] = deck.market_analysis
#                 except MarketAnalysis.DoesNotExist:
#                     pass
#             elif section == 'the-ask':
#                 try:
#                     form_kwargs['instance'] = deck.ask
#                 except FundingAsk.DoesNotExist:
#                     pass
#             elif section == 'the-team':
#                 form_kwargs['instance'] = deck
#             elif section == 'financials':
#                 form_kwargs['instance'] = deck
#         else:  # For POST requests, also set the instance if it exists
#             if section == 'the-problem':
#                 try:
#                     form_kwargs['instance'] = deck.problem
#                 except Problem.DoesNotExist:
#                     pass
#             elif section == 'the-solution':
#                 try:
#                     form_kwargs['instance'] = deck.solution
#                 except Solution.DoesNotExist:
#                     pass
#             elif section == 'market-analysis':
#                 try:
#                     form_kwargs['instance'] = deck.market_analysis
#                 except MarketAnalysis.DoesNotExist:
#                     pass
#             elif section == 'the-ask':
#                 try:
#                     form_kwargs['instance'] = deck.ask
#                     print(f"DEBUG: Setting ask instance for POST: {deck.ask}")  # Debug line
#                 except FundingAsk.DoesNotExist:
#                     print(f"DEBUG: No existing ask for deck {deck.id}, will create new")  # Debug line
#                     pass
#             elif section == 'the-team':
#                 form_kwargs['instance'] = deck
#             elif section == 'financials':
#                 form_kwargs['instance'] = deck

#     # Instantiate form or formset without prefilled instance
#     form_or_formset = form_class(**form_kwargs)
    
#     print(f"DEBUG: Processing {section} - Method: {request.method}")  # Debug line

#     if request.method == 'POST' and form_or_formset.is_valid():
#         print(f"DEBUG: Form is valid for {section}")  # Debug line
#         with transaction.atomic():
#             if is_cover_page:
#                 # Get or create a deck for the cover page
#                 deck_id = request.session.get('deck_id')
#                 if deck_id:
#                     # We're editing an existing deck, update it
#                     try:
#                         deck = get_object_or_404(Deck, id=deck_id, owner_id=startup_user_id)
#                         # Update the existing deck with form data
#                         form_data = form_or_formset.cleaned_data
#                         deck.company_name = form_data.get('company_name', deck.company_name)
#                         deck.tagline = form_data.get('tagline', deck.tagline)
#                         if form_data.get('logo'):
#                             deck.logo = form_data.get('logo')
#                         deck.save()
#                         print(f"DEBUG: Updated existing deck {deck.id} from cover page")  # Debug line
#                     except:
#                         messages.error(request, "Error updating deck.")
#                         return redirect('deck_home')
#                 else:
#                     # We're creating a new deck
#                     deck = form_or_formset.save(commit=False)
#                     try:
#                         owner_instance = Registration.objects.get(id=startup_user_id)
#                         deck.owner = owner_instance
#                         deck.save()
#                         request.session['deck_id'] = deck.id
#                         print(f"DEBUG: Created new deck {deck.id} from cover page")  # Debug line
#                     except Registration.DoesNotExist:
#                         messages.error(request, f"Registration record not found for user ID {startup_user_id}. Please log in again.")
#                         # Clear invalid session data
#                         request.session.flush()
#                         return redirect('startup_login')
#                     except Exception as e:
#                         messages.error(request, f"An error occurred while creating the deck: {e}")
#                         return redirect('deck_home')
#             elif deck:  # Ensure deck exists before proceeding
#                 if is_formset:
#                     instances = form_or_formset.save(commit=False)
#                     for instance in instances:
#                         instance.deck = deck
#                         instance.save()
#                     for obj in form_or_formset.deleted_objects:
#                         obj.delete()
#                 else:  # Regular form - since instance is properly set, just save
#                     instance = form_or_formset.save(commit=False)
#                     instance.deck = deck
#                     instance.save()
#                     print(f"DEBUG: Saved {section} for deck {deck.id}: {instance}")  # Debug line
#             else:
#                 # This case should ideally not be hit if logic is correct
#                 messages.error(request, "No active deck found. Please start over.")
#                 return redirect('deck_home')

#         next_section = config['next_section']
#         if next_section == 'deck_home':
#             # Clear the deck session since we're finished
#             request.session.pop('deck_id', None)
#             return redirect('deck_home')
#         else:
#             return redirect('deck_section', section=next_section)
#     elif request.method == 'POST':
#         # Form is not valid, add error message
#         print(f"DEBUG: Form is NOT valid for {section}")  # Debug line
#         print(f"DEBUG: Form errors: {form_or_formset.errors}")  # Debug line
#         messages.error(request, "Please correct the errors in the form.")

#     # Inject deck preview info regardless of form editing
#     if deck:
#         context.update({
#             'deck_info': deck,
#             'problem': getattr(deck, 'problem', None),
#             'solution': getattr(deck, 'solution', None),
#             'market_analysis': getattr(deck, 'market_analysis', None),
#             'ask': getattr(deck, 'ask', None),
#             'team_members': deck.team_members.all(),
#             'financials': deck.financials.order_by('year'),
#         })

#     context[config['template_key']] = form_or_formset
#     return render(request, f'components/{section}.html', context)

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

            return Response({"message": f"{section} saved successfully", "deck_id": deck.id}, status=status.HTTP_200_OK)
        else:
            return Response({"errors": form.errors}, status=status.HTTP_400_BAD_REQUEST)


# MOD 1 AND MOD 2
# def investor_registration(request):
#     if request.method == 'POST':
#         first_name = request.POST.get('firstName')
#         last_name = request.POST.get('lastName')
#         email = request.POST.get('email')
#         password = request.POST.get('password')
#         confirm_password = request.POST.get('confirmPassword')
#         terms_agreed = request.POST.get('terms')  # Get the terms checkbox value

#         # Validation checks
#         if not terms_agreed:
#             messages.error(request, "You must agree to the Terms of Service and Privacy Policy to create an account.")
#         elif password != confirm_password:
#             messages.error(request, "Passwords do not match.")
#         elif Registration.objects.filter(email=email).exists():
#             messages.error(request, "Email already exists.")
#         else:
#             # Create registration using custom Registration model
#             registration = Registration.objects.create(
#                 email=email,
#                 first_name=first_name,
#                 last_name=last_name,
#                 password=make_password(password),  # Hash the password
#                 label='investor'  # Set label to 'investor' for investor registration
#             )
#             messages.success(request, "Account created! You can now log in.")
#             return redirect('login')
#     return render(request, 'Module_1/Create_Account.html')

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

# def login_view(request):
#     if request.method == 'POST':
#         email = request.POST.get('email')
#         password = request.POST.get('password')
        
#         try:
#             # Find user by email (regardless of user type)
#             user = Registration.objects.get(email=email)
            
#             # Check if password is correct
#             if check_password(password, user.password):
#                 # Store common user info in session
#                 request.session['user_email'] = user.email
#                 request.session['user_name'] = f"{user.first_name} {user.last_name}"
#                 request.session['user_label'] = user.label
                
#                 # Set appropriate session variables and redirect based on user's label
#                 if user.label == 'investor':
#                     request.session['user_id'] = user.id
#                     return redirect('dashboard')
#                 elif user.label == 'startup':
#                     request.session['startup_user_id'] = user.id
#                     return redirect('added_startups')
#                 else:
#                     # Default case (fallback to investor behavior)
#                     request.session['user_id'] = user.id
#                     return redirect('dashboard')
#             else:
#                 messages.error(request, 'Invalid email or password.')
#         except Registration.DoesNotExist:
#             messages.error(request, 'Invalid email or password.')
#     return render(request, 'Module_1/Login.html')

class login_view(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            tokens = get_tokens_for_user(user)
            return Response({
                "message": "Login successful",
                "token": tokens['access'],
                "user": {
                    "id": user.id,
                    "name": f"{user.first_name} {user.last_name}",
                    "email": user.email,
                    "label": user.profile.label
                }
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)
    
#session token
def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    } 


# def dashboard(request):
#     # Check if user is logged in via session
#     if not request.session.get('user_id'):
#         return redirect('login')
    
#     startups = Startup.objects.all()
    
#     industry_filter = request.GET.get('industry', '')
#     risk_filter = request.GET.get('risk', '')
#     min_return_filter = request.GET.get('min_return', '')  # Add this line
#     sort_by = request.GET.get('sort_by', 'recommended')    # Add this line for sorting
    
#     if industry_filter and industry_filter != '':
#         startups = startups.filter(industry=industry_filter)
    
#     if risk_filter and risk_filter != '':
#         risk_value = int(risk_filter)
        
#         if risk_value <= 33:
#             startups = startups.filter(data_source_confidence='High')
#         elif risk_value <= 66:
#             startups = startups.filter(data_source_confidence='Medium')
#         else:
#             startups = startups.filter(data_source_confidence='Low')
    
#     # Calculate projected return and reward potential for each startup
#     for s in startups:
#         # Check if this is a deck builder startup
#         is_deck_builder = hasattr(s, 'source_deck') and s.source_deck is not None
        
#         # Calculate projected return (updated to use financial projections for deck builders)
#         try:
#             if is_deck_builder:
#                 # For deck builder startups, calculate projected return from financial projections
#                 deck = s.source_deck
#                 financials = deck.financials.order_by('year')
                
#                 if financials.count() >= 2:
#                     # Calculate growth rate from first to last year
#                     first_year = financials.first()
#                     last_year = financials.last()
                    
#                     # Convert to float and check for positive values
#                     first_revenue = float(first_year.revenue) if first_year.revenue else 0
#                     last_revenue = float(last_year.revenue) if last_year.revenue else 0
                    
#                     if first_revenue > 0 and last_revenue > 0:
#                         years_span = last_year.year - first_year.year
#                         if years_span > 0:
#                             # Calculate CAGR (Compound Annual Growth Rate)
#                             growth_rate = (last_revenue / first_revenue) ** (1/years_span) - 1
#                             s.projected_return = round(growth_rate * 100, 2)
#                         else:
#                             # Same year data, calculate simple growth if different values
#                             if last_revenue != first_revenue and first_revenue > 0:
#                                 simple_growth = ((last_revenue - first_revenue) / first_revenue) * 100
#                                 s.projected_return = round(simple_growth, 2)
#                             else:
#                                 s.projected_return = 0.0  # No growth
#                     else:
#                         # If no positive revenue in first/last, try to find any positive growth pattern
#                         positive_revenues = [float(f.revenue) for f in financials if f.revenue and float(f.revenue) > 0]
#                         if len(positive_revenues) >= 2:
#                             # Use average growth rate as fallback
#                             avg_growth = sum(positive_revenues) / len(positive_revenues)
#                             s.projected_return = round(min(avg_growth / 1000, 50.0), 2)  # Conservative estimate
#                         else:
#                             s.projected_return = 5.0  # Default moderate return for deck builders
#                 elif financials.count() == 1:
#                     # Only one year of data, use a moderate default
#                     single_revenue = float(financials.first().revenue) if financials.first().revenue else 0
#                     if single_revenue > 0:
#                         s.projected_return = 15.0  # Moderate growth assumption for new startups
#                     else:
#                         s.projected_return = 8.0  # Conservative estimate
#                 else:
#                     # No financial data, use default for deck builders
#                     s.projected_return = 12.0  # Default moderate return for deck builders
#             else:
#                 # For regular startups, use existing calculation
#                 if s.revenue and s.total_assets and s.total_assets > 0:
#                     s.projected_return = round((s.revenue / s.total_assets) * 100, 2)
#                 else:
#                     s.projected_return = None
#         except Exception as e:
#             # If any error occurs, provide fallback values
#             if is_deck_builder:
#                 s.projected_return = 10.0  # Safe fallback for deck builders
#             else:
#                 s.projected_return = None
        
#         # Calculate reward potential
#         try:
#             reward_score = 3.0  # Default moderate reward
            
#             if is_deck_builder:
#                 # For deck builder startups, calculate based on deck financial data
#                 deck = s.source_deck
#                 financials = deck.financials.order_by('year')
                
#                 if financials.exists():
#                     # Calculate average profit margin across all years
#                     total_revenue = sum(float(f.revenue) for f in financials if f.revenue > 0)
#                     total_profit = sum(float(f.profit) for f in financials)
                    
#                     if total_revenue > 0:
#                         avg_profit_margin = total_profit / total_revenue
                        
#                         # Apply the reward scoring based on average profit margin
#                         if avg_profit_margin > 0.2:  # 20%+ profit margin
#                             reward_score = 4.5  # High reward potential
#                         elif avg_profit_margin > 0.1:  # 10-20% profit margin
#                             reward_score = 3.5  # Good reward
#                         elif avg_profit_margin > 0:  # 0-10% profit margin
#                             reward_score = 2.5  # Fair reward
#                         else:  # Negative profit margin
#                             reward_score = 2.0  # Low reward
#                     else:
#                         # No revenue data, check if there's projected growth in financials
#                         future_revenue = sum(float(f.revenue) for f in financials if f.year > 2025 and f.revenue > 0)
#                         if future_revenue > 0:
#                             reward_score = 3.0  # Moderate potential for future growth
#                         else:
#                             reward_score = 2.0  # Low potential
                
#                 # Set special flags for deck builder display
#                 s.is_deck_builder = True
#                 s.display_risk = 'Medium'  # Always show as Medium Risk for deck builders
                
#             else:
#                 # For regular startups, use existing logic
#                 if s.revenue and s.net_income:
#                     revenue = float(s.revenue) if s.revenue else 0
#                     net_income = float(s.net_income) if s.net_income else 0
                    
#                     if revenue > 0:
#                         profit_margin = net_income / revenue
                        
#                         if profit_margin > 0.2:  # 20%+ profit margin
#                             reward_score = 4.5  # Higher reward potential
#                         elif profit_margin > 0.1:  # 10-20% profit margin
#                             reward_score = 3.5
#                         elif profit_margin > 0:  # 0-10% profit margin
#                             reward_score = 2.5
#                         else:  # Negative profit margin
#                             reward_score = 2.0
                
#                 s.is_deck_builder = False
#                 s.display_risk = s.data_source_confidence  # Use actual confidence for regular startups
            
#             s.reward_potential = round(reward_score, 1)
#         except Exception as e:
#             s.reward_potential = 3.0  # Default fallback
#             s.is_deck_builder = False
#             s.display_risk = getattr(s, 'data_source_confidence', 'Medium')
    
#     # Apply minimum return filter AFTER calculating projected returns
#     if min_return_filter and min_return_filter != '':
#         try:
#             min_return_value = float(min_return_filter)
#             # Filter out startups that don't have projected_return or have it below minimum
#             startups = [s for s in startups if s.projected_return is not None and s.projected_return >= min_return_value]
#         except (ValueError, TypeError):
#             pass  # If conversion fails, ignore the filter
    
#     # Apply sorting
#     if sort_by == 'projected_return_desc':
#         startups = sorted(startups, key=lambda x: x.projected_return or 0, reverse=True)
#     elif sort_by == 'projected_return_asc':
#         startups = sorted(startups, key=lambda x: x.projected_return or 0)
#     elif sort_by == 'reward_potential_desc':
#         startups = sorted(startups, key=lambda x: x.reward_potential or 0, reverse=True)
#     elif sort_by == 'confidence_desc':
#         confidence_order = {'High': 3, 'Medium': 2, 'Low': 1}
#         startups = sorted(startups, key=lambda x: confidence_order.get(x.data_source_confidence, 0), reverse=True)
#     elif sort_by == 'risk_asc':
#         confidence_order = {'High': 1, 'Medium': 2, 'Low': 3}  # High confidence = low risk
#         startups = sorted(startups, key=lambda x: confidence_order.get(x.data_source_confidence, 2))
#     elif sort_by == 'company_name':
#         startups = sorted(startups, key=lambda x: x.company_name.lower())
#     # 'recommended' or default - keep original order
    
#     context = {
#         'startups': startups,
#         'selected_industry': industry_filter,
#         'selected_risk': risk_filter or '50',
#     }
    
#     return render(request, 'Module_1/Dashboard.html', context)



class dashboard(APIView):
    def get(self, request):
        # Optional: enforce authentication
        # if not request.user.is_authenticated:
        #     return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

        industry = request.query_params.get('industry', '')
        risk = request.query_params.get('risk', '')
        min_return = request.query_params.get('min_return', '')
        sort_by = request.query_params.get('sort_by', 'recommended')

        startups = Startup.objects.all()

        # Apply filters
        if industry:
            startups = startups.filter(industry=industry)

        if risk:
            try:
                risk_value = int(risk)
                if risk_value <= 33:
                    startups = startups.filter(data_source_confidence='High')
                elif risk_value <= 66:
                    startups = startups.filter(data_source_confidence='Medium')
                else:
                    startups = startups.filter(data_source_confidence='Low')
            except ValueError:
                pass

        # Annotate each startup with projected return and reward potential
        startup_data = []
        for s in startups:
            projected_return = calculate_projected_return(s)
            reward_potential, display_risk, is_deck_builder = calculate_reward_potential(s)

            if min_return:
                try:
                    if projected_return is None or projected_return < float(min_return):
                        continue
                except ValueError:
                    pass

            startup_data.append({
                "id": s.id,
                "company_name": s.company_name,
                "industry": s.industry,
                "projected_return": projected_return,
                "reward_potential": reward_potential,
                "confidence": s.data_source_confidence,
                "display_risk": display_risk,
                "is_deck_builder": is_deck_builder
            })

        # Apply sorting
        startup_data = sort_startups(startup_data, sort_by)

        return Response({
            "startups": startup_data,
            "selected_industry": industry,
            "selected_risk": risk or '50'
        }, status=status.HTTP_200_OK)
    
# Helper functions for calculations and sorting

def calculate_projected_return(startup):
    try:
        if hasattr(startup, 'source_deck') and startup.source_deck:
            deck = startup.source_deck
            financials = deck.financials.order_by('year')

            if financials.count() >= 2:
                first = financials.first()
                last = financials.last()
                first_rev = float(first.revenue or 0)
                last_rev = float(last.revenue or 0)

                if first_rev > 0 and last_rev > 0:
                    span = last.year - first.year
                    if span > 0:
                        cagr = (last_rev / first_rev) ** (1 / span) - 1
                        return round(cagr * 100, 2)
                    elif last_rev != first_rev:
                        return round(((last_rev - first_rev) / first_rev) * 100, 2)
                else:
                    pos_revs = [float(f.revenue) for f in financials if f.revenue and float(f.revenue) > 0]
                    if len(pos_revs) >= 2:
                        avg_growth = sum(pos_revs) / len(pos_revs)
                        return round(min(avg_growth / 1000, 50.0), 2)
                    return 5.0
            elif financials.count() == 1:
                rev = float(financials.first().revenue or 0)
                return 15.0 if rev > 0 else 8.0
            else:
                return 12.0
        else:
            if startup.revenue and startup.total_assets and startup.total_assets > 0:
                return round((startup.revenue / startup.total_assets) * 100, 2)
    except Exception:
        return 10.0 if hasattr(startup, 'source_deck') else None

def calculate_reward_potential(startup):
    try:
        if hasattr(startup, 'source_deck') and startup.source_deck:
            deck = startup.source_deck
            financials = deck.financials.order_by('year')

            if financials.exists():
                total_rev = sum(float(f.revenue or 0) for f in financials)
                total_profit = sum(float(f.profit or 0) for f in financials)

                if total_rev > 0:
                    margin = total_profit / total_rev
                    if margin > 0.2:
                        return 4.5, 'Medium', True
                    elif margin > 0.1:
                        return 3.5, 'Medium', True
                    elif margin > 0:
                        return 2.5, 'Medium', True
                    else:
                        return 2.0, 'Medium', True
                else:
                    future_rev = sum(float(f.revenue or 0) for f in financials if f.year > 2025)
                    return (3.0 if future_rev > 0 else 2.0), 'Medium', True
            return 3.0, 'Medium', True
        else:
            if startup.revenue and startup.net_income:
                rev = float(startup.revenue or 0)
                income = float(startup.net_income or 0)
                if rev > 0:
                    margin = income / rev
                    if margin > 0.2:
                        return 4.5, startup.data_source_confidence, False
                    elif margin > 0.1:
                        return 3.5, startup.data_source_confidence, False
                    elif margin > 0:
                        return 2.5, startup.data_source_confidence, False
                    else:
                        return 2.0, startup.data_source_confidence, False
        return 3.0, getattr(startup, 'data_source_confidence', 'Medium'), False
    except Exception:
        return 3.0, getattr(startup, 'data_source_confidence', 'Medium'), False

def sort_startups(startups, sort_by):    
    if sort_by == 'projected_return_desc':
        return sorted(startups, key=lambda x: x.projected_return or 0, reverse=True)
    elif sort_by == 'projected_return_asc':
        return sorted(startups, key=lambda x: x.projected_return or 0)
    elif sort_by == 'reward_potential_desc':
        return sorted(startups, key=lambda x: x.reward_potential or 0, reverse=True)
    elif sort_by == 'confidence_desc':
        confidence_order = {'High': 3, 'Medium': 2, 'Low': 1}
        return sorted(startups, key=lambda x: confidence_order.get(x.data_source_confidence, 0), reverse=True)
    elif sort_by == 'risk_asc':
        confidence_order = {'High': 1, 'Medium': 2, 'Low': 3}  # High confidence = low risk
        return sorted(startups, key=lambda x: confidence_order.get(x.data_source_confidence, 2))
    elif sort_by == 'company_name':
        return sorted(startups, key=lambda x: x.company_name.lower())
    # 'recommended' or default - keep original order
    return startups

# def watchlist_view(request):
#     # Get Django user from session
#     django_user = get_django_user_from_session(request)
#     if not django_user:
#         return redirect('login')
    
#     watchlist_items = Watchlist.objects.filter(user=django_user).select_related('startup')
    
#     # Process each startup to add deck builder flags and risk display consistency
#     for item in watchlist_items:
#         startup = item.startup
#         # Check if this is a deck builder startup
#         is_deck_builder = hasattr(startup, 'source_deck') and startup.source_deck is not None
#         startup.is_deck_builder = is_deck_builder
        
#         # Calculate projected return for deck builders using financial projections
#         if is_deck_builder:
#             try:
#                 # For deck builder startups, calculate projected return from financial projections
#                 deck = startup.source_deck
#                 financials = deck.financials.order_by('year')
                
#                 if financials.count() >= 2:
#                     # Calculate growth rate from first to last year
#                     first_year = financials.first()
#                     last_year = financials.last()
                    
#                     # Convert to float and check for positive values
#                     first_revenue = float(first_year.revenue) if first_year.revenue else 0
#                     last_revenue = float(last_year.revenue) if last_year.revenue else 0
                    
#                     if first_revenue > 0 and last_revenue > 0:
#                         years_span = last_year.year - first_year.year
#                         if years_span > 0:
#                             # Calculate CAGR (Compound Annual Growth Rate)
#                             growth_rate = (last_revenue / first_revenue) ** (1/years_span) - 1
#                             startup.projected_return = round(growth_rate * 100, 2)
#                         else:
#                             # Same year data, calculate simple growth if different values
#                             if last_revenue != first_revenue and first_revenue > 0:
#                                 simple_growth = ((last_revenue - first_revenue) / first_revenue) * 100
#                                 startup.projected_return = round(simple_growth, 2)
#                             else:
#                                 startup.projected_return = 0.0  # No growth
#                     else:
#                         # If no positive revenue in first/last, try to find any positive growth pattern
#                         positive_revenues = [float(f.revenue) for f in financials if f.revenue and float(f.revenue) > 0]
#                         if len(positive_revenues) >= 2:
#                             # Use average growth rate as fallback
#                             avg_growth = sum(positive_revenues) / len(positive_revenues)
#                             startup.projected_return = round(min(avg_growth / 1000, 50.0), 2)  # Conservative estimate
#                         else:
#                             startup.projected_return = 5.0  # Default moderate return for deck builders
#                 elif financials.count() == 1:
#                     # Only one year of data, use a moderate default
#                     single_revenue = float(financials.first().revenue) if financials.first().revenue else 0
#                     if single_revenue > 0:
#                         startup.projected_return = 15.0  # Moderate growth assumption for new startups
#                     else:
#                         startup.projected_return = 8.0  # Conservative estimate
#                 else:
#                     # No financial data, use default for deck builders
#                     startup.projected_return = 12.0  # Default moderate return for deck builders
#             except:
#                 startup.projected_return = 10.0  # Safe fallback for deck builders
#         else:
#             # For regular startups, use existing calculation if needed
#             if hasattr(startup, 'revenue') and hasattr(startup, 'total_assets') and startup.revenue and startup.total_assets and startup.total_assets > 0:
#                 startup.projected_return = round((startup.revenue / startup.total_assets) * 100, 2)
        
#         # Set display risk consistently with dashboard logic
#         if is_deck_builder:
#             startup.display_risk = 'Medium'  # Always show as Medium Risk for deck builders
#         else:
#             startup.display_risk = startup.data_source_confidence  # Use actual confidence for regular startups
    
#     # Get all comparison sets for the current user
#     comparison_sets = ComparisonSet.objects.filter(user=django_user).prefetch_related('startups')
    
#     # Get downloaded items for the current user
#     downloaded_items = Download.objects.filter(user=django_user).select_related('startup')
    
#     return render(request, 'Module_1/WatchList.html', {
#         'watchlist_items': watchlist_items,
#         'comparison_sets': comparison_sets,  # Pass all comparison sets
#         'compared_count': comparison_sets.count(),  # Count of comparison sets
#         'saved_count': watchlist_items.count(),
#         'downloaded_count': downloaded_items.count(),
#         'downloaded_items': downloaded_items,
#     })

class watchlist_view(APIView):
    def get(self, request):
        user = request.user
        if not user.is_authenticated:
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

        watchlist_items = Watchlist.objects.filter(user=user).select_related('startup')
        comparison_sets = ComparisonSet.objects.filter(user=user).prefetch_related('startups')
        downloaded_items = Download.objects.filter(user=user).select_related('startup')

        startups_data = []
        for item in watchlist_items:
            startup = item.startup
            is_deck_builder = hasattr(startup, 'source_deck') and startup.source_deck is not None
            projected_return = calculate_projected_return(startup)
            reward_potential, display_risk, _ = calculate_reward_potential(startup)

            startups_data.append({
                "id": startup.id,
                "company_name": startup.company_name,
                "industry": startup.industry,
                "is_deck_builder": is_deck_builder,
                "projected_return": projected_return,
                "display_risk": display_risk,
                "reward_potential": reward_potential
            })

        comparison_data = [{
            "id": comp.id,
            "startup_ids": [s.id for s in comp.startups.all()]
        } for comp in comparison_sets]

        downloaded_data = [{
            "id": d.id,
            "startup_id": d.startup.id,
            "company_name": d.startup.company_name
        } for d in downloaded_items]

        return Response({
            "watchlist": startups_data,
            "comparison_sets": comparison_data,
            "downloaded_items": downloaded_data,
            "counts": {
                "saved": len(startups_data),
                "compared": comparison_sets.count(),
                "downloaded": downloaded_items.count()
            }
        }, status=status.HTTP_200_OK)

@require_POST
@csrf_protect
# def remove_from_watchlist(request, startup_id):
#     """
#     Remove a startup from the user's watchlist via AJAX
#     """
#     try:
#         # Get Django user from session
#         django_user = get_django_user_from_session(request)
#         if not django_user:
#             return JsonResponse({'success': False, 'message': 'Please log in to continue.'})
        
#         # Get the watchlist item for this user and startup
#         watchlist_item = get_object_or_404(
#             Watchlist, 
#             user=django_user, 
#             startup_id=startup_id
#         )
        
#         # Store the company name for the response
#         company_name = watchlist_item.startup.company_name
        
#         # Delete the watchlist item
#         watchlist_item.delete()
        
#         # Get updated count
#         updated_count = Watchlist.objects.filter(user=django_user).count()
        
#         return JsonResponse({
#             'success': True,
#             'message': f'{company_name} has been removed from your watchlist.',
#             'updated_count': updated_count
#         })
        
#     except Watchlist.DoesNotExist:
#         return JsonResponse({
#             'success': False,
#             'message': 'This startup is not in your watchlist.'
#         }, status=404)
        
#     except Exception as e:
#         return JsonResponse({
#             'success': False,
#             'message': 'An error occurred while removing the startup.'
#         }, status=500)

class remove_from_watchlist(APIView):
    def delete(self, request, startup_id):
        user = request.user
        if not user.is_authenticated:
            return Response(
                {"success": False, "message": "Please log in to continue."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            watchlist_item = get_object_or_404(Watchlist, user=user, startup_id=startup_id)
            company_name = watchlist_item.startup.company_name
            watchlist_item.delete()

            updated_count = Watchlist.objects.filter(user=user).count()

            return Response({
                "success": True,
                "message": f"{company_name} has been removed from your watchlist.",
                "updated_count": updated_count
            }, status=status.HTTP_200_OK)

        except Watchlist.DoesNotExist:
            return Response(
                {"success": False, "message": "This startup is not in your watchlist."},
                status=status.HTTP_404_NOT_FOUND
            )

        except Exception:
            return Response(
                {"success": False, "message": "An error occurred while removing the startup."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# Helper function to delete a comparison set
# def delete_comparison_set(request, comparison_id):
#     # Get Django user from session
#     django_user = get_django_user_from_session(request)
#     if not django_user:
#         return redirect('login')
    
#     if request.method == 'POST':
#         try:
#             comparison_set = ComparisonSet.objects.get(id=comparison_id, user=django_user)
#             comparison_set.delete()
#         except ComparisonSet.DoesNotExist:
#             pass
#     return redirect('watchlist')

class delete_comparison_set(APIView):
    def delete(self, request, comparison_id):
        user = request.user
        if not user.is_authenticated:
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            comparison_set = ComparisonSet.objects.get(id=comparison_id, user=user)
            comparison_set.delete()
            return Response({"message": "Comparison set deleted successfully"}, status=status.HTTP_200_OK)
        except ComparisonSet.DoesNotExist:
            return Response({"error": "Comparison set not found"}, status=status.HTTP_404_NOT_FOUND)

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
    

# def add_to_watchlist(request, startup_id):
#     # Get Django user from session
#     django_user = get_django_user_from_session(request)
#     if not django_user:
#         return redirect('login')
    
#     startup = get_object_or_404(Startup, id=startup_id)
    
#     # Use get_or_create to check if already exists
#     watchlist_item, created = Watchlist.objects.get_or_create(
#         user=django_user, 
#         startup=startup
#     )
    
#     if created:
#         messages.success(request, f'✅ {startup.company_name} has been added to your watchlist!')
#     else:
#         messages.info(request, f'ℹ️ {startup.company_name} is already in your watchlist.')
    
#     return redirect('company_profile', startup_id=startup.id)

class add_to_watchlist(APIView):
    def post(self, request, startup_id):
        user = request.user
        if not user.is_authenticated:
            return Response(
                {"success": False, "message": "Please log in to continue."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        startup = get_object_or_404(Startup, id=startup_id)

        watchlist_item, created = Watchlist.objects.get_or_create(user=user, startup=startup)

        if created:
            return Response(
                {"success": True, "message": f"{startup.company_name} has been added to your watchlist."},
                status=status.HTTP_201_CREATED
            )
        else:
            return Response(
                {"success": False, "message": f"{startup.company_name} is already in your watchlist."},
                status=status.HTTP_200_OK
            )

# def remove_from_watchlist(request, startup_id):
#     # Get Django user from session
#     django_user = get_django_user_from_session(request)
#     if not django_user:
#         # Check if this is an AJAX request
#         if request.headers.get('Accept') == 'application/json' or request.content_type == 'application/json':
#             return JsonResponse({'success': False, 'message': 'Please log in to continue'}, status=401)
#         return redirect('login')
    
#     startup = get_object_or_404(Startup, id=startup_id)
    
#     # Try to remove from watchlist
#     deleted_count, _ = Watchlist.objects.filter(
#         user=django_user, 
#         startup=startup
#     ).delete()
    
#     # Get updated count for AJAX response
#     updated_count = Watchlist.objects.filter(user=django_user).count()
    
#     # Check if this is an AJAX request
#     is_ajax = request.headers.get('Accept') == 'application/json' or request.content_type == 'application/json'
    
#     if deleted_count > 0:
#         success_message = f'✅ {startup.company_name} has been removed from your watchlist.'
        
#         # Handle AJAX request (from watchlist page)
#         if is_ajax:
#             return JsonResponse({
#                 'success': True, 
#                 'message': success_message,
#                 'updated_count': updated_count
#             })
        
#         # Handle regular form submission (from company profile page)
#         messages.success(request, success_message)
#         return redirect('company_profile', startup_id=startup.id)
#     else:
#         warning_message = f'⚠️ {startup.company_name} was not in your watchlist.'
        
#         # Handle AJAX request
#         if is_ajax:
#             return JsonResponse({
#                 'success': False, 
#                 'message': warning_message,
#                 'updated_count': updated_count
#             })
        
#         # Handle regular form submission
#         messages.warning(request, warning_message)
#         return redirect('company_profile', startup_id=startup.id)

class remove_from_watchlist(APIView):
    def delete(self, request, startup_id):
        user = request.user
        if not user.is_authenticated:
            return Response(
                {"success": False, "message": "Please log in to continue."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        startup = get_object_or_404(Startup, id=startup_id)

        deleted_count, _ = Watchlist.objects.filter(user=user, startup=startup).delete()
        updated_count = Watchlist.objects.filter(user=user).count()

        if deleted_count > 0:
            return Response({
                "success": True,
                "message": f"{startup.company_name} has been removed from your watchlist.",
                "updated_count": updated_count
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "success": False,
                "message": f"{startup.company_name} was not in your watchlist.",
                "updated_count": updated_count
            }, status=status.HTTP_404_NOT_FOUND)
        
# def company_profile(request, startup_id):
#     # Check if user is logged in via session
#     if not request.session.get('user_id'):
#         return redirect('login')
    
#     startup = get_object_or_404(Startup, id=startup_id)
    
#     # Track the view (only for non-owners)
#     django_user = get_django_user_from_session(request)
#     if django_user and django_user != startup.owner:
#         # Get client IP address
#         ip_address = request.META.get('HTTP_X_FORWARDED_FOR')
#         if ip_address:
#             ip_address = ip_address.split(',')[0]
#         else:
#             ip_address = request.META.get('REMOTE_ADDR')
        
#         # Create view record (allow multiple views per day for detailed analytics)
#         StartupView.objects.create(
#             user=django_user,
#             startup=startup,
#             ip_address=ip_address
#         )
    
#     # Check if this startup was created from a deck (deck builder startup)
#     if startup.source_deck:
#         # Show the deck report modal template with the deck data
#         deck = startup.source_deck
        
#         # Check if startup is in user's watchlist
#         is_in_watchlist = False
#         if django_user:
#             is_in_watchlist = Watchlist.objects.filter(
#                 user=django_user, 
#                 startup=startup
#             ).exists()
        
#         context = {
#             'deck_info': deck,
#             'problem': getattr(deck, 'problem', None),
#             'solution': getattr(deck, 'solution', None),
#             'market_analysis': getattr(deck, 'market_analysis', None),
#             'ask': getattr(deck, 'ask', None),
#             'team_members': deck.team_members.all(),
#             'financials': deck.financials.order_by('year'),
#             'startup': startup,  # Include startup info for context
#             'show_modal': True,  # Flag to show modal by default
#             'from_dashboard': True,  # Flag to indicate this is viewed from dashboard
#             'is_in_watchlist': is_in_watchlist,  # Include watchlist status
#         }
        
#         # Use the deck report template for deck builder startups
#         return render(request, 'Module_2/Company_ProfileDB.html', context)

#     # For regular startups (not deck builder), show the standard company profile
#     # Check if we have risk/reward data in session from health report
#     company_data = request.session.get('company_data', {})
    
#     # If session has risk/reward data for this company, use it
#     if (company_data.get('company_name') == startup.company_name and 
#         'risk_score' in company_data and 'reward_score' in company_data):
        
#         risk_score = company_data['risk_score']
#         reward_score = company_data['reward_score']
#         risk_score_percent = company_data['risk_score_percent']
#         reward_score_percent = company_data['reward_score_percent']
        
#     else:
#         # Fallback: Calculate using the same logic as health report
#         risk_score = 2.5  # Default moderate risk
#         reward_score = 3.0  # Default moderate reward
        
#         # Calculate risk and reward based on financial data
#         if startup.revenue and startup.net_income:
#             revenue = float(startup.revenue) if startup.revenue else 0
#             net_income = float(startup.net_income) if startup.net_income else 0
            
#             if revenue > 0:
#                 profit_margin = net_income / revenue
                
#                 if profit_margin > 0.2:  # 20%+ profit margin
#                     risk_score = 2.0  # Lower risk for high profit margin
#                     reward_score = 4.5  # Higher reward potential
#                 elif profit_margin > 0.1:  # 10-20% profit margin
#                     risk_score = 2.5
#                     reward_score = 3.5
#                 elif profit_margin > 0:  # 0-10% profit margin
#                     risk_score = 3.5
#                     reward_score = 2.5
#                 else:  # Negative profit margin
#                     risk_score = 4.5  # Higher risk for negative margins
#                     reward_score = 2.0
        
#         # Adjust based on data confidence
#         confidence_adjustments = {
#             'High': 0.0,   
#             'Medium': 0.0,  
#             'Low': 0.8      
#         }
        
#         confidence_level = getattr(startup, 'data_source_confidence', 'Medium')
#         risk_adjustment = confidence_adjustments.get(confidence_level, 0.3)
#         risk_score = min(risk_score + risk_adjustment, 5.0)  # Cap at 5.0
        
#         risk_score = round(risk_score, 1)
#         reward_score = round(reward_score, 1)
#         risk_score_percent = round((risk_score / 5) * 100, 1)
#         reward_score_percent = round((reward_score / 5) * 100, 1)

#     # Check if startup is in user's watchlist
#     is_in_watchlist = False
#     if django_user:
#         is_in_watchlist = Watchlist.objects.filter(
#             user=django_user, 
#             startup=startup
#         ).exists()

#     context = {
#         'startup': startup,
#         'is_in_watchlist': is_in_watchlist,
#         'company_data': {
#             'risk_score': risk_score,
#             'reward_score': reward_score,
#             'risk_score_percent': risk_score_percent,
#             'reward_score_percent': reward_score_percent,
#         }
#     }

#     return render(request, 'Module_2/Company_Profile.html', context)

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
            "startup": {
                "id": startup.id,
                "company_name": startup.company_name,
                "industry": startup.industry,
                "is_deck_builder": False
            },
            "company_data": {
                "risk_score": round(risk_score, 1),
                "reward_score": round(reward_score, 1),
                "risk_score_percent": round((risk_score / 5) * 100, 1),
                "reward_score_percent": round((reward_score / 5) * 100, 1)
            },
            "is_in_watchlist": is_in_watchlist
        }, status=status.HTTP_200_OK)

# def download_company_profile_pdf(request, startup_id):
#     # Get Django user from session
#     django_user = get_django_user_from_session(request)
#     if not django_user:
#         return redirect('login')
    
#     startup = get_object_or_404(Startup, id=startup_id)
    
#     # Create or get the download record
#     download_record, created = Download.objects.get_or_create(
#         user=django_user,
#         startup=startup,
#         download_type='company_profile'
#     )
    
#     # If it's a new download, update the downloaded_at timestamp
#     if not created:
#         download_record.downloaded_at = datetime.datetime.now()
#         download_record.save()
    
#     # Get the same data as in company_profile view
#     company_data = request.session.get('company_data', {})
    
#     if (company_data.get('company_name') == startup.company_name and 
#         'risk_score' in company_data and 'reward_score' in company_data):
        
#         risk_score = company_data['risk_score']
#         reward_score = company_data['reward_score']
#         risk_score_percent = company_data['risk_score_percent']
#         reward_score_percent = company_data['reward_score_percent']
        
#     else:
#         # Fallback calculation (same logic as company_profile view)
#         risk_score = 2.5
#         reward_score = 3.0
        
#         if startup.revenue and startup.net_income:
#             revenue = float(startup.revenue) if startup.revenue else 0
#             net_income = float(startup.net_income) if startup.net_income else 0
            
#             if revenue > 0:
#                 profit_margin = net_income / revenue
                
#                 if profit_margin > 0.2:
#                     risk_score = 2.0
#                     reward_score = 4.5
#                 elif profit_margin > 0.1:
#                     risk_score = 2.5
#                     reward_score = 3.5
#                 elif profit_margin > 0:
#                     risk_score = 3.5
#                     reward_score = 2.5
#                 else:
#                     risk_score = 4.5
#                     reward_score = 2.0
        
#         confidence_adjustments = {
#             'High': 0.0,
#             'Medium': 0.3,
#             'Low': 0.8
#         }
        
#         confidence_level = getattr(startup, 'data_source_confidence', 'Medium')
#         risk_adjustment = confidence_adjustments.get(confidence_level, 0.3)
#         risk_score = min(risk_score + risk_adjustment, 5.0)
        
#         risk_score = round(risk_score, 1)
#         reward_score = round(reward_score, 1)
#         risk_score_percent = round((risk_score / 5) * 100, 1)
#         reward_score_percent = round((reward_score / 5) * 100, 1)

#     # Create PDF
#     buffer = BytesIO()
#     doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
    
#     # Define styles
#     styles = getSampleStyleSheet()
#     title_style = ParagraphStyle(
#         'CustomTitle',
#         parent=styles['Heading1'],
#         fontSize=24,
#         spaceAfter=30,
#         alignment=TA_CENTER,
#         textColor=colors.HexColor('#1f2937')
#     )
    
#     heading_style = ParagraphStyle(
#         'CustomHeading',
#         parent=styles['Heading2'],
#         fontSize=16,
#         spaceAfter=12,
#         spaceBefore=20,
#         textColor=colors.HexColor('#374151')
#     )
    
#     normal_style = ParagraphStyle(
#         'CustomNormal',
#         parent=styles['Normal'],
#         fontSize=10,
#         spaceAfter=6,
#         textColor=colors.HexColor('#4b5563')
#     )
    
#     # Build PDF content
#     story = []
    
#     # Title
#     story.append(Paragraph(f"{startup.company_name} - Company Profile", title_style))
#     story.append(Spacer(1, 12))
    
#     # Header info
#     header_data = [
#         ['Industry:', startup.industry or 'AI/Machine Learning'],
#         ['Risk Level:', get_risk_level_text(startup.data_source_confidence)],
#         ['Report Date:', datetime.datetime.now().strftime('%B %d, %Y')],
#         ['Data Confidence:', startup.data_source_confidence or 'Unknown']
#     ]
    
#     header_table = Table(header_data, colWidths=[1.5*inch, 4*inch])
#     header_table.setStyle(TableStyle([
#         ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
#         ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
#         ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
#         ('FONTSIZE', (0, 0), (-1, -1), 10),
#         ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
#     ]))
    
#     story.append(header_table)
#     story.append(Spacer(1, 20))
#     story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e5e7eb')))
    
#     # Company Summary
#     story.append(Paragraph("Company Summary", heading_style))
#     description = startup.company_description or "No company description available."
#     story.append(Paragraph(description, normal_style))
#     story.append(Spacer(1, 20))
    
#     # Financial Metrics
#     story.append(Paragraph("Financial Metrics", heading_style))
    
#     financial_data = [
#         ['Metric', 'Value'],
#         ['Revenue', f"${startup.revenue:,.2f}" if startup.revenue else "N/A"],
#         ['Net Income', f"${startup.net_income:,.2f}" if startup.net_income else "N/A"],
#         ['Total Assets', f"${startup.total_assets:,.2f}" if startup.total_assets else "N/A"],
#         ['Cash Flow', f"${startup.cash_flow:,.2f}" if startup.cash_flow else "N/A"],
#     ]
    
#     financial_table = Table(financial_data, colWidths=[2*inch, 3*inch])
#     financial_table.setStyle(TableStyle([
#         ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
#         ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#374151')),
#         ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
#         ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
#         ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
#         ('FONTSIZE', (0, 0), (-1, -1), 10),
#         ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
#         ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
#     ]))
    
#     story.append(financial_table)
#     story.append(Spacer(1, 20))
    
#     # Risk & Reward Analysis
#     story.append(Paragraph("Risk & Reward Analysis", heading_style))
    
#     risk_reward_data = [
#         ['Metric', 'Score', 'Rating'],
#         ['Risk Score', f"{risk_score}/5", get_risk_rating(risk_score)],
#         ['Reward Potential', f"{reward_score}/5", get_reward_rating(reward_score)],
#     ]
    
#     risk_reward_table = Table(risk_reward_data, colWidths=[2*inch, 1.5*inch, 2*inch])
#     risk_reward_table.setStyle(TableStyle([
#         ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
#         ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#374151')),
#         ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
#         ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
#         ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
#         ('FONTSIZE', (0, 0), (-1, -1), 10),
#         ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
#         ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
#     ]))
    
#     story.append(risk_reward_table)
#     story.append(Spacer(1, 20))
    
#     # Qualitative Insights
#     story.append(Paragraph("Qualitative Insights", heading_style))
    
#     insights_data = [
#         ['Aspect', 'Assessment'],
#         ['Team Strength', startup.team_strength or 'No data available'],
#         ['Market Position', startup.market_position or 'No data available'],
#         ['Brand Reputation', startup.brand_reputation or 'No data available'],
#     ]
    
#     insights_table = Table(insights_data, colWidths=[2*inch, 4*inch])
#     insights_table.setStyle(TableStyle([
#         ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
#         ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#374151')),
#         ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
#         ('VALIGN', (0, 0), (-1, -1), 'TOP'),
#         ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
#         ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
#         ('FONTSIZE', (0, 0), (-1, -1), 10),
#         ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
#         ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
#     ]))
    
#     story.append(insights_table)
    
#     # Footer
#     story.append(Spacer(1, 30))
#     story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e5e7eb')))
#     story.append(Spacer(1, 12))
    
#     footer_style = ParagraphStyle(
#         'Footer',
#         parent=styles['Normal'],
#         fontSize=8,
#         alignment=TA_CENTER,
#         textColor=colors.HexColor('#6b7280')
#     )
    
#     story.append(Paragraph(f"Generated on {datetime.datetime.now().strftime('%B %d, %Y at %I:%M %p')} | Investment Analysis Report", footer_style))
    
#     # Build PDF
#     doc.build(story)
    
#     # Return PDF response
#     buffer.seek(0)
#     response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
#     response['Content-Disposition'] = f'attachment; filename="{startup.company_name}_profile.pdf"'
    
#     return response

class download_company_profile_pdf(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, startup_id):
        user = request.user
        startup = get_object_or_404(Startup, id=startup_id)

        # Log the download
        download_record, created = Download.objects.get_or_create(
            user=user,
            startup=startup,
            download_type='company_profile'
        )
        if not created:
            download_record.downloaded_at = timezone.now()
            download_record.save()

        # Risk/reward calculation (fallback logic)
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

        confidence_adjustments = {'High': 0.0, 'Medium': 0.3, 'Low': 0.8}
        confidence = getattr(startup, 'data_source_confidence', 'Medium')
        risk_score = min(risk_score + confidence_adjustments.get(confidence, 0.3), 5.0)

        # PDF generation
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=24, alignment=TA_CENTER, textColor=colors.HexColor('#1f2937'))
        heading_style = ParagraphStyle('Heading', parent=styles['Heading2'], fontSize=16, textColor=colors.HexColor('#374151'))
        normal_style = ParagraphStyle('Normal', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor('#4b5563'))
        footer_style = ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, alignment=TA_CENTER, textColor=colors.HexColor('#6b7280'))

        story = [
            Paragraph(f"{startup.company_name} - Company Profile", title_style),
            Spacer(1, 12),
            Table([
                ['Industry:', startup.industry or 'AI/Machine Learning'],
                ['Risk Level:', get_risk_level_text(confidence)],
                ['Report Date:', timezone.now().strftime('%B %d, %Y')],
                ['Data Confidence:', confidence or 'Unknown']
            ], colWidths=[1.5*inch, 4*inch], style=TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ])),
            Spacer(1, 20),
            HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e5e7eb')),
            Paragraph("Company Summary", heading_style),
            Paragraph(startup.company_description or "No company description available.", normal_style),
            Spacer(1, 20),
            Paragraph("Financial Metrics", heading_style),
            Table([
                ['Metric', 'Value'],
                ['Revenue', f"${startup.revenue:,.2f}" if startup.revenue else "N/A"],
                ['Net Income', f"${startup.net_income:,.2f}" if startup.net_income else "N/A"],
                ['Total Assets', f"${startup.total_assets:,.2f}" if startup.total_assets else "N/A"],
                ['Cash Flow', f"${startup.cash_flow:,.2f}" if startup.cash_flow else "N/A"],
            ], colWidths=[2*inch, 3*inch], style=TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#374151')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
            ])),
            Spacer(1, 20),
            Paragraph("Risk & Reward Analysis", heading_style),
            Table([
                ['Metric', 'Score', 'Rating'],
                ['Risk Score', f"{risk_score}/5", get_risk_rating(risk_score)],
                ['Reward Potential', f"{reward_score}/5", get_reward_rating(reward_score)],
            ], colWidths=[2*inch, 1.5*inch, 2*inch], style=TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#374151')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
            ])),
            Spacer(1, 20),
            Paragraph("Qualitative Insights", heading_style),
            Table([
                ['Aspect', 'Assessment'],
                ['Team Strength', startup.team_strength or 'No data available'],
                ['Market Position', startup.market_position or 'No data available'],
                ['Brand Reputation', startup.brand_reputation or 'No data available'],
            ], colWidths=[2*inch, 4*inch], style=TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#374151')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
            ])),
            Spacer(1, 30),
            HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e5e7eb')),
            Spacer(1, 12),
            Paragraph(f"Generated on {timezone.now().strftime('%B %d, %Y at %I:%M %p')} | Investment Analysis Report", footer_style)
        ]

        doc.build(story)
        buffer.seek(0)
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{startup.company_name}_profile.pdf"'
        return response

def get_risk_level_text(confidence):
    if confidence == 'High':
        return 'Low Risk'
    elif confidence == 'Medium':
        return 'Medium Risk'
    else:
        return 'High Risk'

def get_risk_rating(score):
    if score <= 2.0:
        return 'Low Risk'
    elif score <= 3.5:
        return 'Moderate Risk'
    else:
        return 'High Risk'

def get_reward_rating(score):
    if score >= 4.0:
        return 'High Potential'
    elif score >= 3.0:
        return 'Moderate Potential'
    else:
        return 'Limited Potential'


# Module 2 - Investor Tools
# def compare_startups(request):
#     # Ensure user is logged in
#     django_user = get_django_user_from_session(request)
#     if not django_user:
#         return redirect('login')

#     # Get all startups instead of just the watchlist
#     startups = Startup.objects.all()
#     print(f"Total startups found: {startups.count()}")

#     # Optional: Calculate projected return and reward potential for display (just like in the dashboard)
#     for s in startups:
#         # Check if this is a deck builder startup
#         is_deck_builder = hasattr(s, 'source_deck') and s.source_deck is not None
        
#         # Calculate projected return
#         try:
#             if is_deck_builder:
#                 # For deck builder startups, calculate projected return from financial projections
#                 deck = s.source_deck
#                 financials = deck.financials.order_by('year')
                
#                 if financials.count() >= 2:
#                     # Calculate growth rate from first to last year
#                     first_year = financials.first()
#                     last_year = financials.last()
                    
#                     # Convert to float and check for positive values
#                     first_revenue = float(first_year.revenue) if first_year.revenue else 0
#                     last_revenue = float(last_year.revenue) if last_year.revenue else 0
                    
#                     if first_revenue > 0 and last_revenue > 0:
#                         years_span = last_year.year - first_year.year
#                         if years_span > 0:
#                             # Calculate CAGR (Compound Annual Growth Rate)
#                             growth_rate = (last_revenue / first_revenue) ** (1/years_span) - 1
#                             s.projected_return = round(growth_rate * 100, 2)
#                         else:
#                             # Same year data, calculate simple growth if different values
#                             if last_revenue != first_revenue and first_revenue > 0:
#                                 simple_growth = ((last_revenue - first_revenue) / first_revenue) * 100
#                                 s.projected_return = round(simple_growth, 2)
#                             else:
#                                 s.projected_return = 0.0  # No growth
#                     else:
#                         # If no positive revenue in first/last, try to find any positive growth pattern
#                         positive_revenues = [float(f.revenue) for f in financials if f.revenue and float(f.revenue) > 0]
#                         if len(positive_revenues) >= 2:
#                             # Use average growth rate as fallback
#                             avg_growth = sum(positive_revenues) / len(positive_revenues)
#                             s.projected_return = round(min(avg_growth / 1000, 50.0), 2)  # Conservative estimate
#                         else:
#                             s.projected_return = 5.0  # Default moderate return for deck builders
#                 elif financials.count() == 1:
#                     # Only one year of data, use a moderate default
#                     single_revenue = float(financials.first().revenue) if financials.first().revenue else 0
#                     if single_revenue > 0:
#                         s.projected_return = 15.0  # Moderate growth assumption for new startups
#                     else:
#                         s.projected_return = 8.0  # Conservative estimate
#                 else:
#                     # No financial data, use default for deck builders
#                     s.projected_return = 12.0  # Default moderate return for deck builders
#             else:
#                 # For regular startups, use existing calculation
#                 if s.revenue and s.total_assets and s.total_assets > 0:
#                     s.projected_return = round((s.revenue / s.total_assets) * 100, 2)
#                 else:
#                     s.projected_return = None
#         except Exception as e:
#             # If any error occurs, provide fallback values
#             if is_deck_builder:
#                 s.projected_return = 10.0  # Safe fallback for deck builders
#             else:
#                 s.projected_return = None

#         # Calculate reward potential
#         try:
#             reward_score = 3.0  # Default moderate reward
            
#             if is_deck_builder:
#                 # For deck builder startups, calculate based on deck financial data
#                 deck = s.source_deck
#                 financials = deck.financials.order_by('year')
                
#                 if financials.exists():
#                     # Calculate average profit margin across all years
#                     total_revenue = sum(float(f.revenue) for f in financials if f.revenue > 0)
#                     total_profit = sum(float(f.profit) for f in financials)
                    
#                     if total_revenue > 0:
#                         avg_profit_margin = total_profit / total_revenue
                        
#                         # Apply the reward scoring based on average profit margin
#                         if avg_profit_margin > 0.2:  # 20%+ profit margin
#                             reward_score = 4.5  # High reward potential
#                         elif avg_profit_margin > 0.1:  # 10-20% profit margin
#                             reward_score = 3.5  # Good reward
#                         elif avg_profit_margin > 0:  # 0-10% profit margin
#                             reward_score = 2.5  # Fair reward
#                         else:  # Negative profit margin
#                             reward_score = 2.0  # Low reward
#                     else:
#                         # No revenue data, check if there's projected growth in financials
#                         future_revenue = sum(float(f.revenue) for f in financials if f.year > 2025 and f.revenue > 0)
#                         if future_revenue > 0:
#                             reward_score = 3.0  # Moderate potential for future growth
#                         else:
#                             reward_score = 2.0  # Low potential
#             else:
#                 # For regular startups, use existing logic
#                 if s.revenue and s.net_income:
#                     revenue = float(s.revenue)
#                     net_income = float(s.net_income)
#                     if revenue > 0:
#                         profit_margin = net_income / revenue
#                         if profit_margin > 0.2:
#                             reward_score = 4.5
#                         elif profit_margin > 0.1:
#                             reward_score = 3.5
#                         elif profit_margin > 0:
#                             reward_score = 2.5
#                         else:
#                             reward_score = 2.0
            
#             s.reward_potential = round(reward_score, 1)
#         except:
#             s.reward_potential = 3.0

#     return render(request, 'Module_2/Compare_Startups.html', {
#         'startups': startups
#     })

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
# HeLper functions for calculations
def calculate_projected_return(startup):
    try:
        if hasattr(startup, 'source_deck') and startup.source_deck:
            deck = startup.source_deck
            financials = deck.financials.order_by('year')

            if financials.count() >= 2:
                first = financials.first()
                last = financials.last()
                first_rev = float(first.revenue or 0)
                last_rev = float(last.revenue or 0)

                if first_rev > 0 and last_rev > 0:
                    span = last.year - first.year
                    if span > 0:
                        cagr = (last_rev / first_rev) ** (1 / span) - 1
                        return round(cagr * 100, 2)
                    elif last_rev != first_rev:
                        return round(((last_rev - first_rev) / first_rev) * 100, 2)
                else:
                    pos_revs = [float(f.revenue) for f in financials if f.revenue and float(f.revenue) > 0]
                    if len(pos_revs) >= 2:
                        avg_growth = sum(pos_revs) / len(pos_revs)
                        return round(min(avg_growth / 1000, 50.0), 2)
                    return 5.0
            elif financials.count() == 1:
                rev = float(financials.first().revenue or 0)
                return 15.0 if rev > 0 else 8.0
            else:
                return 12.0
        else:
            if startup.revenue and startup.total_assets and startup.total_assets > 0:
                return round((startup.revenue / startup.total_assets) * 100, 2)
    except Exception:
        return 10.0 if hasattr(startup, 'source_deck') else None

def calculate_reward_potential(startup):
    try:
        if hasattr(startup, 'source_deck') and startup.source_deck:
            deck = startup.source_deck
            financials = deck.financials.order_by('year')

            if financials.exists():
                total_rev = sum(float(f.revenue or 0) for f in financials)
                total_profit = sum(float(f.profit or 0) for f in financials)

                if total_rev > 0:
                    margin = total_profit / total_rev
                    if margin > 0.2:
                        return 4.5, 'Medium', True
                    elif margin > 0.1:
                        return 3.5, 'Medium', True
                    elif margin > 0:
                        return 2.5, 'Medium', True
                    else:
                        return 2.0, 'Medium', True
                else:
                    future_rev = sum(float(f.revenue or 0) for f in financials if f.year > 2025)
                    return (3.0 if future_rev > 0 else 2.0), 'Medium', True
            return 3.0, 'Medium', True
        else:
            if startup.revenue and startup.net_income:
                rev = float(startup.revenue or 0)
                income = float(startup.net_income or 0)
                if rev > 0:
                    margin = income / rev
                    if margin > 0.2:
                        return 4.5, startup.data_source_confidence, False
                    elif margin > 0.1:
                        return 3.5, startup.data_source_confidence, False
                    elif margin > 0:
                        return 2.5, startup.data_source_confidence, False
                    else:
                        return 2.0, startup.data_source_confidence, False
        return 3.0, getattr(startup, 'data_source_confidence', 'Medium'), False
    except Exception:
        return 3.0, getattr(startup, 'data_source_confidence', 'Medium'), False

# def export_startup_comparison_pdf(request):
#     """Export startup comparison as PDF"""
#     # Get Django user from session
#     django_user = get_django_user_from_session(request)
#     if not django_user:
#         return JsonResponse({'error': 'Please log in to continue'}, status=401)
    
#     startup_ids = request.GET.get('startups', '')
    
#     if not startup_ids:
#         return JsonResponse({'error': 'No startups selected'}, status=400)
    
#     # Parse startup IDs
#     try:
#         startup_ids = [int(id.strip()) for id in startup_ids.split(',') if id.strip()]
#     except ValueError:
#         return JsonResponse({'error': 'Invalid startup IDs'}, status=400)
    
#     if len(startup_ids) < 2 or len(startup_ids) > 3:
#         return JsonResponse({'error': 'Select 2-3 startups for comparison'}, status=400)
    
#     # Get startups that are in user's watchlist
#     watchlist_startup_ids = Watchlist.objects.filter(
#         user=django_user
#     ).values_list('startup_id', flat=True)
    
#     # Filter to only include startups in user's watchlist
#     valid_startup_ids = [id for id in startup_ids if id in watchlist_startup_ids]
    
#     if len(valid_startup_ids) < 2:
#         return JsonResponse({'error': 'Invalid startup selection'}, status=400)
    
#     # Get the startups with calculated metrics
#     startups = []
#     for startup_id in valid_startup_ids:
#         try:
#             startup = Startup.objects.get(id=startup_id)
            
#             # Check if this is a deck builder startup
#             is_deck_builder = hasattr(startup, 'source_deck') and startup.source_deck is not None
            
#             # Calculate projected return
#             try:
#                 if is_deck_builder:
#                     # For deck builder startups, calculate projected return from financial projections
#                     deck = startup.source_deck
#                     financials = deck.financials.order_by('year')
                    
#                     if financials.count() >= 2:
#                         # Calculate growth rate from first to last year
#                         first_year = financials.first()
#                         last_year = financials.last()
                        
#                         # Convert to float and check for positive values
#                         first_revenue = float(first_year.revenue) if first_year.revenue else 0
#                         last_revenue = float(last_year.revenue) if last_year.revenue else 0
                        
#                         if first_revenue > 0 and last_revenue > 0:
#                             years_span = last_year.year - first_year.year
#                             if years_span > 0:
#                                 # Calculate CAGR (Compound Annual Growth Rate)
#                                 growth_rate = (last_revenue / first_revenue) ** (1/years_span) - 1
#                                 startup.projected_return = round(growth_rate * 100, 2)
#                             else:
#                                 # Same year data, calculate simple growth if different values
#                                 if last_revenue != first_revenue and first_revenue > 0:
#                                     simple_growth = ((last_revenue - first_revenue) / first_revenue) * 100
#                                     startup.projected_return = round(simple_growth, 2)
#                                 else:
#                                     startup.projected_return = 0.0  # No growth
#                         else:
#                             startup.projected_return = 5.0  # Default moderate return for deck builders
#                     elif financials.count() == 1:
#                         # Only one year of data, use a moderate default
#                         startup.projected_return = 15.0  # Moderate growth assumption for new startups
#                     else:
#                         startup.projected_return = 12.0  # Default moderate return for deck builders
#                 else:
#                     # For regular startups, use existing calculation
#                     if startup.revenue and startup.total_assets and startup.total_assets > 0:
#                         startup.projected_return = round((startup.revenue / startup.total_assets) * 100, 2)
#                     else:
#                         startup.projected_return = 8.0  # Default fallback for regular startups
#             except Exception as e:
#                 # If any error occurs, provide fallback values
#                 if is_deck_builder:
#                     startup.projected_return = 10.0  # Safe fallback for deck builders
#                 else:
#                     startup.projected_return = 8.0  # Safe fallback for regular startups
            
#             # Calculate reward potential
#             try:
#                 reward_score = 3.0  # Default moderate reward
                
#                 if is_deck_builder:
#                     # For deck builder startups, calculate based on deck financial data
#                     deck = startup.source_deck
#                     financials = deck.financials.order_by('year')
                    
#                     if financials.exists():
#                         # Calculate average profit margin across all years
#                         total_revenue = sum(float(f.revenue) for f in financials if f.revenue > 0)
#                         total_profit = sum(float(f.profit) for f in financials)
                        
#                         if total_revenue > 0:
#                             avg_profit_margin = total_profit / total_revenue
                            
#                             # Apply the reward scoring based on average profit margin
#                             if avg_profit_margin > 0.2:  # 20%+ profit margin
#                                 reward_score = 4.5  # High reward potential
#                             elif avg_profit_margin > 0.1:  # 10-20% profit margin
#                                 reward_score = 3.5  # Good reward
#                             elif avg_profit_margin > 0:  # 0-10% profit margin
#                                 reward_score = 2.5  # Fair reward
#                             else:  # Negative profit margin
#                                 reward_score = 2.0  # Low reward
#                         else:
#                             # No revenue data, check if there's projected growth in financials
#                             future_revenue = sum(float(f.revenue) for f in financials if f.year > 2025 and f.revenue > 0)
#                             if future_revenue > 0:
#                                 reward_score = 3.0  # Moderate potential for future growth
#                             else:
#                                 reward_score = 2.0  # Low potential
#                 else:
#                     # For regular startups, use existing logic
#                     if startup.revenue and startup.net_income:
#                         revenue = float(startup.revenue) if startup.revenue else 0
#                         net_income = float(startup.net_income) if startup.net_income else 0
                        
#                         if revenue > 0:
#                             profit_margin = net_income / revenue
                            
#                             if profit_margin > 0.2:
#                                 reward_score = 4.5
#                             elif profit_margin > 0.1:
#                                 reward_score = 3.5
#                             elif profit_margin > 0:
#                                 reward_score = 2.5
#                             else:
#                                 reward_score = 2.0
                    
#                 startup.reward_potential = round(reward_score, 1)
#             except:
#                 startup.reward_potential = 3.0
            
#             # Add risk level
#             startup.risk_level = get_risk_level(startup.data_source_confidence)
#             startups.append(startup)
#         except Startup.DoesNotExist:
#             continue
    
#     if len(startups) < 2:
#         return JsonResponse({'error': 'Insufficient startups for comparison'}, status=400)
    
#     # Generate PDF
#     try:
#         pdf_buffer = generate_comparison_pdf(startups, django_user)
        
#         # Create HTTP response
#         response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
#         response['Content-Disposition'] = f'attachment; filename="startup_comparison_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
        
#         return response
        
#     except Exception as e:
#         return JsonResponse({'error': f'PDF generation failed: {str(e)}'}, status=500)



class export_startup_comparison_pdf(APIView):
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

        watchlist_ids = Watchlist.objects.filter(user=request.user).values_list('startup_id', flat=True)
        valid_ids = [id for id in startup_ids if id in watchlist_ids]

        if len(valid_ids) < 2:
            return Response({'error': 'Invalid startup selection'}, status=400)

        startups = []
        for sid in valid_ids:
            try:
                startup = Startup.objects.get(id=sid)
                startup.projected_return = calculate_projected_return(startup)
                reward, risk_label, _ = calculate_reward_potential(startup)
                startup.reward_potential = reward
                startup.risk_level = get_risk_level(startup.data_source_confidence)
                startups.append(startup)
            except Startup.DoesNotExist:
                continue

        if len(startups) < 2:
            return Response({'error': 'Insufficient startups for comparison'}, status=400)

        try:
            pdf_buffer = generate_comparison_pdf(startups, request.user)
            response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
            timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
            response['Content-Disposition'] = f'attachment; filename="startup_comparison_{timestamp}.pdf"'
            return response
        except Exception as e:
            return Response({'error': f'PDF generation failed: {str(e)}'}, status=500)

def generate_comparison_pdf(startups, user):
    """Generate PDF comparison report"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, 
                          rightMargin=72, leftMargin=72,
                          topMargin=72, bottomMargin=18)
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#1f2937')
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=20,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#6b7280')
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=12,
        textColor=colors.HexColor('#374151')
    )
    
    # Build PDF content
    story = []
    
    # Title
    story.append(Paragraph("Startup Comparison Report", title_style))
    story.append(Paragraph(f"Generated on {timezone.now().strftime('%B %d, %Y')}", subtitle_style))
    story.append(Spacer(1, 20))
    
    # Company Overview Section
    story.append(Paragraph("Company Overview", heading_style))
    
    # Company overview table
    overview_data = [['Company', 'Industry', 'Risk Level']]
    for startup in startups:
        overview_data.append([
            startup.company_name,
            startup.industry or 'Unknown',
            startup.risk_level
        ])
    
    overview_table = Table(overview_data, colWidths=[2.5*inch, 2*inch, 1.5*inch])
    overview_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1f2937')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')])
    ]))
    
    story.append(overview_table)
    story.append(Spacer(1, 30))
    
    # Financial Metrics Section
    story.append(Paragraph("Financial Metrics Comparison", heading_style))
    
    # Financial metrics table
    metrics_data = [['Metric'] + [startup.company_name for startup in startups]]
    
    # Projected Return row
    projected_returns = [f"+{startup.projected_return}%" for startup in startups]
    metrics_data.append(['Projected Return'] + projected_returns)
    
    # Reward Potential row
    reward_potentials = [f"{startup.reward_potential}/5" for startup in startups]
    metrics_data.append(['Reward Potential'] + reward_potentials)
    
    # Data Confidence row
    data_confidence = [getattr(startup, 'data_source_confidence', 'Medium') for startup in startups]
    metrics_data.append(['Data Confidence'] + data_confidence)
    
    # Calculate column widths
    num_startups = len(startups)
    company_col_width = 4.5 / num_startups
    metrics_table = Table(metrics_data, colWidths=[1.5*inch] + [company_col_width*inch] * num_startups)
    
    # Apply table styling
    metrics_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1f2937')),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')])
    ]))
    
    story.append(metrics_table)
    story.append(Spacer(1, 30))
    
    # Individual Company Details
    story.append(Paragraph("Detailed Company Information", heading_style))
    
    for i, startup in enumerate(startups):
        if i > 0:
            story.append(Spacer(1, 20))
        
        # Company name
        company_style = ParagraphStyle(
            'CompanyName',
            parent=styles['Heading3'],
            fontSize=12,
            spaceAfter=10,
            textColor=colors.HexColor('#1f2937')
        )
        story.append(Paragraph(f"{startup.company_name}", company_style))
        
        # Company details
        details_data = [
            ['Industry:', startup.industry or 'Unknown'],
            ['Projected Return:', f"+{startup.projected_return}%"],
            ['Reward Potential:', f"{startup.reward_potential}/5"],
            ['Data Confidence:', getattr(startup, 'data_source_confidence', 'Medium')],
            ['Risk Level:', startup.risk_level]
        ]
        
        details_table = Table(details_data, colWidths=[1.5*inch, 3*inch])
        details_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3)
        ]))
        
        story.append(details_table)
    
    # Footer
    story.append(Spacer(1, 40))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#6b7280')
    )
    story.append(Paragraph("Generated by Fundora - Startup Investment Platform", footer_style))
    story.append(Paragraph(f"Report created for {user.username} on {timezone.now().strftime('%B %d, %Y at %I:%M %p')}", footer_style))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer

def get_risk_level(confidence):
    """Helper function to get risk level based on confidence"""
    if confidence == 'High':
        return 'Low Risk'
    elif confidence == 'Medium':
        return 'Medium Risk'
    else:
        return 'High Risk'

# def startup_comparison(request):
#     """Display detailed comparison of selected startups"""
#     django_user = get_django_user_from_session(request)
#     if not django_user:
#         return redirect('login')

#     startup_ids = request.GET.get('startups', '')

#     if not startup_ids:
#         return redirect('compare_startups')

#     try:
#         startup_ids = [int(id.strip()) for id in startup_ids.split(',') if id.strip()]
#     except ValueError:
#         return redirect('compare_startups')

#     if len(startup_ids) < 2 or len(startup_ids) > 3:
#         return redirect('compare_startups')

#     startups = []
#     for startup_id in startup_ids:
#         try:
#             startup = Startup.objects.get(id=startup_id)
            
#             # Check if this is a deck builder startup
#             is_deck_builder = hasattr(startup, 'source_deck') and startup.source_deck is not None

#             # Calculate projected return
#             try:
#                 if is_deck_builder:
#                     # For deck builder startups, calculate projected return from financial projections
#                     deck = startup.source_deck
#                     financials = deck.financials.order_by('year')
                    
#                     if financials.count() >= 2:
#                         # Calculate growth rate from first to last year
#                         first_year = financials.first()
#                         last_year = financials.last()
                        
#                         # Convert to float and check for positive values
#                         first_revenue = float(first_year.revenue) if first_year.revenue else 0
#                         last_revenue = float(last_year.revenue) if last_year.revenue else 0
                        
#                         if first_revenue > 0 and last_revenue > 0:
#                             years_span = last_year.year - first_year.year
#                             if years_span > 0:
#                                 # Calculate CAGR (Compound Annual Growth Rate)
#                                 growth_rate = (last_revenue / first_revenue) ** (1/years_span) - 1
#                                 startup.projected_return = round(growth_rate * 100, 2)
#                             else:
#                                 # Same year data, calculate simple growth if different values
#                                 if last_revenue != first_revenue and first_revenue > 0:
#                                     simple_growth = ((last_revenue - first_revenue) / first_revenue) * 100
#                                     startup.projected_return = round(simple_growth, 2)
#                                 else:
#                                     startup.projected_return = 0.0  # No growth
#                         else:
#                             startup.projected_return = 5.0  # Default moderate return for deck builders
#                     elif financials.count() == 1:
#                         # Only one year of data, use a moderate default
#                         startup.projected_return = 15.0  # Moderate growth assumption for new startups
#                     else:
#                         startup.projected_return = 12.0  # Default moderate return for deck builders
#                 else:
#                     # For regular startups, use existing calculation
#                     if startup.revenue and startup.total_assets and startup.total_assets > 0:
#                         startup.projected_return = round((startup.revenue / startup.total_assets) * 100, 2)
#                     else:
#                         startup.projected_return = None
#             except Exception as e:
#                 # If any error occurs, provide fallback values
#                 if is_deck_builder:
#                     startup.projected_return = 10.0  # Safe fallback for deck builders
#                 else:
#                     startup.projected_return = None

#             # Calculate reward potential
#             try:
#                 reward_score = 3.0  # Default moderate reward
                
#                 if is_deck_builder:
#                     # For deck builder startups, calculate based on deck financial data
#                     deck = startup.source_deck
#                     financials = deck.financials.order_by('year')
                    
#                     if financials.exists():
#                         # Calculate average profit margin across all years
#                         total_revenue = sum(float(f.revenue) for f in financials if f.revenue > 0)
#                         total_profit = sum(float(f.profit) for f in financials)
                        
#                         if total_revenue > 0:
#                             avg_profit_margin = total_profit / total_revenue
                            
#                             # Apply the reward scoring based on average profit margin
#                             if avg_profit_margin > 0.2:  # 20%+ profit margin
#                                 reward_score = 4.5  # High reward potential
#                             elif avg_profit_margin > 0.1:  # 10-20% profit margin
#                                 reward_score = 3.5  # Good reward
#                             elif avg_profit_margin > 0:  # 0-10% profit margin
#                                 reward_score = 2.5  # Fair reward
#                             else:  # Negative profit margin
#                                 reward_score = 2.0  # Low reward
#                         else:
#                             # No revenue data, use default
#                             reward_score = 2.0  # Low potential
#                 else:
#                     # For regular startups, use existing logic
#                     if startup.revenue and startup.net_income:
#                         revenue = float(startup.revenue)
#                         net_income = float(startup.net_income)
#                         if revenue > 0:
#                             profit_margin = net_income / revenue
#                             if profit_margin > 0.2:
#                                 reward_score = 4.5
#                             elif profit_margin > 0.1:
#                                 reward_score = 3.5
#                             elif profit_margin > 0:
#                                 reward_score = 2.5
#                             else:
#                                 reward_score = 2.0
                    
#                 startup.reward_potential = round(reward_score, 1)
#             except:
#                 startup.reward_potential = 3.0

#             # Calculate risk score
#             try:
#                 confidence_level = getattr(startup, 'data_source_confidence', 'Medium')
                
#                 if confidence_level == 'Low':
#                     # For low confidence, use fixed risk score (matching health report)
#                     risk_score = 2.0
#                 else:
#                     # For high/medium confidence, calculate based on profit margin (matching health report)
#                     risk_score = 2.5  # Default
                    
#                     if startup.revenue and startup.net_income:
#                         revenue = float(startup.revenue)
#                         net_income = float(startup.net_income)
                        
#                         if revenue > 0:
#                             profit_margin = net_income / revenue
                            
#                             if profit_margin > 0.2:
#                                 risk_score = 2.0  # Low risk for high profit margin
#                             elif profit_margin > 0.1:
#                                 risk_score = 2.5  # Medium-low risk
#                             elif profit_margin > 0:
#                                 risk_score = 3.5  # Medium-high risk
#                             else:
#                                 risk_score = 4.5  # High risk for negative profit margin
#                         elif net_income < 0:
#                             # Negative income with no revenue = very high risk
#                             risk_score = 4.5
                
#                 startup.risk_score = round(max(min(risk_score, 5.0), 1.0), 1)
#             except:
#                 startup.risk_score = 3.0

#             startup.risk_level = get_risk_level(startup.data_source_confidence)
#             startup.risk_color = get_risk_color(startup.data_source_confidence)
#             startups.append(startup)
#         except Startup.DoesNotExist:
#             continue

#     if len(startups) < 2:
#         return redirect('compare_startups')

#     comparison_session_id = str(uuid.uuid4())
#     for startup in startups:
#         StartupComparison.objects.create(
#             user=django_user,
#             startup=startup,
#             comparison_set_id=comparison_session_id
#         )

#     sorted_startup_ids = sorted([s.id for s in startups])
#     existing_comparison = None
#     for comparison_set in ComparisonSet.objects.filter(user=django_user):
#         comparison_startup_ids = sorted(comparison_set.startups.values_list('id', flat=True))
#         if comparison_startup_ids == sorted_startup_ids:
#             existing_comparison = comparison_set
#             break

#     if existing_comparison:
#         comparison_set = existing_comparison
#     else:
#         comparison_set = ComparisonSet.objects.create(user=django_user)
#         comparison_set.startups.set(startups)

#     comparison_data = {
#         'startups': startups,
#         'startup_count': len(startups),
#         'comparison_set': comparison_set,
#     }

#     return render(request, 'Module_2/Startup_Comparison.html', comparison_data)

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

        # Build response
        startup_data = [{
            "id": s.id,
            "company_name": s.company_name,
            "industry": s.industry,
            "projected_return": s.projected_return,
            "reward_potential": s.reward_potential,
            "risk_score": s.risk_score,
            "risk_level": s.risk_level,
            "risk_color": s.risk_color,
            "confidence": getattr(s, 'data_source_confidence', 'Medium')
        } for s in startups]

        return Response({
            "startups": startup_data,
            "startup_count": len(startups),
            "comparison_set_id": comparison_set.id
        }, status=200)

# Analytics helper functions
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

# def investment_simulation(request, startup_id=None):
#     # Check if user is logged in via session
#     if not request.session.get('user_id'):
#         return redirect('login')
    
#     # Get startup info if startup_id is provided
#     selected_startup = None
#     if startup_id:
#         selected_startup = get_object_or_404(Startup, id=startup_id)
#         # Store in session for subsequent requests
#         request.session['selected_startup_id'] = startup_id
#         request.session['selected_startup_name'] = selected_startup.company_name
#         request.session['selected_startup_industry'] = selected_startup.industry or "N/A"
#     elif request.session.get('selected_startup_id'):
#         # Try to get from session if no startup_id in URL
#         try:
#             selected_startup = Startup.objects.get(id=request.session['selected_startup_id'])
#         except Startup.DoesNotExist:
#             # Clear invalid session data
#             request.session.pop('selected_startup_id', None)
#             request.session.pop('selected_startup_name', None)
#             request.session.pop('selected_startup_industry', None)

#     if request.method == 'POST':
#         # Get form data with validation
#         try:
#             investment_amount = float(request.POST.get('investment_amount', 0))
#             duration_years = int(request.POST.get('duration_years', 1))
#             growth_rate = 0.05  # Fixed at 5% - cannot be changed by user
            
#             # Validation
#             if investment_amount <= 0:
#                 raise ValueError("Investment amount must be positive")
#             if duration_years <= 0:
#                 raise ValueError("Duration must be positive")
#             if growth_rate < -1:
#                 raise ValueError("Growth rate cannot be less than -100%")
                
#         except (ValueError, TypeError) as e:
#             context = {
#                 'error': str(e),
#                 'simulation_run': False,
#                 'selected_startup': selected_startup,
#                 'startup_name': request.session.get('selected_startup_name', 'Investment'),
#                 'startup_industry': request.session.get('selected_startup_industry', 'General')
#             }
#             return render(request, 'Module_2/Investment_Simulation.html', context)

#         # Calculate compound interest
#         final_value = investment_amount * (1 + growth_rate) ** duration_years
#         total_gain = final_value - investment_amount
#         roi_percentage = (total_gain / investment_amount) * 100 if investment_amount > 0 else 0

#         # Calculate year-by-year breakdown
#         yearly_breakdown = []
#         current_value = investment_amount
        
#         for year in range(1, duration_years + 1):
#             starting_value = current_value
#             growth_amount = current_value * growth_rate
#             ending_value = starting_value + growth_amount
            
#             yearly_breakdown.append({
#                 'year': year,
#                 'starting_value': starting_value,
#                 'growth_amount': growth_amount,
#                 'ending_value': ending_value
#             })
#             current_value = ending_value

#         # Risk assessment based on growth rate
#         if growth_rate <= 0.05:  # 5% or less
#             risk_level = "Low Risk"
#             risk_color = "bg-green-100 text-green-800"
#         elif growth_rate <= 0.10:  # 5-10%
#             risk_level = "Medium Risk"
#             risk_color = "bg-yellow-100 text-yellow-800"
#         else:  # Above 10%
#             risk_level = "High Risk"
#             risk_color = "bg-red-100 text-red-800"

#         # Generate chart data for visualization
#         chart_data = []
#         temp_value = investment_amount
#         chart_data.append({'year': 0, 'value': investment_amount})
        
#         for year in range(1, duration_years + 1):
#             temp_value = temp_value * (1 + growth_rate)
#             chart_data.append({'year': year, 'value': temp_value})

#         context = {
#             'simulation_run': True,
#             'investment_amount': investment_amount,
#             'duration_years': duration_years,
#             'growth_rate': growth_rate * 100,  # Convert back to percentage for display
#             'final_value': final_value,
#             'total_gain': total_gain,
#             'roi_percentage': roi_percentage,
#             'yearly_breakdown': yearly_breakdown,
#             'risk_level': risk_level,
#             'risk_color': risk_color,
#             'chart_data': chart_data,
#             'selected_startup': selected_startup,
#             'startup_name': request.session.get('selected_startup_name', 'Investment'),
#             'startup_industry': request.session.get('selected_startup_industry', 'General')
#         }
        
#         return render(request, 'Module_2/Investment_Simulation.html', context)
    
#     else:
#         # Default values for GET request
#         context = {
#             'simulation_run': False,
#             'investment_amount': 1000,
#             'duration_years': 1,
#             'growth_rate': 5,  # Fixed at 5%
#             'risk_level': "Low Risk",
#             'risk_color': "bg-green-100 text-green-800",
#             'selected_startup': selected_startup,
#             'startup_name': request.session.get('selected_startup_name', 'Investment'),
#             'startup_industry': request.session.get('selected_startup_industry', 'General')
#         }
#         return render(request, 'Module_2/Investment_Simulation.html', context)

class investment_simulation(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        startup_id = request.data.get('startup_id')
        investment_amount = request.data.get('investment_amount', 1000)
        duration_years = request.data.get('duration_years', 1)
        growth_rate = 0.05  # Fixed

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

        final_value = investment_amount * (1 + growth_rate) ** duration_years
        total_gain = final_value - investment_amount
        roi_percentage = (total_gain / investment_amount) * 100

        yearly_breakdown = []
        current_value = investment_amount
        for year in range(1, duration_years + 1):
            growth = current_value * growth_rate
            ending = current_value + growth
            yearly_breakdown.append({
                "year": year,
                "starting_value": current_value,
                "growth_amount": growth,
                "ending_value": ending
            })
            current_value = ending

        chart_data = [{"year": 0, "value": investment_amount}]
        temp_value = investment_amount
        for year in range(1, duration_years + 1):
            temp_value *= (1 + growth_rate)
            chart_data.append({"year": year, "value": temp_value})

        if growth_rate <= 0.05:
            risk_level = "Low Risk"
            risk_color = "bg-green-100 text-green-800"
        elif growth_rate <= 0.10:
            risk_level = "Medium Risk"
            risk_color = "bg-yellow-100 text-yellow-800"
        else:
            risk_level = "High Risk"
            risk_color = "bg-red-100 text-red-800"

        return Response({
            "simulation_run": True,
            "investment_amount": investment_amount,
            "duration_years": duration_years,
            "growth_rate": growth_rate * 100,
            "final_value": final_value,
            "total_gain": total_gain,
            "roi_percentage": roi_percentage,
            "yearly_breakdown": yearly_breakdown,
            "chart_data": chart_data,
            "risk_level": risk_level,
            "risk_color": risk_color,
            "startup": {
                "id": selected_startup.id,
                "name": selected_startup.company_name,
                "industry": selected_startup.industry
            } if selected_startup else None
        })

# Additional helper functions for advanced calculations
def calculate_monthly_contributions(principal, monthly_contribution, annual_rate, years):
    """Calculate future value with monthly contributions"""
    monthly_rate = annual_rate / 12
    months = years * 12
    
    # Future value of principal
    fv_principal = principal * (1 + annual_rate) ** years
    
    # Future value of monthly contributions (ordinary annuity)
    if monthly_rate > 0:
        fv_contributions = monthly_contribution * (((1 + monthly_rate) ** months - 1) / monthly_rate)
    else:
        fv_contributions = monthly_contribution * months
    
    return fv_principal + fv_contributions

def calculate_inflation_adjusted_return(nominal_return, inflation_rate, years):
    """Calculate real return adjusted for inflation"""
    real_rate = ((1 + nominal_return) / (1 + inflation_rate)) - 1
    return real_rate

def monte_carlo_simulation(principal, annual_return, volatility, years, simulations=1000):
    """Run Monte Carlo simulation for investment returns"""
    import random
    import math
    
    results = []
    
    for _ in range(simulations):
        value = principal
        for year in range(years):
            # Generate random return based on normal distribution
            random_return = random.normalvariate(annual_return, volatility)
            value *= (1 + random_return)
        results.append(value)
    
    # Calculate statistics
    results.sort()
    
    return {
        'mean': sum(results) / len(results),
        'median': results[len(results) // 2],
        'percentile_10': results[int(len(results) * 0.1)],
        'percentile_25': results[int(len(results) * 0.25)],
        'percentile_75': results[int(len(results) * 0.75)],
        'percentile_90': results[int(len(results) * 0.9)],
        'min': min(results),
        'max': max(results)
    }

@login_required
# def advanced_investment_simulation(request):
#     """Advanced simulation with multiple scenarios"""
#     if request.method == 'POST':
#         # Get form data
#         investment_amount = float(request.POST.get('investment_amount', 0))
#         duration_years = int(request.POST.get('duration_years', 1))
#         growth_rate = float(request.POST.get('growth_rate', 5)) / 100
#         monthly_contribution = float(request.POST.get('monthly_contribution', 0))
#         inflation_rate = float(request.POST.get('inflation_rate', 2)) / 100
        
#         # Basic compound interest calculation
#         final_value = investment_amount * (1 + growth_rate) ** duration_years
        
#         # With monthly contributions
#         if monthly_contribution > 0:
#             final_value_with_contributions = calculate_monthly_contributions(
#                 investment_amount, monthly_contribution, growth_rate, duration_years
#             )
#         else:
#             final_value_with_contributions = final_value
        
#         # Inflation-adjusted calculations
#         real_growth_rate = calculate_inflation_adjusted_return(growth_rate, inflation_rate, 1)
#         inflation_adjusted_value = investment_amount * (1 + real_growth_rate) ** duration_years
        
#         # Monte Carlo simulation (optional, for advanced users)
#         volatility = 0.15  # 15% volatility assumption
#         monte_carlo_results = monte_carlo_simulation(
#             investment_amount, growth_rate, volatility, duration_years
#         )
        
#         context = {
#             'simulation_run': True,
#             'investment_amount': investment_amount,
#             'duration_years': duration_years,
#             'growth_rate': growth_rate * 100,
#             'monthly_contribution': monthly_contribution,
#             'inflation_rate': inflation_rate * 100,
#             'final_value': final_value,
#             'final_value_with_contributions': final_value_with_contributions,
#             'inflation_adjusted_value': inflation_adjusted_value,
#             'monte_carlo_results': monte_carlo_results,
#             'total_contributions': monthly_contribution * 12 * duration_years,
#             'real_growth_rate': real_growth_rate * 100
#         }
        
#         return render(request, 'Module_2/Advanced_Investment_Simulation.html', context)
    
#     return render(request, 'Module_2/Advanced_Investment_Simulation.html')

class advanced_investment_simulation(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            investment_amount = float(request.data.get('investment_amount', 0))
            duration_years = int(request.data.get('duration_years', 1))
            growth_rate = float(request.data.get('growth_rate', 5)) / 100
            monthly_contribution = float(request.data.get('monthly_contribution', 0))
            inflation_rate = float(request.data.get('inflation_rate', 2)) / 100

            if investment_amount <= 0 or duration_years <= 0:
                raise ValueError("Investment amount and duration must be positive")
        except (ValueError, TypeError) as e:
            return Response({"error": str(e)}, status=400)

        final_value = investment_amount * (1 + growth_rate) ** duration_years

        if monthly_contribution > 0:
            final_value_with_contributions = calculate_monthly_contributions(
                investment_amount, monthly_contribution, growth_rate, duration_years
            )
        else:
            final_value_with_contributions = final_value

        real_growth_rate = calculate_inflation_adjusted_return(growth_rate, inflation_rate, 1)
        inflation_adjusted_value = investment_amount * (1 + real_growth_rate) ** duration_years

        volatility = 0.15
        monte_carlo_results = monte_carlo_simulation(
            investment_amount, growth_rate, volatility, duration_years
        )

        total_contributions = monthly_contribution * 12 * duration_years

        return Response({
            "simulation_run": True,
            "investment_amount": investment_amount,
            "duration_years": duration_years,
            "growth_rate": growth_rate * 100,
            "monthly_contribution": monthly_contribution,
            "inflation_rate": inflation_rate * 100,
            "final_value": final_value,
            "final_value_with_contributions": final_value_with_contributions,
            "inflation_adjusted_value": inflation_adjusted_value,
            "monte_carlo_results": monte_carlo_results,
            "total_contributions": total_contributions,
            "real_growth_rate": real_growth_rate * 100
        }, status=200)

# # API endpoint for real-time calculations (if using AJAX)
# @login_required
# def calculate_investment_api(request):
#     """API endpoint for real-time investment calculations"""
#     if request.method == 'POST':
#         import json
        
#         data = json.loads(request.body)
#         investment_amount = float(data.get('investment_amount', 0))
#         duration_years = int(data.get('duration_years', 1))
#         growth_rate = float(data.get('growth_rate', 5)) / 100
        
#         # Calculate results
#         final_value = investment_amount * (1 + growth_rate) ** duration_years
#         total_gain = final_value - investment_amount
#         roi_percentage = (total_gain / investment_amount) * 100
        
#         # Year-by-year breakdown
#         yearly_breakdown = []
#         current_value = investment_amount
        
#         for year in range(1, duration_years + 1):
#             starting_value = current_value
#             growth_amount = current_value * growth_rate
#             ending_value = starting_value + growth_amount
            
#             yearly_breakdown.append({
#                 'year': year,
#                 'starting_value': round(starting_value, 2),
#                 'growth_amount': round(growth_amount, 2),
#                 'ending_value': round(ending_value, 2)
#             })
            
#             current_value = ending_value
        
#         response_data = {
#             'success': True,
#             'final_value': round(final_value, 2),
#             'total_gain': round(total_gain, 2),
#             'roi_percentage': round(roi_percentage, 2),
#             'yearly_breakdown': yearly_breakdown
#         }
        
#         return JsonResponse(response_data)
    
#     return JsonResponse({'success': False, 'error': 'Invalid request method'})

class calculate_investment_api(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            investment_amount = float(request.data.get('investment_amount', 0))
            duration_years = int(request.data.get('duration_years', 1))
            growth_rate = float(request.data.get('growth_rate', 5)) / 100

            if investment_amount <= 0 or duration_years <= 0:
                raise ValueError("Investment amount and duration must be positive")
        except (ValueError, TypeError) as e:
            return Response({'success': False, 'error': str(e)}, status=400)

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
            'yearly_breakdown': yearly_breakdown
        }, status=200)

# def deck_home(request):
#     startup_user_id = request.session.get('startup_user_id')
#     if not startup_user_id:
#         messages.error(request, "You must be logged in as a startup to view your decks.")
#         return redirect('startup_login')

#     owner_instance = get_object_or_404(Registration, id=startup_user_id)
#     decks = Deck.objects.filter(owner=owner_instance).order_by('-created_at')
    
#     return render(request, 'deck-builder.html', {'decks': decks})

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

# def edit_deck(request, deck_id):
#     """Set the deck for editing and redirect to cover-page"""
#     startup_user_id = request.session.get('startup_user_id')
#     if not startup_user_id:
#         messages.error(request, "Authentication required.")
#         return redirect('startup_login')

#     # Verify the deck belongs to the current user
#     try:
#         deck = get_object_or_404(Deck, id=deck_id, owner_id=startup_user_id)
#         # Store the deck ID in session for editing
#         request.session['deck_id'] = deck_id
#         return redirect('deck_section', section='cover-page')
#     except:
#         messages.error(request, "Deck not found or access denied.")
#         return redirect('deck_home')

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

# def delete_deck(request, deck_id):
#     startup_user_id = request.session.get('startup_user_id')
#     if not startup_user_id:
#         messages.error(request, "Authentication required.")
#         return redirect('startup_login')

#     deck = get_object_or_404(Deck, id=deck_id, owner_id=startup_user_id)
    
#     if request.method == 'POST':
#         deck.delete()
#         messages.success(request, "Deck deleted successfully.")
#         return redirect('deck_home')
    
#     # If it's a GET request, you could show a confirmation page,
#     # but for simplicity, we'll just redirect.
#     return redirect('deck_home')

class delete_deck(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request, deck_id):
        try:
            owner = request.user.profile
            deck = get_object_or_404(Deck, id=deck_id, owner=owner)
            deck.delete()
            return Response({'success': True, 'message': 'Deck deleted successfully.'}, status=200)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({'error': str(e)}, status=500)

# Module 3 - Startup User Views
# def startup_registration(request):
#     if request.method == 'POST':
#         form = RegistrationForm(request.POST)
#         if form.is_valid():
#             # Create a new registration instance but don't save yet
#             registration = form.save(commit=False)
            
#             # Hash the password before saving
#             registration.password = make_password(form.cleaned_data['password'])
            
#             # Set the label to 'startup' for startup registration
#             registration.label = 'startup'
            
#             # Save the registration
#             registration.save()
            
#             # Add success message
#             messages.success(request, 'Registration successful! Please log in with your credentials.')
            
#             # Redirect to startup login page
#             return redirect('startup_login')
#         else:
#             # If form has errors, they will be displayed in the template
#             messages.error(request, 'Please correct the errors below.')
#     else:
#         form = RegistrationForm()
    
#     return render(request, 'Module_3/StartUp_Registration.html', {'form': form})

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

# Module 3 - Startup Registration Views

# def added_startups(request):
#     # Check if user is logged in and is a startup
#     startup_user_id = request.session.get('startup_user_id')
#     if not startup_user_id or request.session.get('user_label') != 'startup':
#         messages.error(request, 'Please log in as a startup to access this page.')
#         return redirect('startup_login')
    
#     # Get the current user
#     try:
#         user = Registration.objects.get(id=startup_user_id)
#         # Get all startups owned by this user
#         startups = Startup.objects.filter(owner=user)
        
#         # Add analytics data to each startup
#         startups_with_analytics = []
#         for startup in startups:
#             analytics = get_startup_analytics(startup)
#             startup.analytics = analytics
#             startups_with_analytics.append(startup)
            
#     except Registration.DoesNotExist:
#         messages.error(request, 'User not found.')
#         return redirect('startup_login')
    
#     return render(request, 'Module_3/Added_Startups.html', {'startups': startups_with_analytics})

class added_startups(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = request.user.profile  # via related_name='profile'
        except RegisteredUser.DoesNotExist:
            return Response({'error': 'Startup profile not found.'}, status=403)

        if profile.label != 'startup':
            return Response({'error': 'You must be logged in as a startup to access this page.'}, status=403)

        startups = Startup.objects.filter(owner=profile)

        enriched_data = []
        for startup in startups:
            analytics = get_startup_analytics(startup)
            serialized = StartupSerializer(startup).data
            serialized['analytics'] = analytics
            enriched_data.append(serialized)

        return Response({'startups': enriched_data}, status=200)

# def user_logout(request):
#     # Clear session
#     request.session.flush()
#     messages.success(request, 'You have been logged out successfully.')
    
#     # Redirect all users to the main login page
#     return redirect('login')

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

# def company_information_form(request):
#     # Check if user is logged in and is a startup
#     startup_user_id = request.session.get('startup_user_id')
#     if not startup_user_id or request.session.get('user_label') != 'startup':
#         messages.error(request, 'Please log in as a startup to access this page.')
#         return redirect('startup_login')
    
#     if request.method == 'POST':
#         # Process the form data here
#         # Store comprehensive form data in session for the health report page
#         company_data = {
#             # Basic company info
#             'company_name': request.POST.get('company-name', '').strip(),
#             'industry': request.POST.get('industry', '').strip(),
#             'company_description': request.POST.get('company-description', '').strip(),
#             'data_source_confidence': request.POST.get('data-source-confidence', 'Medium').strip(),
            
#             # Financial data (for High/Medium confidence)
#             'previous_revenue': request.POST.get('previous-revenue', '').strip(),
#             'current_revenue': request.POST.get('current-revenue', '').strip(),
#             'net_income': request.POST.get('net-income', '').strip(),
#             'total_assets': request.POST.get('total-assets', '').strip(),
#             'total_liabilities': request.POST.get('total-liabilities', '').strip(),
#             'shareholder_equity': request.POST.get('shareholder-equity', '').strip(),
#             'cash_flow': request.POST.get('cash-flow', '').strip(),
            
#             # Qualitative data (for Low confidence)
#             'team_strength': request.POST.get('team-strength', '').strip(),
#             'market_position': request.POST.get('market-position', '').strip(),
#             'brand_reputation': request.POST.get('brand-reputation', '').strip(),
#         }
        
#         request.session['company_data'] = company_data
        
#         # Redirect to health report page
#         return redirect('health_report_page')
    
#     return render(request, 'Module_3/Company_Information_Form.html')

class company_information_form(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        startup_user_id = request.session.get('startup_user_id')
        user_label = request.session.get('user_label')

        if not startup_user_id or user_label != 'startup':
            return Response({'error': 'Please log in as a startup to access this endpoint.'}, status=403)

        data = request.data

        company_data = {
            'company_name': data.get('company_name', '').strip(),
            'industry': data.get('industry', '').strip(),
            'company_description': data.get('company_description', '').strip(),
            'data_source_confidence': data.get('data_source_confidence', 'Medium').strip(),

            # Financial data
            'previous_revenue': data.get('previous_revenue', '').strip(),
            'current_revenue': data.get('current_revenue', '').strip(),
            'net_income': data.get('net_income', '').strip(),
            'total_assets': data.get('total_assets', '').strip(),
            'total_liabilities': data.get('total_liabilities', '').strip(),
            'shareholder_equity': data.get('shareholder_equity', '').strip(),
            'cash_flow': data.get('cash_flow', '').strip(),

            # Qualitative data
            'team_strength': data.get('team_strength', '').strip(),
            'market_position': data.get('market_position', '').strip(),
            'brand_reputation': data.get('brand_reputation', '').strip(),
        }

        request.session['company_data'] = company_data

        return Response({
            'success': True,
            'message': 'Company information saved successfully.',
            'next_step': 'health_report_page'
        }, status=status.HTTP_200_OK)

# def health_report_page(request):
#     # Check if user is logged in and is a startup
#     startup_user_id = request.session.get('startup_user_id')
#     if not startup_user_id or request.session.get('user_label') != 'startup':
#         messages.error(request, 'Please log in as a startup to access this page.')
#         return redirect('startup_login')
    
#     # Get company data from session
#     company_data = request.session.get('company_data', {})
    
#     # Check if we're coming from an edit preview
#     edit_startup_id = request.session.get('edit_startup_id')
    
#     # If no data is found, show an error message
#     if not company_data.get('company_name'):
#         messages.error(request, 'No company data found. Please fill out the company information form first.')
#         return redirect('company_information_form')
    
#     return render(request, 'Module_3/Health_Report_Page.html', {
#         'company_data': company_data,
#         'edit_startup_id': edit_startup_id  # Pass this to determine back button behavior
#     })

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


@require_POST
# def add_startup(request):
#     """Save the startup data from session to database"""
#     # Check if user is logged in and is a startup
#     startup_user_id = request.session.get('startup_user_id')
#     if not startup_user_id or request.session.get('user_label') != 'startup':
#         return JsonResponse({'success': False, 'error': 'Not authenticated'}, status=401)
    
#     try:
#         # Get user
#         user = Registration.objects.get(id=startup_user_id)
        
#         # Get company data from session
#         company_data = request.session.get('company_data', {})
        
#         if not company_data.get('company_name'):
#             return JsonResponse({'success': False, 'error': 'No company data found'}, status=400)
        
#         # Convert string financial data to Decimal or None
#         def to_decimal(value):
#             if value and str(value).strip():
#                 try:
#                     return float(str(value).strip())
#                 except (ValueError, TypeError):
#                     return None
#             return None
        
#         confidence_level = company_data.get('data_source_confidence', 'Medium')
#         if confidence_level == 'High':
#             confidence_percentage = 75
#         elif confidence_level == 'Medium':
#             confidence_percentage = 50
#         else: # Low
#             confidence_percentage = 30

#         # Create the startup record
#         startup = Startup.objects.create(
#             owner=user,
#             company_name=company_data.get('company_name', ''),
#             industry=company_data.get('industry', ''),
#             company_description=company_data.get('company_description', ''),
#             data_source_confidence=company_data.get('data_source_confidence', 'Medium'),
#             confidence_percentage=confidence_percentage,
#             revenue=to_decimal(company_data.get('current_revenue')),  # Use current revenue as main revenue
#             net_income=to_decimal(company_data.get('net_income')),
#             total_assets=to_decimal(company_data.get('total_assets')),
#             total_liabilities=to_decimal(company_data.get('total_liabilities')),
#             cash_flow=to_decimal(company_data.get('cash_flow')),
#             team_strength=company_data.get('team_strength', ''),
#             market_position=company_data.get('market_position', ''),
#             brand_reputation=company_data.get('brand_reputation', '')
#         )
        
#         # Clear the session data since it's now saved
#         if 'company_data' in request.session:
#             del request.session['company_data']
        
#         return JsonResponse({
#             'success': True, 
#             'message': 'Startup added successfully!',
#             'startup_id': startup.id
#         })
        
#     except Registration.DoesNotExist:
#         return JsonResponse({'success': False, 'error': 'User not found'}, status=404)
#     except Exception as e:
#         return JsonResponse({'success': False, 'error': str(e)}, status=500)

class add_startup(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        startup_user_id = request.session.get('startup_user_id')
        user_label = request.session.get('user_label')

        if not startup_user_id or user_label != 'startup':
            return Response({'success': False, 'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            user = RegisteredUser.objects.get(id=startup_user_id)
        except RegisteredUser.DoesNotExist:
            return Response({'success': False, 'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        company_data = request.data

        if not company_data.get('company_name'):
            return Response({'success': False, 'error': 'No company name provided'}, status=status.HTTP_400_BAD_REQUEST)

        def to_decimal(value):
            try:
                return float(str(value).strip()) if value and str(value).strip() else None
            except (ValueError, TypeError):
                return None

        confidence_level = company_data.get('data_source_confidence', 'Medium')
        confidence_percentage = {
            'High': 75,
            'Medium': 50,
            'Low': 30
        }.get(confidence_level, 50)

        try:
            startup = Startup.objects.create(
                owner=user,
                company_name=company_data.get('company_name', ''),
                industry=company_data.get('industry', ''),
                company_description=company_data.get('company_description', ''),
                data_source_confidence=confidence_level,
                confidence_percentage=confidence_percentage,
                revenue=to_decimal(company_data.get('current_revenue')),
                net_income=to_decimal(company_data.get('net_income')),
                total_assets=to_decimal(company_data.get('total_assets')),
                total_liabilities=to_decimal(company_data.get('total_liabilities')),
                cash_flow=to_decimal(company_data.get('cash_flow')),
                team_strength=company_data.get('team_strength', ''),
                market_position=company_data.get('market_position', ''),
                brand_reputation=company_data.get('brand_reputation', '')
            )

            return Response({
                'success': True,
                'message': 'Startup added successfully!',
                'startup_id': startup.id
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@require_POST
# def delete_startup(request, startup_id):
#     """Delete a startup from the database"""
#     # Check if user is logged in and is a startup
#     startup_user_id = request.session.get('startup_user_id')
#     if not startup_user_id or request.session.get('user_label') != 'startup':
#         return JsonResponse({'success': False, 'error': 'Not authenticated'}, status=401)
    
#     try:
#         # Get user
#         user = Registration.objects.get(id=startup_user_id)
        
#         # Get the startup and ensure it belongs to the current user
#         startup = Startup.objects.get(id=startup_id, owner=user)
        
#         # Delete the startup
#         startup_name = startup.company_name
#         startup.delete()
        
#         return JsonResponse({
#             'success': True, 
#             'message': f'Startup "{startup_name}" deleted successfully!'
#         })
        
#     except Registration.DoesNotExist:
#         return JsonResponse({'success': False, 'error': 'User not found'}, status=404)
#     except Startup.DoesNotExist:
#         return JsonResponse({'success': False, 'error': 'Startup not found or access denied'}, status=404)
#     except Exception as e:
#         return JsonResponse({'success': False, 'error': str(e)}, status=500)

class delete_startup(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, startup_id):
        startup_user_id = request.session.get('startup_user_id')
        user_label = request.session.get('user_label')

        if not startup_user_id or user_label != 'startup':
            return Response({'success': False, 'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            user = RegisteredUser.objects.get(id=startup_user_id)
            startup = get_object_or_404(Startup, id=startup_id, owner=user)
            startup_name = startup.company_name
            startup.delete()

            return Response({
                'success': True,
                'message': f'Startup "{startup_name}" deleted successfully!'
            }, status=status.HTTP_204_NO_CONTENT)

        except RegisteredUser.DoesNotExist:
            return Response({'success': False, 'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# def edit_startup(request, startup_id):
#     """Edit an existing startup"""
#     # Check if user is logged in and is a startup
#     startup_user_id = request.session.get('startup_user_id')
#     if not startup_user_id or request.session.get('user_label') != 'startup':
#         messages.error(request, 'Please log in as a startup to access this page.')
#         return redirect('startup_login')
    
#     try:
#         # Get user and startup
#         user = Registration.objects.get(id=startup_user_id)
#         startup = Startup.objects.get(id=startup_id, owner=user)
#     except (Registration.DoesNotExist, Startup.DoesNotExist):
#         messages.error(request, 'Startup not found or access denied.')
#         return redirect('added_startups')
    
#     if request.method == 'POST':
#         # Check if this is a preview request
#         if request.GET.get('preview') == 'true' or request.POST.get('preview'):
#             # Handle preview request - store data in session and redirect to health report page
#             company_data = {
#                 # Basic company info
#                 'company_name': request.POST.get('company-name', '').strip(),
#                 'industry': request.POST.get('industry', '').strip(),
#                 'company_description': request.POST.get('company-description', '').strip(),
#                 'data_source_confidence': request.POST.get('data-source-confidence', 'Medium').strip(),
                
#                 # Financial data (for High/Medium confidence)
#                 'previous_revenue': request.POST.get('previous-revenue', '').strip(),
#                 'current_revenue': request.POST.get('current-revenue', '').strip(),
#                 'net_income': request.POST.get('net-income', '').strip(),
#                 'total_assets': request.POST.get('total-assets', '').strip(),
#                 'total_liabilities': request.POST.get('total-liabilities', '').strip(),
#                 'shareholder_equity': request.POST.get('shareholder-equity', '').strip(),
#                 'cash_flow': request.POST.get('cash-flow', '').strip(),
                
#                 # Qualitative data (for Low confidence)
#                 'team_strength': request.POST.get('team-strength', '').strip(),
#                 'market_position': request.POST.get('market-position', '').strip(),
#                 'brand_reputation': request.POST.get('brand-reputation', '').strip(),
#             }
            
#             request.session['company_data'] = company_data
#             request.session['edit_startup_id'] = startup_id  # Store the startup ID for returning after preview
            
#             # Redirect to health report page
#             return redirect('health_report_page')
        
#         # Handle regular update request
#         # Process the form data
#         company_data = {
#             # Basic company info
#             'company_name': request.POST.get('company-name', '').strip(),
#             'industry': request.POST.get('industry', '').strip(),
#             'company_description': request.POST.get('company-description', '').strip(),
#             'data_source_confidence': request.POST.get('data-source-confidence', 'Medium').strip(),
            
#             # Financial data (for High/Medium confidence)
#             'previous_revenue': request.POST.get('previous-revenue', '').strip(),
#             'current_revenue': request.POST.get('current-revenue', '').strip(),
#             'net_income': request.POST.get('net-income', '').strip(),
#             'total_assets': request.POST.get('total-assets', '').strip(),
#             'total_liabilities': request.POST.get('total-liabilities', '').strip(),
#             'shareholder_equity': request.POST.get('shareholder-equity', '').strip(),
#             'cash_flow': request.POST.get('cash-flow', '').strip(),
            
#             # Qualitative data (for Low confidence)
#             'team_strength': request.POST.get('team-strength', '').strip(),
#             'market_position': request.POST.get('market-position', '').strip(),
#             'brand_reputation': request.POST.get('brand-reputation', '').strip(),
#         }
        
#         # Convert string financial data to Decimal or None
#         def to_decimal(value):
#             if value and str(value).strip():
#                 try:
#                     return float(str(value).strip())
#                 except (ValueError, TypeError):
#                     return None
#             return None
        
#         confidence_level = company_data.get('data_source_confidence', 'Medium')
#         if confidence_level == 'High':
#             confidence_percentage = 75
#         elif confidence_level == 'Medium':
#             confidence_percentage = 50
#         else: # Low
#             confidence_percentage = 30

#         # Update the startup record
#         startup.company_name = company_data.get('company_name', '')
#         startup.industry = company_data.get('industry', '')
#         startup.company_description = company_data.get('company_description', '')
#         startup.data_source_confidence = company_data.get('data_source_confidence', 'Medium')
#         startup.confidence_percentage = confidence_percentage
#         startup.revenue = to_decimal(company_data.get('current_revenue'))  # Use current revenue as main revenue
#         startup.net_income = to_decimal(company_data.get('net_income'))
#         startup.total_assets = to_decimal(company_data.get('total_assets'))
#         startup.total_liabilities = to_decimal(company_data.get('total_liabilities'))
#         startup.cash_flow = to_decimal(company_data.get('cash_flow'))
#         startup.team_strength = company_data.get('team_strength', '')
#         startup.market_position = company_data.get('market_position', '')
#         startup.brand_reputation = company_data.get('brand_reputation', '')
        
#         startup.save()
        
#         messages.success(request, f'Startup "{startup.company_name}" updated successfully!')
        
#         # Clear any preview session data
#         request.session.pop('company_data', None)
#         request.session.pop('edit_startup_id', None)
        
#         return redirect('added_startups')
    
#     # For GET request, prepare the existing data for the form
#     # Check if we're returning from a preview
#     if 'edit_startup_id' in request.session and request.session['edit_startup_id'] == startup_id:
#         # Clear the preview session data
#         request.session.pop('company_data', None)
#         request.session.pop('edit_startup_id', None)
    
#     form_data = {
#         'company_name': startup.company_name,
#         'industry': startup.industry,
#         'company_description': startup.company_description,
#         'data_source_confidence': startup.data_source_confidence,
#         'previous_revenue': startup.revenue if startup.revenue else '',  # Use stored revenue as previous revenue
#         'current_revenue': startup.revenue if startup.revenue else '',   # Use stored revenue as current revenue
#         'net_income': startup.net_income if startup.net_income else '',
#         'total_assets': startup.total_assets if startup.total_assets else '',
#         'total_liabilities': startup.total_liabilities if startup.total_liabilities else '',
#         'cash_flow': startup.cash_flow if startup.cash_flow else '',
#         'team_strength': startup.team_strength,
#         'market_position': startup.market_position,
#         'brand_reputation': startup.brand_reputation,
#     }
    
#     return render(request, 'Module_3/Edit_Startup.html', {
#         'startup': startup,
#         'form_data': form_data
#     })

class edit_startup(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, startup_id):
        startup_user_id = request.session.get('startup_user_id')
        user_label = request.session.get('user_label')

        if not startup_user_id or user_label != 'startup':
            return Response({'error': 'Not authenticated'}, status=403)

        user = get_object_or_404(RegisteredUser, id=startup_user_id)
        startup = get_object_or_404(Startup, id=startup_id, owner=user)

        form_data = {
            'company_name': startup.company_name,
            'industry': startup.industry,
            'company_description': startup.company_description,
            'data_source_confidence': startup.data_source_confidence,
            'previous_revenue': startup.revenue or '',
            'current_revenue': startup.revenue or '',
            'net_income': startup.net_income or '',
            'total_assets': startup.total_assets or '',
            'total_liabilities': startup.total_liabilities or '',
            'cash_flow': startup.cash_flow or '',
            'team_strength': startup.team_strength,
            'market_position': startup.market_position,
            'brand_reputation': startup.brand_reputation,
        }

        return Response({'startup': form_data}, status=200)

    def put(self, request, startup_id):
        startup_user_id = request.session.get('startup_user_id')
        user_label = request.session.get('user_label')

        if not startup_user_id or user_label != 'startup':
            return Response({'error': 'Not authenticated'}, status=403)

        user = get_object_or_404(RegisteredUser, id=startup_user_id)
        startup = get_object_or_404(Startup, id=startup_id, owner=user)

        data = request.data

        def to_decimal(value):
            try:
                return float(str(value).strip()) if value and str(value).strip() else None
            except (ValueError, TypeError):
                return None

        confidence_level = data.get('data_source_confidence', 'Medium')
        confidence_percentage = {'High': 75, 'Medium': 50, 'Low': 30}.get(confidence_level, 50)

        startup.company_name = data.get('company_name', '')
        startup.industry = data.get('industry', '')
        startup.company_description = data.get('company_description', '')
        startup.data_source_confidence = confidence_level
        startup.confidence_percentage = confidence_percentage
        startup.revenue = to_decimal(data.get('current_revenue'))
        startup.net_income = to_decimal(data.get('net_income'))
        startup.total_assets = to_decimal(data.get('total_assets'))
        startup.total_liabilities = to_decimal(data.get('total_liabilities'))
        startup.cash_flow = to_decimal(data.get('cash_flow'))
        startup.team_strength = data.get('team_strength', '')
        startup.market_position = data.get('market_position', '')
        startup.brand_reputation = data.get('brand_reputation', '')

        startup.save()

        request.session.pop('company_data', None)
        request.session.pop('edit_startup_id', None)

        return Response({'success': True, 'message': f'Startup "{startup.company_name}" updated successfully!'}, status=200)

# def view_startup_report(request, startup_id):
#     """View the health report for a specific startup"""
#     # Check if user is logged in and is a startup
#     startup_user_id = request.session.get('startup_user_id')
#     if not startup_user_id or request.session.get('user_label') != 'startup':
#         messages.error(request, 'Please log in as a startup to access this page.')
#         return redirect('startup_login')
    
#     try:
#         # Get user and startup
#         user = Registration.objects.get(id=startup_user_id)
#         startup = Startup.objects.get(id=startup_id, owner=user)
#     except (Registration.DoesNotExist, Startup.DoesNotExist):
#         messages.error(request, 'Startup not found or access denied.')
#         return redirect('added_startups')
    
#     # Check if this startup was created from a deck
#     if startup.source_deck:
#         # Show the deck report modal template with the deck data
#         deck = startup.source_deck
        
#         context = {
#             'deck_info': deck,
#             'problem': getattr(deck, 'problem', None),
#             'solution': getattr(deck, 'solution', None),
#             'market_analysis': getattr(deck, 'market_analysis', None),
#             'ask': getattr(deck, 'ask', None),
#             'team_members': deck.team_members.all(),
#             'financials': deck.financials.order_by('year'),
#             'startup': startup,  # Include startup info for context
#             'show_modal': True,  # Flag to show modal by default
#         }
        
#         # Use a template that shows the report modal content as a full page
#         return render(request, 'Module_3/Startup_Deck_Report.html', context)
#     else:
#         # Show the regular startup report for non-deck startups
#         # Prepare company data for the template (same format as health_report_page)
#         company_data = {
#             'company_name': startup.company_name,
#             'industry': startup.industry,
#             'company_description': startup.company_description,
#             'data_source_confidence': startup.data_source_confidence,
#             'revenue': startup.revenue,
#             'net_income': startup.net_income,
#             'total_assets': startup.total_assets,
#             'total_liabilities': startup.total_liabilities,
#             'cash_flow': startup.cash_flow,
#             'team_strength': startup.team_strength,
#             'market_position': startup.market_position,
#             'brand_reputation': startup.brand_reputation,
#         }
        
#         return render(request, 'Module_3/View_Startup_Report.html', {
#             'company_data': company_data,
#             'startup': startup
#         })

class view_startup_report(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, startup_id):
        owner = request.user.profile
        startup = get_object_or_404(Startup, id=startup_id, owner=owner)

        # ✅ Track view
        StartupView.objects.create(
            user=request.user,
            startup=startup,
            viewed_at = timezone.now(),
            ip_address=request.META.get('REMOTE_ADDR')
        )

        if startup.source_deck:
            deck = startup.source_deck

            # ✅ Serialize deck sections manually
            problem_data = {
                'description': deck.problem.description
            } if hasattr(deck, 'problem') else None

            solution_data = {
                'description': deck.solution.description
            } if hasattr(deck, 'solution') else None

            market_data = {
                'primary_market': deck.market_analysis.primary_market,
                'target_audience': deck.market_analysis.target_audience,
                'market_growth_rate': float(deck.market_analysis.market_growth_rate),
                'competitive_advantage': deck.market_analysis.competitive_advantage
            } if hasattr(deck, 'market_analysis') else None

            ask_data = {
                'amount': float(deck.ask.amount),
                'usage_description': deck.ask.usage_description
            } if hasattr(deck, 'ask') else None

            deck_data = {
                'deck_info': {
                    'id': deck.id,
                    'company_name': getattr(deck, 'company_name', ''),
                    'tagline': getattr(deck, 'tagline', ''),
                    'created_at': deck.created_at
                },
                'problem': problem_data,
                'solution': solution_data,
                'market_analysis': market_data,
                'ask': ask_data,
                'team_members': [
                    {'name': member.name, 'role': member.title}
                    for member in deck.team_members.all()
                ],
                'financials': [
                    {'year': f.year, 'revenue': float(f.revenue), 'profit': float(f.profit)}
                    for f in deck.financials.order_by('year')
                ],
                'startup': {
                    'id': startup.id,
                    'company_name': startup.company_name,
                    'industry': startup.industry
                },
                'report_type': 'deck'
            }
            return Response(deck_data, status=200)

        else:
            company_data = {
                'company_name': startup.company_name,
                'industry': startup.industry,
                'company_description': startup.company_description,
                'data_source_confidence': startup.data_source_confidence,
                'revenue': float(startup.revenue) if startup.revenue else None,
                'net_income': float(startup.net_income) if startup.net_income else None,
                'total_assets': float(startup.total_assets) if startup.total_assets else None,
                'total_liabilities': float(startup.total_liabilities) if startup.total_liabilities else None,
                'cash_flow': float(startup.cash_flow) if startup.cash_flow else None,
                'team_strength': startup.team_strength,
                'market_position': startup.market_position,
                'brand_reputation': startup.brand_reputation,
                'report_type': 'standard'
            }
            return Response({
                'startup': {
                    'id': startup.id,
                    'company_name': startup.company_name,
                    'industry': startup.industry
                },
                'company_data': company_data
            }, status=200)

# def startup_login(request):
#     """Login specifically for startup users using Module_3 template"""
#     if request.method == 'POST':
#         form = LoginForm(request.POST)
#         if form.is_valid():
#             email = form.cleaned_data['email']
#             password = form.cleaned_data['password']
            
#             try:
#                 # Find user by email
#                 registration = Registration.objects.get(email=email)
                
#                 # Check password and ensure user is a startup
#                 if check_password(password, registration.password):
#                     if registration.label == 'startup':
#                         # Store user info in session
#                         request.session['startup_user_id'] = registration.id
#                         request.session['user_email'] = registration.email
#                         request.session['user_name'] = f"{registration.first_name} {registration.last_name}"
#                         request.session['user_label'] = registration.label
                        
#                         return redirect('added_startups')
#                     else:
#                         messages.error(request, 'This login is for startup users only.')
#                 else:
#                     messages.error(request, 'Invalid email or password.')
#             except Registration.DoesNotExist:
#                 messages.error(request, 'Invalid email or password.')
#         else:
#             messages.error(request, 'Please correct the errors below.')
#     else:
#         form = LoginForm()
    
#     return render(request, 'Module_3/Startup_Login.html', {'form': form})

class startup_login(APIView):
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response({'success': False, 'error': 'Email and password are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            registration = RegisteredUser.objects.get(email=email)

            if not check_password(password, registration.password):
                return Response({'success': False, 'error': 'Invalid email or password.'}, status=status.HTTP_401_UNAUTHORIZED)

            if registration.label != 'startup':
                return Response({'success': False, 'error': 'This login is for startup users only.'}, status=status.HTTP_403_FORBIDDEN)

            # Store session data if needed
            request.session['startup_user_id'] = registration.id
            request.session['user_email'] = registration.email
            request.session['user_name'] = f"{registration.first_name} {registration.last_name}"
            request.session['user_label'] = registration.label

            return Response({
                'success': True,
                'message': 'Login successful.',
                'user': {
                    'id': registration.id,
                    'email': registration.email,
                    'name': f"{registration.first_name} {registration.last_name}",
                    'label': registration.label
                }
            }, status=status.HTTP_200_OK)

        except RegisteredUser.DoesNotExist:
            return Response({'success': False, 'error': 'Invalid email or password.'}, status=status.HTTP_401_UNAUTHORIZED)

#MOD - 4
# def create_deck(request):
#     deck_form = DeckForm(request.POST or None, request.FILES or None)
#     problem_form = ProblemForm(request.POST or None)
#     solution_form = SolutionForm(request.POST or None)
#     market_form = MarketAnalysisForm(request.POST or None)
#     ask_form = FundingAskForm(request.POST or None)

#     team_formset = TeamMemberFormSet(request.POST or None, prefix='team')
#     financial_formset = FinancialProjectionFormSet(request.POST or None, prefix='financial')

#     if request.method == 'POST' and deck_form.is_valid():
#         with transaction.atomic():
#             deck = deck_form.save(commit=False)
#             deck.owner = request.user
#             deck.save()

#             # Save One-to-One relationships
#             problem = problem_form.save(commit=False)
#             problem.deck = deck
#             problem.save()

#             solution = solution_form.save(commit=False)
#             solution.deck = deck
#             solution.save()

#             market = market_form.save(commit=False)
#             market.deck = deck
#             market.save()

#             ask = ask_form.save(commit=False)
#             ask.deck = deck
#             ask.save()

#             # Save formsets
#             team_formset = TeamMemberFormSet(request.POST, instance=deck, prefix='team')
#             financial_formset = FinancialProjectionFormSet(request.POST, instance=deck, prefix='financial')

#             if team_formset.is_valid():
#                 team_formset.save()

#             if financial_formset.is_valid():
#                 financial_formset.save()

#         return redirect('some_success_view')

#     context = {
#         'deck_form': deck_form,
#         'problem_form': problem_form,
#         'solution_form': solution_form,
#         'market_form': market_form,
#         'ask_form': ask_form,
#         'team_formset': team_formset,
#         'financial_formset': financial_formset,
#     }
#     return render(request, 'deck/create_deck.html', context)

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

@require_POST
# def add_deck_to_recommended(request):
#     """Add the current deck as a startup to the added_startups list"""
#     try:
#         startup_user_id = request.session.get('startup_user_id')
#         if not startup_user_id:
#             return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
        
#         deck_id = request.session.get('deck_id')
#         if not deck_id:
#             return JsonResponse({'success': False, 'error': 'No active deck found'}, status=400)
        
#         # Get the current user and deck
#         user = Registration.objects.get(id=startup_user_id)
#         deck = get_object_or_404(Deck, id=deck_id, owner=user)
        
#         # Check if a startup with this deck's company name already exists for this user
#         existing_startup = Startup.objects.filter(
#             owner=user, 
#             company_name=deck.company_name
#         ).first()
        
#         if existing_startup:
#             return JsonResponse({
#                 'success': False, 
#                 'error': f'Startup "{deck.company_name}" already exists in your added startups'
#             })
        
#         # Extract financial data from deck's financial projections
#         financials = deck.financials.order_by('year')
#         total_revenue = sum(f.revenue for f in financials if f.revenue) if financials.exists() else None
#         total_profit = sum(f.profit for f in financials if f.profit) if financials.exists() else None
        
#         # Get market analysis data
#         market_analysis = getattr(deck, 'market_analysis', None)
        
#         # Get the ask data
#         ask = getattr(deck, 'ask', None)
#         funding_ask_amount = None
#         funding_ask_text = ""
        
#         if ask and hasattr(ask, 'amount') and ask.amount:
#             funding_ask_amount = ask.amount
#             funding_ask_text = f"Seeking {ask.amount} funding"
        
#         # Create description from problem and solution
#         problem_text = getattr(deck, 'problem', None)
#         solution_text = getattr(deck, 'solution', None)
        
#         description_parts = []
#         if problem_text and problem_text.description:
#             description_parts.append(f"Problem: {problem_text.description}")
#         if solution_text and solution_text.description:
#             description_parts.append(f"Solution: {solution_text.description}")
        
#         company_description = " | ".join(description_parts) if description_parts else "No description available"
        
#         # Determine industry from market analysis or use default
#         industry = market_analysis.primary_market if market_analysis and market_analysis.primary_market else "Technology"
        
#         # Create the startup entry
#         startup = Startup.objects.create(
#             owner=user,
#             company_name=deck.company_name,
#             industry=industry,
#             company_description=company_description,
#             data_source_confidence='High',  # Since it's from a complete deck
#             confidence_percentage=85,  # High confidence for deck-based data
#             revenue=total_revenue,
#             net_income=total_profit,
#             funding_ask=funding_ask_amount,  # Store funding ask properly
#             source_deck=deck,  # Reference to the original deck
#             total_assets=None,  # Not available from deck
#             total_liabilities=None,  # Not available from deck
#             cash_flow=None,  # Not available from deck
#             team_strength=f"Team size: {deck.team_members.count()} members" if deck.team_members.exists() else "",
#             market_position=market_analysis.competitive_advantage if market_analysis and market_analysis.competitive_advantage else "",
#             brand_reputation=funding_ask_text
#         )
        
#         return JsonResponse({
#             'success': True, 
#             'message': f'"{deck.company_name}" has been added to your startup recommendations!',
#             'startup_id': startup.id
#         })
        
#     except Registration.DoesNotExist:
#         return JsonResponse({'success': False, 'error': 'User not found'}, status=404)
#     except Exception as e:
#         import traceback
#         print(f"Error in add_deck_to_recommended: {str(e)}")
#         print(f"Traceback: {traceback.format_exc()}")
#         return JsonResponse({'success': False, 'error': f'An error occurred: {str(e)}'}, status=500)

class add_deck_to_recommended(APIView):
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
        
# def debug_session(request):
#     """Debug endpoint to check session variables"""
#     return JsonResponse({
#         'startup_user_id': request.session.get('startup_user_id'),
#         'deck_id': request.session.get('deck_id'),
#         'session_keys': list(request.session.keys())
#     })

class debug_session(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        session_data = {
            'startup_user_id': request.session.get('startup_user_id'),
            'deck_id': request.session.get('deck_id'),
            'session_keys': list(request.session.keys())
        }
        return Response(session_data, status=200)

# def create_new_deck(request):
#     """Create a fresh new deck and redirect to deck builder"""
#     startup_user_id = request.session.get('startup_user_id')
    
#     if not startup_user_id:
#         messages.error(request, "You need to be logged in as a startup to create a pitch deck.")
#         return redirect('startup_login')
    
#     try:
#         owner_instance = Registration.objects.get(id=startup_user_id)
        
#         # Always create a new deck - don't reuse existing ones
#         deck = Deck.objects.create(
#             owner=owner_instance,
#             company_name="Untitled Deck",
#             tagline=""
#         )
        
#         # Clear any existing deck_id from session and set new one
#         request.session['deck_id'] = deck.id
#         print(f"DEBUG: Created fresh new deck {deck.id} for new deck creation")
        
#         # Redirect to deck builder cover page
#         return redirect('deck_section', section='cover-page')
        
#     except Registration.DoesNotExist:
#         messages.error(request, f"Registration record not found for user ID {startup_user_id}. Please log in again.")
#         request.session.flush()
#         return redirect('startup_login')
#     except Exception as e:
#         messages.error(request, f"An error occurred while creating a new deck: {e}")
#         return redirect('deck_home')

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