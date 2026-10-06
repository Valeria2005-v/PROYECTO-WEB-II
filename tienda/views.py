from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.core.exceptions import FieldDoesNotExist
from django.db import transaction
from django.db.models import ProtectedError, Q, Sum
from django.forms import inlineformset_factory, modelform_factory
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView

from .constantes import ADMIN, ALMACEN, PUBLICO_GENERAL
from .models import Cliente, Color, Inventario, Proveedor, Ropa, Venta
from .permisos import RolRequeridoMixin, roles

# Inventario (Ropa-Color) se captura dentro de la ventana de Ropa, como renglones en línea.
InventarioFormSet = inlineformset_factory(
    Ropa, Inventario, fields=["color", "unidades"], extra=1, can_delete=True)


# Un solo CRUD genérico configurado por módulo.
MODULOS = {
    "ropa": {
        "model": Ropa, "titulo": "Ropa",
        "campos": ["marca", "modelo", "tipo", "talla", "precio", "descripcion", "proveedor"],
        "columnas": ["marca", "modelo", "tipo", "talla", "precio", "proveedor", "existencias"],
        "buscar": ["marca", "modelo", "descripcion", "proveedor__nombre"],
        "select": ["proveedor"], "prefetch": ["inventarios"],
        "formset": InventarioFormSet, "formset_titulo": "Inventario por color",
        "lectura": [ADMIN, ALMACEN], "escritura": [ADMIN],
    },
    "colores": {
        "model": Color, "titulo": "Colores",
        "campos": ["descripcion"], "columnas": ["descripcion"], "buscar": ["descripcion"],
        "lectura": [ADMIN], "escritura": [ADMIN],
    },
    "proveedores": {
        "model": Proveedor, "titulo": "Proveedores",
        "campos": ["nombre", "telefono", "correo"],
        "columnas": ["nombre", "telefono", "correo"], "buscar": ["nombre", "correo"],
        "lectura": [ADMIN], "escritura": [ADMIN],
    },
    "clientes": {
        "model": Cliente, "titulo": "Clientes",
        "campos": ["nombre", "telefono", "correo"],
        "columnas": ["nombre", "telefono", "correo"], "buscar": ["nombre", "correo"],
        "lectura": [ADMIN], "escritura": [ADMIN],
    },
}


def etiqueta(modelo, nombre):
    try:
        return str(modelo._meta.get_field(nombre).verbose_name).capitalize()
    except FieldDoesNotExist:
        return nombre.capitalize()


def valor(obj, nombre):
    display = getattr(obj, f"get_{nombre}_display", None)
    v = display() if display else getattr(obj, nombre)
    return v() if callable(v) else v


class ModuloMixin(RolRequeridoMixin):
    escribe = True  # Crear / Editar / Eliminar; Lista lo pone en False

    def get_roles(self):
        clave = "escritura" if self.escribe else "lectura"
        return self.cfg.get(clave, [ADMIN])

    def dispatch(self, request, *args, **kwargs):
        self.slug = kwargs["slug"]
        self.cfg = MODULOS.get(self.slug)
        if self.cfg is None:
            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return self.cfg["model"].objects.all()

    def get_success_url(self):
        return reverse("lista", args=[self.slug])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(slug=self.slug, titulo=self.cfg["titulo"])
        return ctx


class Inicio(LoginRequiredMixin, TemplateView):
    template_name = "inicio.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        r = roles(self.request)
        if r["es_admin"]:
            ctx["resumen"] = [
                (m["titulo"], m["model"].objects.count(), reverse("lista", args=[s]))
                for s, m in MODULOS.items()]
            ctx["resumen"] += [
                ("Usuarios", User.objects.count(), reverse("usuario_lista")),
                ("Ventas", Venta.objects.count(), reverse("venta_lista"))]
            ctx["ingresos"] = Venta.objects.aggregate(t=Sum("total"))["t"] or 0
        if r["es_admin"] or r["es_cajero"]:
            ctx["ultimas"] = Venta.objects.select_related("cliente")[:5]
        if r["es_admin"] or r["es_almacen"]:
            ctx["bajo_stock"] = (
                Inventario.objects.filter(unidades__lte=5).select_related("ropa", "color")[:8])
        return ctx


class Lista(ModuloMixin, ListView):
    escribe = False
    template_name = "lista.html"
    paginate_by = 10

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.select_related(*self.cfg.get("select", []))
        qs = qs.prefetch_related(*self.cfg.get("prefetch", []))
        q = self.request.GET.get("q", "").strip()
        if q:
            filtro = Q()
            for campo in self.cfg["buscar"]:
                filtro |= Q(**{f"{campo}__icontains": q})
            qs = qs.filter(filtro)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        modelo, columnas = self.cfg["model"], self.cfg["columnas"]
        ctx["encabezados"] = [etiqueta(modelo, c) for c in columnas]
        ctx["filas"] = [(o, [valor(o, c) for c in columnas]) for o in ctx["object_list"]]
        ctx["q"] = self.request.GET.get("q", "")
        ctx["publico_general"] = PUBLICO_GENERAL
        return ctx


class FormularioMixin(ModuloMixin):
    template_name = "form.html"

    def get_form_class(self):
        return modelform_factory(
            self.cfg["model"], fields=self.cfg["campos"], widgets=self.cfg.get("widgets"))

    def _formset(self, instance):
        clase = self.cfg.get("formset")
        return clase(self.request.POST, instance=instance) if clase else None

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        clase = self.cfg.get("formset")
        if clase and "formset" not in ctx:
            ctx["formset"] = clase(instance=self.object)
        ctx["formset_titulo"] = self.cfg.get("formset_titulo")
        return ctx

    def form_valid(self, form):
        fs = self._formset(form.instance)
        if fs is not None and not fs.is_valid():
            return self.render_to_response(self.get_context_data(form=form, formset=fs))
        with transaction.atomic():
            self.object = form.save()
            if fs is not None:
                fs.instance = self.object
                fs.save()
            recalcular = getattr(self.object, "recalcular_total", None)
            if recalcular:
                recalcular()
        messages.success(self.request, "Registro guardado correctamente.")
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        fs = self._formset(form.instance)
        return self.render_to_response(self.get_context_data(form=form, formset=fs))


class Crear(FormularioMixin, CreateView):
    pass


class ProtegePublico:
    """El cliente "Público general" no se puede editar ni eliminar."""

    def get_queryset(self):
        qs = super().get_queryset()
        if self.slug == "clientes":
            qs = qs.exclude(nombre=PUBLICO_GENERAL)
        return qs


class Editar(ProtegePublico, FormularioMixin, UpdateView):
    pass


class Eliminar(ProtegePublico, ModuloMixin, DeleteView):
    template_name = "eliminar.html"

    def form_valid(self, form):
        try:
            self.object.delete()
            messages.success(self.request, "Registro eliminado.")
        except ProtectedError:
            messages.error(
                self.request,
                "No se puede eliminar: tiene registros relacionados "
                "(por ejemplo, ventas o inventario)."
            )
        return redirect(self.get_success_url())

class InventarioView(ModuloMixin, DetailView):
    template_name = "inventario.html"

    def get_roles(self):
        return [ALMACEN]

    def get_queryset(self):
        return Ropa.objects.prefetch_related("inventarios__color")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        inventarios = self.object.inventarios.all()

        ctx["producto"] = self.object
        ctx["inventarios"] = inventarios
        ctx["total_existencias"] = inventarios.aggregate(
            total=Sum("unidades")
        )["total"] or 0

        return ctx

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        inventarios = self.object.inventarios.all()

        with transaction.atomic():
            for inventario in inventarios:
                valor_nuevo = request.POST.get(
                    f"unidades_{inventario.pk}"
                )

                try:
                    unidades = int(valor_nuevo)
                except (TypeError, ValueError):
                    unidades = inventario.unidades

                if unidades < 0:
                    unidades = 0

                inventario.unidades = unidades
                inventario.save()

        messages.success(
            request,
            "Registro guardado correctamente"
        )

        return redirect("lista", slug="ropa")