from django.contrib import admin
from django.urls import path, re_path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve as serve_static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('store.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # cPanel/Passenger shared hosting has no separate web-server rule for
    # /media/ the way it does for /static/ via WhiteNoise. Without this,
    # every uploaded image (product photos, category images, hero slides,
    # blog covers) saves successfully but 404s in the browser the moment
    # DEBUG=False in production. Not ideal for a high-traffic site, but the
    # correct, standard fix for this deployment target.
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve_static, {'document_root': settings.MEDIA_ROOT}),
    ]
