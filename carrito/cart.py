from decimal import Decimal
from catalog.models import Juego

class Cart:
    """Maneja el carrito de compras en la sesión"""
    
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get('cart')
        if not cart:
            cart = self.session['cart'] = {}
        self.cart = cart
    
    def add(self, juego_id, cantidad=1):
        """Agrega un juego al carrito"""
        juego_id = str(juego_id)
        
        if juego_id not in self.cart:
            self.cart[juego_id] = {
                'cantidad': 0,
            }
        
        self.cart[juego_id]['cantidad'] += cantidad
        self.save()
    
    def remove(self, juego_id):
        """Elimina un juego del carrito"""
        juego_id = str(juego_id)
        if juego_id in self.cart:
            del self.cart[juego_id]
            self.save()
    
    def update_quantity(self, juego_id, cantidad):
        """Actualiza la cantidad de un juego"""
        juego_id = str(juego_id)
        if juego_id in self.cart:
            if cantidad <= 0:
                self.remove(juego_id)
            else:
                self.cart[juego_id]['cantidad'] = cantidad
                self.save()
    
    def clear(self):
        """Vacía el carrito"""
        self.session['cart'] = {}
        self.save()
    
    def save(self):
        """Marca la sesión como modificada"""
        self.session.modified = True
    
    def get_items(self):
        """Obtiene los items del carrito con datos de los juegos"""
        juego_ids = self.cart.keys()
        juegos = Juego.objects.filter(id__in=juego_ids)
        items = []
        
        for juego in juegos:
            juego_id = str(juego.id)
            items.append({
                'juego': juego,
                'cantidad': self.cart[juego_id]['cantidad'],
                'subtotal': juego.precio * self.cart[juego_id]['cantidad'],
            })
        
        return items
    
    def get_total_price(self):
        """Calcula el precio total del carrito"""
        items = self.get_items()
        return sum(item['subtotal'] for item in items)
    
    def get_total_items(self):
        """Cuenta el total de items (suma de cantidades)"""
        return sum(item['cantidad'] for item in self.cart.values())
    
    def __len__(self):
        """Retorna cantidad total de items"""
        return self.get_total_items()
    
    def __iter__(self):
        """Permite iterar sobre los items"""
        return iter(self.get_items())