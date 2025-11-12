# core/views.py

from datetime import datetime
import json
from django.http import HttpResponse
import stripe
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response
import os
from dotenv import load_dotenv
from rest_framework import status
from django.db import transaction
from tienda.models import Pago, Venta, Productos, DetalleVenta
from authz.models import Usuario
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated

load_dotenv()
stripe.api_key = settings.STRIPE_SECRET_KEY
url_frontend = os.getenv("URL_FRONTEND", "http://127.0.0.1:3000")


# ============================================================================
# HELPER: Redirección a Deep Links sin validación de esquema
# ============================================================================
def redirect_to_deep_link(url):
    """
    Crea una respuesta de redirección HTTP 302 a cualquier URL, incluyendo
    esquemas personalizados como 'turismoapp://' sin validación.

    Solución para DisallowedRedirect: Django valida esquemas en HttpResponseRedirect.__init__()
    antes de que podamos establecer allowed_schemes. Esta función crea la response manualmente.
    """
    response = HttpResponse(status=302)
    response["Location"] = url
    return response


# @permission_classes([IsAuthenticated])

@api_view(["POST"])
def crear_checkout_session(request):
    try:
        data = request.data
        items = data.get("items", [])  # Lista de productos
        descripcion_general = data.get("descripcion", "Compra en MiTienda")
        
        if not items:
            return Response({"error": "No hay productos en el carrito"}, status=status.HTTP_400_BAD_REQUEST)

        # Calcular total y preparar items para Stripe
        total = 0
        line_items = []
        
        for item in items:
            producto_id = item.get("producto_id")
            cantidad = int(item.get("cantidad", 1))
            precio_unitario = float(item.get("precio", 0))
            nombre = item.get("nombre", "Producto")
            
            if precio_unitario <= 0:
                return Response({"error": f"Precio inválido para {nombre}"}, status=status.HTTP_400_BAD_REQUEST)
            
            total += precio_unitario * cantidad
            
            line_items.append({
                "price_data": {
                    "currency": "bob",
                    "product_data": {"name": nombre},
                    "unit_amount": int(precio_unitario * 100),  # Convertir a centavos
                },
                "quantity": cantidad,
            })

        if total <= 0:
            return Response({"error": "Total inválido"}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ CORREGIDO: Obtener usuario autenticado actual
        if not request.user.is_authenticated:
            return Response({"error": "Usuario no autenticado. Por favor inicia sesión."}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            usuario = Usuario.objects.get(user=request.user)
            usuario_id = str(usuario.id)
        except Usuario.DoesNotExist:
            return Response({"error": "Perfil de usuario no encontrado"}, status=status.HTTP_404_NOT_FOUND)

        # Construir URLs de retorno
        url_frontend = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        success_url = f"{url_frontend}/pago-exitoso?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{url_frontend}/pago-cancelado/"

        # Crear sesión de checkout en Stripe
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="payment",
            line_items=line_items,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "usuario_id": usuario_id,  
                "descripcion": descripcion_general,
                "total": str(total),
                "items": json.dumps(items),  # Guardar todos los items como JSON
                "fecha_solicitud": datetime.now(),  #
            },
        )

        return Response({
            "checkout_url": session.url,
            "session_id": session.id,
            "total": total,
            "mensaje": "Sesión de pago creada correctamente"
        })

    except Exception as e:
        print("❌ Error creando sesión de Stripe:", e)
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@authentication_classes([TokenAuthentication])  # 🔐 Agregar esto
@permission_classes([IsAuthenticated])          # 🔐 Y esto
def verificar_pago(request):
    session_id = request.GET.get("session_id")

    if not session_id:
        return Response({"error": "Falta session_id"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # DEBUG: Verificar autenticación
        print(f"🔐 Usuario autenticado: {request.user}")
        print(f"🔐 Is authenticated: {request.user.is_authenticated}")
        
        # Recuperar la sesión de Stripe
        session = stripe.checkout.Session.retrieve(session_id)
        pago_exitoso = session.payment_status == "paid"

        if not pago_exitoso:
            return Response({
                "pago_exitoso": False,
                "mensaje": "El pago no se ha completado"
            }, status=status.HTTP_400_BAD_REQUEST)

        # El resto de tu código permanece igual...
        metadata = getattr(session, "metadata", {}) or {}
        usuario_id = metadata.get("usuario_id")
        descripcion = metadata.get("descripcion", "Compra en MiTienda")
        total = float(metadata.get("total", 0))
        items_json = metadata.get("items", "[]")
        
        try:
            items = json.loads(items_json)
        except json.JSONDecodeError:
            items = []

        # Buscar si ya existe una venta para esta sesión
        pago_existente = Pago.objects.filter(stripe_key=session.payment_intent).first()
        
        if pago_existente:
            return Response({
                "pago_exitoso": True,
                "mensaje": "El pago ya fue procesado anteriormente",
                "venta_id": pago_existente.venta.id,
                "pago_id": pago_existente.id,
                "total": float(pago_existente.monto)
            })

        # ✅ Ahora request.user está autenticado gracias a los decoradores
        try:
            usuario_venta = Usuario.objects.get(user=request.user)
        except Usuario.DoesNotExist:
            return Response({
                "error": "Perfil de usuario no encontrado"
            }, status=status.HTTP_404_NOT_FOUND)

        # Crear venta, pago y reducir stock en una transacción
        with transaction.atomic():
            venta = Venta.objects.create(
                usuario=usuario_venta,
                total=total,
                estado='Pagado',
            )

            productos_sin_stock = []
            productos_procesados = []  # Para debug
            
            # Crear detalles de venta y reducir stock
            for item in items:
                producto_id = item.get("producto_id")
                cantidad = int(item.get("cantidad", 1))
                precio_unitario = float(item.get("precio", 0))
                
                if not producto_id:
                    productos_sin_stock.append({
                        "producto": "Producto sin ID",
                        "solicitado": cantidad,
                        "disponible": 0,
                        "error": "Falta ID del producto"
                    })
                    continue

                try:
                    producto = Productos.objects.get(id=producto_id, estado='Activo')
                    
                    # ✅ VERIFICAR Y REDUCIR STOCK
                    print(f"📦 Procesando producto: {producto.descripcion}")
                    print(f"📦 Stock antes: {producto.stock}, Cantidad a reducir: {cantidad}")
                    
                    if producto.stock < cantidad:
                        productos_sin_stock.append({
                            "producto": producto.descripcion,
                            "solicitado": cantidad,
                            "disponible": producto.stock
                        })
                        continue
                    
                    # ✅ REDUCIR EL STOCK - ¡Esto es lo importante!
                    producto.stock -= cantidad
                    producto.save()
                    
                    print(f"📦 Stock después: {producto.stock}")
                    productos_procesados.append({
                        "producto": producto.descripcion,
                        "cantidad": cantidad,
                        "stock_restante": producto.stock
                    })
                    
                except Productos.DoesNotExist:
                    productos_sin_stock.append({
                        "producto": f"ID {producto_id}",
                        "solicitado": cantidad,
                        "disponible": 0,
                        "error": "Producto no encontrado"
                    })
                    continue

                # Calcular subtotal y crear detalle de venta
                subtotal = precio_unitario * cantidad
                
                DetalleVenta.objects.create(
                    venta=venta,
                    producto=producto,
                    cantidad=cantidad,
                    subtotal=subtotal
                )

            # Debug: mostrar productos procesados
            print(f"✅ Productos procesados: {productos_procesados}")
            print(f"⚠️ Productos sin stock: {productos_sin_stock}")

            # Crear el pago
            pago = Pago.objects.create(
                monto=total,
                stripe_key=session.payment_intent,
                venta=venta
            )

        # Construir respuesta
        respuesta = {
            "pago_exitoso": True,
            "mensaje": "Pago procesado y venta creada exitosamente",
            "venta_id": venta.id,
            "pago_id": pago.id,
            "total": total,
            "fecha": venta.fecha.isoformat(),
            "usuario": f"{usuario_venta.user.first_name} {usuario_venta.user.last_name}",
            "productos_procesados": productos_procesados,  # Para debug
        }

        if productos_sin_stock:
            respuesta["productos_sin_stock"] = productos_sin_stock
            respuesta["mensaje_stock"] = "Algunos productos tenían stock insuficiente"
        else:
            respuesta["mensaje_stock"] = "Stock actualizado correctamente"

        return Response(respuesta)

    except stripe.error.InvalidRequestError as e:
        print("❌ Error de Stripe:", e)
        return Response({"error": "Sesión de pago no válida"}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        print("❌ Error procesando pago:", e)
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
# ============================================================================
# 📱 ENDPOINTS ESPECÍFICOS PARA APP MÓVIL FLUTTER - STRIPE CON DEEP LINKS
# ============================================================================


@api_view(["POST"])
def crear_checkout_session_mobile(request):
    """
    Crea una sesión de Stripe Checkout específica para app móvil.
    Maneja deep links para retornar automáticamente a la app después del pago.

    POST /api/crear-checkout-session-mobile/

    Headers:
        Authorization: Token <user_token>
        Content-Type: application/json

    Body:
    {
      "reserva_id": 35,
      "nombre": "Tour Salar de Uyuni",
      "precio": 48000,        // EN CENTAVOS (480.00 BOB = 48000)
      "cantidad": 1,          // opcional, default=1
      "moneda": "BOB",        // opcional, default=BOB
      "cliente_email": "user@email.com"  // opcional
    }

    Response:
    {
      "success": true,
      "checkout_url": "https://checkout.stripe.com/...",
      "session_id": "cs_test_...",
      "reserva_id": 35,
      "monto": 480.00,
      "moneda": "BOB"
    }
    """
    from tienda.models import Reserva
    from decimal import Decimal

    try:
        # Validar autenticación
        if not request.user.is_authenticated:
            return Response(
                {
                    "success": False,
                    "error": "Debes estar autenticado para crear una sesión de pago",
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Extraer datos del request
        data = request.data
        reserva_id = data.get("reserva_id")
        nombre = data.get("nombre", "Reserva")
        precio = data.get("precio")
        cantidad = int(data.get("cantidad", 1))
        moneda = data.get("moneda", "BOB").upper()
        cliente_email = data.get("cliente_email", None)

        # Validaciones de campos obligatorios
        if not reserva_id:
            return Response(
                {
                    "success": False,
                    "error": "Campo 'reserva_id' es obligatorio",
                    "campo_faltante": "reserva_id",
                    "ejemplo": {
                        "reserva_id": 35,
                        "nombre": "Tour Uyuni",
                        "precio": 48000,
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not precio:
            return Response(
                {
                    "success": False,
                    "error": "Campo 'precio' es obligatorio (en centavos)",
                    "campo_faltante": "precio",
                    "ejemplo": "Para 480 BOB, enviar: 48000",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Convertir precio a int y validar
        try:
            precio = int(precio)
        except (ValueError, TypeError):
            return Response(
                {
                    "success": False,
                    "error": "El precio debe ser un número entero en centavos",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if precio <= 0:
            return Response(
                {
                    "success": False,
                    "error": "El precio debe ser mayor a 0 (en centavos)",
                    "ejemplo": "Para 480 BOB, enviar: 48000",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Verificar que la reserva existe
        try:
            reserva = Reserva.objects.get(id=reserva_id)
        except Reserva.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "error": f"Reserva con ID {reserva_id} no encontrada",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # Verificar que el usuario tiene permiso para esta reserva
        perfil = getattr(request.user, "perfil", None)
        if not request.user.is_staff:  # Los admins pueden pagar cualquier reserva
            if not perfil or reserva.cliente.id != perfil.id:
                return Response(
                    {
                        "success": False,
                        "error": "No tienes permiso para acceder a esta reserva",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        # Configurar URLs de callback del backend (NO del frontend)
        base_url = "https://backendspring2-production.up.railway.app/api"
        success_url = f"{base_url}/pago-exitoso-mobile/?session_id={{CHECKOUT_SESSION_ID}}&reserva_id={reserva_id}"
        cancel_url = f"{base_url}/pago-cancelado-mobile/?reserva_id={reserva_id}"

        # Preparar metadata para Stripe
        metadata = {
            "usuario_id": str(request.user.id),
            "reserva_id": str(reserva_id),
            "payment_type": "reserva",
            "platform": "mobile_flutter",
            "titulo": nombre,
            "cliente_perfil_id": str(perfil.id) if perfil else None,
            "cliente_email": request.user.email,
        }

        # Preparar parámetros de sesión Stripe
        session_params = {
            "payment_method_types": ["card"],
            "mode": "payment",
            "line_items": [
                {
                    "price_data": {
                        "currency": moneda.lower(),
                        "product_data": {
                            "name": nombre,
                            "description": f"Reserva #{reserva_id}",
                        },
                        "unit_amount": precio,  # Ya en centavos
                    },
                    "quantity": cantidad,
                }
            ],
            "success_url": success_url,
            "cancel_url": cancel_url,
            "metadata": metadata,
        }

        # Agregar email si se proporciona
        if cliente_email:
            session_params["customer_email"] = cliente_email
        elif request.user.email:
            session_params["customer_email"] = request.user.email

        # Crear sesión en Stripe
        session = stripe.checkout.Session.create(**session_params)

        # Log para debugging
        print(f"✅ Sesión Stripe móvil creada")
        print(f"   Session ID: {session.id}")
        print(f"   Reserva ID: {reserva_id}")
        print(f"   Usuario: {request.user.email}")
        print(f"   Monto: {precio/100} {moneda}")
        print(f"   Success URL: {success_url}")

        # Devolver respuesta exitosa
        return Response(
            {
                "success": True,
                "checkout_url": session.url,
                "session_id": session.id,
                "reserva_id": reserva_id,
                "monto": precio / 100,  # Convertir a formato decimal para mostrar
                "moneda": moneda,
                "expires_at": session.expires_at,
            },
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        print(f"❌ Error creando checkout móvil: {str(e)}")
        import traceback

        traceback.print_exc()

        return Response(
            {
                "success": False,
                "error": "Error al crear sesión de pago",
                "detalle": str(e),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
def pago_exitoso_mobile(request):
    """
    Callback de Stripe después de pago exitoso.
    Valida el pago, actualiza la reserva y redirige a la app móvil con deep link.

    GET /api/pago-exitoso-mobile/?session_id=cs_test_...&reserva_id=35

    Este endpoint:
    1. Recibe callback de Stripe con session_id
    2. Verifica el pago con Stripe API
    3. Actualiza el estado de la reserva en la base de datos
    4. Crea registro de pago
    5. Redirige a deep link: turismoapp://payment-success?...

    VERSIÓN: 2024-11-03 v2 - Fix allowed_schemes per-response
    """
    from tienda.models import Reserva, Pago
    from datetime import date
    from decimal import Decimal

    session_id = request.GET.get("session_id")
    reserva_id = request.GET.get("reserva_id")

    print(f"\n{'='*60}")
    print(f"📱 CALLBACK PAGO EXITOSO MÓVIL [v2-fixed-allowed-schemes]")
    print(f"{'='*60}")
    print(f"   Session ID: {session_id}")
    print(f"   Reserva ID: {reserva_id}")

    # Validar parámetros
    if not session_id or not reserva_id:
        print(f"❌ Error: Faltan parámetros")
        missing_params_link = "turismoapp://payment-error?error=missing_params"
        return redirect_to_deep_link(missing_params_link)

    try:
        # Verificar sesión con Stripe API
        session = stripe.checkout.Session.retrieve(session_id)

        print(f"   Estado de pago: {session.payment_status}")
        print(f"   Monto: {session.amount_total} centavos")
        print(f"   Moneda: {session.currency}")

        # Validar que el pago fue completado
        if session.payment_status == "paid":
            # Buscar la reserva
            try:
                reserva = Reserva.objects.get(id=reserva_id)

                # Actualizar estado de la reserva
                estado_anterior = reserva.estado
                reserva.estado = "PAGADA"
                reserva.save(update_fields=["estado"])

                print(f"   ✅ Reserva actualizada: {estado_anterior} → PAGADA")

                # Calcular monto en formato decimal
                monto_decimal = Decimal(str(session.amount_total / 100))

                # Crear o actualizar registro de pago (prevenir duplicados)
                pago, created = Pago.objects.get_or_create(
                    reserva=reserva,
                    url_stripe=session.url,
                    defaults={
                        "monto": monto_decimal,
                        "metodo": "Tarjeta",
                        "estado": "Confirmado",
                        "fecha_pago": date.today(),
                    },
                )

                if created:
                    print(f"   ✅ Pago registrado: ID {pago.id}, Monto {monto_decimal}")
                else:
                    print(
                        f"   ℹ️  Pago ya existía: ID {pago.id} (prevención de duplicados)"
                    )

                # Construir deep link de éxito
                deep_link = (
                    f"turismoapp://payment-success"
                    f"?session_id={session_id}"
                    f"&reserva_id={reserva_id}"
                    f"&monto={monto_decimal}"
                    f"&status=completed"
                    f"&moneda={session.currency.upper()}"
                )

                print(f"   🚀 Redirigiendo a app: {deep_link[:80]}...")
                print(f"{'='*60}\n")

                # Redirigir a la app móvil usando deep link personalizado
                return redirect_to_deep_link(deep_link)

            except Reserva.DoesNotExist:
                print(f"   ❌ Error: Reserva {reserva_id} no encontrada")
                error_link = (
                    f"turismoapp://payment-error"
                    f"?error=reserva_not_found"
                    f"&reserva_id={reserva_id}"
                )
                return redirect_to_deep_link(error_link)

        elif session.payment_status == "unpaid":
            # Pago no completado
            print(f"   ⚠️  Pago no completado: {session.payment_status}")
            pending_link = (
                f"turismoapp://payment-pending"
                f"?session_id={session_id}"
                f"&reserva_id={reserva_id}"
                f"&status={session.payment_status}"
            )
            return redirect_to_deep_link(pending_link)

        else:
            # Otro estado
            print(f"   ⚠️  Estado inesperado: {session.payment_status}")
            error_status_link = (
                f"turismoapp://payment-error"
                f"?error=unexpected_status"
                f"&status={session.payment_status}"
                f"&reserva_id={reserva_id}"
            )
            return redirect_to_deep_link(error_status_link)

    except Exception as e:
        print(f"   ❌ Error procesando pago: {str(e)}")
        import traceback

        traceback.print_exc()
        print(f"{'='*60}\n")

        exception_link = (
            f"turismoapp://payment-error"
            f"?error=processing_error"
            f"&session_id={session_id}"
        )
        return redirect_to_deep_link(exception_link)


@api_view(["GET"])
def pago_cancelado_mobile(request):
    """
    Callback cuando el usuario cancela el pago en Stripe.
    Redirige a la app móvil con deep link de cancelación.

    GET /api/pago-cancelado-mobile/?reserva_id=35
    """
    from tienda.models import Reserva

    reserva_id = request.GET.get("reserva_id")

    print(f"\n{'='*60}")
    print(f"❌ CALLBACK PAGO CANCELADO MÓVIL")
    print(f"{'='*60}")
    print(f"   Reserva ID: {reserva_id}")

    try:
        if reserva_id:
            # Opcionalmente actualizar estado de reserva
            try:
                reserva = Reserva.objects.get(id=reserva_id)
                # Mantener en PENDIENTE para que pueda reintentar
                if reserva.estado not in ["PAGADA", "CONFIRMADA", "COMPLETADA"]:
                    reserva.estado = "PENDIENTE"
                    reserva.save(update_fields=["estado"])
                    print(f"   ℹ️  Reserva mantenida en PENDIENTE para reintento")
            except Reserva.DoesNotExist:
                print(f"   ⚠️  Reserva {reserva_id} no encontrada")

        # Construir deep link de cancelación
        deep_link = (
            f"turismoapp://payment-cancel?reserva_id={reserva_id}&status=cancelled"
        )

        print(f"   🚀 Redirigiendo a app: {deep_link}")
        print(f"{'='*60}\n")

        return redirect_to_deep_link(deep_link)

    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        print(f"{'='*60}\n")

        cancel_link = f"turismoapp://payment-cancel?status=cancelled"
        return redirect_to_deep_link(cancel_link)
