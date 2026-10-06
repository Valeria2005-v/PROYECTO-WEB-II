from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from .models import Cliente, Color, Proveedor, Ropa, Venta

SLUGS = ["ropa", "colores", "proveedores", "clientes", "ventas"]


def management(prefix, n):
    return {f"{prefix}-TOTAL_FORMS": str(n), f"{prefix}-INITIAL_FORMS": "0",
            f"{prefix}-MIN_NUM_FORMS": "0", f"{prefix}-MAX_NUM_FORMS": "1000"}


class TiendaTests(TestCase):
    def setUp(self):
        self.prov = Proveedor.objects.create(nombre="Textiles MX")
        self.color = Color.objects.create(descripcion="Negro")
        self.cliente = Cliente.objects.create(nombre="Ana")

    def test_paginas_cargan(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        for s in SLUGS:
            self.assertEqual(self.client.get(reverse("lista", args=[s])).status_code, 200)
            self.assertEqual(self.client.get(reverse("nuevo", args=[s])).status_code, 200)
        self.assertEqual(self.client.get("/inexistente/").status_code, 404)

    def crear_ropa(self):
        datos = {"marca": "Zeta", "modelo": "Basic", "tipo": "PLAYERA", "talla": "U",
                 "precio": "199.90", "descripcion": "", "proveedor": self.prov.pk,
                 "inventarios-0-color": self.color.pk, "inventarios-0-unidades": "20",
                 **management("inventarios", 1)}
        self.client.post(reverse("nuevo", args=["ropa"]), datos)
        return Ropa.objects.get()

    def test_ropa_con_inventario(self):
        self.assertEqual(self.crear_ropa().existencias(), 20)

    def test_pantalla_inventario(self):
        ropa = self.crear_ropa()

        respuesta = self.client.get(
            reverse("inventario", args=["ropa", ropa.pk])
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Negro")
        self.assertContains(respuesta, "20")

    def test_guardar_inventario(self):
        ropa = self.crear_ropa()
        inventario = ropa.inventarios.get()

        respuesta = self.client.post(
            reverse("inventario", args=["ropa", ropa.pk]),
            {
                f"unidades_{inventario.pk}": "35",
            }
        )

        self.assertRedirects(
            respuesta,
            reverse("lista", args=["ropa"])
        )

        inventario.refresh_from_db()
        self.assertEqual(inventario.unidades, 35)

        mensajes = list(respuesta.wsgi_request._messages)
        self.assertTrue(
            any(
                "Registro guardado correctamente" in str(mensaje)
                for mensaje in mensajes
            )
        )

    def test_pantalla_inventario_sin_colores(self):
        ropa = Ropa.objects.create(
            marca="Zeta",
            modelo="Sin Color",
            tipo="PLAYERA",
            talla="U",
            precio=Decimal("199.90"),
            descripcion="",
            proveedor=self.prov,
        )

        respuesta = self.client.get(
            reverse("inventario", args=["ropa", ropa.pk])
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(
            respuesta,
            "Este producto no tiene colores registrados."
        )
        self.assertContains(
            respuesta,
            "Editar producto y agregar colores"
        )

    def test_venta_calcula_total(self):
        ropa = self.crear_ropa()
        datos = {"fecha": "2026-09-20", "cliente": self.cliente.pk,
                 "detalles-0-ropa": ropa.pk, "detalles-0-cantidad": "3",
                 **management("detalles", 1)}
        self.client.post(reverse("nuevo", args=["ventas"]), datos)
        self.assertEqual(Venta.objects.get().total, Decimal("599.70"))

    def test_no_elimina_proveedor_con_prendas(self):
        self.crear_ropa()
        self.client.post(reverse("eliminar", args=["proveedores", self.prov.pk]))
        self.assertTrue(Proveedor.objects.filter(pk=self.prov.pk).exists())
