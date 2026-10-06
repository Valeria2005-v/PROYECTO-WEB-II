from django.urls import path

from . import usuarios, ventas_views, views

urlpatterns = [
    path("", views.Inicio.as_view(), name="inicio"),
    path("usuarios/", usuarios.UsuarioLista.as_view(), name="usuario_lista"),
    path("usuarios/nuevo/", usuarios.UsuarioCrear.as_view(), name="usuario_nuevo"),
    path("usuarios/<int:pk>/editar/", usuarios.UsuarioEditar.as_view(), name="usuario_editar"),
    path("ventas/", ventas_views.VentaLista.as_view(), name="venta_lista"),
    path("ventas/registrar/", ventas_views.NuevaVenta.as_view(), name="venta_nueva"),
    path("ventas/<int:pk>/", ventas_views.VentaDetalle.as_view(), name="venta_detalle"),
    path("<slug:slug>/", views.Lista.as_view(), name="lista"),
    path("<slug:slug>/nuevo/", views.Crear.as_view(), name="nuevo"),
    path("<slug:slug>/<int:pk>/editar/", views.Editar.as_view(), name="editar"),
    path("<slug:slug>/<int:pk>/eliminar/", views.Eliminar.as_view(), name="eliminar"),
    path("<slug:slug>/<int:pk>/inventario/", views.InventarioView.as_view(), name="inventario"),
]