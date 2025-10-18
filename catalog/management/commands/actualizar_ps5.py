# catalog/management/commands/actualizar_ps5.py
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
    help = 'Actualiza stock de PS5 desde CSV'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='stock_ps5.csv',
            help='CSV con juegos de PS5'
        )
        parser.add_argument(
            '--columna-nombre',
            type=str,
            default='NOMBRE',  # ← CAMBIADO A 'NOMBRE'
            help='Nombre de la columna con el nombre del juego'
        )
        parser.add_argument(
            '--columna-precio',
            type=str,
            default='PRECIO',
            help='Nombre de la columna con el precio'
        )
        parser.add_argument(
            '--columna-disponible',
            type=str,
            default='DISPONIBLE',
            help='Nombre de la columna con disponibilidad (0=False, vacío=True)'
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

    def limpiar_nombre_para_busqueda(self, nombre):
        """Limpia el nombre para búsqueda flexible - QUITA PS5 completamente"""
        if not nombre:
            return ""
        
        # Primero aplicar limpieza avanzada
        nombre = self.limpiar_nombre_avanzado(nombre)
        
        # Quitar todas las variaciones de PS5 para búsqueda
        nombre = re.sub(r'\(\s*PS5\s*\)', '', nombre, flags=re.IGNORECASE)
        nombre = re.sub(r'\(\s*PlayStation 5\s*\)', '', nombre, flags=re.IGNORECASE)
        nombre = re.sub(r'\s*PS5\s*', ' ', nombre, flags=re.IGNORECASE)
        nombre = re.sub(r'\s*PlayStation 5\s*', ' ', nombre, flags=re.IGNORECASE)
        
        # Limpiar espacios extra
        nombre = re.sub(r'\s+', ' ', nombre).strip()
        
        return nombre

    def buscar_juego_similar(self, nombre_csv):
        """Busca juegos en la base de datos que coincidan aproximadamente - VERSIÓN MEJORADA"""
        self.stdout.write(f"🔍 BUSCANDO: '{nombre_csv}'")
        
        # 1. Búsqueda exacta (con y sin PS5)
        juegos_exactos = Juego.objects.filter(
            nombre__iexact=nombre_csv,
            consola='ps5'
        )
        if juegos_exactos.exists():
            self.stdout.write(f"✓ ENCONTRADO (exacto): {juegos_exactos.first().nombre}")
            return juegos_exactos.first()
        
        # 2. Limpiar nombre para búsqueda flexible (sin PS5)
        nombre_limpio = self.limpiar_nombre_para_busqueda(nombre_csv)
        self.stdout.write(f"  Nombre limpio: '{nombre_limpio}'")
        
        # 3. Buscar por nombre limpio (sin PS5)
        if nombre_limpio:
            juegos_por_nombre_limpio = Juego.objects.filter(
                nombre__icontains=nombre_limpio,
                consola='ps5'
            )
            
            if juegos_por_nombre_limpio.exists():
                self.stdout.write(f"  Coincidencias por nombre limpio: {juegos_por_nombre_limpio.count()}")
                
                # Si hay solo uno, devolverlo
                if juegos_por_nombre_limpio.count() == 1:
                    self.stdout.write(f"✓ ENCONTRADO (único): {juegos_por_nombre_limpio.first().nombre}")
                    return juegos_por_nombre_limpio.first()
                
                # Si hay múltiples, buscar la mejor coincidencia
                for juego in juegos_por_nombre_limpio:
                    nombre_juego_limpio = self.limpiar_nombre_para_busqueda(juego.nombre)
                    if nombre_limpio == nombre_juego_limpio:
                        self.stdout.write(f"✓ ENCONTRADO (coincidencia exacta): {juego.nombre}")
                        return juego
                
                # Si no hay coincidencia exacta, devolver el primero
                self.stdout.write(f"✓ ENCONTRADO (primero): {juegos_por_nombre_limpio.first().nombre}")
                return juegos_por_nombre_limpio.first()
        
        # 4. Búsqueda por palabras clave
        palabras_clave = nombre_limpio.split()[:4]
        self.stdout.write(f"  Palabras clave: {palabras_clave}")
        
        if palabras_clave:
            query = None
            for palabra in palabras_clave:
                if len(palabra) > 3:
                    if query is None:
                        query = models.Q(nombre__icontains=palabra)
                    else:
                        query |= models.Q(nombre__icontains=palabra)
            
            if query:
                juegos_similares = Juego.objects.filter(query, consola='ps5')
                if juegos_similares.exists():
                    self.stdout.write(f"  Coincidencias por palabras clave: {juegos_similares.count()}")
                    
                    # Buscar la mejor coincidencia por similitud
                    mejor_juego = None
                    mejor_similitud = 0
                    
                    for juego in juegos_similares:
                        similitud = difflib.SequenceMatcher(
                            None, 
                            nombre_limpio.lower(), 
                            self.limpiar_nombre_para_busqueda(juego.nombre).lower()
                        ).ratio()
                        
                        if similitud > mejor_similitud:
                            mejor_similitud = similitud
                            mejor_juego = juego
                    
                    if mejor_juego and mejor_similitud > 0.6:
                        self.stdout.write(f"✓ ENCONTRADO (similitud {mejor_similitud:.2f}): {mejor_juego.nombre}")
                        return mejor_juego
        
        # 5. Búsqueda final - mostrar qué juegos PS5 hay en la BD para debug
        todos_ps5 = Juego.objects.filter(consola='ps5')
        self.stdout.write(f"  Juegos PS5 en BD: {todos_ps5.count()}")
        for juego in todos_ps5[:5]:
            self.stdout.write(f"    - {juego.nombre}")
        
        self.stdout.write(f"✗ NO ENCONTRADO: '{nombre_csv}'")
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

    def determinar_disponibilidad(self, disponible_str):
        """Determina la disponibilidad basada en el valor de la columna"""
        if not disponible_str or disponible_str.strip() == '':
            return True  # Valor por defecto si está vacío
        
        disponible_str = str(disponible_str).strip().lower()
        
        # Si es "0", "false", "no", "falso" -> False
        if disponible_str in ['0', 'false', 'no', 'falso']:
            return False
        
        # Si es "1", "true", "si", "verdadero" -> True
        if disponible_str in ['1', 'true', 'si', 'verdadero']:
            return True
        
        # Por defecto True
        return True

    def calcular_recargo(self, precio):
        """Calcula el recargo como 10% del precio"""
        if precio <= 0:
            return Decimal('0.0')
        
        recargo = precio * Decimal('0.10')
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
        
        # Determinar consola - para PS5
        if 'ps4' in nombre:
            consola = 'ps4'
        else:
            consola = 'ps5'
        
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
            consola='ps5', 
            disponible=True,
            imagen="img/default.jpg"
        ) | Juego.objects.filter(
            consola='ps5', 
            disponible=True,
            imagen="img/default.png"
        ) | Juego.objects.filter(
            consola='ps5', 
            disponible=True,
            imagen__isnull=True
        )
        
        total_sin_portada = juegos_sin_portada.count()
        self.stdout.write(self.style.ERROR(f'Juegos PS5 SIN portada: {total_sin_portada}'))
        
        if total_sin_portada > 0:
            self.stdout.write("\n📋 Lista de juegos PS5 sin portada:")
            for juego in juegos_sin_portada:
                self.stdout.write(f"   • {juego.nombre}")
                
            # Mostrar sugerencias de nombres de archivo
            self.stdout.write(f"\n💡 Nombres de archivo sugeridos:")
            for juego in juegos_sin_portada[:15]:  # Mostrar más juegos
                nombre_sugerido = self.generar_nombre_imagen_sugerido(juego.nombre)
                self.stdout.write(f"   • {nombre_sugerido}")
    
        # Juegos CON portada
        juegos_con_portada = Juego.objects.filter(
            consola='ps5', 
            disponible=True
        ).exclude(imagen="img/default.jpg").exclude(imagen="img/default.png").exclude(imagen__isnull=True)
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ Juegos PS5 CON portada: {juegos_con_portada.count()}'))
        
    def generar_nombre_imagen_sugerido(self, nombre_juego):
        """Genera el nombre de archivo sugerido para la imagen"""
        nombre = nombre_juego.lower()
        
        # Determinar consola - para PS5
        if 'ps4' in nombre:
            consola = 'ps4'
        else:
            consola = 'ps5'
        
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
        col_disponible = options['columna_disponible']
        
        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f'No se encontro {csv_path}'))
            return
        
        # NO marcar todos como no disponibles al inicio
        juegos_en_stock_ids = []
        actualizados = 0
        errores = []
        no_encontrados = []
        desactivados_por_csv = 0
        
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as file:
                content = file.read()
                content = content.replace('�', '').replace('"', '').replace("'", "")
                
                csv_reader = csv.DictReader(content.splitlines(), delimiter=';')
                
                if csv_reader.fieldnames:
                    csv_reader.fieldnames = [name.strip().upper() for name in csv_reader.fieldnames]
                
                self.stdout.write(f"Columnas encontradas: {csv_reader.fieldnames}")
                
                # Verificar que exista la columna NOMBRE
                if col_nombre not in csv_reader.fieldnames:
                    self.stdout.write(self.style.ERROR(f'No se encontro la columna "{col_nombre}"'))
                    self.stdout.write(f'Columnas disponibles: {csv_reader.fieldnames}')
                    return
                
                if col_precio not in csv_reader.fieldnames:
                    self.stdout.write(self.style.ERROR(f'No se encontro la columna "{col_precio}"'))
                    return
                
                for linea_num, row in enumerate(csv_reader, start=2):
                    try:
                        # USAR COLUMNA "NOMBRE" en lugar de "JUEGOS"
                        nombre_sucio = row.get(col_nombre, '').strip()
                        if not nombre_sucio:
                            continue
                        
                        # Usar el nombre del CSV directamente
                        nombre_busqueda = nombre_sucio
                        
                        self.stdout.write(f"\n📝 PROCESANDO: '{nombre_sucio}'")
                        
                        # Buscar juego en la base de datos (búsqueda flexible)
                        juego = self.buscar_juego_similar(nombre_busqueda)
                        
                        if not juego:
                            no_encontrados.append(nombre_sucio)
                            self.stdout.write(self.style.WARNING(f'NO ENCONTRADO: {nombre_busqueda}'))
                            continue
                        
                        # Obtener y limpiar precio
                        precio_str = row.get(col_precio, '').strip()
                        precio = self.limpiar_precio(precio_str)
                        
                        # DETERMINAR DISPONIBILIDAD
                        disponible_str = row.get(col_disponible, '').strip()
                        disponible = self.determinar_disponibilidad(disponible_str)
                        
                        # CALCULAR RECARGO AUTOMÁTICAMENTE (10% del precio)
                        recargo = self.calcular_recargo(precio)
                        
                        # Actualizar el juego encontrado
                        juego.precio = precio
                        juego.recargo = recargo
                        juego.disponible = disponible
                        if not juego.imagen or "default" in juego.imagen:
                            juego.imagen = self.buscar_imagen_existente(juego.nombre)
                        juego.save()
                        
                        juegos_en_stock_ids.append(juego.id)
                        actualizados += 1
                        
                        if not disponible:
                            desactivados_por_csv += 1
                            self.stdout.write(self.style.WARNING(f'ACTUALIZADO (NO DISPONIBLE): {juego.nombre} - ${precio} | Recargo: ${recargo}'))
                        else:
                            self.stdout.write(self.style.SUCCESS(f'ACTUALIZADO: {juego.nombre} - ${precio} | Recargo: ${recargo}'))
                        
                    except Exception as e:
                        error_msg = f'Linea {linea_num}: {str(e)}'
                        errores.append(error_msg)
                        self.stdout.write(self.style.ERROR(error_msg))
                        continue
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
            return
        
        # ✅ CORREGIDO: Ahora marcar como no disponibles SOLO los PS5 que NO están en el stock
        if juegos_en_stock_ids:
            juegos_a_desactivar = Juego.objects.filter(consola='ps5').exclude(id__in=juegos_en_stock_ids)
            desactivados_count = juegos_a_desactivar.update(disponible=False)
            
            # Mostrar cuántos PS5 se desactivaron
            self.stdout.write(f"\n🔍 PS5 desactivados (fuera de stock): {desactivados_count}")
            if desactivados_count > 0:
                for juego in juegos_a_desactivar[:5]:  # Mostrar primeros 5 como ejemplo
                    self.stdout.write(f"   - {juego.nombre}")
        else:
            desactivados_count = 0
        
        # Resultados
        self.stdout.write(self.style.SUCCESS(f'\n{"="*60}'))
        self.stdout.write(self.style.SUCCESS(f'ACTUALIZADOS: {actualizados}'))
        self.stdout.write(self.style.SUCCESS(f'DESACTIVADOS (PS5 fuera de stock): {desactivados_count}'))
        self.stdout.write(self.style.WARNING(f'DESACTIVADOS (por CSV): {desactivados_por_csv}'))
        self.stdout.write(self.style.WARNING(f'NO ENCONTRADOS: {len(no_encontrados)}'))
        
        if no_encontrados:
            self.stdout.write(self.style.WARNING("\nJuegos no encontrados en BD:"))
            for nombre in no_encontrados[:10]:
                self.stdout.write(f"  - {nombre}")
        
        # Mostrar diagnóstico de la BD
        total_ps5_bd = Juego.objects.filter(consola='ps5').count()
        disponibles_ps5 = Juego.objects.filter(consola='ps5', disponible=True).count()
        total_ps4_bd = Juego.objects.filter(consola='ps4').count()  # Para verificar que no se afectaron
        self.stdout.write(f"\n📊 ESTADO BD:")
        self.stdout.write(f"   PS5: {disponibles_ps5}/{total_ps5_bd} disponibles")
        self.stdout.write(f"   PS4: {Juego.objects.filter(consola='ps4', disponible=True).count()}/{total_ps4_bd} disponibles")

        # Reporte de portadas
        self.generar_reporte_portadas_no_encontradas(actualizados)