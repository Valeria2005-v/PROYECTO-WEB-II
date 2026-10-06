from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction  # <--- Asegúrate de incluir 'transaction' aquí
from django.utils import timezone

class Proveedor(models.Model):
    """Proveedor de prendas. Un proveedor surte muchas prendas (1 - *)."""

    nombre = models.CharField(
        "nombre", max_length=100, unique=True,
        help_text="Razón social o nombre comercial del proveedor.",
    )
    telefono = models.CharField(
        "teléfono", max_length=15, blank=True, default="",
    )
    correo = models.EmailField(
        "correo electrónico", max_length=254, blank=True, default="",
    )

    class Meta:
        verbose_name = "proveedor"
        verbose_name_plural = "proveedores"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Color(models.Model):
    descripcion = models.CharField(
        "descripción", max_length=30, unique=True,
        help_text="Ej. Negro, Blanco, Azul.",
    )

    class Meta:
        verbose_name = "color"
        verbose_name_plural = "colores"
        ordering = ["descripcion"]

    def __str__(self):
        return self.descripcion


class Ropa(models.Model):
    class Tipo(models.TextChoices):
        PLAYERA = "PLAYERA", "Playera"
        CAMISA = "CAMISA", "Camisa"
        PANTALON = "PANTALON", "Pantalón"
        SHORT = "SHORT", "Short"
        VESTIDO = "VESTIDO", "Vestido"
        FALDA = "FALDA", "Falda"
        SUDADERA = "SUDADERA", "Sudadera"
        CHAMARRA = "CHAMARRA", "Chamarra"
        OTRO = "OTRO", "Otro"

    class Talla(models.TextChoices):
        UNITALLA = "U", "Unitalla"
        CH = "CH", "Chica"
        M = "M", "Mediana"
        G = "G", "Grande"
        XG = "XG", "Extra grande"

    modelo = models.CharField("modelo", max_length=50)
    descripcion = models.CharField(
        "descripción", max_length=200, blank=True, default="",
    )
    tipo = models.CharField(
        "tipo", max_length=10, choices=Tipo.choices, default=Tipo.OTRO,
    )
    marca = models.CharField("marca", max_length=50)
    precio = models.DecimalField(
        "precio", max_digits=8, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    talla = models.CharField(
        "talla", max_length=2, choices=Talla.choices, default=Talla.UNITALLA,
    )

    proveedor = models.ForeignKey(
        Proveedor, on_delete=models.PROTECT, related_name="prendas",
    )
    colores = models.ManyToManyField(
        Color, through="Inventario", related_name="prendas",
    )

    class Meta:
        verbose_name = "prenda"
        verbose_name_plural = "ropa"
        ordering = ["marca", "modelo"]
        constraints = [
            models.UniqueConstraint(
                fields=["modelo", "marca", "talla"], name="ropa_modelo_marca_talla_uniq",
            ),
        ]

    def __str__(self):
        return f"{self.marca} {self.modelo} ({self.get_talla_display()})"

    def existencias(self):
        return sum(i.unidades for i in self.inventarios.all())


class Inventario(models.Model):

    ropa = models.ForeignKey(Ropa, on_delete=models.CASCADE, related_name="inventarios")
    color = models.ForeignKey(Color, on_delete=models.PROTECT, related_name="inventarios")
    unidades = models.PositiveIntegerField("unidades", default=0)

    class Meta:
        verbose_name = "inventario"
        verbose_name_plural = "inventarios"
        constraints = [
            models.UniqueConstraint(
                fields=["ropa", "color"], name="inventario_ropa_color_uniq",
            ),
        ]

    def __str__(self):
        return f"{self.ropa} - {self.color}: {self.unidades}"


class Cliente(models.Model):
    nombre = models.CharField("nombre", max_length=100)
    telefono = models.CharField(
        "teléfono", max_length=15, blank=True, default="",
    )
    correo = models.EmailField(
        "correo electrónico", max_length=254, blank=True, default="",
    )

    class Meta:
        verbose_name = "cliente"
        verbose_name_plural = "clientes"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Venta(models.Model):
    fecha = models.DateField("fecha", default=timezone.localdate)
    total = models.DecimalField(
        "total", max_digits=10, decimal_places=2, default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    # Venta (*) ---- (1) Cliente
    cliente = models.ForeignKey(
        Cliente, on_delete=models.PROTECT, related_name="compras",
    )
    # Venta (*) ---- (*) Ropa, con la clase de asociación DetalleVenta
    prendas = models.ManyToManyField(
        Ropa, through="DetalleVenta", related_name="ventas",
    )

    class Meta:
        verbose_name = "venta"
        verbose_name_plural = "ventas"
        ordering = ["-fecha", "-id"]

    def __str__(self):
        return f"Venta #{self.pk} - {self.fecha}"

    def recalcular_total(self):
        """Suma cantidad x precio de cada renglón del detalle."""
        self.total = sum(
            (d.cantidad * d.ropa.precio for d in self.detalles.select_related("ropa")),
            Decimal("0.00"),
        )
        self.save(update_fields=["total"])


class DetalleVenta(models.Model):
    """Clase de asociación entre Venta y Ropa."""

    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name="detalles")
    ropa = models.ForeignKey(Ropa, on_delete=models.PROTECT, related_name="detalles")
    cantidad = models.PositiveIntegerField(
        "cantidad", default=1, validators=[MinValueValidator(1)],
    )

    class Meta:
        verbose_name = "detalle de venta"
        verbose_name_plural = "detalles de venta"
        constraints = [
            models.UniqueConstraint(
                fields=["venta", "ropa"], name="detalleventa_venta_ropa_uniq",
            ),
        ]

    def __str__(self):
        return f"{self.cantidad} x {self.ropa}"

    def clean(self):
        super().clean()
        # Si es un registro nuevo o se modificó la cantidad, validamos stock
        if self.pk:
            original = DetalleVenta.objects.get(pk=self.pk)
            diferencia = self.cantidad - original.cantidad
        else:
            diferencia = self.cantidad

        if diferencia > 0:
            # Validamos que existan suficientes unidades sumando todo el inventario de la prenda
            stock_actual = sum(i.unidades for i in self.ropa.inventarios.all())
            if diferencia > stock_actual:
                raise ValidationError(
                    f"No hay suficiente stock para '{self.ropa}'. Stock disponible: {stock_actual}"
                )

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self.pk:
                # Si ya existe, calculamos la diferencia para descontar o devolver stock
                original = DetalleVenta.objects.get(pk=self.pk)
                diferencia = self.cantidad - original.cantidad
                if diferencia != 0:
                    self._descontar_inventario(diferencia)
            else:
                # Si es nuevo, descontamos la cantidad completa
                self._descontar_inventario(self.cantidad)

            super().save(*args, **kwargs)
            # Recalculamos el total de la venta automáticamente
            self.venta.recalcular_total()

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            # Si se elimina el detalle de venta, devolvemos las unidades al inventario
            self._devolver_inventario(self.cantidad)
            venta_obj = self.venta
            super().delete(*args, **kwargs)
            venta_obj.recalcular_total()

    def _descontar_inventario(self, cantidad_a_descontar):
        """Descuenta unidades de los inventarios asociados a la ropa (de forma FIFO o al primer color con stock)."""
        restante = cantidad_a_descontar
        # Obtenemos los inventarios de esta prenda que tengan unidades disponibles
        inventarios = self.ropa.inventarios.filter(unidades__gt=0)
        
        stock_total = sum(i.unidades for i in inventarios)
        if restante > stock_total:
            raise ValidationError(f"Stock insuficiente para la prenda {self.ropa}. Faltan unidades.")

        for inv in inventarios:
            if restante <= 0:
                break
            if inv.unidades >= restante:
                inv.unidades -= restante
                inv.save(update_fields=["unidades"])
                restante = 0
            else:
                restante -= inv.unidades
                inv.unidades = 0
                inv.save(update_fields=["unidades"])

    def _devolver_inventario(self, cantidad_a_devolver):
        """Devuelve las unidades al inventario (al primer registro de inventario disponible de la ropa)."""
        inv = self.ropa.inventarios.first()
        if inv:
            inv.unidades += cantidad_a_devolver
            inv.save(update_fields=["unidades"])
        else:
            # Si por alguna razón no hay inventarios creados, creamos uno por defecto o manejamos el caso
            pass