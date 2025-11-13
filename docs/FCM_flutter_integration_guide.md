# Guía de integración FCM (rol: Programador Senior) — Flutter (Android)

Propósito
--------
Documento práctico y actualizado para que el equipo Flutter implemente correctamente el registro, refresco y desregistro de tokens FCM y para que pueda trabajar con las API que ya existen en el backend.

Resumen: lo que el backend ya expone
-----------------------------------
- Prefijo API: `/api/` (ver `config/urls.py`).
- Login: `POST /api/authz/login/`.
  - Request: `{ "email": "<email>", "password": "<password>" }`
  - Response: `{ "token": "<TOKEN>", "user": { ... } }` (usar header `Authorization: Token <TOKEN>`).
- Registro de token FCM:
  - `POST /api/devices/register/` — Auth required.
  - Request JSON: `{ "registration_id": "<FCM_TOKEN>", "tipo_dispositivo": "android" }`.
  - Backend hace `update_or_create` por `registration_id`, asocia a `authz.Usuario` si `request.user` tiene perfil y marca `activo=True`.
- Registro opcional durante login: `POST /api/authz/login/` ahora acepta opcionalmente `registration_id` y lo registra automáticamente (si viene en la petición).
- Desregistro:
  - `POST /api/devices/unregister/` — implementado.
  - Request JSON: `{ "registration_id": "<FCM_TOKEN>" }`.
  - Comportamiento: marca `FCMDevice.activo=False`. Si el token pertenece al `Usuario` autenticado se permite; si no, solo admin/staff puede desactivar tokens arbitrarios.
- Listado admin de dispositivos: `GET /api/admin/devices/` (IsAdminUser).
- Envío de notificaciones (admin API): `POST /api/admin/send-notification/` — payload admite `title`/`body`/`broadcast`/`user_ids`/`device_ids`. Implementación en `core.notifications.enviar_tokens_push`.
- Modo de pruebas: variable de entorno `SIMULAR_FCM=1` para simular envíos (útil en staging/dev). Scripts útiles: `scripts/test_firebase.py`, `scripts/test_send_push.py`.

Objetivos de esta guía
----------------------
- Dar instrucciones exactas (endpoints, headers, formatos) que el equipo Flutter deberá usar.
- Proveer snippets de ejemplo en Dart (copiables).
- Listar pruebas concretas que el equipo móvil debe ejecutar.

Flujo recomendado en la app (hecho exactamente conforme al backend)
----------------------------------------------------------------
1) Login (obtener token de autenticación):
   - Llamada: `POST /api/authz/login/`.
   - Body: `{ "email": "...", "password": "..." }`.
   - Response conteniendo `token`. Guardar ese token de sesión seguro en la app.

2) Registrar token FCM (dos opciones válidas, ambas soportadas por el backend):
   - Opción A (recomendada si queréis registro inmediato): Incluir `registration_id` en la misma petición de login:
     - Request `POST /api/authz/login/` con body adicional: `{ "email":..., "password":..., "registration_id": "<FCM_TOKEN>", "tipo_dispositivo": "android" }`.
     - El backend registrará el token y lo asociará al usuario autenticado.
   - Opción B (registro separado): una vez obtenido el token de login, llamar a:
     - `POST /api/devices/register/` con headers `Authorization: Token <TOKEN>`.
     - Body: `{ "registration_id": "<FCM_TOKEN>", "tipo_dispositivo": "android" }`.

3) Refresco de token
   - En Flutter: escuchar `FirebaseMessaging.instance.onTokenRefresh`.
   - Al obtener un `newToken`, enviar al backend usando el mismo `POST /api/devices/register/` con el header `Authorization: Token <TOKEN>`.

4) Logout / Desregistro
   - Llamar `POST /api/devices/unregister/` con `{ "registration_id": "<FCM_TOKEN>" }` y `Authorization: Token <TOKEN>`.
   - El backend marcará `activo=False` para ese token si pertenece al usuario o si la llamada la hace un admin.

5) Gestión en Admin (backend)
   - El administrador puede ver todos los dispositivos (y usuario asociado) en `GET /api/admin/devices/` y desde Django Admin (`FCMDevice` model).
   - Para enviar notificaciones personalizadas el admin usa `POST /api/admin/send-notification/` o desde el Django Admin usar la acción que abre un formulario para título y cuerpo.

Ejemplo de código (Flutter / Dart) — flujo simple (registro separado)
---------------------------------------------------------------
Dependencias mínimas en `pubspec.yaml`:
```yaml
dependencies:
  firebase_core: ^2.0.0
  firebase_messaging: ^14.0.0
  http: ^0.13.0
```

Snippet (copiable):
```dart
import 'dart:convert';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:http/http.dart' as http;

class PushService {
  final String backendBase; // ejemplo: https://api.tudominio.com
  final String authToken;   // token DRF del usuario

  PushService({required this.backendBase, required this.authToken});

  Future<void> init() async {
    await Firebase.initializeApp();
    FirebaseMessaging messaging = FirebaseMessaging.instance;
    await messaging.requestPermission();

    final token = await messaging.getToken();
    if (token != null) await _sendTokenToBackend(token);

    FirebaseMessaging.instance.onTokenRefresh.listen((newToken) async {
      await _sendTokenToBackend(newToken);
    });

    FirebaseMessaging.onMessage.listen((RemoteMessage m) {
      // manejar notificación en foreground
      print('Mensaje foreground: ${m.notification?.title}');
    });
  }

  Future<void> _sendTokenToBackend(String fcmToken) async {
    final url = Uri.parse('$backendBase/api/devices/register/');
    final resp = await http.post(url,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Token $authToken',
      },
      body: jsonEncode({'registration_id': fcmToken, 'tipo_dispositivo': 'android'}),
    );
    if (resp.statusCode >= 400) {
      print('Error registrando token: ${resp.statusCode} ${resp.body}');
    }
  }

  Future<void> unregister(String fcmToken) async {
    final url = Uri.parse('$backendBase/api/devices/unregister/');
    await http.post(url,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Token $authToken',
      },
      body: jsonEncode({'registration_id': fcmToken}),
    );
  }
}
```

Notas exactas sobre formatos y headers (para evitar errores comunes)
-----------------------------------------------------------------
- Siempre usar `Content-Type: application/json`.
- Header de autorización exacto: `Authorization: Token <TOKEN>` (no `Bearer`).
- El backend acepta `registration_id` también con nombres alternativos en algunas rutas (`token`, `registrationId`) — pero enviar `registration_id` es lo más explícito.

Pruebas que debe ejecutar el equipo móvil
-----------------------------------------
1. Login + registration_id en la misma petición → verificar en Admin (`GET /api/admin/devices/`) que el dispositivo aparece asociado al usuario.
2. Login → registro separado con `POST /api/devices/register/` → verificar presencia en admin.
3. Forzar `onTokenRefresh` (reinstalación o borrar app) → el token nuevo debe aparecer y el antiguo debe dejarse inactivo por FCM (el backend marca tokens inválidos tras respuesta de FCM cuando se envía una notificación).
4. Logout → llamar `POST /api/devices/unregister/` y verificar `activo=False` para ese token.
5. Test admin sending: solicitar a admin que use `POST /api/admin/send-notification/` con payload tipo `{ "title":"x","body":"y","user_ids":[<id>] }` y verificar recepción en dispositivo.

Problemas conocidos y cómo reportarlos (qué enviar al backend)
-------------------------------------------------------------
- Si un token no aparece en admin tras registro: enviar al backend los logs de la petición (URL, body JSON exacto, headers, status code y response body).
- Si no se reciben notificaciones: enviar `registration_id` que usó la app y la salida de `FirebaseMessaging.instance.getToken()` en consola.
- Para errores 401/403 al llamar a endpoints protegidos: enviar la respuesta del login (JSON con `token`) y el header `Authorization` que la app está enviando.

Checklist mínima antes de PR/Release
----------------------------------
- [ ] Token de login se guarda y se usa exactamente como `Authorization: Token <TOKEN>`.
- [ ] App registra token en login o en llamada separada a `/api/devices/register/`.
- [ ] App escucha `onTokenRefresh` y re-registra el token.
- [ ] App hace `unregister` al logout.
- [ ] Admin ha probado el envío vía `POST /api/admin/send-notification/`.

Archivos/ubicaciones backend relevantes (referencia rápida)
---------------------------------------------------------
- Registro en login: `authz/views.py` (lógica añadida para `registration_id`).
- Registro/desregistro y envío admin: `tienda/api.py` (`FCMDeviceRegisterView`, `FCMDeviceUnregisterView`, `SendNotificationView`).
- Modelo: `tienda/models.py` (`FCMDevice`).
- Serializers: `tienda/serializer.py` (`FCMDeviceSerializer`).
- Admin UI: `tienda/admin.py` (acción y formulario para enviar notificaciones personalizadas).
- Lógica de envío: `core/notifications.py` (función `enviar_tokens_push`).

Entrega y soporte
-----------------
He preparado esta guía como archivo en el repo:
`docs/FCM_flutter_integration_guide.md`

Si queréis, puedo:
- añadir un snippet más detallado para manejo de permisos en Android 13+;
- crear un pequeño Postman collection con requests de ejemplo;
- agregar tests automáticos para `unregister` y el endpoint admin.

Fin de la guía.
