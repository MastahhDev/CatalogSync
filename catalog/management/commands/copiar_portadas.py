import csv
import os
import re
import shutil
from django.core.management.base import BaseCommand
from django.conf import settings
from pathlib import Path

class Command(BaseCommand):
    help = 'Busca y copia portadas de juegos PS4 desde el CSV a una carpeta destino'

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
            '--carpeta-destino',
            type=str,
            default='portadas_ps4_encontradas',
            help='Carpeta donde copiar las portadas encontradas'
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
            r'\bespañol\b', r'\bspanish\b', r'\bespaol\b', r'\bespaa\b',
            
            # Ediciones (EXCEPTO definitive edition que se mantiene)
            r'\bdeluxe\s+edition\b', r'\bgold\s+edition\b', r'\bstandard\s+edition\b',
            r'\bspecial\s+edition\b', r'\bcollector\'s\s+edition\b', r'\bultimate\s+edition\b',
            r'\bpremium\s+edition\b', r'\bcomplete\s+edition\b', r'\bgame\s+of\s+the\s+year\b',
            r'\bgoty\b', r'\bedición\s+deluxe\b', r'\bedición\s+gold\b',
            r'\bedición\s+estándar\b', r'\bedición\s+especial\b', r'\blatino\b',
            
            # Palabras generales a eliminar
            r'\bversion\b', r'\bedicion\b', r'\bdigital\b', r'\bfisico\b',
            r'\bphysical\b', r'\bdownload\b', r'\bdescarga\b', r'\bdeluxe\b', r'\bdeadman\s+edition\b',
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
        
        return nombre_archivo

    def buscar_imagen(self, nombre_juego, img_dir, archivos_existentes, archivos_lower):
        """Busca la imagen correspondiente al juego"""
        # Generar nombre base
        nombre_base = self.generar_nombre_imagen_simple(nombre_juego)
        
        # Buscar coincidencia exacta
        if nombre_base in archivos_existentes:
            return nombre_base
        
        # Buscar coincidencia insensible a mayúsculas
        if nombre_base.lower() in archivos_lower:
            archivo_real = archivos_existentes[archivos_lower.index(nombre_base.lower())]
            return archivo_real
        
        return None

    def handle(self, *args, **options):
        csv_filename = options['file']
        csv_path = os.path.join(settings.BASE_DIR, csv_filename)
        col_nombre = options['columna_nombre']
        carpeta_destino = options['carpeta_destino']
        
        # Crear carpeta destino
        destino_path = os.path.join(settings.BASE_DIR, carpeta_destino)
        os.makedirs(destino_path, exist_ok=True)
        
        # Directorio de imágenes
        img_dir = os.path.join(settings.BASE_DIR, 'static', 'img')
        
        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f'No se encontró {csv_path}'))
            return
        
        if not os.path.exists(img_dir):
            self.stdout.write(self.style.ERROR(f'No se encontró el directorio {img_dir}'))
            return
        
        # Listar archivos existentes una sola vez
        archivos_existentes = [f for f in os.listdir(img_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        archivos_lower = [f.lower() for f in archivos_existentes]
        
        self.stdout.write(self.style.SUCCESS(f'📁 Archivos de imagen disponibles: {len(archivos_existentes)}'))
        self.stdout.write(self.style.SUCCESS(f'📂 Carpeta destino: {destino_path}\n'))
        
        encontradas = []
        no_encontradas = []
        copiadas = 0
        
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as file:
                content = file.read()
                content = content.replace('�', '').replace('"', '').replace("'", "")
                
                csv_reader = csv.DictReader(content.splitlines(), delimiter=';')
                
                if csv_reader.fieldnames:
                    csv_reader.fieldnames = [name.strip().upper() for name in csv_reader.fieldnames]
                
                if col_nombre not in csv_reader.fieldnames:
                    self.stdout.write(self.style.ERROR(f'No se encontró la columna "{col_nombre}"'))
                    self.stdout.write(f'Columnas disponibles: {csv_reader.fieldnames}')
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
                        
                        # Buscar imagen
                        imagen_encontrada = self.buscar_imagen(
                            nombre_busqueda, 
                            img_dir, 
                            archivos_existentes, 
                            archivos_lower
                        )
                        
                        if imagen_encontrada:
                            # Copiar imagen a carpeta destino
                            origen = os.path.join(img_dir, imagen_encontrada)
                            destino = os.path.join(destino_path, imagen_encontrada)
                            
                            try:
                                shutil.copy2(origen, destino)
                                encontradas.append({
                                    'original': nombre_sucio,
                                    'limpio': nombre_busqueda,
                                    'imagen': imagen_encontrada
                                })
                                copiadas += 1
                                self.stdout.write(self.style.SUCCESS(
                                    f'✅ {nombre_busqueda[:50]:<50} -> {imagen_encontrada}'
                                ))
                            except Exception as e:
                                self.stdout.write(self.style.ERROR(
                                    f'Error copiando {imagen_encontrada}: {str(e)}'
                                ))
                        else:
                            no_encontradas.append({
                                'original': nombre_sucio,
                                'limpio': nombre_busqueda,
                                'imagen_esperada': self.generar_nombre_imagen_simple(nombre_busqueda)
                            })
                            self.stdout.write(self.style.WARNING(
                                f'❌ {nombre_busqueda[:50]:<50} -> NO ENCONTRADA'
                            ))
                        
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'Error en línea {linea_num}: {str(e)}'))
                        continue
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error leyendo CSV: {str(e)}'))
            return
        
        # REPORTE FINAL
        self.stdout.write(self.style.SUCCESS(f'\n{"="*80}'))
        self.stdout.write(self.style.SUCCESS(f'📊 RESUMEN'))
        self.stdout.write(self.style.SUCCESS(f'{"="*80}'))
        self.stdout.write(self.style.SUCCESS(f'✅ Portadas encontradas y copiadas: {copiadas}'))
        self.stdout.write(self.style.WARNING(f'❌ Portadas NO encontradas: {len(no_encontradas)}'))
        self.stdout.write(self.style.SUCCESS(f'📂 Destino: {destino_path}\n'))
        
        # Detalle de NO encontradas
        if no_encontradas:
            self.stdout.write(self.style.WARNING(f'\n{"🚨 PORTADAS NO ENCONTRADAS":=^80}'))
            self.stdout.write(self.style.WARNING(f'\nTotal: {len(no_encontradas)} juegos sin portada\n'))
            
            for item in no_encontradas:
                self.stdout.write(f"📌 Juego: {item['limpio']}")
                self.stdout.write(f"   Original: {item['original']}")
                self.stdout.write(f"   Nombre esperado: {item['imagen_esperada']}\n")
        
        # Lista de encontradas (opcional, comentado para no saturar)
        """
        if encontradas:
            self.stdout.write(self.style.SUCCESS(f'\n{"✅ PORTADAS ENCONTRADAS":=^80}\n'))
            for item in encontradas:
                self.stdout.write(f"✓ {item['limpio']} -> {item['imagen']}")
        """
        
        self.stdout.write(self.style.SUCCESS(f'\n✨ Proceso completado'))