from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import DetailView, ListView

from .constantes import ADMIN, CAJERO
from .models import Cliente, Inventario, Venta
from .permisos import RolRequeridoMixin
from .servicios import obtener_publico_general, registrar_venta


class VentaLista(RolRequeridoMixin, ListView):
    roles = [ADMIN, CAJERO]
    template_name = "venta_lista.html"
    paginate_by = 10

    def get_queryset(self):
        qs = Venta.objects.select_related("cliente", "usuario")
        self.q = self.request.GET.get("q", "").strip()
        if self.q:
            qs = qs.filter(cliente__nombre__icontains=self.q)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.q
        return ctx


class VentaDetalle(RolRequeridoMixin, DetailView):
    roles = [ADMIN, CAJERO]
    template_name = "venta_detalle.html"
    queryset = Venta.objects.select_related("cliente", "usuario").prefetch_related(
        "detalles__inventario__ropa", "detalles__inventario__color")


class NuevaVenta(RolRequeridoMixin, View):
    """Registra una venta con uno o varios productos. Toda la lógica y las validaciones
    (duplicados, existencias, descuento de inventario) viven en servicios.registrar_venta."""
    roles = [CAJERO]
    template_name = "venta_nueva.html"

    def contexto(self, cliente_sel=None, filas=None):
        return {
            "clientes": Cliente.objects.all(),
            "cliente_sel": cliente_sel or obtener_publico_general().pk,
            "inventarios": Inventario.objects.filter(unidades__gt=0).select_related(
                "ropa", "color").order_by("ropa__marca", "ropa__modelo", "color__descripcion"),
            "filas": filas or [{"inventario": None, "cantidad": 1}],
        }

    def get(self, request):
        return render(request, self.template_name, self.contexto())

    def post(self, request):
        try:
            cliente = Cliente.objects.get(pk=int(request.POST.get("cliente", "")))
        except (ValueError, Cliente.DoesNotExist):
            messages.error(request, "Elige un cliente válido.")
            return render(request, self.template_name, self.contexto())

        try:
            filas = [
                {"inventario": int(i), "cantidad": int(c)}
                for i, c in zip(request.POST.getlist("inventario"), request.POST.getlist("cantidad"))
                if i
            ]
        except ValueError:
            messages.error(request, "Revisa las cantidades.")
            return render(request, self.template_name, self.contexto(cliente.pk))

        try:
            venta = registrar_venta(
                cliente, [(f["inventario"], f["cantidad"]) for f in filas], request.user)
        except ValidationError as e:
            messages.error(request, e.messages[0])
            return render(request, self.template_name, self.contexto(cliente.pk, filas))

        messages.success(request, f"Venta #{venta.pk} registrada.")
        return redirect("venta_detalle", pk=venta.pk)
