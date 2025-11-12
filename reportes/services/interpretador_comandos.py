# services/interpretador_comandos.py
"""
Interpretador de comandos de voz/texto para reportes de SmartSales365.
Se enfoca en EXTRAER FILTROS (tipo_reporte, montos, fechas, formato, etc.)
y retornar un diccionario listo para usar por el Generador/Processor.

Mejoras:
- Manejo robusto de fechas relativas con datetime.
- Soporte "diciembre del año pasado", "<mes> de este año", "<mes> de 2024",
  y AHORA "<mes> del año 2025" / "<mes> del 2025".
- No confunde montos como "1000 bolivianos" con años.
"""

import re
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from django.utils import timezone

# (Opcional) Intentamos importar modelos sólo para hints; el interpretador no depende de ellos.
try:
    from tienda.models import Venta, Categoria, SubCategoria, Productos  # noqa
except Exception:
    Venta = Categoria = SubCategoria = Productos = None


class InterpretadorComandosVoz:
    """
    Interpreta un comando y produce un diccionario de filtros para reportes.
    No consulta BD aquí; la obtención de datos la hace el Processor.
    """

    # Hints opcionales (por nombre) si no se desea tocar la BD desde el interpretador.
    CATEGORIAS_REALES_HINT = {
        'electrodomésticos': 'Electrodomésticos',
        'electrodomestico': 'Electrodomésticos',
        'electro': 'Electrodomésticos',
        'cocina': 'Cocina',
        'lavandería': 'Lavandería',
        'lavanderia': 'Lavandería',
        'cuidado hogar': 'Cuidado del hogar',
        'hogar': 'Cuidado del hogar',
        'entretenimiento': 'Entretenimiento y Tecnología',
        'tecnología': 'Entretenimiento y Tecnología',
        'tecnologia': 'Entretenimiento y Tecnología',
        'climatización': 'Climatización',
        'clima': 'Climatización',
        'cuidado personal': 'Cuidado personal',
        'cocina y preparación': 'Cocina y Preparación de Bebidas',
        'preparación bebidas': 'Cocina y Preparación de Bebidas',
        'preparacion bebidas': 'Cocina y Preparación de Bebidas',
        'electrodomésticos inteligentes': 'Electrodomésticos inteligentes',
        'pequeños electrodomésticos': 'Pequeños electrodomésticos',
        'portátil': 'Pequeños electrodomésticos',
        'portatil': 'Pequeños electrodomésticos',
    }

    MESES_MAP = {
        'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
        'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
        'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
    }

    def __init__(self, usar_datos_reales: bool = True):
        self.usar_datos_reales = usar_datos_reales
        print("🔧 InterpretadorComandosVoz - Estado:")
        print(f"   • usar_datos_reales: {usar_datos_reales}")
        print(f"   • Modelos disponibles: Venta={Venta is not None}, "
              f"Categoria={Categoria is not None}, SubCategoria={SubCategoria is not None}, "
              f"Productos={Productos is not None}")

    # ============= Utilidades =============
    @staticmethod
    def _norm_text(t: str) -> str:
        t = (t or "")
        t = t.replace("\u00a0", " ")
        t = re.sub(r"\s+", " ", t, flags=re.UNICODE).strip().lower()
        return t

    # ============= Fechas =============
    @classmethod
    def parsear_fecha(cls, texto: str) -> Optional[datetime]:
        """
        Intenta parsear fechas en formato:
        - dd/mm/yyyy o dd-mm-yyyy
        - '1 de enero de 2025'
        Retorna datetime (naive).
        """
        if not texto:
            return None
        t = cls._norm_text(texto)

        # dd/mm/yyyy o dd-mm-yyyy
        m = re.search(r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b', t)
        if m:
            try:
                d, mth, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
                return datetime(y, mth, d)
            except Exception:
                pass

        # '1 de enero de 2025'
        m2 = re.search(
            r'\b(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+de\s+(\d{4})\b',
            t
        )
        if m2:
            try:
                d = int(m2.group(1))
                mes = cls.MESES_MAP[m2.group(2)]
                y = int(m2.group(3))
                return datetime(y, mes, d)
            except Exception:
                pass

        return None

    @classmethod
    def extraer_rango_fechas(cls, texto: str) -> Tuple[Optional[datetime], Optional[datetime]]:
        """
        Extrae (fecha_inicio, fecha_fin) desde el comando.
        Usa datetime para validar los rangos.
        Soporta:
          - hoy / ayer
          - últimos N días / esta semana / semana pasada
          - este mes / mes pasado
          - este año / año pasado
          - <mes> del año pasado / <mes> de este año
          - <mes> de YYYY
          - <mes> del año YYYY   <-- NUEVO
          - <mes> del YYYY       <-- NUEVO
          - Fechas dd/mm/yyyy (una o dos)
        NO interpreta números sueltos como años (evita confundir montos).
        Retorna datetimes *naive*. (Luego se vuelven aware en interpretar()).
        """
        import calendar

        t = cls._norm_text(texto)
        hoy = timezone.now().date()

        # 1) hoy / ayer
        if 'hoy' in t:
            d = hoy
            return datetime.combine(d, datetime.min.time()), datetime.combine(d, datetime.max.time())
        if 'ayer' in t:
            d = hoy - timedelta(days=1)
            return datetime.combine(d, datetime.min.time()), datetime.combine(d, datetime.max.time())

        # 2) últimos N días
        m = re.search(r'\búltimos?\s+(\d+)\s+días?\b', t)
        if m:
            n = int(m.group(1))
            fi = hoy - timedelta(days=n)
            return datetime.combine(fi, datetime.min.time()), datetime.combine(hoy, datetime.max.time())

        # 3) esta semana (lunes -> hoy)
        if 'esta semana' in t:
            inicio_sem = hoy - timedelta(days=hoy.weekday())
            return datetime.combine(inicio_sem, datetime.min.time()), datetime.combine(hoy, datetime.max.time())

        # 4) semana pasada
        if re.search(r'\b(semana\s+pasada|última\s+semana|semana\s+anterior)\b', t):
            fin = hoy - timedelta(days=hoy.weekday() + 1)
            ini = fin - timedelta(days=6)
            return datetime.combine(ini, datetime.min.time()), datetime.combine(fin, datetime.max.time())

        # 5) este mes / mes pasado
        if 'este mes' in t:
            ini = hoy.replace(day=1)
            return datetime.combine(ini, datetime.min.time()), datetime.combine(hoy, datetime.max.time())

        if re.search(r'\b(mes\s+pasado|último\s+mes|mes\s+anterior)\b', t):
            primer_dia_mes_actual = hoy.replace(day=1)
            ultimo_dia_mes_pasado = primer_dia_mes_actual - timedelta(days=1)
            primer_dia_mes_pasado = ultimo_dia_mes_pasado.replace(day=1)
            return datetime.combine(primer_dia_mes_pasado, datetime.min.time()), datetime.combine(ultimo_dia_mes_pasado, datetime.max.time())

        # 6) este año / año pasado
        if 'este año' in t:
            ini = hoy.replace(month=1, day=1)
            return datetime.combine(ini, datetime.min.time()), datetime.combine(hoy, datetime.max.time())

        if re.search(r'\b(año\s+pasado|último\s+año)\b', t):
            y = hoy.year - 1
            fi = datetime(y, 1, 1)
            ff = datetime(y, 12, 31, 23, 59, 59, 999000)
            return fi, ff

        # 7) <mes> del año pasado
        m_rel = re.search(
            r'\b(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\b\s+del?\s+año\s+pasado',
            t
        )
        if m_rel:
            mes = cls.MESES_MAP[m_rel.group(1)]
            y = hoy.year - 1
            ultimo = calendar.monthrange(y, mes)[1]
            fi = datetime(y, mes, 1)
            ff = datetime(y, mes, ultimo, 23, 59, 59, 999000)
            return fi, ff

        # 8) <mes> de este año
        m_rel2 = re.search(
            r'\b(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\b\s+de\s+este\s+año',
            t
        )
        if m_rel2:
            mes = cls.MESES_MAP[m_rel2.group(1)]
            y = hoy.year
            ultimo = calendar.monthrange(y, mes)[1]
            fi = datetime(y, mes, 1)
            ff = datetime(y, mes, ultimo, 23, 59, 59, 999000)
            return fi, ff

        # 9) <mes> de YYYY  (explícito)
        m_exp = re.search(
            r'\b(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\b\s+de\s+(\d{4})\b',
            t
        )
        if m_exp:
            try:
                mes = cls.MESES_MAP[m_exp.group(1)]
                y = int(m_exp.group(2))
                ultimo = calendar.monthrange(y, mes)[1]
                fi = datetime(y, mes, 1)
                ff = datetime(y, mes, ultimo, 23, 59, 59, 999000)
                return fi, ff
            except Exception:
                pass

        # 10) <mes> del año YYYY  (NUEVO)  — ej: "noviembre del año 2025"
        m_exp_del_anio = re.search(
            r'\b(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\b\s+del?\s+año\s+(\d{4})\b',
            t
        )
        if m_exp_del_anio:
            try:
                mes = cls.MESES_MAP[m_exp_del_anio.group(1)]
                y = int(m_exp_del_anio.group(2))
                ultimo = calendar.monthrange(y, mes)[1]
                fi = datetime(y, mes, 1)
                ff = datetime(y, mes, ultimo, 23, 59, 59, 999000)
                return fi, ff
            except Exception:
                pass

        # 11) <mes> del YYYY  (NUEVO) — ej: "noviembre del 2025"
        m_exp_del = re.search(
            r'\b(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\b\s+del?\s+(\d{4})\b',
            t
        )
        if m_exp_del:
            try:
                mes = cls.MESES_MAP[m_exp_del.group(1)]
                y = int(m_exp_del.group(2))
                ultimo = calendar.monthrange(y, mes)[1]
                fi = datetime(y, mes, 1)
                ff = datetime(y, mes, ultimo, 23, 59, 59, 999000)
                return fi, ff
            except Exception:
                pass

        # 12) Fechas sueltas dd/mm/yyyy (una o dos)
        fechas = re.findall(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b', t)
        if len(fechas) >= 2:
            def _p(dmy: str) -> datetime:
                d, mth, y = re.split(r'[/-]', dmy)
                return datetime(int(y), int(mth), int(d))
            fi = _p(fechas[0])
            ff = _p(fechas[1]).replace(hour=23, minute=59, second=59, microsecond=999000)
            return fi, ff
        elif len(fechas) == 1:
            d, mth, y = re.split(r'[/-]', fechas[0])
            fi = datetime(int(y), int(mth), int(d))
            ff = datetime.combine(hoy, datetime.max.time())
            return fi, ff

        # No detectado
        return None, None

    # ============= Montos =============
    @staticmethod
    def extraer_monto_minimo(texto: str) -> Optional[float]:
        """
        Detecta comparadores de mínimo: mayor a/que, más de, superior a, >=, >, desde.
        Retorna float o None.
        """
        t = InterpretadorComandosVoz._norm_text(texto)
        patrones = [
            r'(?:mayor(?:es)?\s+(?:a|que)|m[aá]s\s+de|mas\s+de|superior(?:es)?\s+a|>=|>\s*)(\d[\d\.,\s]*)',
            r'(?:desde)\s+(\d[\d\.,\s]*)',
        ]
        for p in patrones:
            m = re.search(p, t, re.IGNORECASE)
            if m:
                num = m.group(1)
                clean = re.sub(r'[^\d,\.]', '', num).replace('.', '').replace(',', '')
                try:
                    return float(clean)
                except Exception:
                    continue
        return None

    @staticmethod
    def extraer_monto_maximo(texto: str) -> Optional[float]:
        """
        Detecta comparadores de máximo: menor a/que, menos de, inferior a, <=, <, hasta.
        Retorna float o None.
        """
        t = InterpretadorComandosVoz._norm_text(texto)
        patrones = [
            r'(?:menor(?:es)?\s+(?:a|que)|menos\s+de|inferior(?:es)?\s+a|<=|<\s*)(\d[\d\.,\s]*)',
            r'(?:hasta)\s+(\d[\d\.,\s]*)',
        ]
        for p in patrones:
            m = re.search(p, t, re.IGNORECASE)
            if m:
                num = m.group(1)
                clean = re.sub(r'[^\d,\.]', '', num).replace('.', '').replace(',', '')
                try:
                    return float(clean)
                except Exception:
                    continue
        return None

    # ============= Categoría / Estado / Otros =============
    def extraer_categoria(self, texto: str) -> Optional[str]:
        """
        Intenta reconocer categoría/subcategoría:
        1) Si hay modelos: buscar por coincidencia en BD (descripcion).
        2) Si no, usar hints estáticos (CATEGORIAS_REALES_HINT).
        Retorna texto (nombre canónico) para que el Processor lo interprete.
        """
        t = self._norm_text(texto)

        # 1) SubCategoria
        if SubCategoria is not None:
            try:
                for sc in SubCategoria.objects.all():
                    name = (sc.descripcion or "").lower()
                    if name and name in t:
                        return f"subcategoria:{sc.descripcion}"
            except Exception:
                pass

        # 2) Categoria
        if Categoria is not None:
            try:
                for c in Categoria.objects.all():
                    name = (c.descripcion or "").lower()
                    if name and name in t:
                        return f"categoria:{c.descripcion}"
            except Exception:
                pass

        # 3) Hints
        for k, v in self.CATEGORIAS_REALES_HINT.items():
            if k in t:
                return f"categoria:{v}"

        return None

    @staticmethod
    def extraer_estado(texto: str) -> Optional[str]:
        t = (texto or "").lower()
        if 'pendiente' in t:
            return 'Pendiente'
        if 'pagado' in t or 'pagada' in t:
            return 'Pagado'
        if 'cancelado' in t or 'cancelada' in t:
            return 'Cancelado'
        return None

    @staticmethod
    def extraer_limite(texto: str) -> Optional[int]:
        t = (texto or "").lower()
        patrones = [
            r'\btop\s+(\d+)\b',
            r'\bprimeros?\s+(\d+)\b',
            r'\bmejores\s+(\d+)\b',
            r'\búltimos?\s+(\d+)\b',
            r'\bs[oó]lo\s+(\d+)\b',
            r'\bm[aá]ximo\s+(\d+)\b',
        ]
        for p in patrones:
            m = re.search(p, t, re.IGNORECASE)
            if m:
                try:
                    return int(m.group(1))
                except Exception:
                    continue
        return None

    @staticmethod
    def extraer_formato(texto: str) -> str:
        t = (texto or "").lower()
        if 'pdf' in t:
            return 'pdf'
        if 'excel' in t or 'xlsx' in t or 'hoja de cálculo' in t:
            return 'excel'
        return 'json'

    @staticmethod
    def extraer_tipo_reporte(texto: str) -> str:
        t = (texto or "").lower()
        if any(w in t for w in ['productos', 'inventario', 'stock']):
            return 'productos' if 'productos' in t else ('inventario' if 'inventario' in t else 'productos')
        if any(w in t for w in ['clientes', 'usuarios', 'compradores']):
            return 'clientes'
        return 'ventas'  # por defecto e-commerce

    # ============= API principal =============
    @classmethod
    def interpretar(cls, comando_voz: str) -> Dict[str, Any]:
        """
        Interpreta un comando y retorna filtros estructurados.
        Convierte fechas a timezone-aware si vienen naive.
        """
        inst = cls()

        filtros: Dict[str, Any] = {'comando_original': comando_voz}

        # Tipo de reporte
        tipo = cls.extraer_tipo_reporte(comando_voz)
        filtros['tipo_reporte'] = tipo

        # Rango de fechas
        fi, ff = cls.extraer_rango_fechas(comando_voz)
        if fi is not None:
            if timezone.is_naive(fi):
                fi = timezone.make_aware(fi)
            filtros['fecha_inicio'] = fi
        if ff is not None:
            if timezone.is_naive(ff):
                ff = timezone.make_aware(ff)
            filtros['fecha_fin'] = ff

        # Montos
        mmin = cls.extraer_monto_minimo(comando_voz)
        if mmin is not None:
            filtros['monto_minimo'] = float(mmin)
        mmax = cls.extraer_monto_maximo(comando_voz)
        if mmax is not None:
            filtros['monto_maximo'] = float(mmax)

        # Categoria/Subcategoria
        cat = inst.extraer_categoria(comando_voz)
        if cat:
            filtros['categoria'] = cat  # ej: "categoria:Lavandería" o "subcategoria:Televisores"

        # Estado
        estado = cls.extraer_estado(comando_voz)
        if estado:
            filtros['estado'] = estado

        # Límite
        lim = cls.extraer_limite(comando_voz)
        if lim:
            filtros['limite'] = lim

        # Formato
        formato = cls.extraer_formato(comando_voz)
        if formato:
            filtros['formato'] = formato

        # Query libre (para debug/búsqueda textual aguas arriba)
        filtros['q'] = cls._norm_text(comando_voz)

        return filtros
