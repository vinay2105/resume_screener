from django.urls import path
from . import views

app_name = "screener"

urlpatterns = [
    path("", views.home, name="home"),
    path("results/<int:pk>/", views.results, name="results"),
    path("history/", views.history, name="history"),
]
