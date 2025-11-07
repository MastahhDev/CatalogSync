import os
import shutil
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Copia todas las portadas que contengan "ps5" en el nombre a otra carpeta destino.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--carpeta-origen',
            type=str,
            default='static/img',
            help='Carpeta donde están las portadas originales'
        )
        parser.add_argument(
            '--carpeta-destino',
            type=str,
            default='portadas_ps5',
            help='Carpeta donde se copiarán las portadas PS5'
        )

    def handle(self, *args, **options):
        carpeta_origen = os.path.join(settings.BASE_DIR, options['carpeta_origen'])
        carpeta_destino = os.path.join(settings.BASE_DIR, options['carpeta_destino'])

        # Crear carpeta destino si no existe
        os.makedirs(carpeta_destino, exist_ok=True)

        # Verificar existencia de la carpeta origen
        if not os.path.exists(carpeta_origen):
            self.stdout.write(self.style.ERROR(f'❌ No se encontró la carpeta origen: {carpeta_origen}'))
            return

        # Obtener todos los archivos de imagen
        archivos = [
            f for f in os.listdir(carpeta_origen)
            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))
        ]

        # Filtrar los que contengan "ps5" en el nombre
        archivos_ps5 = [f for f in archivos if 'ps5' in f.lower()]

        if not archivos_ps5:
            self.stdout.write(self.style.WARNING('⚠️  No se encontraron archivos con "ps5" en el nombre.'))
            return

        # Copiar los archivos
        for archivo in archivos_ps5:
            origen = os.path.join(carpeta_origen, archivo)
            destino = os.path.join(carpeta_destino, archivo)
            try:
                shutil.copy2(origen, destino)
                self.stdout.write(self.style.SUCCESS(f'✅ Copiado: {archivo}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error copiando {archivo}: {str(e)}'))

        self.stdout.write(self.style.SUCCESS(
            f'\n✨ Proceso completado: {len(archivos_ps5)} archivos copiados a "{carpeta_destino}"'
        ))
