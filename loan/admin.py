from django.contrib import admin
from loan.models import *

admin.site.register(LoanModel)
admin.site.register(StatusModel)
admin.site.register(BankModel)
admin.site.register(LoanApplicationModel)
admin.site.register(UploadedFile)
admin.site.register(StaffSelectionModel)
admin.site.register(StaffAssignmentModel)
