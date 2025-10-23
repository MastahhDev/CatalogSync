import csv
import os
import re
from django.core.management.base import BaseCommand
from django.conf import settings
from catalog.models import Juego

class Command(BaseCommand):
    help = 'Verifica qué juegos del CSV no están en la base de datos'

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
            default='NOMBRE',
            help='Nombre de la columna con el nombre del juego'
        )

    def limpiar_nombre_para_comparacion(self, nombre):
        """Limpia el nombre para hacer comparaciones uniformes"""
        if not nombre:
            return ""
        
        # Convertir a minúsculas
        nombre = nombre.lower()
        
        # Quitar emojis y caracteres especiales
        nombre = re.sub(r'[^\x00-\x7F]+', '', nombre)
        
        # Quitar símbolos
        nombre = nombre.replace('®', '').replace('™', '').replace('©', '')
        nombre = nombre.replace(':', '').replace('#', '').replace('-', ' ')
        
        # Quitar precio
        nombre = re.sub(r'\$\s*[\d.,]+', '', nombre)
        
        # Patrones a eliminar
        patrones_a_eliminar = [
            r'\bespañol\s+españa\b', r'\bespañol\s+latino\b', r'\binglés\b',
            r'\benglish\b', r'\bsubtitulado\b', r'\bsubtitulada\b',
            r'\bespañol\b', r'\bspanish\b', r'\bespaol\b', r'\bespaa\b',
            r'\bdeluxe\s+edition\b', r'\bgold\s+edition\b', r'\bstandard\s+edition\b',
            r'\bspecial\s+edition\b', r'\bcollector\'s\s+edition\b', r'\bultimate\s+edition\b',
            r'\bpremium\s+edition\b', r'\bcomplete\s+edition\b', r'\bgame\s+of\s+the\s+year\b',
            r'\bgoty\b', r'\bedición\s+deluxe\b', r'\bedición\s+gold\b',
            r'\bedición\s+estándar\b', r'\bedición\s+especial\b', r'\blatino\b',
            r'\bversion\b', r'\bedicion\b', r'\bdigital\b', r'\bfisico\b',
            r'\bphysical\b', r'\bdownload\b', r'\bdescarga\b', r'\bdeluxe\b',
            r'\bps4\b', r'\bps5\b',
        ]
        
        for patron in patrones_a_eliminar:
            nombre = re.sub(patron, '', nombre, flags=re.IGNORECASE)
        
        # Limpiar espacios y puntuación
        nombre = re.sub(r'\(\s*\)', '', nombre)
        nombre = re.sub(r'\[\s*\]', '', nombre)
        nombre = re.sub(r'\s+', ' ', nombre)
        nombre = nombre.strip()
        nombre = re.sub(r'[.,;\s]+$', '', nombre)
        
        return nombre

    def handle(self, *args, **options):
        csv_filename = options['file']
        csv_path = os.path.join(settings.BASE_DIR, csv_filename)
        col_nombre = options['columna_nombre']
        
        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f'❌ No se encontró {csv_path}'))
            return
        
        # Leer juegos del CSV
        juegos_csv = []
        
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as file:
                content = file.read()
                content = content.replace('�', '').replace('"', '').replace("'", "")
                
                csv_reader = csv.DictReader(content.splitlines(), delimiter=';')
                
                if csv_reader.fieldnames:
                    csv_reader.fieldnames = [name.strip().upper() for name in csv_reader.fieldnames]
                
                if col_nombre not in csv_reader.fieldnames:
                    self.stdout.write(self.style.ERROR(f'❌ No se encontró la columna "{col_nombre}"'))
                    self.stdout.write(f'Columnas disponibles: {csv_reader.fieldnames}')
                    return
                
                for row in csv_reader:
                    nombre_original = row.get(col_nombre, '').strip()
                    if nombre_original and len(nombre_original) > 2:
                        nombre_limpio = self.limpiar_nombre_para_comparacion(nombre_original)
                        if nombre_limpio:
                            juegos_csv.append({
                                'original': nombre_original,
                                'limpio': nombre_limpio
                            })
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error leyendo CSV: {str(e)}'))
            return
        
        # Obtener juegos de la BD
        try:
            juegos_bd = Juego.objects.filter(consola='ps5').values_list('nombre', flat=True)
            juegos_bd_limpios = {self.limpiar_nombre_para_comparacion(titulo): titulo for titulo in juegos_bd}
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error consultando BD: {str(e)}'))
            return
        
        # Comparar
        faltantes = []
        encontrados = []
        
        for juego_csv in juegos_csv:
            nombre_limpio = juego_csv['limpio']
            
            if nombre_limpio in juegos_bd_limpios:
                encontrados.append({
                    'csv': juego_csv['original'],
                    'bd': juegos_bd_limpios[nombre_limpio]
                })
            else:
                faltantes.append(juego_csv)
        
        # REPORTE
        self.stdout.write(self.style.SUCCESS(f'\n{"="*80}'))
        self.stdout.write(self.style.SUCCESS(f'📊 ANÁLISIS DE JUEGOS PS5'))
        self.stdout.write(self.style.SUCCESS(f'{"="*80}'))
        self.stdout.write(f'📁 Juegos en CSV: {len(juegos_csv)}')
        self.stdout.write(f'💾 Juegos en BD (PS5): {len(juegos_bd_limpios)}')
        self.stdout.write(self.style.SUCCESS(f'✅ Juegos encontrados en BD: {len(encontrados)}'))
        self.stdout.write(self.style.ERROR(f'❌ Juegos NO encontrados en BD: {len(faltantes)}'))
        self.stdout.write(f'{"="*80}\n')
        
        # Mostrar faltantes
        if faltantes:
            self.stdout.write(self.style.ERROR(f'🚨 JUEGOS FALTANTES EN LA BASE DE DATOS'))
            self.stdout.write(self.style.ERROR(f'{"="*80}\n'))
            
            for i, juego in enumerate(faltantes, 1):
                self.stdout.write(f'{i}. {juego["original"]}')
                self.stdout.write(f'   (Normalizado: {juego["limpio"]})\n')
        
        # Opción: Mostrar algunos encontrados como verificación
        if encontrados and len(encontrados) <= 10:
            self.stdout.write(self.style.SUCCESS(f'\n✅ EJEMPLOS DE JUEGOS ENCONTRADOS'))
            self.stdout.write(self.style.SUCCESS(f'{"="*80}\n'))
            for item in encontrados[:10]:
                self.stdout.write(f'✓ CSV: {item["csv"]}')
                self.stdout.write(f'  BD:  {item["bd"]}\n')
        
        # Diferencia esperada vs real
        diferencia = len(juegos_csv) - len(juegos_bd_limpios)
        if diferencia != 0:
            self.stdout.write(self.style.WARNING(f'\n⚠️  Diferencia: {abs(diferencia)} juegos'))
            if diferencia > 0:
                self.stdout.write(self.style.WARNING(f'   El CSV tiene {diferencia} juegos más que la BD'))
            else:
                self.stdout.write(self.style.WARNING(f'   La BD tiene {abs(diferencia)} juegos más que el CSV'))
        
        self.stdout.write(self.style.SUCCESS(f'\n✨ Análisis completado'))