# catalog/management/commands/actualizar_ps4.py
import csv
import os
import re
import difflib
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import models
from catalog.models import Juego

class Command(BaseCommand):
    help = 'Actualiza stock de PS4 desde CSV'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='stock_ps4.csv',
            help='CSV con juegos de PS4'
        )
        parser.add_argument(
            '--columna-nombre',
            type=str,
            default='JUEGOS',
            help='Nombre de la columna con el nombre del juego'
        )
        parser.add_argument(
            '--columna-precio',
            type=str,
            default='PRECIO',
            help='Nombre de la columna con el precio'
        )

    def limpiar_nombre_avanzado(self, nombre):
        """Limpia el nombre quitando idiomas, ediciones específicas, etc."""
        if not nombre:
            return ""
            
        # Quitar emojis y caracteres especiales
        nombre = re.sub(r'[^\x00-\x7F]+', '', nombre)
        
        # Quitar símbolos especiales
        nombre = nombre.replace('®', '').replace('™', '').replace('©', '')
        nombre = nombre.replace(':', '').replace('#', '').replace('-', ' ')
        
        # Quitar el precio del nombre si está
        nombre = re.sub(r'\$\s*[\d.,]+', '', nombre)
        
        # Quitar caracteres especiales al inicio
        nombre = re.sub(r'^[\'\"\#\-\s]+', '', nombre)
        
        # PATRONES A FILTRAR (case insensitive)
        patrones_a_eliminar = [
            # Idiomas y subtítulos
            r'\bespañol\s+españa\b', r'\bespañol\s+latino\b', r'\binglés\b',
            r'\benglish\b', r'\bsubtitulado\b', r'\bsubtitulada\b',
            r'\bespañol\b', r'\bspanish\b',
            
            # Ediciones (EXCEPTO definitive edition que se mantiene)
            r'\bdeluxe\s+edition\b', r'\bgold\s+edition\b', r'\bstandard\s+edition\b',
            r'\bspecial\s+edition\b', r'\bcollector\'s\s+edition\b', r'\bultimate\s+edition\b',
            r'\bpremium\s+edition\b', r'\bcomplete\s+edition\b', r'\bgame\s+of\s+the\s+year\b',
            r'\bgoty\b', r'\bedición\s+deluxe\b', r'\bedición\s+gold\b',
            r'\bedición\s+estándar\b', r'\bedición\s+especial\b', r'\blatino\b',
            
            # Palabras generales a eliminar
            r'\bversion\b', r'\bedicion\b', r'\bdigital\b', r'\bfisico\b',
            r'\bphysical\b', r'\bdownload\b', r'\bdescarga\b'
        ]
        
        # Aplicar todos los patrones
        for patron in patrones_a_eliminar:
            nombre = re.sub(patron, '', nombre, flags=re.IGNORECASE)
        
        # Quitar paréntesis vacíos y espacios extra
        nombre = re.sub(r'\(\s*\)', '', nombre)
        nombre = re.sub(r'\[\s*\]', '', nombre)
        
        # Quitar múltiples espacios
        nombre = re.sub(r'\s+', ' ', nombre)
        
        # Quitar espacios al inicio y final
        nombre = nombre.strip()
        
        # Quitar comas y puntos al final
        nombre = re.sub(r'[.,;\s]+$', '', nombre)
        
        return nombre

    def buscar_juego_similar(self, nombre_limpio):
        """Busca juegos en la base de datos que coincidan aproximadamente"""
        # Primero intenta búsqueda exacta sin "PS4"
        nombre_sin_ps4 = nombre_limpio.replace(' PS4', '').strip()
        
        # Buscar coincidencias exactas
        juegos_exactos = Juego.objects.filter(
            nombre__iexact=nombre_limpio,
            consola='ps4'
        )
        if juegos_exactos.exists():
            return juegos_exactos.first()
        
        # Buscar por nombre sin "PS4"
        juegos_sin_ps4 = Juego.objects.filter(
            nombre__icontains=nombre_sin_ps4,
            consola='ps4'
        )
        if juegos_sin_ps4.exists():
            return juegos_sin_ps4.first()
        
        # Limpiar también el nombre para búsqueda más flexible
        nombre_muy_limpio = self.limpiar_nombre_avanzado(nombre_sin_ps4)
        
        # Buscar por nombre muy limpio
        if nombre_muy_limpio != nombre_sin_ps4:
            juegos_muy_limpios = Juego.objects.filter(
                nombre__icontains=nombre_muy_limpio,
                consola='ps4'
            )
            if juegos_muy_limpios.exists():
                return juegos_muy_limpios.first()
        
        # Buscar por palabras clave (las primeras 3-4 palabras)
        palabras_clave = nombre_muy_limpio.split()[:4]
        query = None
        for palabra in palabras_clave:
            if len(palabra) > 3:
                if query is None:
                    query = models.Q(nombre__icontains=palabra)
                else:
                    query |= models.Q(nombre__icontains=palabra)
        
        if query:
            juegos_similares = Juego.objects.filter(query, consola='ps4')
            if juegos_similares.exists():
                for juego_candidato in juegos_similares:
                    nombre_juego_limpio = self.limpiar_nombre_avanzado(juego_candidato.nombre)
                    if nombre_muy_limpio in nombre_juego_limpio or nombre_juego_limpio in nombre_muy_limpio:
                        return juego_candidato
                return juegos_similares.first()
        
        return None

    def limpiar_precio(self, precio_str):
        """Convierte string con precio a Decimal"""
        if not precio_str or precio_str.strip() == '':
            return Decimal('0.0')
        
        precio_str = str(precio_str).replace('$', '').replace(' ', '').strip()
        
        if ',' in precio_str and '.' in precio_str:
            precio_str = precio_str.replace('.', '').replace(',', '.')
        elif ',' in precio_str:
            precio_str = precio_str.replace(',', '.')
        
        precio_str = re.sub(r'[^\d.]', '', precio_str)
        
        try:
            return Decimal(precio_str)
        except:
            return Decimal('0.0')
        
    def calcular_recargo(self, precio):
        """Calcula el recargo como 10% del precio"""
        if precio <= 0:
            return Decimal('0.0')
        
        recargo = precio + (precio * Decimal('0.10'))
        # Redondear a 2 decimales
        return recargo.quantize(Decimal('0.01'))

    def buscar_imagen_existente(self, nombre_juego):
        """Busca la imagen correspondiente al juego"""
        return self.buscar_imagen(nombre_juego)

    def buscar_imagen(self, nombre_juego):
        """Busca la imagen correspondiente al juego - VERSIÓN SIMPLIFICADA"""
        self.stdout.write(f"\n🖼️  BUSCANDO IMAGEN PARA: {nombre_juego}")
        
        # Generar nombre base
        nombre_base = self.generar_nombre_imagen_simple(nombre_juego)
        
        img_dir = os.path.join(settings.BASE_DIR, 'static', 'img')
        
        # Buscar archivos existentes
        archivos_existentes = [f for f in os.listdir(img_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        
        self.stdout.write(f"Archivos en directorio: {len(archivos_existentes)}")
        
        # Buscar coincidencia exacta
        if nombre_base in archivos_existentes:
            self.stdout.write(self.style.SUCCESS(f"✓ IMAGEN ENCONTRADA: {nombre_base}"))
            return f"img/{nombre_base}"
        
        # Buscar coincidencia insensible a mayúsculas
        archivos_lower = [f.lower() for f in archivos_existentes]
        if nombre_base.lower() in archivos_lower:
            archivo_real = archivos_existentes[archivos_lower.index(nombre_base.lower())]
            self.stdout.write(self.style.SUCCESS(f"✓ IMAGEN ENCONTRADA: {archivo_real}"))
            return f"img/{archivo_real}"
        
        # Mostrar archivos relacionados para debug
        self.mostrar_archivos_relacionados(nombre_juego, archivos_existentes)
        
        self.stdout.write(self.style.ERROR(f"✗ NO SE ENCONTRÓ IMAGEN: {nombre_base}"))
        return "img/default.jpg"

    def generar_nombre_imagen_simple(self, nombre_juego):
        """Genera nombre de imagen de forma simple y directa"""
        nombre = nombre_juego.lower()
        
        # Determinar consola
        if 'ps5' in nombre:
            consola = 'ps5'
        else:
            consola = 'ps4'
        
        # Quitar consola del nombre
        nombre = nombre.replace(' ps4', '').replace(' ps5', '').strip()
        
        # Limpiar caracteres
        nombre = nombre.replace("'", "").replace(":", "").replace("&", "and")
        nombre = nombre.replace(" ", "_")
        
        # Nombre final
        nombre_archivo = f"{nombre}_{consola}.jpg"
        
        self.stdout.write(f"Nombre generado: {nombre_archivo}")
        return nombre_archivo

    def mostrar_archivos_relacionados(self, nombre_juego, archivos_existentes):
        """Muestra archivos relacionados para debug"""
        palabras_busqueda = [p for p in nombre_juego.lower().split() if len(p) > 3]
        
        self.stdout.write("Archivos relacionados encontrados:")
        relacionados = []
        
        for archivo in archivos_existentes:
            archivo_lower = archivo.lower()
            if any(palabra in archivo_lower for palabra in palabras_busqueda):
                relacionados.append(archivo)
        
        for archivo in relacionados[:10]:
            self.stdout.write(f"  - {archivo}")
        
        if not relacionados:
            self.stdout.write("  (ningún archivo relacionado encontrado)")
            
    def generar_reporte_portadas_no_encontradas(self, juegos_actualizados):
        """Genera un reporte de las portadas que no se encontraron"""
        self.stdout.write(self.style.WARNING(f'\n{"🚨 REPORTE DE PORTADAS NO ENCONTRADAS 🚨":=^60}'))
        
        juegos_sin_portada = Juego.objects.filter(
            consola='ps4', 
            disponible=True,
            imagen="img/default.jpg"
        ) | Juego.objects.filter(
            consola='ps4', 
            disponible=True,
            imagen="img/default.png"
        ) | Juego.objects.filter(
            consola='ps4', 
            disponible=True,
            imagen__isnull=True
        )
        
        total_sin_portada = juegos_sin_portada.count()
        self.stdout.write(self.style.ERROR(f'Juegos SIN portada: {total_sin_portada}'))
        
        if total_sin_portada > 0:
            self.stdout.write("\n📋 Lista de juegos sin portada:")
            for juego in juegos_sin_portada:
                self.stdout.write(f"   • {juego.nombre}")
                
            # Mostrar sugerencias de nombres de archivo
            self.stdout.write(f"\n💡 Nombres de archivo sugeridos:")
            for juego in juegos_sin_portada[:10]:  # Mostrar solo los primeros 10
                nombre_sugerido = self.generar_nombre_imagen_sugerido(juego.nombre)
                self.stdout.write(f"   • {nombre_sugerido}")
    
        # Juegos CON portada
        juegos_con_portada = Juego.objects.filter(
            consola='ps4', 
            disponible=True
        ).exclude(imagen="img/default.jpg").exclude(imagen="img/default.png").exclude(imagen__isnull=True)
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ Juegos CON portada: {juegos_con_portada.count()}'))
        
    def generar_nombre_imagen_sugerido(self, nombre_juego):
        """Genera el nombre de archivo sugerido para la imagen"""
        nombre = nombre_juego.lower()
        
        # Determinar consola
        if 'ps5' in nombre:
            consola = 'ps5'
        else:
            consola = 'ps4'
        
        # Quitar consola del nombre
        nombre = nombre.replace(' ps4', '').replace(' ps5', '').strip()
        
        # Limpiar caracteres
        nombre = nombre.replace("'", "").replace(":", "").replace("&", "and")
        nombre = nombre.replace(" ", "_")
        
        return f"{nombre}_{consola}.jpg"

    def handle(self, *args, **options):
        csv_filename = options['file']
        csv_path = os.path.join(settings.BASE_DIR, csv_filename)
        col_nombre = options['columna_nombre']
        col_precio = options['columna_precio']
        
        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f'No se encontro {csv_path}'))
            return
        
        # NO marcar todos como no disponibles al inicio
        juegos_en_stock_ids = []
        actualizados = 0
        errores = []
        no_encontrados = []
        
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as file:
                content = file.read()
                content = content.replace('�', '').replace('"', '').replace("'", "")
                
                csv_reader = csv.DictReader(content.splitlines(), delimiter=';')
                
                if csv_reader.fieldnames:
                    csv_reader.fieldnames = [name.strip().upper() for name in csv_reader.fieldnames]
                
                self.stdout.write(f"Columnas encontradas: {csv_reader.fieldnames}")
                
                if col_nombre not in csv_reader.fieldnames:
                    self.stdout.write(self.style.ERROR(f'No se encontro la columna "{col_nombre}"'))
                    return
                
                if col_precio not in csv_reader.fieldnames:
                    self.stdout.write(self.style.ERROR(f'No se encontro la columna "{col_precio}"'))
                    return
                
                for linea_num, row in enumerate(csv_reader, start=2):
                    try:
                        nombre_sucio = row.get(col_nombre, '').strip()
                        if not nombre_sucio:
                            continue
                        
                        # Limpiar nombre avanzado
                        nombre_limpio = self.limpiar_nombre_avanzado(nombre_sucio)
                        
                        if not nombre_limpio or len(nombre_limpio) < 3:
                            continue
                        
                        # Agregar PS4 al nombre si no lo tiene
                        if not nombre_limpio.upper().endswith('PS4'):
                            nombre_busqueda = f"{nombre_limpio} PS4"
                        else:
                            nombre_busqueda = nombre_limpio
                        
                        self.stdout.write(f"TRANSFORMACIÓN: '{nombre_sucio}' -> '{nombre_busqueda}'")
                        
                        # Buscar juego en la base de datos
                        juego = self.buscar_juego_similar(nombre_busqueda)
                        
                        if not juego:
                            no_encontrados.append(f"'{nombre_sucio}' -> '{nombre_busqueda}'")
                            self.stdout.write(self.style.WARNING(f'NO ENCONTRADO: {nombre_busqueda}'))
                            continue
                        
                        # Obtener y limpiar precio
                        precio_str = row.get(col_precio, '').strip()
                        precio = self.limpiar_precio(precio_str)
                        
                        # Actualizar el juego encontrado
                        juego.precio = precio
                        juego.recargo = Decimal('0.0')
                        juego.disponible = True
                        if not juego.imagen or "default" in juego.imagen:
                            juego.imagen = self.buscar_imagen_existente(juego.nombre)
                        juego.save()
                        
                        juegos_en_stock_ids.append(juego.id)
                        actualizados += 1
                        
                        self.stdout.write(self.style.SUCCESS(f'ACTUALIZADO: {juego.nombre} - ${precio}'))
                        
                    except Exception as e:
                        error_msg = f'Linea {linea_num}: {str(e)}'
                        errores.append(error_msg)
                        self.stdout.write(self.style.ERROR(error_msg))
                        continue
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
            return
        
        # ✅ CORREGIDO: Ahora marcar como no disponibles SOLO los PS4 que NO están en el stock
        if juegos_en_stock_ids:
            juegos_a_desactivar = Juego.objects.filter(consola='ps4').exclude(id__in=juegos_en_stock_ids)
            desactivados_count = juegos_a_desactivar.update(disponible=False)
            
            # Mostrar cuántos PS4 se desactivaron
            self.stdout.write(f"\n🔍 PS4 desactivados (fuera de stock): {desactivados_count}")
            if desactivados_count > 0:
                for juego in juegos_a_desactivar[:5]:
                    self.stdout.write(f"   - {juego.nombre}")
        else:
            desactivados_count = 0
        
        # Resultados
        self.stdout.write(self.style.SUCCESS(f'\n{"="*60}'))
        self.stdout.write(self.style.SUCCESS(f'ACTUALIZADOS: {actualizados}'))
        self.stdout.write(self.style.SUCCESS(f'DESACTIVADOS: {desactivados_count}'))
        self.stdout.write(self.style.WARNING(f'NO ENCONTRADOS: {len(no_encontrados)}'))
        
        if no_encontrados:
            self.stdout.write(self.style.WARNING("\nJuegos no encontrados en BD:"))
            for nombre in no_encontrados[:10]:
                self.stdout.write(f"  - {nombre}")
        self.generar_reporte_portadas_no_encontradas(actualizados)