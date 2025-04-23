"""
URL configuration for agentrtw project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
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
from django.contrib import admin
from django.urls import path, include
from django.views.decorators.csrf import csrf_exempt

urlpatterns = [
    path('admin/', admin.site.urls),

    #API
    path('api/', include('apps.core.urls')),


    #dj-rest-auth
    path('api/auth/', include('dj_rest_auth.urls')),

    #dj-rest-auth registration
    path('api/auth/registration/', include('dj_rest_auth.registration.urls')),

    #DRF for Browser
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
]


# /api/auth/login/ (方法: POST, 参数: username/email, password -> 返回: access 和 refresh tokens)
# /api/auth/logout/ (方法: POST, 如果使用了 session 会登出 session，JWT token 需要客户端自行删除)
# /api/auth/token/verify/ (方法: POST, 参数: token -> 验证 token 是否有效)
# /api/auth/token/refresh/ (方法: POST, 参数: refresh -> 返回: 新的 access token)
# /api/auth/password/reset/ (密码重置流程)
# /api/auth/password/reset/confirm/ (密码重置流程)
# /api/auth/registration/ (方法: POST, 参数: username, email, password 等 -> 注册用户)
