from django.urls import path

from .consumers import TempoRealConsumer

websocket_urlpatterns = [
    path('ws/app/', TempoRealConsumer.as_asgi()),
]
