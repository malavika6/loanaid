from django.shortcuts import get_object_or_404, redirect
from loan.models import LoanApplicationModel

def delete_loan(request, loan_id):
    """Delete a loan application by its ID."""
    loan = get_object_or_404(LoanApplicationModel, pk=loan_id)
    if request.method == 'POST':
        loan.delete()
        return redirect('loan-page', loan_id)
    return redirect('loan-page', loan_id)
# Import optimized loan views and utilities
from .loan_views import (
    LoanApplicationView,
    LoanDetailView,
    LoanListView,
    LoanStatusView,
    AddLoanView,
    AddStatusView,
    AddBankView,
    # Legacy function-based views for backward compatibility
    loanform,
    loan_page,
    all_app,
    loan_application_status,
    addloan,
    addstatus,
    addbank
)
from .loan_utils import get_loan_stats, get_loan_performance_metrics, get_loan_notifications

import logging
logger = logging.getLogger(__name__)

# Additional utility functions for loan management
def update_status(request, form_id):
    """Update loan application status"""
    from django.shortcuts import get_object_or_404, redirect
    from django.contrib import messages
    from .models import LoanApplicationModel
    from users.models import AdminModel
    
    loan_form = get_object_or_404(LoanApplicationModel, form_id=form_id)
    user_id = request.session.get('user_id', None)
    if user_id is None:
        return redirect('/login')

    admin = AdminModel.objects.get(admin_id=user_id)

    if not admin.is_superadmin and not admin.is_staff:
        return redirect('/')

    if request.method == 'POST':
        status = request.POST.get('status')
        if status in ['Accept', 'Reject']:
            loan_form.workstatus = status
            loan_form.save()
            messages.success(request, f"Status updated to {status}")
    return redirect('/')

def delete_status(request, status_id):
    """Delete loan status"""
    from django.shortcuts import get_object_or_404, redirect
    from .models import StatusModel
    from users.models import AdminModel
    
    user_id = request.session.get('user_id', None)
    if user_id is None:
        return redirect('/login')

    admin = AdminModel.objects.get(admin_id=user_id)

    if not admin.is_superadmin:
        return redirect('/')

    status = get_object_or_404(StatusModel, pk=status_id)
    if request.method == 'POST':
        status.delete()
        return redirect('addstatus')
    return redirect('addstatus')

def delete_bank(request, bank_id):
    """Delete bank"""
    from django.shortcuts import get_object_or_404, redirect
    from .models import BankModel
    from users.models import AdminModel
    
    user_id = request.session.get('user_id', None)
    if user_id is None:
        return redirect('/login')

    admin = AdminModel.objects.get(admin_id=user_id)

    if not admin.is_superadmin:
        return redirect('/')

    bank = get_object_or_404(BankModel, pk=bank_id)
    if request.method == 'POST':
        bank.delete()
        return redirect('addbank')
    return redirect('addbank')

def delete_loanpage(request, form_id):
    """Delete loan application"""
    from django.shortcuts import get_object_or_404, redirect
    from .models import LoanApplicationModel
    from users.models import AdminModel
    
    user_id = request.session.get('user_id', None)
    if user_id is None:
        return redirect('/login')

    admin = AdminModel.objects.get(admin_id=user_id)

    loan = get_object_or_404(LoanApplicationModel, pk=form_id)
    if not admin.is_superadmin and (loan.franchise != admin):
        return redirect('/')

    if request.method == 'POST':
        loan.delete()
        return redirect('/')
    return redirect('/')

def delete_files(request, id):
    """Delete uploaded files"""
    from django.shortcuts import get_object_or_404, redirect
    from .models import UploadedFile
    
    file = get_object_or_404(UploadedFile, pk=id)
    loan_id = file.loan_application.form_id
    if request.method == 'POST':
        file.delete()
        return redirect('loan-page', loan_id)
    return redirect('loan-page', loan_id)

def delete_application(request, form_id):
    """Delete loan application"""
    from django.shortcuts import get_object_or_404, redirect
    from .models import LoanApplicationModel
    from users.models import AdminModel, StaffModel, Franchise
    
    user_id = request.session.get('user_id')
    user_type = request.session.get('user_type')
    if not user_id or user_type not in ['admin', 'staff', 'franchise']:
        return redirect('/login')

    loan_app = get_object_or_404(LoanApplicationModel, form_id=form_id)

    # Only allow admin, staff, or the franchise owner to delete
    if user_type == 'admin':
        pass  # Admin can delete any
    elif user_type == 'staff':
        staff = StaffModel.objects.get(pk=user_id)
        # Optionally, check if staff is assigned to this franchise
    elif user_type == 'franchise':
        franchise = Franchise.objects.get(pk=user_id)
        if loan_app.franchise != franchise:
            return redirect('/login')

    if request.method == 'POST':
        loan_app.delete()
        return redirect('all-application')
    return render(request, 'confirm_delete.html', {'object': loan_app})

# Placeholder views for future implementation
def apply_loan(request):
    """Placeholder view for applying for a loan."""
    from django.http import HttpResponse
    return HttpResponse("Apply Loan Page")

def list_loan(request):
    """Placeholder view for listing loans."""
    from django.http import HttpResponse
    return HttpResponse("List Loan Page")
