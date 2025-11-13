"""
Vistas para el sistema de reportes de SmartSales365.
"""
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json

from .services.generador_reportes import GeneradorReportes


@method_decorator(csrf_exempt, name='dispatch')
class ReporteVozView(View):
    """
    Vista para procesar comandos de voz/texto y generar reportes.
    """
    
    def post(self, request):
        """
        Procesa un comando de voz/texto y genera un reporte.
        
        Body JSON esperado:
        {
            "comando": "ventas del último mes en excel",
            "usar_ia": true
        }
        """
        try:
            # Parsear el cuerpo de la solicitud
            data = json.loads(request.body)
            comando = data.get('comando', '').strip()
            usar_ia = data.get('usar_ia', True)
            
            if not comando:
                return JsonResponse({
                    'success': False,
                    'error': 'El campo "comando" es requerido'
                }, status=400)
            
            # Generar el reporte
            generador = GeneradorReportes()
            resultado = generador.reporte_por_comando(comando, usar_ia=usar_ia)
            
            return JsonResponse({
                'success': True,
                'comando_procesado': comando,
                'reporte': resultado,
                'metadata': resultado.get('metadata', {})
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Cuerpo de solicitud JSON inválido'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error al procesar el comando: {str(e)}'
            }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class ReporteVentasView(View):
    """
    Vista para generar reportes de ventas con filtros específicos.
    """
    
    def get(self, request):
        """
        GET con parámetros en query string para dashboards.
        """
        try:
            filtros = {
                'fecha_inicio': request.GET.get('fecha_inicio'),
                'fecha_fin': request.GET.get('fecha_fin'),
                'categoria': request.GET.get('categoria'),
                'estado': request.GET.get('estado'),
                'monto_minimo': request.GET.get('monto_minimo'),
                'monto_maximo': request.GET.get('monto_maximo'),
                'limite': int(request.GET.get('limite', 10))
            }
            
            # Limpiar filtros vacíos
            filtros = {k: v for k, v in filtros.items() if v is not None}
            
            generador = GeneradorReportes()
            resultado = generador.reporte_ventas_general(filtros)
            
            return JsonResponse({
                'success': True,
                'filtros_aplicados': filtros,
                'reporte': resultado
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error al generar reporte: {str(e)}'
            }, status=500)
    
    def post(self, request):
        """
        POST con parámetros en body JSON.
        """
        try:
            data = json.loads(request.body)
            
            generador = GeneradorReportes()
            resultado = generador.reporte_ventas_general(data)
            
            return JsonResponse({
                'success': True,
                'reporte': resultado
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error al generar reporte: {str(e)}'
            }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class ReporteProductosView(View):
    """
    Vista para generar reportes de productos.
    """
    
    def get(self, request):
        """
        GET con parámetros en query string.
        """
        try:
            filtros = {
                'categoria': request.GET.get('categoria'),
                'stock_minimo': request.GET.get('stock_minimo'),
                'stock_maximo': request.GET.get('stock_maximo'),
                'limite': int(request.GET.get('limite', 10))
            }
            
            # Limpiar filtros vacíos
            filtros = {k: v for k, v in filtros.items() if v is not None}
            
            generador = GeneradorReportes()
            resultado = generador.reporte_productos_rendimiento(filtros)
            
            return JsonResponse({
                'success': True,
                'filtros_aplicados': filtros,
                'reporte': resultado
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error al generar reporte: {str(e)}'
            }, status=500)
    
    def post(self, request):
        """
        POST con parámetros en body JSON.
        """
        try:
            data = json.loads(request.body)
            
            generador = GeneradorReportes()
            resultado = generador.reporte_productos_rendimiento(data)
            
            return JsonResponse({
                'success': True,
                'reporte': resultado
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error al generar reporte: {str(e)}'
            }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class ReporteClientesView(View):
    """
    Vista para generar reportes de clientes.
    """
    
    def get(self, request):
        """
        GET con parámetros en query string.
        """
        try:
            filtros = {
                'tipo_cliente': request.GET.get('tipo_cliente'),
                'fecha_inicio': request.GET.get('fecha_inicio'),
                'fecha_fin': request.GET.get('fecha_fin'),
                'limite': int(request.GET.get('limite', 10))
            }
            
            # Limpiar filtros vacíos
            filtros = {k: v for k, v in filtros.items() if v is not None}
            
            generador = GeneradorReportes()
            resultado = generador.reporte_clientes_detallado(filtros)
            
            return JsonResponse({
                'success': True,
                'filtros_aplicados': filtros,
                'reporte': resultado
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error al generar reporte: {str(e)}'
            }, status=500)
    
    def post(self, request):
        """
        POST con parámetros en body JSON.
        """
        try:
            data = json.loads(request.body)
            
            generador = GeneradorReportes()
            resultado = generador.reporte_clientes_detallado(data)
            
            return JsonResponse({
                'success': True,
                'reporte': resultado
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error al generar reporte: {str(e)}'
            }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class ReporteInventarioView(View):
    """
    Vista para generar reportes de inventario.
    """
    
    def get(self, request):
        """
        GET con parámetros en query string.
        """
        try:
            filtros = {
                'stock_minimo': request.GET.get('stock_minimo'),
                'stock_maximo': request.GET.get('stock_maximo'),
                'categoria': request.GET.get('categoria')
            }
            
            # Limpiar filtros vacíos
            filtros = {k: v for k, v in filtros.items() if v is not None}
            
            generador = GeneradorReportes()
            resultado = generador.reporte_inventario_analitico(filtros)
            
            return JsonResponse({
                'success': True,
                'filtros_aplicados': filtros,
                'reporte': resultado
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error al generar reporte: {str(e)}'
            }, status=500)
    
    def post(self, request):
        """
        POST con parámetros en body JSON.
        """
        try:
            data = json.loads(request.body)
            
            generador = GeneradorReportes()
            resultado = generador.reporte_inventario_analitico(data)
            
            return JsonResponse({
                'success': True,
                'reporte': resultado
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error al generar reporte: {str(e)}'
            }, status=500)


###para voz
@method_decorator(csrf_exempt, name='dispatch')
class ReporteVozAudioView(View):
    """
    Vista para procesar audio de voz y generar reportes.
    """
    
    def post(self, request):
        try:
            # Verificar si se envió un archivo de audio
            if 'audio' not in request.FILES:
                return JsonResponse({
                    'success': False,
                    'error': 'No se envió archivo de audio'
                }, status=400)
            
            audio_file = request.FILES['audio']
            
            # Validar tipo de archivo
            if not audio_file.name.lower().endswith(('.wav', '.mp3', '.ogg', '.webm')):
                return JsonResponse({
                    'success': False,
                    'error': 'Formato de audio no soportado. Use WAV, MP3, OGG o WEBM'
                }, status=400)
            
            # Convertir audio a texto (necesitas instalar speech_recognition)
            texto_transcrito = self.convertir_audio_a_texto(audio_file)
            
            if not texto_transcrito:
                return JsonResponse({
                    'success': False,
                    'error': 'No se pudo transcribir el audio. Intente nuevamente.'
                }, status=400)
            
            # Procesar el comando como el endpoint normal de voz
            generador = GeneradorReportes()
            resultado = generador.reporte_por_comando(texto_transcrito, usar_ia=True)
            
            return JsonResponse({
                'success': True,
                'comando_detectado': texto_transcrito,
                'reporte': resultado,
                'metadata': resultado.get('metadata', {})
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error al procesar audio: {str(e)}'
            }, status=500)
    
    def convertir_audio_a_texto(self, audio_file):
        """Convierte audio a texto usando speech_recognition y pydub."""
        import speech_recognition as sr
        import tempfile
        import os
        from pydub import AudioSegment

        temp_input = None
        temp_wav = None

        try:
            ext = os.path.splitext(audio_file.name)[1].lower() or ".webm"
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_in:
                for chunk in audio_file.chunks():
                    tmp_in.write(chunk)
                temp_input = tmp_in.name

            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_wav:
                temp_wav = tmp_wav.name

            audio_seg = AudioSegment.from_file(temp_input)
            audio_seg.export(temp_wav, format="wav")

            recognizer = sr.Recognizer()
            with sr.AudioFile(temp_wav) as source:
                audio_data = recognizer.record(source)
                texto = recognizer.recognize_google(audio_data, language='es-ES')

            return texto

        except Exception as e:
            print(f"Error en transcripción: {e}")
            return None

        finally:
            if temp_input and os.path.exists(temp_input):
                os.unlink(temp_input)
            if temp_wav and os.path.exists(temp_wav):
                os.unlink(temp_wav)


# Vista de prueba para verificar que la app funciona
@method_decorator(csrf_exempt, name='dispatch')
class ReportesStatusView(View):
    """
    Vista para verificar el estado del sistema de reportes.
    """
    
    def get(self, request):
        """
        Retorna el estado del sistema de reportes.
        """
        generador = GeneradorReportes()
        
        return JsonResponse({
            'success': True,
            'status': 'operacional',
            'ia_disponible': generador.procesador_ia.ia_disponible,
            'endpoints': {
                'reporte_voz': '/api/reportes/voz/',
                'reporte_ventas': '/api/reportes/ventas/',
                'reporte_productos': '/api/reportes/productos/',
                'reporte_clientes': '/api/reportes/clientes/',
                'reporte_inventario': '/api/reportes/inventario/',
                'status': '/api/reportes/status/'
            },
            'ejemplos_get': {
                'ventas': '/api/reportes/ventas/?fecha_inicio=2024-01-01&fecha_fin=2024-01-31&limite=5',
                'productos': '/api/reportes/productos/?categoria=Electrónicos&limite=10',
                'clientes': '/api/reportes/clientes/?tipo_cliente=vip&limite=5',
                'inventario': '/api/reportes/inventario/?stock_minimo=10'
            }
        })
    
    def post(self, request):
        """POST también permitido para status"""
        return self.get(request)