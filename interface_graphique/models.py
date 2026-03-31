from constants import *
import json
import os


def load_labware_dims(json_filename):
    """Charge les dimensions réelles depuis le dossier master de science-jubilee."""
   # 1. On récupère le chemin du dossier où se trouve ce fichier (model.py)
    # On suppose que tu es dans : .../science-jubilee/interface_graphique/
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 2. On remonte d'un niveau pour arriver à la racine 'science-jubilee'
    project_root = os.path.dirname(current_dir)
    
    # 3. On construit le chemin vers les définitions
    # Cela donne : .../science-jubilee/src/science_jubilee/labware/labware_definition/
    base_path = os.path.join(
        project_root, 
        "src", "science_jubilee", "labware", "labware_definition"
    )
    
    full_path = os.path.join(base_path, json_filename)
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"⚠️ Erreur chargement JSON {json_filename}: {e}")
        return None
    

class DraggableObject:
    def __init__(self, canvas, x, y, json_name, color, name, check_collision_callback, check_inside_callback):
        self.canvas = canvas
        self.name = name
        

        self.data = load_labware_dims(json_name)
        if self.data:
            # On récupère les vraies dimensions du JSON
            self.w_mm = self.data["dimensions"]["xDimension"]
            self.h_mm = self.data["dimensions"]["yDimension"]
        else:
            self.w_mm, self.h_mm = 50, 50 # Valeurs de secours
            
        # Conversion immédiate pour le dessin
        w_px = self.w_mm * MM_TO_PIX
        h_px = self.h_mm * MM_TO_PIX


        self.id = canvas.create_rectangle(x, y, x + w_px, y + h_px, fill=color, outline="white", width=2)
        self.text = canvas.create_text(x + w_px/2, y + h_px/2, text=name, fill="white", font=("Arial", 10))
        self.items = [self.id, self.text]


        self.angle = 0
        self.check_collision = check_collision_callback
        self.check_inside = check_inside_callback

        

        for item in self.items:
            canvas.tag_bind(item, "<Button-1>", self.start_drag)
            canvas.tag_bind(item, "<B1-Motion>", self.do_drag)
            canvas.tag_bind(item, "<Button-3>", self.rotate)

    def start_drag(self, event):
        self.start_x = event.x
        self.start_y = event.y

    def do_drag(self, event):
        dx = event.x - self.start_x
        dy = event.y - self.start_y
        x1, y1, x2, y2 = self.canvas.coords(self.id)
        w, h = x2 - x1, y2 - y1

        if self.check_inside(x1 + dx, y1 + dy, w, h) and self.check_collision(x1 + dx, y1 + dy, w, h, ignore_id=self.id):
            for item in self.items:
                self.canvas.move(item, dx, dy)
            self.start_x = event.x
            self.start_y = event.y

    def rotate(self, event):
        x1, y1, x2, y2 = self.canvas.coords(self.id)
        w, h = x2 - x1, y2 - y1
        cx, cy = x1 + w/2, y1 + h/2
        self.canvas.coords(self.id, cx - h/2, cy - w/2, cx + h/2, cy + w/2)
        self.canvas.coords(self.text, cx, cy)
        self.angle = (self.angle + 90) % 360

        self.w_mm, self.h_mm = self.h_mm, self.w_mm#echanger w et h pour la rotation (x et y)


    