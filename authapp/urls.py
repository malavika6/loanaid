from django.urls import path
from . import views

urlpatterns = [
    # Admin can add franchises
    # Assign staff form page
    path('assign/', views.assign_staff, name='assign_staff'),
    path('assignments/', views.all_staff_assignments, name='staff_assignments'),
    path('update_assignment/<int:assignment_id>/',
         views.update_assignment, name='update_assignment'),



    path('edit/<uuid:franchise_id>/', views.edit_franchise, name='edit_franchise'),
    path("franchise/profile/", views.view_franchise_profile,
         name="view_franchise_profile"),


    # Franchise management
    path('franchise_dashboard/', views.franchise_dashboard,
         name='franchise_dashboard'),
    path('delete/<uuid:franchise_id>/',
         views.delete_franchise, name='delete_franchise'),
    path('add_franchise/', views.add_franchise, name='add_franchise'),
    path('list_franchise/', views.list_franchise, name='list_franchise'),
    path('franchise_list/', views.franchise_list, name='franchise_list'),
    path('franchise_wallet/', views.franchise_wallet, name='franchise_wallet'),
    path('franchise_change_password/', views.franchise_change_password, name='franchise_change_password'),
    path('franchise_logout/', views.franchise_logout, name='franchise_logout'),
]
