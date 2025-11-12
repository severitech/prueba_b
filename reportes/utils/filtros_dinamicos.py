"""
Utilidades para aplicar filtros dinámicos a consultas.
"""
from django.db.models import Q, Count, Sum
from typing import Dict, Any, List
from datetime import datetime, timedelta


class FiltrosDinamicos:
    """
    Aplica filtros dinámicos a querysets de manera flexible.
    """
    
    @staticmethod
    def construir_filtros_complejos(filtros: Dict[str, Any]) -> Q:
        """
        Construye filtros Q complejos basados en múltiples criterios.
        
        Args:
            filtros: Diccionario con criterios de filtrado
            
        Returns:
            Objeto Q con todos los filtros aplicados
        """
        q_filters = Q()
        
        # Filtros temporales
        q_filters &= FiltrosDinamicos._aplicar_filtros_temporales(filtros)
        
        # Filtros de monto
        q_filters &= FiltrosDinamicos._aplicar_filtros_monto(filtros)
        
        # Filtros de estado
        q_filters &= FiltrosDinamicos._aplicar_filtros_estado(filtros)
        
        # Filtros de categoría
        q_filters &= FiltrosDinamicos._aplicar_filtros_categoria(filtros)
        
        # Filtros de cliente
        q_filters &= FiltrosDinamicos._aplicar_filtros_cliente(filtros)
        
        return q_filters
    
    @staticmethod
    def _aplicar_filtros_temporales(filtros: Dict[str, Any]) -> Q:
        """Aplica filtros relacionados con tiempo/fechas."""
        q_temp = Q()
        
        # Rango de fechas específico
        if filtros.get('fecha_inicio'):
            q_temp &= Q(fecha__gte=filtros['fecha_inicio'])
        if filtros.get('fecha_fin'):
            q_temp &= Q(fecha__lte=filtros['fecha_fin'])
        
        # Filtros por mes/año
        if filtros.get('mes'):
            q_temp &= Q(fecha__month=filtros['mes'])
        if filtros.get('año'):
            q_temp &= Q(fecha__year=filtros['año'])
        
        # Filtros temporales predefinidos
        if filtros.get('periodo') == 'hoy':
            from django.utils import timezone
            hoy = timezone.now().date()
            q_temp &= Q(fecha__date=hoy)
        elif filtros.get('periodo') == 'ayer':
            from django.utils import timezone
            ayer = timezone.now().date() - timedelta(days=1)
            q_temp &= Q(fecha__date=ayer)
        elif filtros.get('periodo') == 'esta_semana':
            from django.utils import timezone
            inicio_semana = timezone.now().date() - timedelta(days=timezone.now().weekday())
            q_temp &= Q(fecha__date__gte=inicio_semana)
        
        return q_temp
    
    @staticmethod
    def _aplicar_filtros_monto(filtros: Dict[str, Any]) -> Q:
        """Aplica filtros relacionados con montos."""
        q_monto = Q()
        
        if filtros.get('monto_minimo'):
            q_monto &= Q(total__gte=filtros['monto_minimo'])
        if filtros.get('monto_maximo'):
            q_monto &= Q(total__lte=filtros['monto_maximo'])
        
        # Rangos predefinidos
        if filtros.get('rango_monto') == 'bajo':
            q_monto &= Q(total__lt=100)
        elif filtros.get('rango_monto') == 'medio':
            q_monto &= Q(total__gte=100, total__lte=500)
        elif filtros.get('rango_monto') == 'alto':
            q_monto &= Q(total__gt=500)
        
        return q_monto
    
    @staticmethod
    def _aplicar_filtros_estado(filtros: Dict[str, Any]) -> Q:
        """Aplica filtros de estado."""
        q_estado = Q()
        
        if filtros.get('estado'):
            if isinstance(filtros['estado'], list):
                q_estado &= Q(estado__in=filtros['estado'])
            else:
                q_estado &= Q(estado=filtros['estado'])
        
        # Estados predefinidos
        if filtros.get('solo_pagadas'):
            q_estado &= Q(estado='PAGADA')
        if filtros.get('excluir_canceladas'):
            q_estado &= ~Q(estado='CANCELADA')
        
        return q_estado
    
    @staticmethod
    def _aplicar_filtros_categoria(filtros: Dict[str, Any]) -> Q:
        """Aplica filtros de categoría."""
        q_categoria = Q()
        
        if filtros.get('categoria'):
            if isinstance(filtros['categoria'], list):
                # Múltiples categorías
                for categoria in filtros['categoria']:
                    q_categoria |= Q(producto__categoria__descripcion__icontains=categoria)
            else:
                # Una categoría
                q_categoria &= Q(producto__categoria__descripcion__icontains=filtros['categoria'])
        
        if filtros.get('categorias'):
            # Lista específica de categorías
            q_categoria &= Q(producto__categoria__descripcion__in=filtros['categorias'])
        
        return q_categoria
    
    @staticmethod
    def _aplicar_filtros_cliente(filtros: Dict[str, Any]) -> Q:
        """Aplica filtros relacionados con clientes."""
        q_cliente = Q()
        
        if filtros.get('cliente_id'):
            q_cliente &= Q(usuario_id=filtros['cliente_id'])
        
        if filtros.get('tipo_cliente'):
            tipo = filtros['tipo_cliente']
            # Aquí se podrían implementar lógicas más complejas de segmentación
            if tipo == 'nuevo':
                # Clientes con pocas compras
                from tienda.models import Usuario
                clientes_nuevos = Usuario.objects.annotate(
                    num_compras=Count('venta')
                ).filter(num_compras__lte=2).values_list('id', flat=True)
                q_cliente &= Q(usuario_id__in=clientes_nuevos)
            elif tipo == 'vip':
                # Clientes con muchas compras o alto gasto
                from tienda.models import Usuario
                clientes_vip = Usuario.objects.annotate(
                    total_gastado=Sum('venta__total')
                ).filter(total_gastado__gt=1000).values_list('id', flat=True)
                q_cliente &= Q(usuario_id__in=clientes_vip)
        
        return q_cliente
    
    @staticmethod
    def optimizar_consulta(queryset, filtros: Dict[str, Any]):
        """
        Optimiza una consulta aplicando select_related y prefetch_related según los filtros.
        """
        # Determinar relaciones necesarias basadas en los filtros
        select_related = []
        prefetch_related = []
        
        if any(key in filtros for key in ['categoria', 'categorias']):
            select_related.append('producto__categoria')
        
        if 'cliente_id' in filtros or 'tipo_cliente' in filtros:
            select_related.append('usuario')
        
        # Aplicar optimizaciones
        if select_related:
            queryset = queryset.select_related(*select_related)
        if prefetch_related:
            queryset = queryset.prefetch_related(*prefetch_related)
        
        return queryset