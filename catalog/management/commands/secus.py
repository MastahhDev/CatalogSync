# catalog/management/commands/actualizar_secundarios.py
import csv
import os
import re
import unicodedata
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import models
from catalog.models import Juego
from difflib import SequenceMatcher

class Command(BaseCommand):
    help = 'Actualiza juegos secundarios - agrega precio secundario si existe o crea nuevo juego'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='stock_secus.csv',
            help='CSV con juegos secundarios'
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
        parser.add_argument(
            '--columna-disponible',
            type=str,
            default='DISPONIBLE',
            help='Nombre de la columna con disponibilidad (vacío=True, 0=False)'
        )
        parser.add_argument(
            '--consola',
            type=str,
            default='ps4',
            help='Consola (ps4 o ps5)'
        )
        parser.add_argument(
            '--solo-actualizar',
            action='store_true',
            help='Solo actualizar juegos existentes, NO crear nuevos'
        )
        parser.add_argument(
            '--mostrar-portadas-faltantes',
            action='store_true',
            help='Mostrar lista de portadas faltantes'
        )
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Mostrar información de depuración del proceso de limpieza'
        )
        parser.add_argument(
            '--corregir-precios',
            action='store_true',
            help='Corregir juegos secundarios con precios en campos equivocados'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simular sin hacer cambios reales (solo con --corregir-precios)'
        )

    def corregir_precios_secundarios(self, dry_run=False):
        """Corrige juegos secundarios que tienen el precio en el campo equivocado"""
        # Buscar juegos secundarios con precio_secundario NULL pero precio válido
        juegos_incorrectos = Juego.objects.filter(
            es_solo_secundario=True,
            precio_secundario__isnull=True,
            precio__gt=0
        )
        
        total = juegos_incorrectos.count()
        
        if total == 0:
            self.stdout.write(self.style.SUCCESS('✅ No hay juegos con precios incorrectos'))
            return 0, 0
        
        self.stdout.write(self.style.WARNING(f'\n🔧 CORRECCIÓN DE PRECIOS - Encontrados {total} juegos para corregir\n'))
        
        corregidos = 0
        errores = 0
        
        for juego in juegos_incorrectos:
            try:
                self.stdout.write(f"{'[DRY-RUN] ' if dry_run else ''}Corrigiendo: {juego.nombre}")
                self.stdout.write(f"  precio: {juego.precio} -> 0")
                self.stdout.write(f"  precio_secundario: None -> {juego.precio}")
                self.stdout.write(f"  recargo: {juego.recargo} -> 0")
                self.stdout.write(f"  recargo_secundario: None -> {juego.recargo}")
                
                if not dry_run:
                    # Guardar valores originales
                    precio_original = juego.precio
                    recargo_original = juego.recargo
                    
                    # Mover precios a los campos correctos
                    juego.precio_secundario = precio_original
                    juego.recargo_secundario = recargo_original
                    juego.precio = 0
                    juego.recargo = 0
                    juego.save()
                    
                    self.stdout.write(self.style.SUCCESS(f"  ✅ Corregido\n"))
                else:
                    self.stdout.write(self.style.WARNING(f"  ⚠️  Simulado\n"))
                
                corregidos += 1
                
            except Exception as e:
                errores += 1
                self.stdout.write(self.style.ERROR(f"  ❌ Error: {str(e)}\n"))
        
        return corregidos, errores

    def quitar_acentos(self, texto):
        """Elimina acentos y diacríticos de un texto"""
        if not texto:
            return ""
        
        texto_normalizado = unicodedata.normalize('NFD', texto)
        texto_sin_acentos = ''.join(
            c for c in texto_normalizado
            if unicodedata.category(c) != 'Mn'
        )
        
        return texto_sin_acentos

    def limpiar_nombre_avanzado(self, nombre, debug=False):
        """Limpia el nombre quitando idiomas, ediciones específicas, etc. - MISMA QUE PS5"""
        if not nombre:
            return ""

        # Primero quitar acentos y diacríticos
        nombre = self.quitar_acentos(nombre)
            
        # Quitar emojis y caracteres especiales
        nombre = re.sub(r'[^\x00-\x7F]+', '', nombre)
        
        # Quitar símbolos especiales
        nombre = nombre.replace('®', '').replace('™', '').replace('©', '')
        nombre = nombre.replace(':', '').replace('#', '').replace('-', ' ')
        
        # Quitar el precio del nombre si está
        nombre = re.sub(r'\$\s*[\d.,]+', '', nombre)
        
        # Quitar caracteres especiales al inicio
        nombre = re.sub(r'^[\'\"\#\-\s]+', '', nombre)
        
        # PATRONES A FILTRAR (case insensitive) - MISMA LISTA QUE PS5
        patrones_a_eliminar = [
            # Idiomas y subtítulos
            r'\bespanol\s+espana\b', r'\bespanol\s+latino\b',
            r'\benglish\b', r'\bsubtitulado\b', r'\bsubtitulada\b',
            r'\bespanol\b', r'\bspanish\b',
            
            # Ediciones
            r'\bdeluxe\s+edition\b', r'\bgold\s+edition\b', r'\bstandard\s+edition\b',
            r'\bspecial\s+edition\b', r'\bcollector\'s\s+edition\b', r'\bultimate\s+edition\b',
            r'\bpremium\s+edition\b', r'\bcomplete\s+edition\b', r'\bgame\s+of\s+the\s+year\b',
            r'\bgoty\b', r'\bedicion\s+deluxe\b', r'\bedicion\s+gold\b',
            r'\bedicion\s+estandar\b', r'\bedicion\s+especial\b', r'\blatino\b', r'\bespaol\s+espaa\b',
            
            # Palabras generales a eliminar
            r'\bversion\b', r'\bedicion\b', r'\bdigital\b', r'\bfisico\b',
            r'\bphysical\b', r'\bdownload\b', r'\bdescarga\b', r'\bespaol\b', r'\bespaa\b',
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

    def buscar_juego_similar(self, nombre_limpio, consola):
        """Busca juegos en la base de datos que coincidan aproximadamente - MISMA LÓGICA QUE PS5"""
        # Primero intenta búsqueda exacta sin consola
        nombre_sin_consola = nombre_limpio.replace(f' {consola.upper()}', '').replace(f' {consola}', '').strip()
        
        # 1. Buscar coincidencias EXACTAS (case insensitive) - INCLUYE NO DISPONIBLES
        juegos_exactos = Juego.objects.filter(
            nombre__iexact=nombre_limpio,
            consola=consola
        )
        if juegos_exactos.exists():
            juego = juegos_exactos.first()
            self.stdout.write(f"  ✓ Encontrado exacto (disponible={juego.disponible}): {juego.nombre}")
            return juego
        
        # 2. Buscar sin consola pero EXACTO
        juegos_sin_consola_exacto = Juego.objects.filter(
            nombre__iexact=nombre_sin_consola,
            consola=consola
        )
        if juegos_sin_consola_exacto.exists():
            juego = juegos_sin_consola_exacto.first()
            self.stdout.write(f"  ✓ Encontrado sin consola (disponible={juego.disponible}): {juego.nombre}")
            return juego
        
        # 3. Limpiar el nombre de la BD también antes de comparar
        nombre_muy_limpio = self.limpiar_nombre_avanzado(nombre_sin_consola)
        
        # 4. Obtener TODOS los juegos de la consola y compararlos uno por uno
        todos_juegos_consola = Juego.objects.filter(consola=consola)
        
        mejor_coincidencia = None
        mejor_ratio = 0.0
        
        for juego_candidato in todos_juegos_consola:
            # Limpiar el nombre del candidato de la BD
            nombre_candidato_limpio = self.limpiar_nombre_avanzado(
                juego_candidato.nombre.replace(f' {consola.upper()}', '').replace(f' {consola}', '')
            )
            
            # Calcular similitud
            ratio = SequenceMatcher(
                None, 
                nombre_muy_limpio.lower(), 
                nombre_candidato_limpio.lower()
            ).ratio()
            
            # Debug: mostrar comparación
            if ratio > 0.7:
                self.stdout.write(
                    f"  Comparando: '{nombre_muy_limpio}' vs '{nombre_candidato_limpio}' = {ratio:.2f}"
                )
            
            if ratio > mejor_ratio:
                mejor_ratio = ratio
                mejor_coincidencia = juego_candidato
        
        # Solo aceptar coincidencias MUY similares
        if mejor_ratio >= 0.90:
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ MATCH encontrado: '{mejor_coincidencia.nombre}' (similitud: {mejor_ratio:.2f})"
                )
            )
            return mejor_coincidencia
        elif mejor_ratio > 0.7:
            self.stdout.write(
                self.style.WARNING(
                    f"⚠ Match rechazado (muy bajo): '{mejor_coincidencia.nombre if mejor_coincidencia else 'N/A'}' (similitud: {mejor_ratio:.2f})"
                )
            )
        
        return None

    def determinar_disponibilidad(self, disponible_str):
        """Determina la disponibilidad basada en el valor de la columna"""
        # Verificar si es None primero
        if disponible_str is None:
            return True
        
        # Convertir a string y limpiar
        disponible_str = str(disponible_str).strip()
        
        # Caso especial: string vacío después de strip significa disponible
        if disponible_str == '':
            return True
        
        # Manejar diferentes representaciones de False
        if disponible_str.lower() in ['0', 'false', 'no', 'falso']:
            return False
        
        # Cualquier otro valor se considera True
        return True

    def limpiar_precio(self, precio_str):
        """Convierte string con precio a Decimal - FORMATO ARGENTINO"""
        if not precio_str or precio_str.strip() == '':
            return Decimal('0.0')
        
        precio_str = str(precio_str).replace('$', '').replace(' ', '').strip()
        
        if ',' in precio_str:
            precio_str = precio_str.replace('.', '').replace(',', '.')
        else:
            precio_str = precio_str.replace('.', '')
        
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
        return recargo.quantize(Decimal('0.01'))

    def buscar_imagen(self, nombre_juego, consola):
        """Busca la imagen correspondiente al juego - VERSIÓN MEJORADA"""
        try:
            # Limpiar el nombre más agresivamente
            nombre = re.sub(r'\s*\(SECUNDARIO\)\s*', '', nombre_juego, flags=re.IGNORECASE)
            nombre = self.quitar_acentos(nombre.lower())
            
            # Remover consola del nombre si está presente
            nombre = nombre.replace(f' {consola}', '').replace(f'{consola}', '').strip()
            
            # Limpiar caracteres problemáticos
            nombre = nombre.replace("'", "").replace(":", "").replace("&", "and")
            nombre = nombre.replace("+", "").replace("#", "").replace("!", "")
            nombre = nombre.replace("?", "").replace("*", "").replace("/", "")
            nombre = nombre.replace("\\", "").replace('"', "").replace("|", "")
            
            # Primera versión: reemplazar espacios con guiones bajos
            nombre_archivo1 = f"{nombre.replace(' ', '_')}_{consola}.jpg"
            
            # Segunda versión: sin espacios
            nombre_archivo2 = f"{nombre.replace(' ', '')}_{consola}.jpg"
            
            # Tercera versión: solo palabras clave
            palabras = [p for p in nombre.split() if len(p) > 2 and p not in ['the', 'and', 'del', 'de', 'la', 'el']]
            nombre_archivo3 = f"{'_'.join(palabras[:4])}_{consola}.jpg" if palabras else None
            
            img_dir = os.path.join(settings.BASE_DIR, 'static', 'img')
            
            # DEBUG: Mostrar qué estamos buscando
            self.stdout.write(f"  🔍 Buscando imagen para: '{nombre_juego}'")
            self.stdout.write(f"  📁 En directorio: {img_dir}")
            self.stdout.write(f"  🎯 Nombres a buscar: {nombre_archivo1}, {nombre_archivo2}, {nombre_archivo3}")
            
            # Verificar si el directorio existe
            if not os.path.exists(img_dir):
                self.stdout.write(self.style.ERROR(f"  ❌ Directorio de imágenes no existe: {img_dir}"))
                return "img/default.jpg"
            
            # Listar archivos disponibles (para debug)
            archivos_existentes = [f for f in os.listdir(img_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            self.stdout.write(f"  📂 Archivos en directorio: {len(archivos_existentes)}")
            
            # Buscar por nombres exactos primero
            for nombre_archivo in [nombre_archivo1, nombre_archivo2, nombre_archivo3]:
                if nombre_archivo and os.path.exists(os.path.join(img_dir, nombre_archivo)):
                    self.stdout.write(f"  ✅ Encontrada imagen exacta: {nombre_archivo}")
                    return f"img/{nombre_archivo}"
            
            # Buscar case-insensitive
            archivos_lower = [f.lower() for f in archivos_existentes]
            
            for nombre_archivo in [nombre_archivo1, nombre_archivo2, nombre_archivo3]:
                if nombre_archivo and nombre_archivo.lower() in archivos_lower:
                    archivo_real = archivos_existentes[archivos_lower.index(nombre_archivo.lower())]
                    self.stdout.write(f"  ✅ Encontrada imagen (case-insensitive): {archivo_real}")
                    return f"img/{archivo_real}"
            
            # Búsqueda flexible por partes del nombre
            nombre_busqueda = nombre.replace(' ', '_').lower()
            
            for archivo in archivos_existentes:
                archivo_lower = archivo.lower()
                archivo_sin_ext = archivo_lower.rsplit('.', 1)[0]
                
                # Verificar si el nombre del juego está en el archivo o viceversa
                if (nombre_busqueda in archivo_sin_ext or 
                    archivo_sin_ext in nombre_busqueda or
                    any(palabra in archivo_sin_ext for palabra in nombre_busqueda.split('_') if len(palabra) > 3)):
                    
                    self.stdout.write(f"  ✅ Encontrada imagen flexible: {archivo}")
                    return f"img/{archivo}"
            
            # Búsqueda por similitud para casos como "Terraria"
            nombre_simplificado = re.sub(r'[_\-\d\s]+', '', nombre).lower()
            
            for archivo in archivos_existentes:
                archivo_sin_ext = re.sub(r'[_\-\d\s]+', '', archivo.lower().rsplit('.', 1)[0])
                
                if nombre_simplificado in archivo_sin_ext or archivo_sin_ext in nombre_simplificado:
                    self.stdout.write(f"  ✅ Encontrada imagen por similitud: {archivo}")
                    return f"img/{archivo}"
            
            self.stdout.write(self.style.WARNING(f"  ⚠️  No se encontró imagen, usando default"))
            return "img/default.jpg"
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ❌ Error buscando imagen: {str(e)}"))
            return "img/default.jpg"

    def verificar_imagenes_problema(self, juegos_procesados):
        """Verificación especial para imágenes problemáticas"""
        img_dir = os.path.join(settings.BASE_DIR, 'static', 'img')
        problemas = []
        
        for juego_info in juegos_procesados:
            nombre_juego = juego_info['nombre']
            imagen_actual = juego_info.get('imagen', '')
            
            # Verificar si la imagen existe físicamente
            if imagen_actual and imagen_actual != "img/default.jpg":
                ruta_imagen = os.path.join(settings.BASE_DIR, 'static', imagen_actual.replace('img/', ''))
                if not os.path.exists(ruta_imagen):
                    problemas.append({
                        'juego': nombre_juego,
                        'imagen_referenciada': imagen_actual,
                        'problema': 'ARCHIVO NO EXISTE',
                        'ruta_buscada': ruta_imagen
                    })
            
            # Verificar si está usando default.jpg pero debería tener imagen
            elif imagen_actual == "img/default.jpg":
                # Intentar buscar manualmente
                nombres_posibles = self.generar_nombres_sugeridos(nombre_juego, juego_info['consola'])
                archivos_existentes = [f for f in os.listdir(img_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
                
                encontrados = []
                for nombre_posible in nombres_posibles:
                    if nombre_posible.lower() in [f.lower() for f in archivos_existentes]:
                        encontrados.append(nombre_posible)
                
                if encontrados:
                    problemas.append({
                        'juego': nombre_juego,
                        'imagen_referenciada': imagen_actual,
                        'problema': 'USANDO DEFAULT PERO EXISTE IMAGEN',
                        'imagenes_encontradas': encontrados
                    })
        
        return problemas

    def verificar_portadas_faltantes(self, juegos_procesados):
        """Verifica qué juegos no tienen portada y sugiere nombres de archivo"""
        img_dir = os.path.join(settings.BASE_DIR, 'static', 'img')
        portadas_faltantes = []
        
        for juego_info in juegos_procesados:
            nombre_juego = juego_info['nombre']
            consola = juego_info['consola']
            imagen_actual = juego_info.get('imagen', '')
            
            if imagen_actual and imagen_actual != "img/default.jpg":
                continue
            
            nombres_sugeridos = self.generar_nombres_sugeridos(nombre_juego, consola)
            
            portadas_faltantes.append({
                'juego': nombre_juego,
                'consola': consola,
                'nombres_sugeridos': nombres_sugeridos,
                'imagen_actual': imagen_actual
            })
        
        return portadas_faltantes

    def generar_nombres_sugeridos(self, nombre_juego, consola):
        """Genera nombres de archivo sugeridos para las portadas"""
        nombre_limpio = re.sub(r'\s*\(SECUNDARIO\)\s*', '', nombre_juego, flags=re.IGNORECASE)
        nombre_limpio = self.quitar_acentos(nombre_limpio.lower())
        nombre_limpio = nombre_limpio.replace(f' {consola}', '').strip()
        
        variaciones = []
        
        basico = nombre_limpio.replace("'", "").replace(":", "").replace("&", "and")
        basico = basico.replace(" ", "_")
        variaciones.append(f"{basico}_{consola}.jpg")
        
        sin_articulos = re.sub(r'\b(the|a|an|el|la|los|las|un|una|unos|unas)\b', '', nombre_limpio, flags=re.IGNORECASE)
        sin_articulos = re.sub(r'\s+', ' ', sin_articulos).strip()
        sin_articulos = sin_articulos.replace(" ", "_")
        variaciones.append(f"{sin_articulos}_{consola}.jpg")
        
        muy_limpio = re.sub(r'\b(deluxe|gold|standard|special|collector\'s|ultimate|premium|complete|edition|edicion|goty|game of the year)\b', '', nombre_limpio, flags=re.IGNORECASE)
        muy_limpio = re.sub(r'\s+', ' ', muy_limpio).strip()
        muy_limpio = muy_limpio.replace(" ", "_")
        if muy_limpio and muy_limpio != basico:
            variaciones.append(f"{muy_limpio}_{consola}.jpg")
        
        palabras = nombre_limpio.split()
        if len(palabras) > 3:
            clave = "_".join(palabras[:3])
            variaciones.append(f"{clave}_{consola}.jpg")
        
        return variaciones[:5]

    def handle(self, *args, **options):
        # Si solo se solicita corrección de precios
        if options['corregir_precios']:
            dry_run = options['dry_run']
            corregidos, errores = self.corregir_precios_secundarios(dry_run)
            
            # Resumen de corrección
            self.stdout.write(self.style.SUCCESS(f'\n{"="*60}'))
            self.stdout.write(self.style.SUCCESS('📊 RESUMEN DE CORRECCIÓN'))
            self.stdout.write(self.style.SUCCESS(f'{"="*60}'))
            
            if dry_run:
                self.stdout.write(self.style.WARNING(f'🔍 MODO SIMULACIÓN - No se hicieron cambios reales'))
            
            self.stdout.write(self.style.SUCCESS(f'✅ Juegos corregidos: {corregidos}'))
            
            if errores > 0:
                self.stdout.write(self.style.ERROR(f'❌ Errores: {errores}'))
            
            if dry_run:
                self.stdout.write(self.style.WARNING(f'\n💡 Ejecuta sin --dry-run para aplicar los cambios'))
            
            return
        
        # Proceso normal de actualización de secundarios
        csv_filename = options['file']
        csv_path = os.path.join(settings.BASE_DIR, csv_filename)
        col_nombre = options['columna_nombre']
        col_precio = options['columna_precio']
        col_disponible = options['columna_disponible']
        consola = options['consola'].lower()
        solo_actualizar = options['solo_actualizar']
        debug = options.get('debug', False)
        
        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f'No se encontró {csv_path}'))
            return
        
        actualizados_existentes = 0
        creados_nuevos = 0
        errores = []
        no_encontrados = []
        omitidos_no_disponibles = 0
        reactivados = 0
        convertidos_a_solo_secundario = 0
        secundarios_ids = []
        secundarios_disponibles_ids = []  # ⭐ NUEVA LISTA: solo IDs de secundarios DISPONIBLES
        juegos_procesados = []
        
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as file:
                content = file.read()
                content = content.replace('�', '').replace('"', '').replace("'", "")
                
                csv_reader = csv.DictReader(content.splitlines(), delimiter=';')
                
                if csv_reader.fieldnames:
                    csv_reader.fieldnames = [name.strip().upper() for name in csv_reader.fieldnames]
                
                self.stdout.write(f"Columnas encontradas: {csv_reader.fieldnames}")
                
                if col_nombre not in csv_reader.fieldnames:
                    self.stdout.write(self.style.ERROR(f'No se encontró la columna "{col_nombre}"'))
                    return
                
                if col_precio not in csv_reader.fieldnames:
                    self.stdout.write(self.style.ERROR(f'No se encontró la columna "{col_precio}"'))
                    return
                
                tiene_columna_disponible = col_disponible in csv_reader.fieldnames
                if not tiene_columna_disponible:
                    self.stdout.write(self.style.WARNING(f'No se encontró la columna "{col_disponible}". Usando disponible=True por defecto.'))
                
                for linea_num, row in enumerate(csv_reader, start=2):
                    try:
                        nombre_sucio = row.get(col_nombre, '').strip()
                        if not nombre_sucio:
                            continue
                        
                        if tiene_columna_disponible:
                            disponible_str = row.get(col_disponible, '')
                            if disponible_str is None:
                                disponible_str = ''
                            disponible = self.determinar_disponibilidad(disponible_str)
                        else:
                            disponible = True
                        
                        # ⭐ CORRECCIÓN: SI NO ESTÁ DISPONIBLE, OMITIR PERO NO AGREGAR A LA LISTA DE DISPONIBLES
                        if not disponible:
                            omitidos_no_disponibles += 1
                            if debug:
                                self.stdout.write(f"  ⏭️  OMITIDO (no disponible en CSV): {nombre_sucio}")
                            continue  # ⭐ IMPORTANTE: saltar este juego
                        
                        if debug:
                            self.stdout.write(f"\n{'='*60}")
                            self.stdout.write(f"🔍 DEBUG - Limpieza de: '{nombre_sucio}'")
                        
                        nombre_limpio = self.limpiar_nombre_avanzado(nombre_sucio, debug=debug)
                        
                        if not nombre_limpio or len(nombre_limpio) < 3:
                            self.stdout.write(self.style.ERROR(f'⚠️  Nombre muy corto después de limpiar: "{nombre_sucio}" -> "{nombre_limpio}"'))
                            continue
                        
                        nombre_upper = nombre_limpio.upper()
                        tiene_ps4 = 'PS4' in nombre_upper
                        tiene_ps5 = 'PS5' in nombre_upper
                        
                        if tiene_ps5:
                            consola_real = 'ps5'
                            nombre_busqueda = nombre_limpio
                        elif tiene_ps4:
                            consola_real = 'ps4'
                            nombre_busqueda = nombre_limpio
                        else:
                            consola_real = consola
                            nombre_busqueda = f"{nombre_limpio} {consola.upper()}"
                        
                        if not debug:
                            self.stdout.write(f"\n{'='*60}")
                            self.stdout.write(f"PROCESANDO: '{nombre_sucio}' -> '{nombre_busqueda}'")
                        
                        precio_str = row.get(col_precio, '').strip()
                        precio_secundario = self.limpiar_precio(precio_str)
                        recargo_secundario = self.calcular_recargo(precio_secundario)
                        
                        # ⭐ USAR LA NUEVA BÚSQUEDA INTELIGENTE
                        juego_existente = self.buscar_juego_similar(nombre_busqueda, consola_real)
                        
                        if juego_existente:
                            # ⭐ ACTUALIZAR IMAGEN si está en default
                            if juego_existente.imagen == "img/default.jpg" or not juego_existente.imagen:
                                nueva_imagen = self.buscar_imagen(nombre_busqueda, consola_real)
                                if nueva_imagen != "img/default.jpg":
                                    juego_existente.imagen = nueva_imagen
                                    self.stdout.write(f"  🖼️  Imagen actualizada: {nueva_imagen}")
                            
                            if juego_existente.precio == Decimal('0.0'):
                                self.stdout.write(f"  ⚡ Juego con precio primario 0 - Marcando como solo secundario")
                                
                                if "(SECUNDARIO)" not in juego_existente.nombre.upper():
                                    nombre_original = juego_existente.nombre
                                    juego_existente.nombre = f"{nombre_original} (SECUNDARIO)"
                                    self.stdout.write(f"  ✏️  Nombre actualizado: {nombre_original} -> {juego_existente.nombre}")
                                
                                juego_existente.es_solo_secundario = True
                                juego_existente.tiene_secundario = False
                                convertidos_a_solo_secundario += 1
                            else:
                                juego_existente.es_solo_secundario = False
                                juego_existente.tiene_secundario = True
                            
                            estaba_desactivado = not juego_existente.disponible
                            if estaba_desactivado:
                                reactivados += 1
                                juego_existente.disponible = True
                                self.stdout.write(self.style.SUCCESS(f"  🔄 REACTIVADO juego previamente deshabilitado"))
                            
                            juego_existente.precio_secundario = precio_secundario
                            juego_existente.recargo_secundario = recargo_secundario
                            juego_existente.save()
                            
                            secundarios_ids.append(juego_existente.id)
                            secundarios_disponibles_ids.append(juego_existente.id)  # ⭐ AGREGAR A DISPONIBLES
                            actualizados_existentes += 1
                            
                            juegos_procesados.append({
                                'nombre': juego_existente.nombre,
                                'consola': consola_real,
                                'imagen': juego_existente.imagen
                            })
                            
                            self.stdout.write(self.style.SUCCESS(
                                f'✅ AGREGADO PRECIO SECUNDARIO: {juego_existente.nombre}\n'
                                f'   Primario: ${juego_existente.precio} | Secundario: ${precio_secundario}'
                            ))
                        
                        else:
                            if solo_actualizar:
                                self.stdout.write(self.style.WARNING(
                                    f'⏭️  OMITIDO (--solo-actualizar): {nombre_busqueda}'
                                ))
                                no_encontrados.append(f"'{nombre_sucio}' -> '{nombre_busqueda}'")
                                continue
                            
                            nombre_con_identificador = f"{nombre_busqueda} (SECUNDARIO)"
                            imagen = self.buscar_imagen(nombre_busqueda, consola_real)
                            
                            # ⭐ CORREGIDO: Guardar precio en el campo correcto
                            nuevo_juego = Juego.objects.create(
                                nombre=nombre_con_identificador,
                                precio=0,  # Precio primario en 0
                                recargo=0,
                                consola=consola_real,
                                disponible=True,
                                imagen=imagen,
                                es_solo_secundario=True,
                                precio_secundario=precio_secundario,  # ✅ AQUÍ va el precio
                                recargo_secundario=recargo_secundario,  # ✅ AQUÍ va el recargo
                                tiene_secundario=False
                            )
                            
                            secundarios_ids.append(nuevo_juego.id)
                            secundarios_disponibles_ids.append(nuevo_juego.id)  # ⭐ AGREGAR A DISPONIBLES
                            creados_nuevos += 1
                            
                            juegos_procesados.append({
                                'nombre': nuevo_juego.nombre,
                                'consola': consola_real,
                                'imagen': nuevo_juego.imagen
                            })
                            
                            self.stdout.write(self.style.WARNING(
                                f'🆕 CREADO COMO SECUNDARIO NUEVO: {nuevo_juego.nombre}\n'
                                f'   Precio: ${precio_secundario}'
                            ))
                        
                    except Exception as e:
                        error_msg = f'Línea {linea_num}: {str(e)}'
                        errores.append(error_msg)
                        self.stdout.write(self.style.ERROR(error_msg))
                        continue
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
            return
        
        # ⭐ CORRECCIÓN: Usar secundarios_disponibles_ids para la desactivación
        if secundarios_disponibles_ids:
            # Desactivar precios secundarios de juegos que ya no están disponibles
            juegos_a_desactivar_secundario = Juego.objects.filter(
                tiene_secundario=True
            ).exclude(id__in=secundarios_disponibles_ids)
            
            for juego in juegos_a_desactivar_secundario:
                juego.precio_secundario = None
                juego.recargo_secundario = None
                juego.tiene_secundario = False
                juego.save()
            
            desactivados_secundario_count = juegos_a_desactivar_secundario.count()
            
            # Desactivar juegos "solo secundarios" que ya no están disponibles
            juegos_solo_secundarios = Juego.objects.filter(
                es_solo_secundario=True
            ).exclude(id__in=secundarios_disponibles_ids)
            
            desactivados_solo_secundario = juegos_solo_secundarios.update(disponible=False)
        else:
            desactivados_secundario_count = 0
            desactivados_solo_secundario = 0
        
        # Verificar portadas faltantes
        if juegos_procesados:
            portadas_faltantes = self.verificar_portadas_faltantes(juegos_procesados)
            
            if portadas_faltantes:
                self.stdout.write(self.style.WARNING(f'\n{'='*60}'))
                self.stdout.write(self.style.WARNING('🖼️  PORTADAS FALTANTES DETECTADAS'))
                self.stdout.write(self.style.WARNING(f'{"="*60}'))
                
                for i, portada in enumerate(portadas_faltantes, 1):
                    self.stdout.write(self.style.WARNING(f'\n{i}. {portada["juego"]}'))
                    self.stdout.write(f'   Consola: {portada["consola"]}')
                    self.stdout.write(f'   Imagen actual: {portada["imagen_actual"]}')
                    self.stdout.write(f'   📝 Nombres sugeridos para la portada:')
                    for sugerencia in portada['nombres_sugeridos']:
                        self.stdout.write(f'      - {sugerencia}')
        
        # RESUMEN FINAL
        self.stdout.write(self.style.SUCCESS(f'\n{"="*60}'))
        self.stdout.write(self.style.SUCCESS('📊 RESUMEN DE ACTUALIZACIÓN DE SECUNDARIOS'))
        self.stdout.write(self.style.SUCCESS(f'{"="*60}'))
        self.stdout.write(self.style.SUCCESS(f'✅ Juegos con precio secundario agregado: {actualizados_existentes}'))
        self.stdout.write(self.style.SUCCESS(f'🔄 Juegos reactivados: {reactivados}'))
        self.stdout.write(self.style.SUCCESS(f'⚡ Juegos convertidos a solo secundario: {convertidos_a_solo_secundario}'))
        self.stdout.write(self.style.WARNING(f'🆕 Juegos nuevos creados (solo secundarios): {creados_nuevos}'))
        self.stdout.write(self.style.ERROR(f'🔴 Precios secundarios eliminados: {desactivados_secundario_count}'))
        self.stdout.write(self.style.ERROR(f'🔴 Secundarios puros desactivados: {desactivados_solo_secundario}'))
        self.stdout.write(self.style.WARNING(f'⏭️  Juegos omitidos (no disponibles en CSV): {omitidos_no_disponibles}'))
        self.stdout.write(self.style.WARNING(f'🔍 Juegos no encontrados en BD: {len(no_encontrados)}'))
        
        if no_encontrados:
            self.stdout.write(self.style.WARNING("\nJuegos no encontrados en BD:"))
            for nombre in no_encontrados[:10]:
                self.stdout.write(f"  - {nombre}")
        
        if juegos_procesados:
            portadas_faltantes_count = len(self.verificar_portadas_faltantes(juegos_procesados))
            self.stdout.write(self.style.WARNING(f'🖼️  Portadas faltantes detectadas: {portadas_faltantes_count}'))
        
        if errores:
            self.stdout.write(self.style.ERROR(f'\n❌ ERRORES: {len(errores)}'))
            for error in errores[:10]:
                self.stdout.write(f"  - {error}")