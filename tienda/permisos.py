from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect

from .constantes import ADMIN, ALMACEN, CAJERO


def roles_de(usuario):
    return set(usuario.groups.values_list("name", flat=True))


class RolRequeridoMixin(LoginRequiredMixin):
    """Define `roles = [...]` o sobreescribe get_roles(). El superusuario pasa siempre."""
    roles = []

    def get_roles(self):
        return self.roles

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_superuser and not (roles_de(request.user) & set(self.get_roles())):
            messages.error(request, "No tienes permiso para entrar a esa pantalla.")
            return redirect("inicio")
        return super().dispatch(request, *args, **kwargs)


def roles(request):
    """Context processor: es_admin / es_almacen / es_cajero para las plantillas.
    El superusuario ve todo."""
    u = request.user
    if not u.is_authenticated:
        return {"es_admin": False, "es_almacen": False, "es_cajero": False}
    nombres = roles_de(u)
    return {
        "es_admin": u.is_superuser or ADMIN in nombres,
        "es_almacen": u.is_superuser or ALMACEN in nombres,
        "es_cajero": u.is_superuser or CAJERO in nombres,
    }
