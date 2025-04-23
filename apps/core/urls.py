from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.stocks.views import StockViewSet
from apps.users.views import UserViewSet

router = DefaultRouter()


router.register(r'stocks', StockViewSet, basename='stocks')
router.register(r'users', UserViewSet, basename='users')
router.register(r'watchlist', UserViewSet, basename='watchlist')

urlpatterns = [
    path('', include(router.urls))
]