from django.urls import path

from apps.deadlines.views import (
    ClientCreateView,
    ClientListView,
    DeadlineCompleteConfirmView,
    DeadlineCreateView,
    DeadlineDetailView,
    DeadlineListView,
    DeadlineUpdateView,
    home,
)

urlpatterns = [
    path("", home, name="home"),
    path("deadlines/", DeadlineListView.as_view(), name="deadline-list"),
    path("deadlines/nuevo/", DeadlineCreateView.as_view(), name="deadline-create"),
    path(
        "deadlines/<uuid:pk>/",
        DeadlineDetailView.as_view(),
        name="deadline-detail",
    ),
    path(
        "deadlines/<uuid:pk>/editar/",
        DeadlineUpdateView.as_view(),
        name="deadline-edit",
    ),
    path(
        "deadlines/<uuid:pk>/complete/",
        DeadlineCompleteConfirmView.as_view(),
        name="deadline-complete",
    ),
    path(
        "deadlines/<uuid:pk>/complete",
        DeadlineCompleteConfirmView.as_view(),
        name="deadline-complete-noslash",
    ),
    path("clientes/", ClientListView.as_view(), name="client-list"),
    path("clientes/nuevo/", ClientCreateView.as_view(), name="client-create"),
]
