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
        parser.add_argument('--file', type=str, default='stock_secus.csv', help='CSV con juegos secundarios')
        parser.add_argument('--columna-nombre', type=str, default='JUEGOS', help='Nombre de la columna con el nombre del juego')
        parser.add_argument('--columna-precio', type=str, default='PRECIO', help='Nombre de la columna con el precio')
        parser.add_argument('--columna-disponible', type=str, default='DISPONIBLE', help='Nombre de la columna con disponibilidad')
        parser.add_argument('--consola', type=str, default='ps4', help='Consola (ps4 o ps5)')
        parser.add_argument('--solo-actualizar', action='store_true', help='Solo actualizar juegos existentes')
        parser.add_argument('--mostrar-portadas-faltantes', action='store_true', help='Mostrar lista de portadas faltantes')
        parser.add_argument('--debug', action='store_true', help='Mostrar información de depuración')
        parser.add_argument('--corregir-precios', action='store_true', help='Corregir juegos secundarios con precios en campos equivocados')
        parser.add_argument('--dry-run', action='store_true', help='Simular sin hacer cambios reales')

    def corregir_precios_secundarios(self, dry_run=False):
        """Corrige juegos secundarios que tienen el precio en el campo equivocado"""
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
                
                if not dry_run:
                    precio_original = juego.precio
                    recargo_original = juego.recargo
                    
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

    def extraer_version(self, nombre):
        """Extrae información de versión/idioma del nombre - IGUAL QUE PS5"""
        versiones = {
            'subtitulado': ['subtitulado', 'subtitulada', '(subtitulado)'],
            'español_latino': ['espanol latino', 'español latino', 'latino'],
            'español_españa': ['espanol espana', 'español españa'],
            'ingles': ['english', 'ingles', 'inglés']
        }
        
        nombre_lower = nombre.lower()
        
        for tipo, keywords in versiones.items():
            for keyword in keywords:
                if keyword in nombre_lower:
                    return tipo
        
        return None

    def limpiar_nombre_base(self, nombre):
        """Limpia el nombre pero MANTIENE información de versión importante - IGUAL QUE PS5"""
        if not nombre:
            return "", None

        # Extraer versión ANTES de limpiar
        version = self.extraer_version(nombre)
        
        # Quitar acentos
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
        
        # PATRONES A FILTRAR (pero SIN quitar idiomas/versiones)
        patrones_a_eliminar = [
            # Ediciones
            r'\bdeluxe\s+edition\b', r'\bgold\s+edition\b', r'\bstandard\s+edition\b',
            r'\bspecial\s+edition\b', r'\bcollector\'s\s+edition\b', r'\bultimate\s+edition\b',
            r'\bpremium\s+edition\b', r'\bcomplete\s+edition\b', r'\bgame\s+of\s+the\s+year\b',
            r'\bgoty\b', r'\bedicion\s+deluxe\b', r'\bedicion\s+gold\b',
            r'\bedicion\s+estandar\b', r'\bedicion\s+especial\b',
            
            # Palabras generales
            r'\bversion\b', r'\bedicion\b', r'\bdigital\b', r'\bfisico\b',
            r'\bphysical\b', r'\bdownload\b', r'\bdescarga\b', r'\b(ps5)\b', r'\b(ps4)\b',
            r'\bsecundario\b',
        ]
        
        # Aplicar patrones
        for patron in patrones_a_eliminar:
            nombre = re.sub(patron, '', nombre, flags=re.IGNORECASE)
        
        # Limpiar espacios
        nombre = re.sub(r'\(\s*\)', '', nombre)
        nombre = re.sub(r'\[\s*\]', '', nombre)
        nombre = re.sub(r'\s+', ' ', nombre)
        nombre = nombre.strip()
        nombre = re.sub(r'[.,;\s]+$', '', nombre)
        
        return nombre, version

    def buscar_juego_exacto(self, nombre_csv, consola):
        """Busca el juego con coincidencia EXACTA incluyendo versión - IGUAL QUE PS5"""
        nombre_base, version_csv = self.limpiar_nombre_base(nombre_csv)
        
        self.stdout.write(f"\n🔍 Buscando: '{nombre_csv}'")
        self.stdout.write(f"   Nombre base: '{nombre_base}'")
        self.stdout.write(f"   Versión detectada: {version_csv}")
        
        # Obtener todos los juegos de la consola
        juegos_consola = Juego.objects.filter(consola=consola)
        
        candidatos = []
        
        for juego in juegos_consola:
            nombre_bd, version_bd = self.limpiar_nombre_base(juego.nombre)
            
            # Calcular similitud del nombre base
            ratio_nombre = SequenceMatcher(None, nombre_base.lower(), nombre_bd.lower()).ratio()
            
            # El nombre debe ser MUY similar
            if ratio_nombre < 0.85:
                continue
            
            # Calcular score de versión
            version_match = 0.0
            if version_csv == version_bd:
                version_match = 1.0  # Versión exacta
            elif version_csv is None and version_bd is None:
                version_match = 1.0  # Ambos sin versión específica
            elif version_csv is None or version_bd is None:
                version_match = 0.3  # Uno tiene versión, otro no
            else:
                version_match = 0.0  # Versiones diferentes
            
            # Score combinado (70% nombre, 30% versión)
            score_total = (ratio_nombre * 0.7) + (version_match * 0.3)
            
            candidatos.append({
                'juego': juego,
                'score': score_total,
                'ratio_nombre': ratio_nombre,
                'version_bd': version_bd,
                'nombre_bd': nombre_bd
            })
            
            if ratio_nombre > 0.85:
                self.stdout.write(
                    f"   Candidato: '{juego.nombre}' | "
                    f"Nombre: {ratio_nombre:.2f} | "
                    f"Versión: {version_bd} | "
                    f"Score: {score_total:.2f}"
                )
        
        # Ordenar por score
        candidatos.sort(key=lambda x: x['score'], reverse=True)
        
        if not candidatos:
            self.stdout.write(self.style.ERROR("   ✗ No se encontraron candidatos"))
            return None
        
        mejor = candidatos[0]
        
        # Requerir score mínimo de 0.90 para aceptar
        if mejor['score'] >= 0.90:
            self.stdout.write(
                self.style.SUCCESS(
                    f"   ✓ MATCH: '{mejor['juego'].nombre}' (Score: {mejor['score']:.2f})"
                )
            )
            return mejor['juego']
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"   ⚠ Score muy bajo: {mejor['score']:.2f} - RECHAZADO"
                )
            )
            return None

    def determinar_disponibilidad(self, disponible_str):
        """Determina la disponibilidad basada en el valor de la columna"""
        if disponible_str is None:
            return True
        
        disponible_str = str(disponible_str).strip()
        
        if disponible_str == '':
            return True
        
        if disponible_str.lower() in ['0', 'false', 'no', 'falso']:
            return False
        
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
        """Busca la imagen correspondiente al juego"""
        try:
            nombre = re.sub(r'\s*\(SECUNDARIO\)\s*', '', nombre_juego, flags=re.IGNORECASE)
            nombre = self.quitar_acentos(nombre.lower())
            
            nombre = nombre.replace(f' {consola}', '').replace(f'{consola}', '').strip()
            
            nombre = nombre.replace("'", "").replace(":", "").replace("&", "and")
            nombre = nombre.replace("+", "").replace("#", "").replace("!", "")
            nombre = nombre.replace("?", "").replace("*", "").replace("/", "")
            nombre = nombre.replace("\\", "").replace('"', "").replace("|", "")
            
            nombre_archivo1 = f"{nombre.replace(' ', '_')}_{consola}.jpg"
            nombre_archivo2 = f"{nombre.replace(' ', '')}_{consola}.jpg"
            
            palabras = [p for p in nombre.split() if len(p) > 2 and p not in ['the', 'and', 'del', 'de', 'la', 'el']]
            nombre_archivo3 = f"{'_'.join(palabras[:4])}_{consola}.jpg" if palabras else None
            
            img_dir = os.path.join(settings.BASE_DIR, 'static', 'img')
            
            if not os.path.exists(img_dir):
                return "img/default.jpg"
            
            archivos_existentes = [f for f in os.listdir(img_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            
            for nombre_archivo in [nombre_archivo1, nombre_archivo2, nombre_archivo3]:
                if nombre_archivo and os.path.exists(os.path.join(img_dir, nombre_archivo)):
                    return f"img/{nombre_archivo}"
            
            archivos_lower = [f.lower() for f in archivos_existentes]
            
            for nombre_archivo in [nombre_archivo1, nombre_archivo2, nombre_archivo3]:
                if nombre_archivo and nombre_archivo.lower() in archivos_lower:
                    archivo_real = archivos_existentes[archivos_lower.index(nombre_archivo.lower())]
                    return f"img/{archivo_real}"
            
            return "img/default.jpg"
            
        except Exception as e:
            return "img/default.jpg"

    def verificar_portadas_faltantes(self, juegos_procesados):
        """Verifica qué juegos no tienen portada y sugiere nombres de archivo"""
        portadas_faltantes = []
        
        for juego_info in juegos_procesados:
            imagen_actual = juego_info.get('imagen', '')
            
            if imagen_actual and imagen_actual != "img/default.jpg":
                continue
            
            nombres_sugeridos = self.generar_nombres_sugeridos(juego_info['nombre'], juego_info['consola'])
            
            portadas_faltantes.append({
                'juego': juego_info['nombre'],
                'consola': juego_info['consola'],
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
        
        return variaciones[:5]

    def handle(self, *args, **options):
        if options['corregir_precios']:
            dry_run = options['dry_run']
            corregidos, errores = self.corregir_precios_secundarios(dry_run)
            
            self.stdout.write(self.style.SUCCESS(f'\n{"="*60}'))
            self.stdout.write(self.style.SUCCESS('📊 RESUMEN DE CORRECCIÓN'))
            self.stdout.write(self.style.SUCCESS(f'{"="*60}'))
            
            if dry_run:
                self.stdout.write(self.style.WARNING(f'🔍 MODO SIMULACIÓN'))
            
            self.stdout.write(self.style.SUCCESS(f'✅ Juegos corregidos: {corregidos}'))
            
            if errores > 0:
                self.stdout.write(self.style.ERROR(f'❌ Errores: {errores}'))
            
            return
        
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
        secundarios_disponibles_ids = []
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
                        
                        if not disponible:
                            omitidos_no_disponibles += 1
                            if debug:
                                self.stdout.write(f"  ⏭️  OMITIDO (no disponible): {nombre_sucio}")
                            continue
                        
                        precio_str = row.get(col_precio, '').strip()
                        precio_secundario = self.limpiar_precio(precio_str)
                        recargo_secundario = self.calcular_recargo(precio_secundario)
                        
                        # Usar la nueva búsqueda inteligente que respeta versiones
                        juego_existente = self.buscar_juego_exacto(nombre_sucio, consola)
                        
                        if juego_existente:
                            if juego_existente.imagen == "img/default.jpg" or not juego_existente.imagen:
                                nueva_imagen = self.buscar_imagen(nombre_sucio, consola)
                                if nueva_imagen != "img/default.jpg":
                                    juego_existente.imagen = nueva_imagen
                            
                            if juego_existente.precio == Decimal('0.0'):
                                if "(SECUNDARIO)" not in juego_existente.nombre.upper():
                                    juego_existente.nombre = f"{juego_existente.nombre} (SECUNDARIO)"
                                
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
                            
                            juego_existente.precio_secundario = precio_secundario
                            juego_existente.recargo_secundario = recargo_secundario
                            juego_existente.save()
                            
                            secundarios_ids.append(juego_existente.id)
                            secundarios_disponibles_ids.append(juego_existente.id)
                            actualizados_existentes += 1
                            
                            juegos_procesados.append({
                                'nombre': juego_existente.nombre,
                                'consola': consola,
                                'imagen': juego_existente.imagen
                            })
                            
                            self.stdout.write(self.style.SUCCESS(
                                f'✅ AGREGADO PRECIO SECUNDARIO: {juego_existente.nombre} - ${precio_secundario}'
                            ))
                        
                        else:
                            if solo_actualizar:
                                self.stdout.write(self.style.WARNING(f'⏭️  OMITIDO: {nombre_sucio}'))
                                no_encontrados.append(nombre_sucio)
                                continue
                            
                            nombre_con_identificador = f"{nombre_sucio} (SECUNDARIO)"
                            imagen = self.buscar_imagen(nombre_sucio, consola)
                            
                            nuevo_juego = Juego.objects.create(
                                nombre=nombre_con_identificador,
                                precio=0,
                                recargo=0,
                                consola=consola,
                                disponible=True,
                                imagen=imagen,
                                es_solo_secundario=True,
                                precio_secundario=precio_secundario,
                                recargo_secundario=recargo_secundario,
                                tiene_secundario=False
                            )
                            
                            secundarios_ids.append(nuevo_juego.id)
                            secundarios_disponibles_ids.append(nuevo_juego.id)
                            creados_nuevos += 1
                            
                            juegos_procesados.append({
                                'nombre': nuevo_juego.nombre,
                                'consola': consola,
                                'imagen': nuevo_juego.imagen
                            })
                            
                            self.stdout.write(self.style.WARNING(
                                f'🆕 CREADO: {nuevo_juego.nombre} - ${precio_secundario}'
                            ))
                        
                    except Exception as e:
                        error_msg = f'Línea {linea_num}: {str(e)}'
                        errores.append(error_msg)
                        self.stdout.write(self.style.ERROR(error_msg))
                        continue
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
            return
        
        if secundarios_disponibles_ids:
            juegos_a_desactivar_secundario = Juego.objects.filter(
                tiene_secundario=True
            ).exclude(id__in=secundarios_disponibles_ids)
            
            for juego in juegos_a_desactivar_secundario:
                juego.precio_secundario = None
                juego.recargo_secundario = None
                juego.tiene_secundario = False
                juego.save()
            
            desactivados_secundario_count = juegos_a_desactivar_secundario.count()
            
            juegos_solo_secundarios = Juego.objects.filter(
                es_solo_secundario=True
            ).exclude(id__in=secundarios_disponibles_ids)
            
            desactivados_solo_secundario = juegos_solo_secundarios.update(disponible=False)
        else:
            desactivados_secundario_count = 0
            desactivados_solo_secundario = 0
        
        if juegos_procesados:
            portadas_faltantes = self.verificar_portadas_faltantes(juegos_procesados)
            
            if portadas_faltantes:
                self.stdout.write(self.style.WARNING(f'\n{"="*60}'))
                self.stdout.write(self.style.WARNING('🖼️  PORTADAS FALTANTES'))
                self.stdout.write(self.style.WARNING(f'{"="*60}'))
                
                for i, portada in enumerate(portadas_faltantes, 1):
                    self.stdout.write(self.style.WARNING(f'\n{i}. {portada["juego"]}'))
                    self.stdout.write(f'   📝 Nombres sugeridos:')
                    for sugerencia in portada['nombres_sugeridos']:
                        self.stdout.write(f'      - {sugerencia}')
        
        self.stdout.write(self.style.SUCCESS(f'\n{"="*60}'))
        self.stdout.write(self.style.SUCCESS('📊 RESUMEN'))
        self.stdout.write(self.style.SUCCESS(f'{"="*60}'))
        self.stdout.write(self.style.SUCCESS(f'✅ Actualizados: {actualizados_existentes}'))
        self.stdout.write(self.style.SUCCESS(f'🔄 Reactivados: {reactivados}'))
        self.stdout.write(self.style.SUCCESS(f'⚡ Convertidos: {convertidos_a_solo_secundario}'))
        self.stdout.write(self.style.WARNING(f'🆕 Creados: {creados_nuevos}'))
        self.stdout.write(self.style.ERROR(f'🔴 Desactivados (precios): {desactivados_secundario_count}'))
        self.stdout.write(self.style.ERROR(f'🔴 Desactivados (juegos): {desactivados_solo_secundario}'))
        self.stdout.write(self.style.WARNING(f'⏭️  Omitidos: {omitidos_no_disponibles}'))
        self.stdout.write(self.style.WARNING(f'🔍 No encontrados: {len(no_encontrados)}'))
        
        if no_encontrados and len(no_encontrados) <= 10:
            self.stdout.write(self.style.WARNING("\nNo encontrados:"))
            for nombre in no_encontrados:
                self.stdout.write(f"  - {nombre}")