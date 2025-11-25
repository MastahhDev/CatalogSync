import csv
import os
import re
import difflib
import unicodedata
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import models
from catalog.models import Juego
from difflib import SequenceMatcher

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
            help='Nombre de la columna con disponibilidad (0=False, vacío=True)'
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

    def extraer_version(self, nombre):
        """Extrae información de versión/idioma del nombre"""
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
        """Limpia el nombre pero MANTIENE información de versión importante"""
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

    def buscar_juego_exacto(self, nombre_csv):
        """Busca el juego con coincidencia EXACTA incluyendo versión"""
        nombre_base, version_csv = self.limpiar_nombre_base(nombre_csv)
        
        self.stdout.write(f"\n🔍 Buscando: '{nombre_csv}'")
        self.stdout.write(f"   Nombre base: '{nombre_base}'")
        self.stdout.write(f"   Versión detectada: {version_csv}")
        
        # Obtener todos los PS5
        juegos_ps5 = Juego.objects.filter(consola='ps5')
        
        candidatos = []
        
        for juego in juegos_ps5:
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

    def calcular_recargo(self, precio):
        """Calcula el recargo como 10% del precio"""
        if precio <= 0:
            return Decimal('0.0')
        
        recargo = precio + (precio * Decimal('0.10'))
        return recargo.quantize(Decimal('0.01'))

    def buscar_imagen_existente(self, nombre_juego):
        """Busca la imagen correspondiente al juego"""
        return self.buscar_imagen(nombre_juego)

    def buscar_imagen(self, nombre_juego):
        """Busca la imagen correspondiente al juego"""
        nombre_base = self.generar_nombre_imagen_simple(nombre_juego)
        img_dir = os.path.join(settings.BASE_DIR, 'static', 'img')
        
        if not os.path.exists(img_dir):
            return "img/default.jpg"
        
        archivos_existentes = [f for f in os.listdir(img_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        
        if nombre_base in archivos_existentes:
            return f"img/{nombre_base}"
        
        archivos_lower = [f.lower() for f in archivos_existentes]
        if nombre_base.lower() in archivos_lower:
            archivo_real = archivos_existentes[archivos_lower.index(nombre_base.lower())]
            return f"img/{archivo_real}"
        
        return "img/default.jpg"

    def generar_nombre_imagen_simple(self, nombre_juego):
        """Genera nombre de imagen de forma simple y directa"""
        nombre = self.quitar_acentos(nombre_juego.lower())
        
        if 'ps4' in nombre:
            consola = 'ps4'
        else:
            consola = 'ps5'
        
        nombre = nombre.replace(' ps4', '').replace(' ps5', '').replace('(ps5)', '').replace('(ps4)', '').strip()
        nombre = nombre.replace("'", "").replace(":", "").replace("&", "and")
        nombre = nombre.replace(" ", "_")
        
        return f"{nombre}_{consola}.jpg"

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

    def handle(self, *args, **options):
        csv_filename = options['file']
        csv_path = os.path.join(settings.BASE_DIR, csv_filename)
        col_nombre = options['columna_nombre']
        col_precio = options['columna_precio']
        col_disponible = options['columna_disponible']
        
        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f'No se encontro {csv_path}'))
            return
        
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
                
                if col_nombre not in csv_reader.fieldnames:
                    self.stdout.write(self.style.ERROR(f'No se encontro la columna "{col_nombre}"'))
                    return
                
                if col_precio not in csv_reader.fieldnames:
                    self.stdout.write(self.style.ERROR(f'No se encontro la columna "{col_precio}"'))
                    return
                
                tiene_columna_disponible = col_disponible in csv_reader.fieldnames
                
                for linea_num, row in enumerate(csv_reader, start=2):
                    try:
                        nombre_csv = row.get(col_nombre, '').strip()
                        if not nombre_csv or len(nombre_csv) < 3:
                            continue
                        
                        # Determinar disponibilidad
                        if tiene_columna_disponible:
                            disponible = self.determinar_disponibilidad(row.get(col_disponible, ''))
                        else:
                            disponible = True
                        
                        # Buscar juego con coincidencia exacta
                        juego = self.buscar_juego_exacto(nombre_csv)
                        
                        if not juego:
                            no_encontrados.append(nombre_csv)
                            self.stdout.write(self.style.WARNING(f'NO ENCONTRADO: {nombre_csv}'))
                            continue
                        
                        # Obtener y limpiar precio
                        precio = self.limpiar_precio(row.get(col_precio, ''))
                        recargo = self.calcular_recargo(precio)
                        
                        # Actualizar
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
                        
                        estado = "NO DISPONIBLE" if not disponible else "OK"
                        self.stdout.write(
                            self.style.SUCCESS(f'✓ {estado}: {juego.nombre} - ${precio}')
                        )
                        
                    except Exception as e:
                        error_msg = f'Linea {linea_num}: {str(e)}'
                        errores.append(error_msg)
                        self.stdout.write(self.style.ERROR(error_msg))
                        continue
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
            return
        
        # Desactivar juegos no en stock
        if juegos_en_stock_ids:
            juegos_a_desactivar = Juego.objects.filter(consola='ps5').exclude(id__in=juegos_en_stock_ids)
            desactivados_count = juegos_a_desactivar.update(disponible=False)
        else:
            desactivados_count = 0
        
        # Resultados
        self.stdout.write(self.style.SUCCESS(f'\n{"="*60}'))
        self.stdout.write(self.style.SUCCESS(f'ACTUALIZADOS: {actualizados}'))
        self.stdout.write(self.style.SUCCESS(f'DESACTIVADOS: {desactivados_count}'))
        self.stdout.write(self.style.WARNING(f'DESACTIVADOS (por CSV): {desactivados_por_csv}'))
        self.stdout.write(self.style.WARNING(f'NO ENCONTRADOS: {len(no_encontrados)}'))
        
        if no_encontrados:
            self.stdout.write(self.style.WARNING("\nJuegos no encontrados en BD:"))
            for nombre in no_encontrados[:20]:
                self.stdout.write(f"  - {nombre}")
        
        self.generar_reporte_portadas_no_encontradas(actualizados)