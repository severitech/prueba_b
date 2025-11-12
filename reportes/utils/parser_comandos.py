"""
Validadores para filtros y parámetros de reportes.
"""
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List, Tuple


class ValidadorFiltros:
    """
    Valida y normaliza filtros para reportes.
    """
    
    @staticmethod
    def validar_filtros_ventas(filtros: Dict[str, Any]) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Valida filtros para reportes de ventas.
        
        Returns:
            Tuple (es_valido, errores, filtros_normalizados)
        """
        errores = []
        filtros_normalizados = filtros.copy()
        
        # Validar fechas
        es_valido_fechas, errores_fechas = ValidadorFiltros._validar_fechas(filtros)
        errores.extend(errores_fechas)
        
        # Validar montos
        es_valido_montos, errores_montos = ValidadorFiltros._validar_montos(filtros)
        errores.extend(errores_montos)
        
        # Validar límites
        es_valido_limites, errores_limites = ValidadorFiltros._validar_limites(filtros)
        errores.extend(errores_limites)
        
        # Normalizar valores
        filtros_normalizados = ValidadorFiltros._normalizar_filtros(filtros_normalizados)
        
        es_valido = len(errores) == 0
        return es_valido, errores, filtros_normalizados
    
    @staticmethod
    def _validar_fechas(filtros: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Valida filtros de fecha."""
        errores = []
        
        fecha_inicio = filtros.get('fecha_inicio')
        fecha_fin = filtros.get('fecha_fin')
        
        if fecha_inicio and fecha_fin:
            if fecha_inicio > fecha_fin:
                errores.append('La fecha de inicio no puede ser mayor que la fecha de fin')
        
        # Validar que las fechas no sean futuras (si se proporcionan)
        ahora = datetime.now()
        if fecha_inicio and fecha_inicio > ahora:
            errores.append('La fecha de inicio no puede ser futura')
        
        if fecha_fin and fecha_fin > ahora:
            errores.append('La fecha de fin no puede ser futura')
        
        return len(errores) == 0, errores
    
    @staticmethod
    def _validar_montos(filtros: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Valida filtros de monto."""
        errores = []
        
        monto_min = filtros.get('monto_minimo')
        monto_max = filtros.get('monto_maximo')
        
        if monto_min is not None:
            try:
                monto_min = Decimal(str(monto_min))
                if monto_min < 0:
                    errores.append('El monto mínimo no puede ser negativo')
            except:
                errores.append('El monto mínimo tiene un formato inválido')
        
        if monto_max is not None:
            try:
                monto_max = Decimal(str(monto_max))
                if monto_max < 0:
                    errores.append('El monto máximo no puede ser negativo')
            except:
                errores.append('El monto máximo tiene un formato inválido')
        
        if monto_min is not None and monto_max is not None:
            if monto_min > monto_max:
                errores.append('El monto mínimo no puede ser mayor que el monto máximo')
        
        return len(errores) == 0, errores
    
    @staticmethod
    def _validar_limites(filtros: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Valida límites de resultados."""
        errores = []
        
        limite = filtros.get('limite')
        if limite is not None:
            try:
                limite_int = int(limite)
                if limite_int <= 0:
                    errores.append('El límite debe ser mayor que 0')
                elif limite_int > 1000:
                    errores.append('El límite no puede ser mayor a 1000')
            except:
                errores.append('El límite tiene un formato inválido')
        
        return len(errores) == 0, errores
    
    @staticmethod
    def _normalizar_filtros(filtros: Dict[str, Any]) -> Dict[str, Any]:
        """Normaliza y sanitiza los filtros."""
        normalizados = {}
        
        for clave, valor in filtros.items():
            if valor is None or valor == '':
                continue
                
            # Normalizar según el tipo de filtro
            if clave in ['monto_minimo', 'monto_maximo']:
                try:
                    normalizados[clave] = Decimal(str(valor))
                except:
                    continue  # Ignorar valores inválidos
            
            elif clave == 'limite':
                try:
                    normalizados[clave] = int(valor)
                except:
                    continue
            
            elif clave in ['fecha_inicio', 'fecha_fin']:
                if isinstance(valor, str):
                    try:
                        # Intentar parsear string a datetime
                        normalizados[clave] = datetime.fromisoformat(valor.replace('Z', '+00:00'))
                    except:
                        continue
                else:
                    normalizados[clave] = valor
            
            else:
                normalizados[clave] = valor
        
        return normalizados
    
    @staticmethod
    def validar_parametros_exportacion(formato: str, tipo_reporte: str) -> Tuple[bool, List[str]]:
        """
        Valida parámetros para exportación.
        """
        errores = []
        
        # Validar formato
        formatos_validos = ['pdf', 'excel', 'json']
        if formato not in formatos_validos:
            errores.append(f'Formato no válido: {formato}. Formatos válidos: {", ".join(formatos_validos)}')
        
        # Validar tipo de reporte
        tipos_validos = ['ventas', 'productos', 'clientes', 'inventario']
        if tipo_reporte not in tipos_validos:
            errores.append(f'Tipo de reporte no válido: {tipo_reporte}. Tipos válidos: {", ".join(tipos_validos)}')
        
        return len(errores) == 0, errores