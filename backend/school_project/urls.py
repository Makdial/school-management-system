from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('accounts.urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('api/', include('core.urls')),
    path('api/', include('schools.urls')),
    path('api/', include('admissions.urls')),
    path('api/', include('students.urls')),
    path('api/', include('academics.urls')),
    path('api/', include('attendance.urls')),
    path('api/', include('timetable.urls')),
    path('api/', include('examinations.urls')),
    path('api/', include('finance.urls')),
    path('api/', include('assignments.urls')),
    path('api/', include('communications.urls')),
    path('api/', include('library.urls')),
    path('api/', include('hr.urls')),
    path('api/', include('transport.urls')),
    path('api/', include('reports.urls')),
    path('api/', include('audit.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
