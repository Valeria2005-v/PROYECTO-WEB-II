from django.contrib import admin

from .models import Cliente, Color, DetalleVenta, Inventario, Proveedor, Ropa, Venta


class InventarioInline(admin.TabularInline):
    model = Inventario
    extra = 1


class DetalleVentaInline(admin.TabularInline):
    """Solo lectura: las ventas se registran desde la pantalla de ventas."""
    model = DetalleVenta
    extra = 0
    can_delete = False
    readonly_fields = ("inventario", "cantidad", "precio_unitario")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Ropa)
class RopaAdmin(admin.ModelAdmin):
    list_display = ("marca", "modelo", "tipo", "talla", "precio", "proveedor")
    list_filter = ("tipo", "talla", "proveedor")
    search_fields = ("modelo", "marca", "descripcion")
    inlines = [InventarioInline]


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ("id", "fecha", "cliente", "total", "usuario")
    inlines = [DetalleVentaInline]

    def has_add_permission(self, request):
        return False


admin.site.register([Proveedor, Color, Cliente])
