from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from tienda.constantes import ADMIN, ALMACEN, CAJERO, PUBLICO_GENERAL
from tienda.models import Cliente


class Command(BaseCommand):
    help = "Crea los grupos de roles y el cliente Público general (se puede repetir)."

    def handle(self, *args, **opciones):
        for nombre in (ADMIN, ALMACEN, CAJERO):
            Group.objects.get_or_create(name=nombre)
        Cliente.objects.get_or_create(nombre=PUBLICO_GENERAL)
        self.stdout.write(self.style.SUCCESS("Roles y cliente listos."))
