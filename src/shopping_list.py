class ShoppingList:
    # Eine einfache Shopping-Liste die Items verwaltet
    
    def __init__(self):
        self.items = []
    
    def add_item(self, item):
        # Fügt ein Item zur Liste hinzu
        if item in self.items:
            return False
        self.items.append(item)
        return True
    
    def remove_item(self, item):
        # Entfernt ein Item aus der Liste
        if item not in self.items:
            return False
        self.items.remove(item)
        return True
    
    def get_items(self):
        # Gibt alle Items zurück
        return self.items.copy()
    
    def __str__(self):
        # String-Repräsentation
        if not self.items:
            return "Shopping-Liste ist leer"
        
        result = "Shopping-Liste:\n"
        for i, item in enumerate(self.items, 1):
            result += f"   {i}. {item}\n"
        return result