# carrito/cart.py
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
        
        Args:
            juego_id: ID del juego
            tipo_precio: 'primario' o 'secundario'
            cantidad: cantidad a agregar (default 1)
        """
        juego_id = str(juego_id)
        tipo_precio = str(tipo_precio)
        
        # Crear clave única: juego_id + tipo de precio
        # Esto permite tener el mismo juego con diferentes precios
        item_key = f"{juego_id}_{tipo_precio}"
        
        if item_key not in self.cart:
            # Obtener el juego de la base de datos
            try:
                juego = Juego.objects.get(id=juego_id)
            except Juego.DoesNotExist:
                return False
            
            # Determinar precio según el tipo
            if tipo_precio == 'secundario':
                if juego.tiene_secundario and juego.precio_secundario:
                    # Tiene precio secundario disponible
                    precio_base = float(juego.precio_secundario)
                    precio_final = float(juego.recargo_secundario)
                    etiqueta = "Secundario"
                elif juego.es_solo_secundario:
                    # Es un juego solo secundario
                    precio_base = float(juego.precio)
                    precio_final = float(juego.recargo)
                    etiqueta = "Secundario"
                else:
                    # No tiene secundario, usar primario
                    precio_base = float(juego.precio)
                    precio_final = float(juego.recargo)
                    etiqueta = "Primario"
                    tipo_precio = 'primario'  # Corregir tipo
            else:
                # Precio primario (por defecto)
                precio_base = float(juego.precio)
                precio_final = float(juego.recargo)
                etiqueta = "Primario"
            
            # Crear item en el carrito
            self.cart[item_key] = {
                'juego_id': juego_id,
                'tipo_precio': tipo_precio,
                'etiqueta': etiqueta,
                'cantidad': cantidad,
                'precio_base': precio_base,
                'precio_final': precio_final,
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
        """
        Retorna una lista de items del carrito con información completa.
        Cada item incluye el objeto Juego y los datos del carrito.
        """
        items = []
        juego_ids = [item['juego_id'] for item in self.cart.values()]
        
        # Obtener todos los juegos de una sola query
        juegos = Juego.objects.filter(id__in=juego_ids)
        juegos_dict = {str(juego.id): juego for juego in juegos}
        
        for item_key, item_data in self.cart.items():
            juego_id = item_data['juego_id']
            
            if juego_id in juegos_dict:
                juego = juegos_dict[juego_id]
                
                items.append({
                    'item_key': item_key,
                    'juego': juego,
                    'juego_id': juego_id,
                    'tipo_precio': item_data['tipo_precio'],
                    'etiqueta': item_data['etiqueta'],
                    'cantidad': item_data['cantidad'],
                    'precio_base': Decimal(str(item_data['precio_base'])),
                    'precio_final': Decimal(str(item_data['precio_final'])),
                    'subtotal': Decimal(str(item_data['precio_final'])) * item_data['cantidad'],
                })
        
        return items
    
    def get_total_price(self):
        """Calcula el precio total del carrito"""
        return sum(
            Decimal(str(item['precio_final'])) * item['cantidad'] 
            for item in self.cart.values()
        )
    
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