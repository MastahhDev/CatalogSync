# catalog/management/commands/actualizar_ps5.py
import csv
import os
from django.core.management.base import BaseCommand
from django.conf import settings
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

    def handle(self, *args, **options):
        csv_filename = options['file']
        csv_path = os.path.join(settings.BASE_DIR, csv_filename)
        
        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f'No se encontro {csv_path}'))
            return
        
        # Marcar todos los PS5 como NO disponibles
        Juego.objects.filter(consola='ps5').update(disponible=False)
        self.stdout.write(self.style.WARNING('Todos los PS5 marcados como no disponibles'))
        
        actualizados = 0
        creados = 0
        errores = []
        
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as file:
                csv_reader = csv.DictReader(file)
                
                if csv_reader.fieldnames:
                    csv_reader.fieldnames = [name.strip().lower() for name in csv_reader.fieldnames]
                
                for linea_num, row in enumerate(csv_reader, start=2):
                    try:
                        nombre = row.get('nombre', '').strip()
                        if not nombre:
                            continue
                        
                        try:
                            precio = float(row.get('precio', '0').replace(',', '.'))
                        except ValueError:
                            errores.append(f'Linea {linea_num} ({nombre}): Precio invalido')
                            precio = 0.0
                        
                        try:
                            recargo = float(row.get('recargo', '0').replace(',', '.'))
                        except ValueError:
                            recargo = 0.0
                        
                        # Actualizar o crear
                        juego, created = Juego.objects.update_or_create(
                            nombre=nombre,
                            defaults={
                                'precio': precio,
                                'recargo': recargo,
                                'consola': 'ps5',
                                'disponible': True,
                            }
                        )
                        
                        if created:
                            creados += 1
                            self.stdout.write(self.style.SUCCESS(f'NUEVO: {nombre}'))
                        else:
                            actualizados += 1
                            self.stdout.write(f'OK: {nombre} - ${precio}')
                        
                    except Exception as e:
                        errores.append(f'Linea {linea_num}: {str(e)}')
                        continue
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'\n{"="*60}'))
        self.stdout.write(self.style.SUCCESS(f'PS5: {actualizados} actualizados, {creados} nuevos'))
        
        if errores:
            self.stdout.write(self.style.ERROR(f'{len(errores)} errores'))