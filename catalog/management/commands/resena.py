import os
import pandas as pd
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils.text import slugify
from catalog.models import ResenaCliente

class Command(BaseCommand):
    help = 'Carga reseñas de clientes desde un archivo CSV'

    def add_arguments(self, parser):
        parser.add_argument(
            '--archivo',
            type=str,
            help='Ruta del archivo CSV a cargar',
            default='resena.csv'
        )
        parser.add_argument(
            '--separador',
            type=str,
            help='Separador del CSV (por defecto ;)',
            default=';'
        )

    def encontrar_imagen_cliente(self, cliente):
        """Busca la imagen del cliente en diferentes formatos y ubicaciones"""
        nombre_limpio = slugify(cliente)
        posibles_rutas = [
            f"img/{nombre_limpio}.jpg",
            f"img/{nombre_limpio}.jpeg", 
            f"img/{nombre_limpio}.png",
            f"img/{cliente}.jpg",
            f"img/{cliente}.jpeg",
            f"img/{cliente}.png",
            f"img/{nombre_limpio}.JPG",
            f"img/{nombre_limpio}.JPEG",
            f"img/{nombre_limpio}.PNG",
        ]
        
        for ruta in posibles_rutas:
            ruta_completa = os.path.join(settings.STATICFILES_DIRS[0], ruta)
            if os.path.exists(ruta_completa):
                return ruta
        return None

    def handle(self, *args, **options):
        archivo = options['archivo']
        separador = options['separador']
        
        # Verificar que el archivo existe
        if not os.path.exists(archivo):
            self.stdout.write(
                self.style.ERROR(f'El archivo {archivo} no existe')
            )
            return
        
        try:
            # Leer el archivo CSV
            df = pd.read_csv(archivo, sep=separador)
            
            # Verificar columnas requeridas
            columnas_requeridas = ['cliente', 'juego', 'reseña']
            for columna in columnas_requeridas:
                if columna not in df.columns:
                    self.stdout.write(
                        self.style.ERROR(f'Falta la columna: {columna}')
                    )
                    self.stdout.write(f'Columnas encontradas: {list(df.columns)}')
                    return
            
            # Procesar cada fila
            reseñas_creadas = 0
            for index, fila in df.iterrows():
                try:
                    # Limpiar datos (eliminar espacios en blanco)
                    cliente = str(fila['cliente']).strip()
                    juego = str(fila['juego']).strip()
                    reseña_texto = str(fila['reseña']).strip()
                    
                    # Verificar que no exista ya esta reseña
                    if ResenaCliente.objects.filter(cliente=cliente, juego=juego).exists():
                        self.stdout.write(
                            self.style.WARNING(f'✓ Reseña ya existe para {cliente} - {juego}')
                        )
                        continue
                    
                    # Buscar imagen del cliente
                    ruta_imagen = self.encontrar_imagen_cliente(cliente)
                    
                    # Crear la reseña
                    reseña = ResenaCliente(
                        cliente=cliente,
                        juego=juego,
                        reseña=reseña_texto,
                        imagen=ruta_imagen  # Vincular la imagen si se encuentra
                    )
                    reseña.save()
                    reseñas_creadas += 1
                    
                    if ruta_imagen:
                        self.stdout.write(
                            self.style.SUCCESS(f'✓ Reseña creada para {cliente} (imagen: {ruta_imagen})')
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(f'✓ Reseña creada para {cliente} (imagen NO encontrada)')
                        )
                        
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Error en fila {index + 2}: {str(e)}')
                    )
            
            self.stdout.write(
                self.style.SUCCESS(f'Proceso completado. {reseñas_creadas} reseñas creadas.')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error al procesar el archivo: {str(e)}')
            )