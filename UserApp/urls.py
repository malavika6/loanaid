from django.urls import path
from UserApp import views

urlpatterns = [
    path('', views.home, name='home'),
    path('index/<int:user_id>', views.other_user_dashboard, name='index'),
    path('login/', views.login, name='login'),
    path('payment-redirect/', views.payment_redirect, name='payment_redirect'),
    path('payment-confirmation/', views.payment_confirmation, name='payment_confirmation'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.home, name='dashboard'),
    path('franchise_dashboard/', views.home, name='franchise_dashboard'),
    path('update-profile/', views.update_profile, name='update_profile'),
    path('view_profile/<int:staff_id>', views.view_staffs, name = 'view_profile'),
    path('create-user/', views.create_staff, name='create_staff'),
    path('list_staff/',views.list_staff,name='list_staff'),
    path('delete_staff/<int:staff_id>/', views.delete_staff, name='delete_staff'),
    path('delete-file/<int:id>/', views.delete_files, name='delete_file'),
    path('profile/', views.update_profile, name='profile'),
]
