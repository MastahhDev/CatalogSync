# catalog/management/commands/sincronizar_imagenes.py
import os
import re
import unicodedata
from django.core.management.base import BaseCommand
from django.conf import settings
from catalog.models import Juego

class Command(BaseCommand):
    help = 'Sincroniza las imágenes de los juegos con las disponibles en static/img'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simular sin hacer cambios reales'
        )
        parser.add_argument(
            '--solo-default',
            action='store_true',
            help='Solo actualizar juegos que tienen imagen default'
        )
        parser.add_argument(
            '--consola',
            type=str,
            help='Filtrar por consola (ps4 o ps5)'
        )

    def quitar_acentos(self, texto):
        """Elimina acentos y diacríticos de un texto"""
        if not texto:
            return ""
        texto_normalizado = unicodedata.normalize('NFD', texto)
        return ''.join(c for c in texto_normalizado if unicodedata.category(c) != 'Mn')

    def buscar_imagen(self, nombre_juego, consola):
        """Busca la imagen correspondiente al juego"""
        nombre = re.sub(r'\s*\(SECUNDARIO\)\s*', '', nombre_juego, flags=re.IGNORECASE)
        nombre = self.quitar_acentos(nombre.lower())
        nombre = nombre.replace(f' {consola}', '').replace(f' {consola.upper()}', '').strip()
        nombre = nombre.replace("'", "").replace(":", "").replace("&", "and")
        nombre = nombre.replace("+", "").replace(" ", "_")
        nombre_archivo = f"{nombre}_{consola}.jpg"
        
        img_dir = os.path.join(settings.BASE_DIR, 'static', 'img')
        
        # Buscar exacto
        if os.path.exists(os.path.join(img_dir, nombre_archivo)):
            return f"img/{nombre_archivo}"
        
        # Buscar case-insensitive
        try:
            archivos_existentes = [f for f in os.listdir(img_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            archivos_lower = [f.lower() for f in archivos_existentes]
            
            if nombre_archivo.lower() in archivos_lower:
                archivo_real = archivos_existentes[archivos_lower.index(nombre_archivo.lower())]
                return f"img/{archivo_real}"
            
            # Buscar variaciones
            nombre_simplificado = re.sub(r'[_\-\d]+', '_', nombre).strip('_')
            nombre_busqueda = f"{nombre_simplificado}_{consola}".lower()
            
            for archivo in archivos_lower:
                archivo_sin_ext = archivo.rsplit('.', 1)[0]
                if nombre_busqueda in archivo_sin_ext or archivo_sin_ext in nombre_busqueda:
                    indice = archivos_lower.index(archivo)
                    return f"img/{archivos_existentes[indice]}"
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error buscando imagen: {e}"))
        
        return "img/default.jpg"

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        solo_default = options['solo_default']
        consola_filtro = options.get('consola')
        
        # Construir query
        query = Juego.objects.all()
        
        if solo_default:
            query = query.filter(imagen='img/default.jpg') | query.filter(imagen='') | query.filter(imagen__isnull=True)
        
        if consola_filtro:
            query = query.filter(consola=consola_filtro.lower())
        
        total = query.count()
        
        if total == 0:
            self.stdout.write(self.style.SUCCESS('✅ No hay juegos para procesar'))
            return
        
        self.stdout.write(self.style.WARNING(f'\n🔍 Procesando {total} juegos...\n'))
        
        actualizados = 0
        sin_cambios = 0
        errores = 0
        
        for juego in query:
            try:
                imagen_actual = juego.imagen or "img/default.jpg"
                imagen_nueva = self.buscar_imagen(juego.nombre, juego.consola)
                
                # Solo actualizar si encontró una imagen diferente y no es default
                if imagen_nueva != imagen_actual and imagen_nueva != "img/default.jpg":
                    self.stdout.write(f"{'[DRY-RUN] ' if dry_run else ''}🖼️  {juego.nombre}")
                    self.stdout.write(f"  Actual: {imagen_actual}")
                    self.stdout.write(f"  Nueva:  {imagen_nueva}")
                    
                    if not dry_run:
                        juego.imagen = imagen_nueva
                        juego.save()
                        self.stdout.write(self.style.SUCCESS(f"  ✅ Actualizado\n"))
                    else:
                        self.stdout.write(self.style.WARNING(f"  ⚠️  Simulado\n"))
                    
                    actualizados += 1
                else:
                    sin_cambios += 1
                    
            except Exception as e:
                errores += 1
                self.stdout.write(self.style.ERROR(f"❌ Error en {juego.nombre}: {str(e)}"))
        
        # Resumen
        self.stdout.write(self.style.SUCCESS(f'\n{"="*60}'))
        self.stdout.write(self.style.SUCCESS('📊 RESUMEN DE SINCRONIZACIÓN'))
        self.stdout.write(self.style.SUCCESS(f'{"="*60}'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING(f'🔍 MODO SIMULACIÓN - No se hicieron cambios reales'))
        
        self.stdout.write(self.style.SUCCESS(f'✅ Imágenes actualizadas: {actualizados}'))
        self.stdout.write(self.style.WARNING(f'⏭️  Sin cambios: {sin_cambios}'))
        
        if errores > 0:
            self.stdout.write(self.style.ERROR(f'❌ Errores: {errores}'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING(f'\n💡 Ejecuta sin --dry-run para aplicar los cambios'))