from django.contrib import admin

# Register your models here.
from .models import *


admin.site.register(Client)
admin.site.register(Room)
admin.site.register(Service)
admin.site.register(Booking)
