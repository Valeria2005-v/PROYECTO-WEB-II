from django.urls import path

from . import views

urlpatterns = [
    path("", views.Inicio.as_view(), name="inicio"),
    path("<slug:slug>/", views.Lista.as_view(), name="lista"),
    path("<slug:slug>/nuevo/", views.Crear.as_view(), name="nuevo"),
    path("<slug:slug>/<int:pk>/editar/", views.Editar.as_view(), name="editar"),
    path("<slug:slug>/<int:pk>/eliminar/", views.Eliminar.as_view(), name="eliminar"),
    path("<slug:slug>/<int:pk>/inventario/", views.InventarioView.as_view(), name="inventario"),
]