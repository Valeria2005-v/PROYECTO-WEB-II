from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from .constantes import PUBLICO_GENERAL
from .models import Cliente, DetalleVenta, Inventario, Venta


def obtener_publico_general():
    """El cliente por omisión de las ventas (se crea si todavía no existe)."""
    return Cliente.objects.get_or_create(nombre=PUBLICO_GENERAL)[0]


@transaction.atomic
def registrar_venta(cliente, renglones, usuario=None):
    """Registra una venta completa o no registra nada.

    renglones = [(inventario_id, cantidad), ...]
    Valida: al menos un renglón, sin productos repetidos, cantidades >= 1 y que no se
    venda más de lo que hay en inventario. Guarda precio y descuenta existencias.
    Lanza ValidationError con el mensaje que se puede mostrar al usuario.
    """
    if not renglones:
        raise ValidationError("Agrega al menos un producto.")
    ids = [inv_id for inv_id, _ in renglones]
    if len(ids) != len(set(ids)):
        raise ValidationError("No puedes repetir el mismo producto en la venta.")

    inventarios = {
        inv.pk: inv
        for inv in Inventario.objects.select_for_update()
        .select_related("ropa", "color").filter(pk__in=ids).order_by("pk")
    }

    venta = Venta.objects.create(cliente=cliente, usuario=usuario)
    total = Decimal("0.00")
    for inv_id, cantidad in renglones:
        inv = inventarios.get(inv_id)
        if inv is None:
            raise ValidationError("Uno de los productos no existe.")
        if cantidad < 1:
            raise ValidationError("La cantidad debe ser al menos 1.")
        if cantidad > inv.unidades:
            raise ValidationError(
                f"Solo hay {inv.unidades} unidades de {inv.ropa} - {inv.color}.")
        inv.unidades -= cantidad
        inv.save(update_fields=["unidades"])
        precio = inv.ropa.precio
        DetalleVenta.objects.create(
            venta=venta, inventario=inv, cantidad=cantidad, precio_unitario=precio)
        total += precio * cantidad

    venta.total = total
    venta.save(update_fields=["total"])
    return venta
