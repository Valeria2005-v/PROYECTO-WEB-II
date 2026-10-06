from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import Group, User
from django.forms import inlineformset_factory

from .models import Inventario, Ropa


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Usuario",
        widget=forms.TextInput(attrs={"autofocus": True, "autocomplete": "username"}),
    )
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )


InventarioFormSet = inlineformset_factory(
    Ropa,
    Inventario,
    fields=["color", "unidades"],
    extra=1,
    can_delete=True,
)


class UsuarioForm(forms.ModelForm):
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput,
        required=False,
        help_text="Déjala en blanco si no deseas cambiar la contraseña existente.",
    )
    rol = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        required=True,
        label="Rol asignado",
    )

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["password"].required = False
            grupos = self.instance.groups.all()
            if grupos.exists():
                self.fields["rol"].initial = grupos.first()
        else:
            self.fields["password"].required = True

    def save(self, commit=True):
        usuario = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            usuario.set_password(password)
        if commit:
            usuario.save()
            usuario.groups.clear()
            usuario.groups.add(self.cleaned_data["rol"])
        return usuario