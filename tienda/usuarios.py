from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.models import Group, User
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView

from .constantes import ADMIN
from .permisos import RolRequeridoMixin


class UsuarioForm(forms.ModelForm):
    password = forms.CharField(
        label="Contraseña", widget=forms.PasswordInput(render_value=False), required=False,
        help_text="Al editar, déjala vacía para no cambiarla.")
    rol = forms.ModelChoiceField(Group.objects.order_by("name"), label="Rol")

    class Meta:
        model = User
        fields = ["username", "first_name", "email", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["rol"].initial = self.instance.groups.first()

    def clean_password(self):
        clave = self.cleaned_data["password"]
        if clave:
            password_validation.validate_password(clave, self.instance)
        return clave

    def clean(self):
        datos = super().clean()
        if not self.instance.pk and not datos.get("password"):
            self.add_error("password", "La contraseña es obligatoria.")
        return datos

    def save(self, commit=True):
        usuario = super().save(commit=False)
        if self.cleaned_data["password"]:
            usuario.set_password(self.cleaned_data["password"])
        usuario.save()
        usuario.groups.set([self.cleaned_data["rol"]])
        return usuario


class UsuarioBase(RolRequeridoMixin):
    roles = [ADMIN]
    success_url = reverse_lazy("usuario_lista")


class UsuarioLista(UsuarioBase, ListView):
    queryset = User.objects.prefetch_related("groups").order_by("username")
    template_name = "usuario_lista.html"
    paginate_by = 10


class UsuarioCrear(UsuarioBase, CreateView):
    form_class = UsuarioForm
    template_name = "usuario_form.html"


class UsuarioEditar(UsuarioBase, UpdateView):
    model = User
    form_class = UsuarioForm
    template_name = "usuario_form.html"
