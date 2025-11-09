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

    def limpiar_nombre_avanzado(self, nombre):
        """Limpia el nombre quitando idiomas, ediciones específicas, etc."""
        if not nombre:
            return ""
        
        nombre = self.quitar_acentos(nombre)
        nombre = re.sub(r'[^\x00-\x7F]+', '', nombre)
        nombre = nombre.replace('®', '').replace('™', '').replace('©', '')
        nombre = nombre.replace(':', '').replace('#', '').replace('-', ' ')
        nombre = re.sub(r'\$\s*[\d.,]+', '', nombre)
        nombre = re.sub(r'^[\'\"\#\-\s]+', '', nombre)
        
        patrones_a_eliminar = [
            r'\bespanol\s+espana\b', r'\bespanol\s+latino\b', r'\bingles\b',
            r'\benglish\b', r'\bsubtitulado\b', r'\bsubtitulada\b',
            r'\bespanol\b', r'\bspanish\b',
            r'\bdeluxe\s+edition\b', r'\bgold\s+edition\b', r'\bstandard\s+edition\b',
            r'\bspecial\s+edition\b', r'\bcollector\'s\s+edition\b', r'\bultimate\s+edition\b',
            r'\bpremium\s+edition\b', r'\bcomplete\s+edition\b', r'\bgame\s+of\s+the\s+year\b',
            r'\bgoty\b', r'\bedicion\s+deluxe\b', r'\bedicion\s+gold\b',
            r'\bedicion\s+estandar\b', r'\bedicion\s+especial\b', r'\blatino\b',
            r'\bversion\b', r'\bedicion\b', r'\bdigital\b', r'\bfisico\b',
            r'\bphysical\b', r'\bdownload\b', r'\bdescarga\b',
        ]
        
        for patron in patrones_a_eliminar:
            nombre = re.sub(patron, '', nombre, flags=re.IGNORECASE)
        
        nombre = re.sub(r'\(\s*\)', '', nombre)
        nombre = re.sub(r'\[\s*\]', '', nombre)
        nombre = re.sub(r'\s+', ' ', nombre)
        nombre = nombre.strip()
        nombre = re.sub(r'[.,;\s]+$', '', nombre)
        
        return nombre

    def determinar_disponibilidad(self, disponible_str):
        """Determina la disponibilidad basada en el valor de la columna"""
        if not disponible_str or disponible_str.strip() == '':
            return True
        
        disponible_str = str(disponible_str).strip().lower()
        
        if disponible_str in ['0', 'false', 'no', 'falso']:
            return False
        
        if disponible_str in ['1', 'true', 'si', 'verdadero']:
            return True
        
        return True

    def buscar_juego_similar(self, nombre_limpio, consola):
        """Busca juegos en la base de datos que coincidan aproximadamente - INCLUYE NO DISPONIBLES"""
        nombre_limpio_sin_secundario = re.sub(r'\s*\(SECUNDARIO\)\s*', '', nombre_limpio, flags=re.IGNORECASE).strip()
        nombre_sin_consola = nombre_limpio_sin_secundario.replace(f' {consola.upper()}', '').replace(f' {consola}', '').strip()
        
        # Buscar coincidencias exactas (incluyendo no disponibles)
        juegos_exactos = Juego.objects.filter(
            nombre__iexact=nombre_limpio_sin_secundario,
            consola=consola
        )
        
        if juegos_exactos.exists():
            juego = juegos_exactos.first()
            self.stdout.write(f"  ✓ Encontrado exacto (disponible={juego.disponible}): {juego.nombre}")
            return juego
        
        # Buscar por nombre sin consola (incluyendo no disponibles)
        juegos_sin_consola = Juego.objects.filter(
            nombre__icontains=nombre_sin_consola,
            consola=consola
        )
        
        if juegos_sin_consola.exists():
            juego = juegos_sin_consola.first()
            self.stdout.write(f"  ✓ Encontrado por nombre (disponible={juego.disponible}): {juego.nombre}")
            return juego
        
        # Limpiar también el nombre para búsqueda más flexible
        nombre_muy_limpio = self.limpiar_nombre_avanzado(nombre_sin_consola)
        
        if nombre_muy_limpio != nombre_sin_consola:
            juegos_muy_limpios = Juego.objects.filter(
                nombre__icontains=nombre_muy_limpio,
                consola=consola
            )
            
            if juegos_muy_limpios.exists():
                juego = juegos_muy_limpios.first()
                self.stdout.write(f"  ✓ Encontrado por nombre limpio (disponible={juego.disponible}): {juego.nombre}")
                return juego
        
        # Buscar por palabras clave (incluyendo no disponibles)
        palabras_clave = nombre_muy_limpio.split()[:4]
        query = None
        for palabra in palabras_clave:
            if len(palabra) > 3:
                if query is None:
                    query = models.Q(nombre__icontains=palabra)
                else:
                    query |= models.Q(nombre__icontains=palabra)
        
        if query:
            juegos_similares = Juego.objects.filter(query, consola=consola)
            
            if juegos_similares.exists():
                mejor_coincidencia = None
                mejor_ratio = 0.0

                for juego_candidato in juegos_similares:
                    nombre_juego_limpio = self.limpiar_nombre_avanzado(juego_candidato.nombre)
                    ratio = SequenceMatcher(None, nombre_muy_limpio.lower(), nombre_juego_limpio.lower()).ratio()

                    if ratio > mejor_ratio:
                        mejor_ratio = ratio
                        mejor_coincidencia = juego_candidato

                if mejor_ratio > 0.85:
                    self.stdout.write(f"  ✓ Encontrado por similitud {mejor_ratio:.2f} (disponible={mejor_coincidencia.disponible}): {mejor_coincidencia.nombre}")
                    return mejor_coincidencia
        
        self.stdout.write(f"  ✗ No encontrado en BD: {nombre_limpio_sin_secundario}")
        return None

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
        """Busca la imagen correspondiente al juego"""
        nombre = re.sub(r'\s*\(SECUNDARIO\)\s*', '', nombre_juego, flags=re.IGNORECASE)
        nombre = self.quitar_acentos(nombre.lower())
        nombre = nombre.replace(f' {consola}', '').strip()
        nombre = nombre.replace("'", "").replace(":", "").replace("&", "and")
        nombre = nombre.replace(" ", "_")
        nombre_archivo = f"{nombre}_{consola}.jpg"
        
        img_dir = os.path.join(settings.BASE_DIR, 'static', 'img')
        
        if os.path.exists(os.path.join(img_dir, nombre_archivo)):
            return f"img/{nombre_archivo}"
        
        archivos_existentes = [f for f in os.listdir(img_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        archivos_lower = [f.lower() for f in archivos_existentes]
        
        if nombre_archivo.lower() in archivos_lower:
            archivo_real = archivos_existentes[archivos_lower.index(nombre_archivo.lower())]
            return f"img/{archivo_real}"
        
        return "img/default.jpg"

    def verificar_portadas_faltantes(self, juegos_procesados):
        """Verifica qué juegos no tienen portada y sugiere nombres de archivo"""
        img_dir = os.path.join(settings.BASE_DIR, 'static', 'img')
        portadas_faltantes = []
        
        for juego_info in juegos_procesados:
            nombre_juego = juego_info['nombre']
            consola = juego_info['consola']
            imagen_actual = juego_info.get('imagen', '')
            
            # Si ya tiene imagen y no es default, saltar
            if imagen_actual and imagen_actual != "img/default.jpg":
                continue
            
            # Generar nombres sugeridos para portada
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
        # Limpiar el nombre para el archivo
        nombre_limpio = re.sub(r'\s*\(SECUNDARIO\)\s*', '', nombre_juego, flags=re.IGNORECASE)
        nombre_limpio = self.quitar_acentos(nombre_limpio.lower())
        nombre_limpio = nombre_limpio.replace(f' {consola}', '').strip()
        
        # Variaciones del nombre
        variaciones = []
        
        # 1. Nombre básico con consola
        basico = nombre_limpio.replace("'", "").replace(":", "").replace("&", "and")
        basico = basico.replace(" ", "_")
        variaciones.append(f"{basico}_{consola}.jpg")
        
        # 2. Nombre sin artículos
        sin_articulos = re.sub(r'\b(the|a|an|el|la|los|las|un|una|unos|unas)\b', '', nombre_limpio, flags=re.IGNORECASE)
        sin_articulos = re.sub(r'\s+', ' ', sin_articulos).strip()
        sin_articulos = sin_articulos.replace(" ", "_")
        variaciones.append(f"{sin_articulos}_{consola}.jpg")
        
        # 3. Nombre muy limpio (sin ediciones especiales)
        muy_limpio = re.sub(r'\b(deluxe|gold|standard|special|collector\'s|ultimate|premium|complete|edition|edicion|goty|game of the year)\b', '', nombre_limpio, flags=re.IGNORECASE)
        muy_limpio = re.sub(r'\s+', ' ', muy_limpio).strip()
        muy_limpio = muy_limpio.replace(" ", "_")
        if muy_limpio and muy_limpio != basico:
            variaciones.append(f"{muy_limpio}_{consola}.jpg")
        
        # 4. Solo palabras clave (primeras 3-4 palabras)
        palabras = nombre_limpio.split()
        if len(palabras) > 3:
            clave = "_".join(palabras[:3])
            variaciones.append(f"{clave}_{consola}.jpg")
        
        return variaciones[:5]  # Máximo 5 sugerencias

    def handle(self, *args, **options):
        csv_filename = options['file']
        csv_path = os.path.join(settings.BASE_DIR, csv_filename)
        col_nombre = options['columna_nombre']
        col_precio = options['columna_precio']
        col_disponible = options['columna_disponible']
        consola = options['consola'].lower()
        solo_actualizar = options['solo_actualizar']
        
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
        juegos_procesados = []  # ⭐ NUEVO: Para trackear juegos procesados
        
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
                            disponible_str = row.get(col_disponible, '').strip()
                            disponible = self.determinar_disponibilidad(disponible_str)
                        else:
                            disponible = True
                        
                        if not disponible:
                            omitidos_no_disponibles += 1
                            self.stdout.write(self.style.WARNING(f'⏭️  OMITIDO (no disponible): {nombre_sucio}'))
                            continue
                        
                        nombre_limpio = self.limpiar_nombre_avanzado(nombre_sucio)
                        
                        if not nombre_limpio or len(nombre_limpio) < 3:
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
                        
                        self.stdout.write(f"\n{'='*60}")
                        self.stdout.write(f"PROCESANDO: '{nombre_sucio}' -> '{nombre_busqueda}'")
                        
                        precio_str = row.get(col_precio, '').strip()
                        precio_secundario = self.limpiar_precio(precio_str)
                        recargo_secundario = self.calcular_recargo(precio_secundario)
                        
                        juego_existente = self.buscar_juego_similar(nombre_busqueda, consola_real)
                        
                        if juego_existente:
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
                            actualizados_existentes += 1
                            
                            # ⭐ NUEVO: Agregar a juegos procesados para verificación de portadas
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
                                continue
                            
                            nombre_con_identificador = f"{nombre_busqueda} (SECUNDARIO)"
                            imagen = self.buscar_imagen(nombre_busqueda, consola_real)
                            
                            nuevo_juego = Juego.objects.create(
                                nombre=nombre_con_identificador,
                                precio=precio_secundario,
                                recargo=recargo_secundario,
                                consola=consola_real,
                                disponible=True,
                                imagen=imagen,
                                es_solo_secundario=True,
                                precio_secundario=None,
                                recargo_secundario=None,
                                tiene_secundario=False
                            )
                            
                            secundarios_ids.append(nuevo_juego.id)
                            creados_nuevos += 1
                            
                            # ⭐ NUEVO: Agregar a juegos procesados para verificación de portadas
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
        
        # Desactivar secundarios que ya no están en stock
        if secundarios_ids:
            juegos_a_desactivar_secundario = Juego.objects.filter(
                tiene_secundario=True
            ).exclude(id__in=secundarios_ids)
            
            for juego in juegos_a_desactivar_secundario:
                juego.precio_secundario = None
                juego.recargo_secundario = None
                juego.tiene_secundario = False
                juego.save()
            
            desactivados_secundario_count = juegos_a_desactivar_secundario.count()
            
            juegos_solo_secundarios = Juego.objects.filter(
                es_solo_secundario=True
            ).exclude(id__in=secundarios_ids)
            
            desactivados_solo_secundario = juegos_solo_secundarios.update(disponible=False)
        else:
            desactivados_secundario_count = 0
            desactivados_solo_secundario = 0
        
        # ⭐ CAMBIO: Verificar portadas faltantes SIEMPRE (sin condición de mostrar_portadas)
        if juegos_procesados:
            portadas_faltantes = self.verificar_portadas_faltantes(juegos_procesados)
            
            if portadas_faltantes:
                self.stdout.write(self.style.WARNING(f'\n{"="*60}'))
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
        
        # ⭐ CAMBIO: Mostrar siempre el conteo de portadas faltantes
        if juegos_procesados:
            portadas_faltantes_count = len(self.verificar_portadas_faltantes(juegos_procesados))
            self.stdout.write(self.style.WARNING(f'🖼️  Portadas faltantes detectadas: {portadas_faltantes_count}'))
        
        if errores:
            self.stdout.write(self.style.ERROR(f'\n❌ ERRORES: {len(errores)}'))
            for error in errores[:10]:
                self.stdout.write(f"  - {error}")