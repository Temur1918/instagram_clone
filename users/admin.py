from django.contrib import admin
from .models import User, UserConfirmation

# Register your models here.

class UserModelAdmin(admin.ModelAdmin):
    list_display = ['id', 'username', 'email', 'phone_number', 'auth_status']    

admin.site.register(User, UserModelAdmin)
admin.site.register(UserConfirmation)