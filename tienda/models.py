from django.db import models
from authz.models import Usuario


# Modelo para guardar tokens FCM de dispositivos móviles
class FCMDevice(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='fcm_devices', null=True, blank=True)
    registration_id = models.CharField(max_length=255, unique=True)
    TIPO_CHOICES = [
        ('android', 'Android'),
        ('ios', 'iOS'),
        ('web', 'Web'),
    ]
    tipo_dispositivo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='android')
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'FCM Device'
        verbose_name_plural = 'FCM Devices'

    def __str__(self):
        usuario_str = self.usuario.user.username if self.usuario and hasattr(self.usuario, 'user') else 'anon'
        return f"{self.registration_id} ({usuario_str})"

# =======================================
# TABLAS DE CLASIFICACIÓN: CATEGORÍA Y SUBCATEGORÍA
# =======================================
class Categoria(models.Model):
    descripcion = models.CharField(max_length=100)
    def __str__(self):
        return self.descripcion


class SubCategoria(models.Model):
    descripcion = models.CharField(max_length=100)
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, related_name='subcategorias')

    def __str__(self):
        return f"{self.descripcion} ({self.categoria.descripcion})"


# =======================================
# TABLA PRODUCTOS
# =======================================
class Productos(models.Model):
    ESTADO_CHOICES = [
        ('Activo', 'Activo'),
        ('Inactivo', 'Inactivo'),
    ]

    descripcion = models.CharField(max_length=200)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(default=0)
    imagenes = models.JSONField(blank=True, null=True)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='Activo')
    subcategoria = models.ForeignKey(SubCategoria, on_delete=models.SET_NULL, null=True, related_name='productos')

    def __str__(self):
        return self.descripcion


# =======================================
# TABLA GARANTIA
# =======================================
class Garantia(models.Model):
    descripcion = models.TextField()
    tiempo = models.IntegerField(help_text="Tiempo de garantía en meses")
    producto = models.ForeignKey(Productos, on_delete=models.CASCADE, related_name='garantias')

    def __str__(self):
        return f"Garantía {self.tiempo} meses - {self.producto.descripcion}"




# =======================================
# TABLA VENTA
# =======================================
class Venta(models.Model):
    ESTADO_CHOICES = [
        ('Pendiente', 'Pendiente'),
        ('Pagado', 'Pagado'),
        ('Cancelado', 'Cancelado'),
    ]

    fecha = models.DateTimeField(auto_now_add=False)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='Pendiente')
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='ventas')

    def __str__(self):
        return f"Venta #{self.id} - {self.usuario.user.first_name}"


# =======================================
# TABLA DETALLE_VENTA
# =======================================
class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Productos, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField()
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.cantidad} x {self.producto.descripcion}"

# =======================================
# TABLA MANTENIMIENTO
# =======================================
class Mantenimiento(models.Model):
    ESTADO_CHOICES = [
        ('Pendiente', 'Pendiente'),
        ('En proceso', 'En proceso'),
        ('Completado', 'Completado'),
    ]

    fecha_solicitud = models.DateTimeField(blank=True, null=True)
    fecha_atencion = models.DateTimeField(blank=True, null=True)
    costo = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='Pendiente')
    descripcion = models.TextField(blank=True, null=True)
    detalle_venta = models.ForeignKey(DetalleVenta, on_delete=models.CASCADE, related_name='mantenimientos')
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='mantenimientos')

    def __str__(self):
        return f"Mantenimiento de {self.producto.descripcion}"


# =======================================
# TABLA PAGO
# =======================================
# tienda/models.py
class Pago(models.Model):
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    fecha = models.DateTimeField(auto_now_add=True)
    stripe_key = models.CharField(max_length=200, blank=True, null=True)
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='pagos')
        
    def __str__(self):
        return f"Pago {self.monto} - Venta #{self.venta.id}"

# =======================================
# TABLA INGRESO / DETALLE_INGRESO
# =======================================
class Ingreso(models.Model):
    ESTADO_CHOICES = [
        ('Pendiente', 'Pendiente'),
        ('Completado', 'Completado'),
    ]

    fecha = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='Completado')
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='ingresos')

    def __str__(self):
        return f"Ingreso #{self.id}"


class DetalleIngreso(models.Model):
    ingreso = models.ForeignKey(Ingreso, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Productos, on_delete=models.CASCADE)
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.cantidad} x {self.producto.descripcion}"


# =======================================
# TABLA PROMOCION / PRODUCTO_PROMOCION
# =======================================
class Promocion(models.Model):
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    descripcion = models.TextField()
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.BooleanField(default=True)
    def __str__(self):
        return f"Promo {self.monto}% - {self.descripcion[:30]}"


class ProductoPromocion(models.Model):
    fecha = models.DateTimeField(auto_now_add=True)
    producto = models.ForeignKey(Productos, on_delete=models.CASCADE)
    promocion = models.ForeignKey(Promocion, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.producto.descripcion} en {self.promocion}"


# =======================================
# TABLA PREDICCION (IA / ML)
# =======================================
class Prediccion(models.Model):
    producto = models.ForeignKey(Productos, on_delete=models.CASCADE, related_name='predicciones')
    #subcategoria = models.ForeignKey(SubCategoria, on_delete=models.CASCADE, related_name='predicciones')
    fecha = models.DateTimeField(auto_now_add=True)
    valor_predicho = models.DecimalField(max_digits=10, decimal_places=2)
    modelo_usado = models.CharField(max_length=100)
    exactitud = models.DecimalField(max_digits=5, decimal_places=2)

    def __str__(self):
        return f"{self.modelo_usado} ({self.exactitud}%) - {self.producto.descripcion}"