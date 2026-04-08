from django.urls import path
from . import views
from .views import (
    StartupListView, 
    StartupDetailView, 
    CurrentUserView, 
    StartupProfileView, 
    FinancialProjectionListView,
    UpdateStartupProfileView,
    RecordStartupViewAPI,
    RecordStartupComparisonAPI,
    AIRecommendationsView
)

from django.conf import settings
from django.conf.urls.static import static
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

    path('index/', views.index, name='index'),

    path('startup/register/', views.startup_registration.as_view(), name='startup_registration'),
    path('startup/register/success/', views.registration_success, name='registration_success'),
    
    path('logout/', views.user_logout.as_view(), name='user_logout'),
    path('startups/', views.added_startups.as_view(), name='added_startups'),
    path('startup/<int:startup_id>/', views.startup_detail.as_view(), name='startup_detail'),
    path('startup/<int:startup_id>/update/', views.startup_detail.as_view(), name='startup_update'),

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
    path('startups/<int:startup_id>/view/', RecordStartupViewAPI.as_view(), name='record-startup-view'),
    
    # Analytics
    path('analytics/comparison/', RecordStartupComparisonAPI.as_view(), name='record-startup-comparison'),
    
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

    #Starutp Account Update
    path('startup/profile/update/', UpdateStartupProfileView.as_view(), name='update_startup_profile'),
    path('investor/startups/compare/', views.compare_startups.as_view(), name='compare_startups_list'),

    # AI Recommendations
    path('ai-recommendations/', AIRecommendationsView.as_view(), name='ai_recommendations'),

    path('test/', TestAPI.as_view(), name='test-api'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)