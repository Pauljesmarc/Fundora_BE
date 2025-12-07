from django.urls import path
from . import views
from .views import (
    StartupListView, 
    StartupDetailView, 
    CurrentUserView, 
    StartupProfileView, 
    FinancialProjectionListView,
    UpdateStartupProfileView
)
from rest_framework.response import Response
from rest_framework.views import APIView
from .views import TestAPI

import inspect
print("SaveComparisonView type:", type(getattr(views, 'SaveComparisonView', None)))
print("SaveComparisonView is class?:", inspect.isclass(getattr(views, 'SaveComparisonView', None)))
print("Dir of views:", [x for x in dir(views) if 'comparison' in x.lower()])

class StartupRegistrationView(APIView):
    def post(self, request):
        # handle registration logic
        return Response({"message": "Startup registered successfully"})

urlpatterns = [

    path('index/', views.index.as_view(), name='index'),
    path('deck/', views.deck_home.as_view(), name='deck_home'),
    path('deck/create/', views.create_new_deck.as_view(), name='deck_create'),
    path('deck/add-to-recommended/', views.add_deck_to_recommended.as_view(), name='add_deck_to_recommended'),
    path('deck/<int:deck_id>/edit/', views.edit_deck.as_view(), name='edit_deck'),
    path('deck/<int:deck_id>/delete/', views.delete_deck.as_view(), name='deck_delete'),
    path('deck/section/<str:section>/', views.deck_builder.as_view(), name='deck_section'),
    path('deck/section-list/', views.section_list.as_view(), name='section_list'),

    #Deck Creation URLS
    path('deck/cover/', views.create_cover.as_view(), name='create_cover'),
    path('deck/problem/', views.create_problem.as_view(), name='problem_section'),
    path('deck/solution/', views.create_solution.as_view(), name='solution_section'),
    path('deck/market-analysis/', views.create_market_analysis.as_view(), name='market_analysis_section'),
    path('deck/team/', views.create_team.as_view(), name='team_section'),
    path('deck/financial/', views.create_financial.as_view(), name='financial_section'),
    path('deck/ask/', views.create_ask.as_view(), name='ask_section'),

    #Deck list URL
    path('deck/list/', views.UserDeckListView.as_view(), name='user_deck_list'),
    #Deck financial list URL
    path('deck/financial-list/', views.FinancialsView.as_view(), name='user_financial_list'),
    #Deck report URL
    path('deck/report/<int:deck_id>', views.DeckReportView.as_view(), name='user_deck_report'),

    path('startup/register/', views.startup_registration.as_view(), name='startup_registration'),
    path('startup/register/success/', views.registration_success, name='registration_success'),
    
    path('logout/', views.user_logout.as_view(), name='user_logout'),
    path('startups/', views.added_startups.as_view(), name='added_startups'),
    path('startup/<int:startup_id>/', views.startup_detail.as_view(), name='startup_detail'),
    path('startup/<int:startup_id>/update/', views.startup_detail.as_view(), name='startup_update'),

    path('startup/company-info/', views.company_information_form.as_view(), name='company_information_form'),
    path('startup/health-report/', views.health_report_page.as_view(), name='health_report_page'),
    path('startup/add/', views.add_startup, name='add_startup'),
    path('startup/<int:startup_id>/delete/', views.delete_startup.as_view(), name='delete_startup'),
    path('startup/<int:startup_id>/edit/', views.startup_detail.as_view(), name='edit_startup'),
    path('startup/<int:startup_id>/report/', views.view_startup_report.as_view(), name='view_startup_report'),

    # Auth & Registration
    path('investor/register/', views.investor_registration.as_view(), name='investor_registration'),
    path('login/', views.login_view.as_view(), name='login'),

    # Dashboard & Watchlist 
    path('investor/dashboard/', views.dashboard.as_view(), name='dashboard'),
    path('investor/watchlist/', views.watchlist_view.as_view(), name='watchlist'),
    path('investor/watchlist/add/<int:startup_id>/', views.add_to_watchlist.as_view(), name='add_to_watchlist'),
    path('investor/watchlist/remove/<int:startup_id>/', views.remove_from_watchlist.as_view(), name='remove_from_watchlist'),
    
    # Startups
    path('investor/startups/', StartupListView.as_view(), name='startup-list'),
    path('startups/<int:pk>/', StartupDetailView.as_view(), name='startup-detail'),
    path('startups/<int:startup_id>/profile/', StartupProfileView.as_view(), name='startup-profile'),
    
    # Financials
    path('financials/<int:startup_id>/', FinancialProjectionListView.as_view(), name='financials'),
    
    # Users
    path('users/me/', CurrentUserView.as_view(), name='current-user'),
    
    # Investment Simulation
    path('investor/simulation/', views.investment_simulation.as_view(), name='investment_simulation'),
    path('investor/simulation/<int:startup_id>/', views.investment_simulation.as_view(), name='investment_simulation_with_startup'),
    
    # Startup Comparison
    path('investor/comparison/', views.startup_comparison.as_view(), name='startup_comparison'),
    path('investor/comparisons/save/', views.SaveComparisonView.as_view(), name='save_comparison'),
    path('investor/comparisons/', views.ListComparisonsView.as_view(), name='list_comparisons'),
    path('investor/comparisons/delete/<int:comparison_id>/', views.DeleteComparisonSetView.as_view(), name='delete_comparison_set'),
    
    # Profile endpoints
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('profile/update/', views.UpdateProfileView.as_view(), name='update-profile'),

    # Startup Profile
    path('startup/profile/', views.StartupProfileAccountView.as_view(), name='startup-profile-account'),

    # Projection
    path('deck-builder/pitch-financials/', views.save_pitch_deck_financials.as_view(), name='save_pitch_financials'),

    #Starutp Account Update
    path('startup/profile/update/', UpdateStartupProfileView.as_view(), name='update_startup_profile'),

    path('test/', TestAPI.as_view(), name='test-api'),
]