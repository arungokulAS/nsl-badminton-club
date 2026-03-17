from django.urls import path
from . import views

urlpatterns = [
    path('court/<int:court_id>/', views.referee_court_page, name='referee_court_page'),
    path('admin/tokens/', views.admin_generate_token, name='admin_generate_referee_token'),
    path('admin/live-manage/fragment', views.admin_live_manage_fragment, name='admin_live_manage_fragment'),
]
