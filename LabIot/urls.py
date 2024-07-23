"""
URL configuration for LabIot project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

# urls.py
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from sensor.views import (
    sensor_data,
    rssi_data,
    admin_list,
    admin_add,
    admin_edit,
    admin_delete,
    admin_reset,
    login,
    logout,
    image_code,
    get_heatmap_json,
    get_heatmap_img,
    get_sysinfo,
    get_smokemap_img,
    get_hydrogenmap_img,
    get_comap_img

)
# appname = 'sensor'

urlpatterns = [
    path('', login),
    path('login/', login),
    path('logout/', logout),

    path('sensordata/', sensor_data),
    path('rssidata/', rssi_data),

    path('admin/list/', admin_list),
    path('admin/add/', admin_add),
    path('admin/<int:nid>/edit/', admin_edit),
    path('admin/<int:nid>/delete/', admin_delete),
    path('admin/<int:nid>/reset/', admin_reset),

    # monitor
    path('monitor/temp/', get_heatmap_img),
    path('monitor/temp/generate/', get_heatmap_json),
    path('monitor/smoke/', get_smokemap_img),
    path('monitor/hydrogen/', get_hydrogenmap_img),
    path('monitor/co/', get_comap_img),

    # sysinfo
    path('sysinfo/state/', get_sysinfo)

]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)