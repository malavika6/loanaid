from django.urls import path
from . import views

urlpatterns = [
    path('application/', views.loanform, name='form'),
    path('all-application/', views.all_app, name='all-application'),
    path('loan-page/<str:form_id>/', views.loan_page, name='loan-page'),
    path('application-status/', views.loan_application_status, name='loan_application_status'),
    path('update-status/<int:form_id>/', views.update_status, name='update_status'),
    path('add-loan/', views.addloan, name='addloan'),
    path('add-status/', views.addstatus, name='addstatus'),
    path('add-bank/', views.addbank, name='addbank'),
    path('delete_files/<int:id>/', views.delete_files, name='delete_files'),
    path('delete_loan/<int:loan_id>/', views.delete_loan, name='delete_loan'),
    path('delete_status/<int:status_id>/', views.delete_status, name='delete_status'),
    path('delete_bank/<int:bank_id>/', views.delete_bank, name='delete_bank'),
    path('delete_loan_page/<int:form_id>/', views.delete_loanpage, name='delete_loan_page'),
    path('apply-loan/', views.apply_loan, name='apply-loan'),
    path('list-loan/', views.list_loan, name='list-loan'),
    path('delete-application/<int:form_id>/', views.delete_application, name='delete_application'),
]
