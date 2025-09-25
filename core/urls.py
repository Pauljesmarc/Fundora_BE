from django.urls import path
from . import views
from rest_framework.response import Response
from rest_framework.views import APIView

class StartupRegistrationView(APIView):
    def post(self, request):
        # handle registration logic
        return Response({"message": "Startup registered successfully"})

urlpatterns = [
    # path('', views.index, name='index'),
    # path('index/', views.index, name='index'),
    # path('deck/', views.deck_home, name='deck_home'),
    # path('deck/create/', views.create_new_deck, name='deck_create'),
    # path('deck/add-to-recommended/', views.add_deck_to_recommended, name='add_deck_to_recommended'),
    # path('deck/edit/<int:deck_id>/', views.edit_deck, name='edit_deck'),
    # path('deck/delete/<int:deck_id>/', views.delete_deck, name='delete_deck'),
    # path('deck/<str:section>/', views.deck_builder, name='deck_section'),

    path('index/', views.index.as_view(), name='index'),
    path('deck/', views.deck_home.as_view(), name='deck_home'),
    path('deck/create/', views.create_new_deck.as_view(), name='deck_create'),
    path('deck/add-to-recommended/', views.add_deck_to_recommended, name='add_deck_to_recommended'),
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

    # Module 3 - Startup Registration URLs
    # path('startup-registration/', views.startup_registration, name='startup_registration'),
    # path('registration-success/', views.registration_success, name='registration_success'),

    path('startup/register/', views.startup_registration.as_view(), name='startup_registration'),
    path('startup/register/success/', views.registration_success, name='registration_success'),
    
    # Login and Dashboard URLs
    #path('startup-login/', views.startup_login, name='startup_login'),
    # path('logout/', views.user_logout, name='user_logout'),
    # path('added-startups/', views.added_startups, name='added_startups'),
    
    path('logout/', views.user_logout.as_view(), name='user_logout'),
    path('startups/', views.added_startups.as_view(), name='added_startups'),


    # Company Information Form and Health Report
    # path('company-information/', views.company_information_form, name='company_information_form'),
    # path('health-report/', views.health_report_page, name='health_report_page'),
    # path('add-startup/', views.add_startup, name='add_startup'),
    # path('delete-startup/<int:startup_id>/', views.delete_startup, name='delete_startup'),
    # path('edit-startup/<int:startup_id>/', views.edit_startup, name='edit_startup'),
    # path('view-startup-report/<int:startup_id>/', views.view_startup_report, name='view_startup_report'),


    path('startup/company-info/', views.company_information_form.as_view(), name='company_information_form'),
    path('startup/health-report/', views.health_report_page.as_view(), name='health_report_page'),
    path('startup/add/', views.add_startup, name='add_startup'),
    path('startup/<int:startup_id>/delete/', views.delete_startup, name='delete_startup'),
    path('startup/<int:startup_id>/edit/', views.edit_startup.as_view(), name='edit_startup'),
    path('startup/<int:startup_id>/report/', views.view_startup_report.as_view(), name='view_startup_report'),
    
    # MOD1 AND MOD2
    # path('investor-registration/', views.investor_registration, name='investor_registration'),
    # path('login/', views.login_view, name='login'),
    # path('dashboard/', views.dashboard, name='dashboard'),
    # path('watchlist/', views.watchlist_view, name='watchlist'),
    # path('add-to-watchlist/<int:startup_id>/', views.add_to_watchlist, name='add_to_watchlist'),
    # path('delete-comparison/<int:comparison_id>/', views.delete_comparison_set, name='delete_comparison_set'),
    # path('watchlist/remove/<int:startup_id>/', views.remove_from_watchlist, name='remove_from_watchlist'),
    # path('company-profile/<int:startup_id>/', views.company_profile, name='company_profile'),
    # path('company-profile/<int:startup_id>/download-pdf/', views.download_company_profile_pdf, name='download_company_profile_pdf'),
    # path('compare-startups/', views.compare_startups, name='compare_startups'),
    # path('startup-comparison/', views.startup_comparison, name='startup_comparison'),
    # path('export-startup-comparison-pdf/', views.export_startup_comparison_pdf, name='export_startup_comparison_pdf'),
    # path('investment-simulation/', views.investment_simulation, name='investment_simulation'),
    # path('investment-simulation/<int:startup_id>/', views.investment_simulation, name='investment_simulation_with_startup'),

    # Auth & Registration
    path('investor/register/', views.investor_registration.as_view(), name='investor_registration'),
    path('login/', views.login_view.as_view(), name='login'),
    # path('api/logout/', views.LogoutView.as_view(), name='logout'),

    # Dashboard & Watchlist
    path('investor/dashboard/', views.dashboard.as_view(), name='dashboard'),
    path('investor/watchlist/', views.watchlist_view.as_view(), name='watchlist'),
    path('investor/watchlist/add/<int:startup_id>/', views.add_to_watchlist.as_view(), name='add_to_watchlist'),
    path('investor/watchlist/remove/<int:startup_id>/', views.remove_from_watchlist.as_view(), name='remove_from_watchlist'),

    # Startup Comparison
    path('investor/comparison/', views.startup_comparison.as_view(), name='startup_comparison'),
    path('investor/comparison/delete/<int:comparison_id>/', views.delete_comparison_set.as_view(), name='delete_comparison_set'),
    path('investor/comparison/export-pdf/', views.export_startup_comparison_pdf.as_view(), name='export_startup_comparison_pdf'),

    # Company Profile
    path('startup/<int:startup_id>/profile/', views.company_profile.as_view(), name='company_profile'),
    path('startup/<int:startup_id>/profile/download-pdf/', views.download_company_profile_pdf.as_view(), name='download_company_profile_pdf'),

    # Investment Simulation
    path('investor/simulation/', views.investment_simulation.as_view(), name='investment_simulation'),
    path('investor/simulation/<int:startup_id>/', views.investment_simulation.as_view(), name='investment_simulation_with_startup'),
]