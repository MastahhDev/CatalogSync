# catalog/management/commands/corregir_nombres_imagenes.py
import os
import re
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Corrige nombres de archivos de imagen'

    def handle(self, *args, **options):
        img_dir = os.path.join(settings.BASE_DIR, 'static', 'img')
        archivos_corregidos = 0
        
        for archivo in os.listdir(img_dir):
            if archivo.lower().endswith(('.jpg', '.jpeg', '.png')):
                nombre_original = archivo
                nombre_corregido = self.corregir_nombre_archivo(archivo)
                
                if nombre_corregido != nombre_original:
                    ruta_original = os.path.join(img_dir, nombre_original)
                    ruta_corregida = os.path.join(img_dir, nombre_corregido)
                    
                    try:
                        os.rename(ruta_original, ruta_corregida)
                        archivos_corregidos += 1
                        self.stdout.write(f"✓ {nombre_original} -> {nombre_corregido}")
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Error renombrando {nombre_original}: {e}"))
        
        self.stdout.write(self.style.SUCCESS(f"Archivos corregidos: {archivos_corregidos}"))
    
    def corregir_nombre_archivo(self, nombre_archivo):
        """Corrige nombres de archivos de imagen"""
        nombre = nombre_archivo
        
        # Agregar punto antes de jpg si falta
        nombre = re.sub(r'ps4jpg$', 'ps4.jpg', nombre, flags=re.IGNORECASE)
        nombre = re.sub(r'ps5jpg$', 'ps5.jpg', nombre, flags=re.IGNORECASE)
        nombre = re.sub(r'ps4jpeg$', 'ps4.jpeg', nombre, flags=re.IGNORECASE)
        nombre = re.sub(r'ps5jpeg$', 'ps5.jpeg', nombre, flags=re.IGNORECASE)
        
        # Corregir errores comunes
        nombre = nombre.replace("assassin's", "assassins")
        nombre = nombre.replace("'", "")
        nombre = nombre.replace(" ", "_")
        nombre = nombre.lower()
        
        return nombre