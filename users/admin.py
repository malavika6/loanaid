from django.contrib import admin
from users.models import *

# Register your models here
admin.site.register(AdminModel)
admin.site.register(StaffModel)

@admin.register(Franchise)
class FranchiseAdmin(admin.ModelAdmin):
    list_display = ['franchise_name', 'franchise_owner', 'referral_code', 'referred_by', 'franchise_type', 'is_active', 'created_at']
    list_filter = ['franchise_type', 'is_active', 'payment_status', 'created_at']
    search_fields = ['franchise_name', 'franchise_owner', 'email', 'referral_code']
    readonly_fields = ['referral_code', 'franchise_id', 'created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('franchise_name', 'franchise_owner', 'franchise_place', 'franchise_type', 'email', 'mobile_no')
        }),
        ('Referral Information', {
            'fields': ('referral_code', 'referred_by')
        }),
        ('Account Details', {
            'fields': ('password', 'is_active', 'payment_status', 'is_franchise')
        }),
        ('Documents', {
            'fields': ('aadhar', 'GST', 'pan', 'ac_no', 'ifsc_code', 'screenshot')
        }),
        ('System Information', {
            'fields': ('franchise_id', 'staff', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ['wallet_id', 'franchise', 'allowance', 'commission', 'incentive', 'get_total_balance', 'created_at']
    list_filter = ['created_at']
    search_fields = ['franchise__franchise_name']
    readonly_fields = ['wallet_id', 'created_at', 'updated_at']

