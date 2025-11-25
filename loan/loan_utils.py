from django.db.models import Q, Count, Sum, Avg, Max, Min
from django.utils import timezone
from datetime import datetime, timedelta
import logging

from .models import (
    LoanApplicationModel, LoanModel, StatusModel, BankModel, 
    UploadedFile, StaffAssignmentModel
)

logger = logging.getLogger(__name__)


def get_loan_context(username, loan, status, bank, form, hide_fields):
    """Get context for loan application form"""
    return {
        'username': username,
        'loan': loan,
        'status': status,
        'bank': bank,
        'form': form,
        'hide_fields': hide_fields
    }


def get_loan_stats(user_type, user_id=None, franchise=None):
    """Get comprehensive loan statistics based on user type"""
    try:
        if user_type == 'admin':
            # Admin can see all stats
            stats = {
                'total_applications': LoanApplicationModel.objects.count(),
                'pending_applications': LoanApplicationModel.objects.filter(
                    status_name__status_name='Pending'
                ).count(),
                'approved_applications': LoanApplicationModel.objects.filter(
                    status_name__status_name='Accept'
                ).count(),
                'rejected_applications': LoanApplicationModel.objects.filter(
                    status_name__status_name='Reject'
                ).count(),
                'total_loan_amount': LoanApplicationModel.objects.aggregate(
                    total=Sum('loan_amount')
                )['total'] or 0,
                'average_loan_amount': LoanApplicationModel.objects.aggregate(
                    avg=Avg('loan_amount')
                )['avg'] or 0,
                'applications_this_month': LoanApplicationModel.objects.filter(
                    created_at__month=timezone.now().month
                ).count(),
            }
            
        elif user_type == 'staff':
            # Staff can see stats for assigned franchises
            assignment = StaffAssignmentModel.objects.filter(
                staff_name_id=user_id
            ).prefetch_related('franchise_name').first()
            
            if assignment:
                franchises = assignment.franchise_name.all()
                franchise_ids = [f.franchise_id for f in franchises]
                
                stats = {
                    'total_applications': LoanApplicationModel.objects.filter(
                        franchise_id__in=franchise_ids
                    ).count(),
                    'pending_applications': LoanApplicationModel.objects.filter(
                        franchise_id__in=franchise_ids,
                        status_name__status_name='Pending'
                    ).count(),
                    'approved_applications': LoanApplicationModel.objects.filter(
                        franchise_id__in=franchise_ids,
                        status_name__status_name='Accept'
                    ).count(),
                    'rejected_applications': LoanApplicationModel.objects.filter(
                        franchise_id__in=franchise_ids,
                        status_name__status_name='Reject'
                    ).count(),
                    'total_loan_amount': LoanApplicationModel.objects.filter(
                        franchise_id__in=franchise_ids
                    ).aggregate(total=Sum('loan_amount'))['total'] or 0,
                    'average_loan_amount': LoanApplicationModel.objects.filter(
                        franchise_id__in=franchise_ids
                    ).aggregate(avg=Avg('loan_amount'))['avg'] or 0,
                    'applications_this_month': LoanApplicationModel.objects.filter(
                        franchise_id__in=franchise_ids,
                        created_at__month=timezone.now().month
                    ).count(),
                }
            else:
                stats = get_empty_stats()
                
        elif user_type == 'franchise':
            # Franchise can see only their stats
            stats = {
                'total_applications': LoanApplicationModel.objects.filter(
                    franchise=franchise
                ).count(),
                'pending_applications': LoanApplicationModel.objects.filter(
                    franchise=franchise,
                    status_name__status_name='Pending'
                ).count(),
                'approved_applications': LoanApplicationModel.objects.filter(
                    franchise=franchise,
                    status_name__status_name='Accept'
                ).count(),
                'rejected_applications': LoanApplicationModel.objects.filter(
                    franchise=franchise,
                    status_name__status_name='Reject'
                ).count(),
                'total_loan_amount': LoanApplicationModel.objects.filter(
                    franchise=franchise
                ).aggregate(total=Sum('loan_amount'))['total'] or 0,
                'average_loan_amount': LoanApplicationModel.objects.filter(
                    franchise=franchise
                ).aggregate(avg=Avg('loan_amount'))['avg'] or 0,
                'applications_this_month': LoanApplicationModel.objects.filter(
                    franchise=franchise,
                    created_at__month=timezone.now().month
                ).count(),
            }
            
        else:
            stats = get_empty_stats()
            
        return stats
        
    except Exception as e:
        logger.error(f"Error getting loan stats: {e}")
        return get_empty_stats()


def get_empty_stats():
    """Return empty loan statistics"""
    return {
        'total_applications': 0,
        'pending_applications': 0,
        'approved_applications': 0,
        'rejected_applications': 0,
        'total_loan_amount': 0,
        'average_loan_amount': 0,
        'applications_this_month': 0,
    }


def get_loan_filters(request, queryset):
    """Apply filters to loan queryset"""
    try:
        # Filter by first name
        first_name_filter = request.GET.get('first_name', '')
        if first_name_filter:
            queryset = queryset.filter(first_name__icontains=first_name_filter)
        
        # Filter by last name
        last_name_filter = request.GET.get('last_name', '')
        if last_name_filter:
            queryset = queryset.filter(last_name__icontains=last_name_filter)
        
        # Filter by district
        district_filter = request.GET.get('district', '')
        if district_filter:
            queryset = queryset.filter(district__icontains=district_filter)
        
        # Filter by place
        place_filter = request.GET.get('place', '')
        if place_filter:
            queryset = queryset.filter(place__icontains=place_filter)
        
        # Filter by address
        address_filter = request.GET.get('address', '')
        if address_filter:
            queryset = queryset.filter(address__icontains=address_filter)
        
        # Filter by loan type
        loan_type_filter = request.GET.get('loan_type', '')
        if loan_type_filter:
            queryset = queryset.filter(loan_name__loan_name=loan_type_filter)
        
        # Filter by status
        status_filter = request.GET.get('status', '')
        if status_filter:
            queryset = queryset.filter(status_name__status_name=status_filter)
        
        # Filter by bank
        bank_filter = request.GET.get('bank', '')
        if bank_filter:
            queryset = queryset.filter(bank_name__bank_name=bank_filter)
        
        # Filter by executive name
        executive_filter = request.GET.get('executive', '')
        if executive_filter:
            queryset = queryset.filter(executive_name__icontains=executive_filter)
        
        # Filter by reference number 1
        reference_no_1_filter = request.GET.get('reference_no_1', '')
        if reference_no_1_filter:
            queryset = queryset.filter(reference_no_1__icontains=reference_no_1_filter)
        
        # Legacy followup_from/followup_to filters now apply to created_at
        followup_from = request.GET.get('followup_from', '')
        followup_to = request.GET.get('followup_to', '')

        if followup_from:
            try:
                followup_from_date = datetime.strptime(followup_from, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__gte=followup_from_date)
            except ValueError:
                pass

        if followup_to:
            try:
                followup_to_date = datetime.strptime(followup_to, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__lte=followup_to_date)
            except ValueError:
                pass
        
        # Legacy filter by loan name (for general search)
        loan_name_filter = request.GET.get('loan_name', '')
        if loan_name_filter:
            queryset = queryset.filter(
                Q(loan_name__loan_name__icontains=loan_name_filter) |
                Q(first_name__icontains=loan_name_filter) |
                Q(last_name__icontains=loan_name_filter) |
                Q(phone_no__icontains=loan_name_filter)
            )
        
        # Filter by franchise
        franchise_filter = request.GET.get('franchise', '')
        if franchise_filter:
            queryset = queryset.filter(franchise_id=franchise_filter)
        
        # Filter by amount range
        min_amount = request.GET.get('min_amount', '')
        max_amount = request.GET.get('max_amount', '')
        
        if min_amount:
            try:
                min_amount = float(min_amount)
                queryset = queryset.filter(loan_amount__gte=min_amount)
            except ValueError:
                pass
        
        if max_amount:
            try:
                max_amount = float(max_amount)
                queryset = queryset.filter(loan_amount__lte=max_amount)
            except ValueError:
                pass
        
        return queryset
        
    except Exception as e:
        logger.error(f"Error applying loan filters: {e}")
        return queryset


def get_loan_performance_metrics(user_type, user_id=None, franchise=None):
    """Get loan performance metrics for analytics"""
    try:
        if user_type == 'admin':
            # Admin metrics for all loans
            base_queryset = LoanApplicationModel.objects.all()
        elif user_type == 'staff':
            # Staff metrics for assigned franchises
            assignment = StaffAssignmentModel.objects.filter(
                staff_name_id=user_id
            ).prefetch_related('franchise_name').first()
            
            if assignment:
                franchises = assignment.franchise_name.all()
                franchise_ids = [f.franchise_id for f in franchises]
                base_queryset = LoanApplicationModel.objects.filter(
                    franchise_id__in=franchise_ids
                )
            else:
                return get_empty_performance_metrics()
                
        elif user_type == 'franchise':
            # Franchise metrics for their loans only
            base_queryset = LoanApplicationModel.objects.filter(franchise=franchise)
        else:
            return get_empty_performance_metrics()
        
        # Calculate performance metrics
        total_applications = base_queryset.count()
        if total_applications == 0:
            return get_empty_performance_metrics()
        
        # Status distribution
        status_distribution = base_queryset.values('status_name__status_name').annotate(
            count=Count('form_id')
        )
        
        # Monthly trend (last 6 months)
        six_months_ago = timezone.now() - timedelta(days=180)
        monthly_trend = base_queryset.filter(
            created_at__gte=six_months_ago
        ).extra(
            select={'month': "EXTRACT(month FROM created_at)"}
        ).values('month').annotate(
            count=Count('form_id'),
            total_amount=Sum('loan_amount')
        ).order_by('month')
        
        # Loan type distribution
        loan_type_distribution = base_queryset.values('loan_name__loan_name').annotate(
            count=Count('form_id'),
            total_amount=Sum('loan_amount'),
            avg_amount=Avg('loan_amount')
        )
        
        # Bank distribution
        bank_distribution = base_queryset.values('bank_name__bank_name').annotate(
            count=Count('form_id')
        )
        
        # Processing time analysis removed (followup_date no longer used)
        processing_time = {}
        
        return {
            'total_applications': total_applications,
            'status_distribution': list(status_distribution),
            'monthly_trend': list(monthly_trend),
            'loan_type_distribution': list(loan_type_distribution),
            'bank_distribution': list(bank_distribution),
            'processing_time': processing_time,
            'success_rate': calculate_success_rate(status_distribution),
            'average_loan_amount': base_queryset.aggregate(
                avg=Avg('loan_amount')
            )['avg'] or 0,
        }
        
    except Exception as e:
        logger.error(f"Error getting loan performance metrics: {e}")
        return get_empty_performance_metrics()


def get_empty_performance_metrics():
    """Return empty performance metrics"""
    return {
        'total_applications': 0,
        'status_distribution': [],
        'monthly_trend': [],
        'loan_type_distribution': [],
        'bank_distribution': [],
        'processing_time': {},
        'success_rate': 0,
        'average_loan_amount': 0,
    }


def calculate_success_rate(status_distribution):
    """Calculate loan application success rate"""
    try:
        total = sum(item['count'] for item in status_distribution)
        if total == 0:
            return 0
        
        approved = next(
            (item['count'] for item in status_distribution 
             if item['status_name__status_name'] == 'Accept'), 0
        )
        
        return round((approved / total) * 100, 2)
        
    except Exception as e:
        logger.error(f"Error calculating success rate: {e}")
        return 0


def get_recent_loan_activity(user_type, user_id=None, franchise=None, limit=10):
    """Get recent loan activity for dashboard"""
    try:
        if user_type == 'admin':
            queryset = LoanApplicationModel.objects.all()
        elif user_type == 'staff':
            assignment = StaffAssignmentModel.objects.filter(
                staff_name_id=user_id
            ).prefetch_related('franchise_name').first()
            
            if assignment:
                franchises = assignment.franchise_name.all()
                franchise_ids = [f.franchise_id for f in franchises]
                queryset = LoanApplicationModel.objects.filter(
                    franchise_id__in=franchise_ids
                )
            else:
                return []
                
        elif user_type == 'franchise':
            queryset = LoanApplicationModel.objects.filter(franchise=franchise)
        else:
            return []
        
        return list(queryset.select_related(
            'franchise', 'loan_name', 'status_name', 'bank_name'
        ).order_by('-created_at')[:limit])
        
    except Exception as e:
        logger.error(f"Error getting recent loan activity: {e}")
        return []


def get_loan_summary_by_franchise():
    """Get loan summary grouped by franchise for admin dashboard"""
    try:
        return list(LoanApplicationModel.objects.values(
            'franchise__franchise_name'
        ).annotate(
            total_applications=Count('form_id'),
            pending_applications=Count(
                'form_id', 
                filter=Q(status_name__status_name='Pending')
            ),
            approved_applications=Count(
                'form_id', 
                filter=Q(status_name__status_name='Accept')
            ),
            total_amount=Sum('loan_amount'),
            avg_amount=Avg('loan_amount')
        ).order_by('-total_applications'))
        
    except Exception as e:
        logger.error(f"Error getting loan summary by franchise: {e}")
        return []


def validate_loan_data(loan_data):
    """Validate loan application data"""
    errors = []
    
    try:
        # Required field validation
        required_fields = ['first_name', 'phone_no', 'loan_amount']
        for field in required_fields:
            if not loan_data.get(field):
                errors.append(f"{field.replace('_', ' ').title()} is required")
        
        # Phone number validation
        phone = loan_data.get('phone_no', '')
        if phone and len(phone) < 10:
            errors.append("Phone number must be at least 10 digits")
        
        # Loan amount validation
        try:
            amount = float(loan_data.get('loan_amount', 0))
            if amount <= 0:
                errors.append("Loan amount must be greater than 0")
        except (ValueError, TypeError):
            errors.append("Invalid loan amount")
        
        # CIBIL score validation
        cibil_score = loan_data.get('cibil_score', '')
        if cibil_score:
            try:
                score = int(cibil_score)
                if score < 300 or score > 900:
                    errors.append("CIBIL score must be between 300 and 900")
            except (ValueError, TypeError):
                errors.append("Invalid CIBIL score")
        
        return errors
        
    except Exception as e:
        logger.error(f"Error validating loan data: {e}")
        errors.append("Validation error occurred")
        return errors


def get_loan_notifications(user_type, user_id=None, franchise=None):
    """Get loan-related notifications for users"""
    try:
        notifications = []
        
        if user_type == 'admin':
            # Admin notifications
            pending_count = LoanApplicationModel.objects.filter(
                status_name__status_name='Pending'
            ).count()
            
            if pending_count > 0:
                notifications.append({
                    'type': 'warning',
                    'message': f'{pending_count} loan applications pending approval',
                    'count': pending_count
                })
            
            # Recent applications
            recent_count = LoanApplicationModel.objects.filter(
                created_at__date=timezone.now().date()
            ).count()
            
            if recent_count > 0:
                notifications.append({
                    'type': 'info',
                    'message': f'{recent_count} new applications today',
                    'count': recent_count
                })
                
        elif user_type == 'staff':
            # Staff notifications for assigned franchises
            assignment = StaffAssignmentModel.objects.filter(
                staff_name_id=user_id
            ).prefetch_related('franchise_name').first()
            
            if assignment:
                franchises = assignment.franchise_name.all()
                franchise_ids = [f.franchise_id for f in franchises]
                
                pending_count = LoanApplicationModel.objects.filter(
                    franchise_id__in=franchise_ids,
                    status_name__status_name='Pending'
                ).count()
                
                if pending_count > 0:
                    notifications.append({
                        'type': 'warning',
                        'message': f'{pending_count} applications pending in your franchises',
                        'count': pending_count
                    })
                    
        elif user_type == 'franchise':
            # Franchise notifications
            pending_count = LoanApplicationModel.objects.filter(
                franchise=franchise,
                status_name__status_name='Pending'
            ).count()
            
            if pending_count > 0:
                notifications.append({
                    'type': 'info',
                    'message': f'{pending_count} of your applications are pending',
                    'count': pending_count
                })
        
        return notifications
        
    except Exception as e:
        logger.error(f"Error getting loan notifications: {e}")
        return []
