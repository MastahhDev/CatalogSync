# catalog/management/commands/corregir_precios_secundarios.py
from django.core.management.base import BaseCommand
from catalog.models import Juego

class Command(BaseCommand):
    help = 'Corrige juegos secundarios que tienen el precio en el campo equivocado'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simular sin hacer cambios reales'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Buscar juegos secundarios con precio_secundario NULL pero precio válido
        juegos_incorrectos = Juego.objects.filter(
            es_solo_secundario=True,
            precio_secundario__isnull=True,
            precio__gt=0
        )
        
        total = juegos_incorrectos.count()
        
        if total == 0:
            self.stdout.write(self.style.SUCCESS('✅ No hay juegos con precios incorrectos'))
            return
        
        self.stdout.write(self.style.WARNING(f'\n🔧 Encontrados {total} juegos para corregir\n'))
        
        corregidos = 0
        errores = 0
        
        for juego in juegos_incorrectos:
            try:
                self.stdout.write(f"{'[DRY-RUN] ' if dry_run else ''}Corrigiendo: {juego.nombre}")
                self.stdout.write(f"  precio: {juego.precio} -> 0")
                self.stdout.write(f"  precio_secundario: None -> {juego.precio}")
                self.stdout.write(f"  recargo: {juego.recargo} -> 0")
                self.stdout.write(f"  recargo_secundario: None -> {juego.recargo}")
                
                if not dry_run:
                    # Guardar valores originales
                    precio_original = juego.precio
                    recargo_original = juego.recargo
                    
                    # Mover precios a los campos correctos
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
        
        # Resumen
        self.stdout.write(self.style.SUCCESS(f'\n{"="*60}'))
        self.stdout.write(self.style.SUCCESS('📊 RESUMEN'))
        self.stdout.write(self.style.SUCCESS(f'{"="*60}'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING(f'🔍 MODO SIMULACIÓN - No se hicieron cambios reales'))
        
        self.stdout.write(self.style.SUCCESS(f'✅ Juegos corregidos: {corregidos}'))
        
        if errores > 0:
            self.stdout.write(self.style.ERROR(f'❌ Errores: {errores}'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING(f'\n💡 Ejecuta sin --dry-run para aplicar los cambios'))