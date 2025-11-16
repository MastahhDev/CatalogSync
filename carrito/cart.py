# carrito/cart.py - VERSIÓN CORRECTA
from decimal import Decimal
from catalog.models import Juego

class Cart:
    def __init__(self, request):
        """Inicializa el carrito"""
        self.session = request.session
        cart = self.session.get('cart')
        
        if not cart:
            cart = self.session['cart'] = {}
        
        self.cart = cart
    
    def add(self, juego_id, tipo_precio='primario', cantidad=1):
        """
        Agrega un juego al carrito con el tipo de precio especificado.
        """
        juego_id = str(juego_id)
        tipo_precio = str(tipo_precio)
        
        # Crear clave única
        item_key = f"{juego_id}_{tipo_precio}"
        
        if item_key not in self.cart:
            try:
                juego = Juego.objects.get(id=juego_id)
            except Juego.DoesNotExist:
                return False
            
            # 🔧 LÓGICA CORRECTA:
            # - precio = precio BASE (sin recargo) → el que se cobra
            # - recargo = precio CON recargo (+10%) → va tachado
            
            if tipo_precio == 'secundario':
                # Caso 1: Juego que SOLO existe como secundario (prioridad)
                if juego.es_solo_secundario:
                    # Primero intentar con precio_secundario
                    if juego.precio_secundario is not None and juego.precio_secundario > 0:
                        precio_cobrar = float(juego.precio_secundario)
                        precio_recargo = float(juego.recargo_secundario) if juego.recargo_secundario and juego.recargo_secundario > 0 else 0
                        etiqueta = "Secundario"
                    # Fallback a precio normal
                    elif juego.precio is not None and juego.precio > 0:
                        precio_cobrar = float(juego.precio)
                        precio_recargo = float(juego.recargo) if juego.recargo and juego.recargo > 0 else 0
                        etiqueta = "Secundario"
                    else:
                        return False
                # Caso 2: Juego con precio secundario disponible
                elif juego.tiene_secundario and juego.precio_secundario is not None and juego.precio_secundario > 0:
                    precio_cobrar = float(juego.precio_secundario)
                    precio_recargo = float(juego.recargo_secundario) if juego.recargo_secundario and juego.recargo_secundario > 0 else 0
                    etiqueta = "Secundario"
                # Caso 3: No tiene secundario, fallback a primario
                elif juego.precio is not None and juego.precio > 0:
                    precio_cobrar = float(juego.precio)
                    precio_recargo = float(juego.recargo) if juego.recargo and juego.recargo > 0 else 0
                    etiqueta = "Primario"
                    tipo_precio = 'primario'
                else:
                    # Sin precio válido
                    return False
            else:
                # Precio primario (por defecto)
                if juego.precio is not None and juego.precio > 0:
                    precio_cobrar = float(juego.precio)
                    precio_recargo = float(juego.recargo) if juego.recargo and juego.recargo > 0 else 0
                    etiqueta = "Primario"
                else:
                    # Sin precio válido
                    return False
            
            # Crear item en el carrito
            self.cart[item_key] = {
                'juego_id': juego_id,
                'tipo_precio': tipo_precio,
                'etiqueta': etiqueta,
                'cantidad': cantidad,
                'precio': precio_cobrar,          # Precio real a cobrar
                'precio_recargo': precio_recargo, # Precio con recargo (tachado)
            }
        else:
            # Si ya existe, incrementar cantidad
            self.cart[item_key]['cantidad'] += cantidad
        
        self.save()
        return True
    
    def remove(self, item_key):
        """Elimina un item del carrito por su clave única"""
        item_key = str(item_key)
        
        if item_key in self.cart:
            del self.cart[item_key]
            self.save()
    
    def update_quantity(self, item_key, cantidad):
        """Actualiza la cantidad de un item"""
        item_key = str(item_key)
        cantidad = int(cantidad)
        
        if item_key in self.cart:
            if cantidad <= 0:
                self.remove(item_key)
            else:
                self.cart[item_key]['cantidad'] = cantidad
                self.save()
    
    def clear(self):
        """Vacía el carrito"""
        self.session['cart'] = {}
        self.save()
    
    def get_items(self):
        """Retorna una lista de items del carrito con información completa."""
        items = []
        juego_ids = [item['juego_id'] for item in self.cart.values()]
        
        # Obtener todos los juegos de una sola query
        juegos = Juego.objects.filter(id__in=juego_ids)
        juegos_dict = {str(juego.id): juego for juego in juegos}
        
        for item_key, item_data in self.cart.items():
            juego_id = item_data['juego_id']
            
            if juego_id in juegos_dict:
                juego = juegos_dict[juego_id]
                
                precio = Decimal(str(item_data.get('precio', 0)))
                precio_recargo = Decimal(str(item_data.get('precio_recargo', 0)))
                cantidad = item_data.get('cantidad', 1)
                
                items.append({
                    'item_key': item_key,
                    'juego': juego,
                    'juego_id': juego_id,
                    'tipo_precio': item_data.get('tipo_precio', 'primario'),
                    'etiqueta': item_data.get('etiqueta', 'Primario'),
                    'cantidad': cantidad,
                    'precio': precio,                    # Precio real a cobrar
                    'precio_recargo': precio_recargo,    # Precio con recargo (tachado)
                    'subtotal': precio * cantidad,       # Subtotal con precio base
                })
        
        return items
    
    def get_total_price(self):
        """Calcula el precio total del carrito (usando precio base)"""
        items = self.get_items()
        return sum(item['subtotal'] for item in items)
    
    def get_total_items(self):
        """Retorna el total de items (suma de cantidades)"""
        return sum(item['cantidad'] for item in self.cart.values())
    
    def __len__(self):
        """Retorna el número de items únicos en el carrito"""
        return len(self.cart)
    
    def __iter__(self):
        """Permite iterar sobre el carrito"""
        return iter(self.get_items())
    
    def save(self):
        """Marca la sesión como modificada para que se guarde"""
        self.session.modified = True