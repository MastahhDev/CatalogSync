from django import forms
import os
from django.conf import settings
from django.utils.text import slugify
from .models import Juego

class JuegoAdminForm(forms.ModelForm):
    nueva_portada = forms.ImageField(required=False, label="Subir nueva portada")

    class Meta:
        model = Juego
        fields = "__all__"

    def save(self, commit=True):
        instance = super().save(commit=False)

        nueva_imagen = self.cleaned_data.get("nueva_portada")

        if nueva_imagen:
            # Crear nombre normalizado por el nombre del juego
            nombre_archivo = slugify(instance.nombre) + ".jpg"

            # Ruta absoluta a static/img/
            carpeta_destino = os.path.join(settings.BASE_DIR, "static", "img")
            os.makedirs(carpeta_destino, exist_ok=True)

            ruta_final = os.path.join(carpeta_destino, nombre_archivo)

            # Guardar el archivo subido
            with open(ruta_final, "wb+") as destino:
                for chunk in nueva_imagen.chunks():
                    destino.write(chunk)

            # Guardar ruta en el modelo
            instance.imagen = f"img/{nombre_archivo}"

        if commit:
            instance.save()
        return instance
