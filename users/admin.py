from django.contrib import admin
from users.models import *

# Register your models here
admin.site.register(AdminModel)
admin.site.register(StaffModel)
admin.site.register(Franchise)

