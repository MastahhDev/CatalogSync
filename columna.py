import pandas as pd

# Leer CSV tolerando comillas y líneas con errores
df = pd.read_csv('juegos2.csv', sep=',', quotechar='"', engine='python', on_bad_lines='skip')


# Guardar solo la primera columna
df[['nombre']].to_csv('solo_nombres.csv', index=False)

print("Listo ✅ Se creó el archivo solo_nombres.csv")
