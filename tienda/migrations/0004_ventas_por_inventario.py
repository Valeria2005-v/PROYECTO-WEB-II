import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def borrar_ventas_antiguas(apps, schema_editor):
    """Las ventas viejas guardaban la prenda sin color ni precio; no se pueden convertir
    al modelo nuevo, así que se descartan (eran datos de prueba). SQL directo para que
    funcione aunque la tabla esté a medio migrar."""
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("DELETE FROM tienda_detalleventa")
        cursor.execute("DELETE FROM tienda_venta")


class Migration(migrations.Migration):

    dependencies = [
        ('tienda', '0003_alter_cliente_id_alter_color_id_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(borrar_ventas_antiguas, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='venta',
            name='prendas',
        ),
        # La tabla de detalles se vuelve a crear (así no depende de índices viejos).
        migrations.DeleteModel(
            name='DetalleVenta',
        ),
        migrations.AddField(
            model_name='venta',
            name='usuario',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ventas', to=settings.AUTH_USER_MODEL),
        ),
        migrations.CreateModel(
            name='DetalleVenta',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cantidad', models.PositiveIntegerField(default=1, validators=[django.core.validators.MinValueValidator(1)], verbose_name='cantidad')),
                ('precio_unitario', models.DecimalField(decimal_places=2, max_digits=8, verbose_name='precio unitario')),
                ('inventario', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='detalles', to='tienda.inventario')),
                ('venta', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='detalles', to='tienda.venta')),
            ],
            options={
                'verbose_name': 'detalle de venta',
                'verbose_name_plural': 'detalles de venta',
                'constraints': [models.UniqueConstraint(fields=('venta', 'inventario'), name='detalleventa_venta_inventario_uniq')],
            },
        ),
    ]
