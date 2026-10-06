from django.contrib import admin

from .models import Cliente, Color, DetalleVenta, Inventario, Proveedor, Ropa, Venta


class InventarioInline(admin.TabularInline):
    model = Inventario
    extra = 1


class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 1


@admin.register(Ropa)
class RopaAdmin(admin.ModelAdmin):
    list_display = ("marca", "modelo", "tipo", "talla", "precio", "proveedor")
    list_filter = ("tipo", "talla", "proveedor")
    search_fields = ("modelo", "marca", "descripcion")
    inlines = [InventarioInline]


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ("id", "fecha", "cliente", "total")
    inlines = [DetalleVentaInline]


admin.site.register([Proveedor, Color, Cliente])
