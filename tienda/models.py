from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
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
    # Quién registró la venta (el cajero)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="ventas",
    )

    class Meta:
        verbose_name = "venta"
        verbose_name_plural = "ventas"
        ordering = ["-fecha", "-id"]

    def __str__(self):
        return f"Venta #{self.pk} - {self.fecha}"


class DetalleVenta(models.Model):
    """Renglón de una venta: una prenda en un color (Inventario), con su cantidad y el
    precio al que se vendió. La lógica de inventario vive en servicios.registrar_venta."""

    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name="detalles")
    inventario = models.ForeignKey(
        Inventario, on_delete=models.PROTECT, related_name="detalles",
    )
    cantidad = models.PositiveIntegerField(
        "cantidad", default=1, validators=[MinValueValidator(1)],
    )
    precio_unitario = models.DecimalField("precio unitario", max_digits=8, decimal_places=2)

    class Meta:
        verbose_name = "detalle de venta"
        verbose_name_plural = "detalles de venta"
        constraints = [
            models.UniqueConstraint(
                fields=["venta", "inventario"], name="detalleventa_venta_inventario_uniq",
            ),
        ]

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario

    def __str__(self):
        return f"{self.cantidad} x {self.inventario}"
