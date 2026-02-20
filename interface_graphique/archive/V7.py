import customtkinter as ctk
import tkinter as tk
import json
#crétion du plan dxf pour lazer cut
import ezdxf
import math

#convertir les milimetres en pixels
MM_TO_PIX = 3 
#dimension plateau
PLATEAU_W_MM = 305
PLATEAU_H_MM = 305
DIAMETRE_TROU = 3 # mm (pour M3)
OFFSET_TROU_BAS_X = 15.39 # distance des trous du bas en x
OFFSET_TROU_BAS_y = 5 # distance des trous du bas en y//
OFFSET_TROU_HAUT_X = 5 # distance des trous du haut en x//
OFFSET_TROU_HAUT_Y = 1.5 # distance des trous du haut en y//
OFFSET_CONTOUR = 5 # distance hors cadre

PLATEAU_W = PLATEAU_W_MM * MM_TO_PIX
PLATEAU_H = PLATEAU_H_MM * MM_TO_PIX

#marge pour le placement des labwares
MARGIN_BETWEEN_OBJECTS = 5     # mm
MARGIN_BORDER = 10              # mm
MARGIN_BORDER_PX = MARGIN_BORDER * (PLATEAU_H / PLATEAU_H_MM)
MARGIN_BETWEEN_OBJECTS_PX = MARGIN_BETWEEN_OBJECTS * (PLATEAU_H / PLATEAU_H_MM)

#--------------tag à ne pas supprimé-----------------------
TAGS_PROTEGES = {
    "__background__",
    "__grid__",
    "plateau_marge",
    "slot_text",
    "outil_1", "outil_2", "outil_3", "outil_4",
    "slot_text_1", "slot_text_2", "slot_text_3", "slot_text_4"
}

#------------------------------------------------------------------------------------------
#emplacement des slot outils Positions fixes des slots dans le parc à outils (en pixels)
# Largeur du panneau pour les slots à gauche du plateau
SLOT_PANEL_WIDTH = 100 
OUTIL_SLOTS = {
    1: {"x": 200, "y": 100},   # Slot 1
    2: {"x": 200, "y": 300},  # Slot 2
    3: {"x": 200, "y": 500},  # Slot 3
    4: {"x": 200, "y": 700},  # Slot 4
}
canvas_slot_text_ids = {}   # contiendra l'id du texte de chaque slot
# Liste des outils disponibles
outils = ["None", "Pipette", "Inoculator", "Fluo", "Other"]

#liste pour utiliser le bon json associé
TOOL_SCIENTIFIC_NAMES = {
    "None": None,
    "Pipette": "tyesttttt",
    "Inoculator": "single_channel_pipette_1000ul",
    "Fluo": "wash_station_standard",
    "Other": "liquid_waste_container"
}

slot_assignments = {slot_id: "None" for slot_id in OUTIL_SLOTS}

slot_windows = {}
# -------------------- CONFIG --------------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Dimensions par défaut des outils (en pixels sur le Canvas)
TOOLS = {
    "Plaque 24 puits": {"w_mm": 127.76, "h_mm": 85.48, "json": "greiner_24_wellplate_3300ul_orth.json"},
    "Réservoir eau": {"w_mm": 50, "h_mm": 30, "json": "pot_de_d'eau.json"},
    "Réservoir lentilles": {"w_mm": 30, "h_mm": 30, "json": "pot_de_lentille.json"}
}
# -------------------- APP --------------------
app = ctk.CTk()
app.title("Virtual Workspace — Interface complète")
MARGIN = 50  # pixels autour du plateau
WINDOW_SIZE = PLATEAU_H + MARGIN*2  # fenêtre carrée
app.geometry(f"{WINDOW_SIZE}x{WINDOW_SIZE}")

# ---------- STATE ----------
selected_tool_name = None        # outil choisi dans la banque (pour placer)
placed_objects = []              # liste des objets DraggableObject

# -------------------- DRAGGABLE OBJECT --------------------
class DraggableObject:
    def __init__(self, canvas, x, y, w, h, color, name):
        self.canvas = canvas
        self.name = name
        self.angle = 0
        self.assigned_slot = None  # aucun slot outil assigné par défaut

        # rectangle + texte
        self.id = canvas.create_rectangle(x, y, x + w, y + h, fill=color, outline="white", width=2)
        self.text = canvas.create_text(x + w/2, y + h/2, text=name, fill="white", font=("Arial", 10))
        self.items = [self.id, self.text]

        # drag state
        self.dragging = False
        self.start_x = 0
        self.start_y = 0

        # bind events
        for item in self.items:
            canvas.tag_bind(item, "<Button-1>", self.start_drag)
            canvas.tag_bind(item, "<B1-Motion>", self.do_drag)
            canvas.tag_bind(item, "<Button-3>", self.rotate)

 # DRAG
    def start_drag(self, event):
        self.dragging = True
        self.start_x = event.x
        self.start_y = event.y

    def do_drag(self, event):
        if self.dragging:
            dx = event.x - self.start_x
            dy = event.y - self.start_y
            
            x1, y1, x2, y2 = self.canvas.coords(self.id)
            new_x1, new_y1 = x1 + dx, y1 + dy
            w, h = x2 - x1, y2 - y1

             #Vérifier la sécurité (Plateau + Collisions)
            if is_inside_plateau(new_x1, new_y1, w, h) and is_free_space(new_x1, new_y1, w, h, ignore_id=self.id):
                for item in self.items:
                    self.canvas.move(item, dx, dy)
                
                # Mettre à jour la position de départ pour le prochain mouvement
                self.start_x = event.x
                self.start_y = event.y
            else:
                self.start_x = event.x
                self.start_y = event.y
   

    # ROTATION 90°
    def rotate(self, event):
        x1, y1, x2, y2 = self.canvas.coords(self.id)
        w = x2 - x1
        h = y2 - y1
        cx = x1 + w/2
        cy = y1 + h/2
        new_w, new_h = h, w
        new_x1 = cx - new_w/2
        new_y1 = cy - new_h/2
        new_x2 = new_x1 + new_w
        new_y2 = new_y1 + new_h
        self.canvas.coords(self.id, new_x1, new_y1, new_x2, new_y2)
        self.canvas.coords(self.text, new_x1 + new_w/2, new_y1 + new_h/2)
        self.angle = (self.angle + 90) % 360


# -------------------- LAYOUT --------------------
sidebar = ctk.CTkFrame(app, width=260)
sidebar.pack(side="left", fill="y", padx=12, pady=12)

title = ctk.CTkLabel(sidebar, text="Banque d'outils", font=("Arial", 18))
title.pack(pady=(6, 12))

lbl_selected = ctk.CTkLabel(sidebar, text="Outil sélectionné:\nAucun", font=("Arial", 12))
lbl_selected.pack(pady=(12,8))

# ---------- FUNCTIONS ----------
def select_tool(name):
    global selected_tool_name
    selected_tool_name = name
    lbl_selected.configure(text=f"Outil sélectionné:\n{name}")

def create_placed_item(tool_name, x, y, w, h, angle=0):
    color = "#1f6aa5" if "Plaque" in tool_name else ("#2e7d32" if "eau" in tool_name.lower() else "#c2185b")
    obj = DraggableObject(canvas, x, y, w, h, color, tool_name)
    obj.angle = angle
    placed_objects.append(obj)
    return obj

def place_tool_center(tool_name):
    w = TOOLS[tool_name]["w"]
    h = TOOLS[tool_name]["h"]
    x = (canvas.winfo_width() - w)/2
    y = (canvas.winfo_height() - h)/2
    create_placed_item(tool_name, x, y, w, h)

def export_layout(filename="test1.json"):
    # --- Plateau en pixels ---
    x0_px, y0_px, x1_px, y1_px = canvas.coords(canvas_plateau)
    PLATEAU_W_PX = x1_px - x0_px
    PLATEAU_H_PX = y1_px - y0_px

    SCALE_X = PLATEAU_W_MM / PLATEAU_W_PX
    SCALE_Y = PLATEAU_H_MM / PLATEAU_H_PX

    # coin bottom-left en pixels
    bl_x_px = x0_px
    bl_y_px = y0_px + PLATEAU_H_PX

    # --- JSON racine ---
    data = {
        "name": "Experience1",
        "description": "Simulation de l'éclairage + prise de photos",
        "type": "SLAS",
        "deck_offset": [0.0, 0.0],
        "material": {
            "deck": "Plastic",
            "mask": ""
        },
        "slot_reference_corner": "top_left",
        #"safe_z_clearance": 10.0,
        "slots": {},
        "tool_slots": {}
    }

    # =========================================================
    # 1) SLOTS DU PLATEAU (labwares)
    # =========================================================


    for idx, obj in enumerate(placed_objects):
        x1_px, y1_px, x2_px, y2_px = canvas.coords(obj.id)

        # centre en pixels
        cx_px = (x1_px + x2_px) / 2
        cy_px = (y1_px + y2_px) / 2

        # conversion mm (bottom_left)
        x_mm = (cx_px - bl_x_px) * SCALE_X
        y_mm = (bl_y_px - cy_px) * SCALE_Y

        w_mm = (x2_px - x1_px) * SCALE_X
        h_mm = (y2_px - y1_px) * SCALE_Y

        labware_json = None
        if obj.name in TOOLS:
            labware_json = TOOLS[obj.name]["json"]


        data["slots"][str(idx)] = {
            "coordinates": [round(x_mm, 2), round(y_mm, 2)],
            "shape": "rectangle",
            "width": round(w_mm, 2),
            "length": round(h_mm, 2),
            "has_labware": True,
            "labware": labware_json
        }

    # =========================================================
    # 2) SLOTS OUTILS (parc à outils)
    # =========================================================
    for slot_id, tool_name in slot_assignments.items():
        if tool_name != "None":
            # On récupère le nom scientifique via le dictionnaire
            scientific_name = TOOL_SCIENTIFIC_NAMES.get(tool_name, tool_name)
            
            data["tool_slots"][str(slot_id)] = {
                "display_name": tool_name,
                "scientific_name": scientific_name
            }

    # --- Sauvegarde ---
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print(f"Export JSON OK → {filename}")


def load_json():
    try:
        with open("test1.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("Aucun fichier test1.json trouvé.")
        return

    # 1) Nettoyage du canvas
    for item in canvas.find_all():
        tags = canvas.gettags(item)
        if any(tag in TAGS_PROTEGES for tag in tags):
            continue
        canvas.delete(item)

    placed_objects.clear()

    # 2) Dimensions plateau
    x0_px, y0_px, x1_px, y1_px = canvas.coords(canvas_plateau)
    PLATEAU_W_PX = x1_px - x0_px
    PLATEAU_H_PX = y1_px - y0_px

    SCALE_X = PLATEAU_W_PX / PLATEAU_W_MM
    SCALE_Y = PLATEAU_H_PX / PLATEAU_H_MM

    bl_x_px = x0_px
    bl_y_px = y0_px + PLATEAU_H_PX

    # 3) Réinitialiser slots outils
    for slot_id in OUTIL_SLOTS:
        slot_assignments[slot_id] = "None"
        update_slot_display(slot_id)

    # 4) Import des LABWARES
    slots = data.get("slots", {})
    for _, slot in slots.items():
        if not slot.get("has_labware", False):
            continue

        labware_json = slot.get("labware")
        if labware_json is None:
            continue

        x_mm, y_mm = slot["coordinates"]
        w_mm = slot.get("width", 0)
        h_mm = slot.get("length", 0)

        x_px = bl_x_px + x_mm * SCALE_X - (w_mm * SCALE_X) / 2
        y_px = bl_y_px - y_mm * SCALE_Y - (h_mm * SCALE_Y) / 2

        
        display_name = "Labware" 
        for name, info in TOOLS.items():
            if info["json"] == labware_json:
                display_name = name
                break

        create_placed_item(
            display_name,
            x_px,
            y_px,
            w_mm * SCALE_X,
            h_mm * SCALE_Y,
            angle=0
        )

    # 5) Import des OUTILS
    tool_slots = data.get("tool_slots", {})

    for slot_id, tool_info in tool_slots.items():
        slot_id = int(slot_id)
        
        if isinstance(tool_info, dict):
            assigned = tool_info.get("display_name", "None")
        else:
            assigned = tool_info if tool_info else "None"
            
        slot_assignments[slot_id] = assigned
        update_slot_display(slot_id)

    print("Import JSON OK")


       
            

def clear_canvas():
     # supprime tous les objets sauf le plateau (__background__) et la grille (__grid__)
    for item in canvas.find_all():
        tags = canvas.gettags(item)
        if not any(tag in TAGS_PROTEGES for tag in tags):
            canvas.delete(item)
    placed_objects.clear()

def delete_object_under_cursor(event):
    x, y = canvas.winfo_pointerxy()
    canvas_x = canvas.canvasx(x - canvas.winfo_rootx())
    canvas_y = canvas.canvasy(y - canvas.winfo_rooty())
    items = canvas.find_overlapping(canvas_x, canvas_y, canvas_x, canvas_y)
    for obj in placed_objects:
        if obj.id in items:
            for item in obj.items:
                canvas.delete(item)
            placed_objects.remove(obj)
            break


def export_to_dxf(json_file="test1.json"):
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print("Impossible d’ouvrir", json_file, e)
        return

    milieu_x = PLATEAU_W_MM / 2

    parties = [
        {"name": "plan_left.dxf",  "x_min_zone": 0,        "x_max_zone": milieu_x},
        {"name": "plan_right.dxf", "x_min_zone": milieu_x, "x_max_zone": PLATEAU_W_MM}
    ]

    for p in parties:
        doc = ezdxf.new(dxfversion="R2010")
        doc.header["$INSUNITS"] = 4 
        msp = doc.modelspace()

        def draw_rectangle(x1, y1, x2, y2, layer="default"):
            msp.add_lwpolyline([(x1, y1), (x2, y1), (x2, y2), (x1, y2)],
                               close=True, dxfattribs={"layer": layer})

        # 1) PLATEAU
        draw_rectangle(p["x_min_zone"], -2*OFFSET_CONTOUR, p["x_max_zone"], PLATEAU_H_MM + 2*OFFSET_CONTOUR, layer="plateau")

        # 2) TROUS DE FIXATION
        r = DIAMETRE_TROU / 2
        trous = [
            (OFFSET_TROU_BAS_X, -OFFSET_TROU_BAS_y),
            (PLATEAU_W_MM - OFFSET_TROU_BAS_X, -OFFSET_TROU_BAS_y),
            (PLATEAU_W_MM - OFFSET_TROU_HAUT_X, PLATEAU_H_MM + OFFSET_TROU_HAUT_Y),
            (OFFSET_TROU_HAUT_X, PLATEAU_H_MM + OFFSET_TROU_HAUT_Y),
        ]
        for tx, ty in trous:
            if p["x_min_zone"] <= tx <= p["x_max_zone"]:
                msp.add_circle(center=(tx, ty), radius=r, dxfattribs={"layer": "fixation_holes"})

        # 3) LABWARES
        slots = data.get("slots", {})
        for slot in slots.values():
            if not slot.get("has_labware", False): continue
            
            cx, cy = slot["coordinates"]
            w, h = slot.get("width", 0), slot.get("length", 0)
            
            # Coordonnées réelles du labware
            lx1, lx2 = cx - w/2, cx + w/2
            ly1, ly2 = cy - h/2, cy + h/2

            # (Si le bord droit du labware > début zone ET bord gauche < fin zone)
            if lx2 >= p["x_min_zone"] and lx1 <= p["x_max_zone"]:
               
                draw_x1 = max(lx1, p["x_min_zone"])
                draw_x2 = min(lx2, p["x_max_zone"])
                
                # On ajoute une marge de 0.5mm pour le jeu comme dans votre code
                draw_rectangle(draw_x1 - 0.5, ly1 - 0.5, draw_x2 + 0.5, ly2 + 0.5, layer="labware")

        doc.saveas(p["name"])
        print(f"Fichier généré : {p['name']}")



# ---------- TOOL BUTTONS ----------
for tname in TOOLS.keys():
    ctk.CTkButton(sidebar, text=tname, command=lambda n=tname: select_tool(n)).pack(fill="x", pady=6)

ctk.CTkButton(sidebar, text="Exporter JSON", command=export_layout, fg_color="#1976d2").pack(fill="x", pady=8)
ctk.CTkButton(sidebar, text="Charger JSON", command=load_json).pack(fill="x", pady=4)
ctk.CTkButton(sidebar, text="Plan Lazer Cut", command=export_to_dxf).pack(fill="x", pady=4)
ctk.CTkButton(sidebar, text="Vider plateau", command=clear_canvas, fg_color="#c62828").pack(fill="x", pady=4)

ctk.CTkLabel(sidebar, text="Raccourcis:\n- Clic gauche: déplacer\n- Clic droit: tourner 90°\n- Suppr: supprimer objet sous curseur",
             wraplength=230, justify="left").pack(pady=12)


slot_windows = {}  # dictionnaire pour garder les fenêtres ouvertes
def select_outil(slot_id):
    if slot_id in slot_windows:
        slot_windows[slot_id].lift()
        return

    window = ctk.CTkToplevel(app)
    window.title(f"Choisir outil pour Slot {slot_id}")
    window.geometry("200x120")
    window.protocol("WM_DELETE_WINDOW", lambda: close_window(slot_id))
    slot_windows[slot_id] = window

     # Sélection actuelle (toujours une string valide)
    current_value = slot_assignments.get(slot_id, "None")
    if current_value not in outils:
        current_value = "None"  # sécurité anti crash


    combo = ctk.CTkComboBox(window, values=outils)
    combo.set(slot_assignments[slot_id])  # ⬅ charge l’outil actuel
    combo.pack(padx=10, pady=10)

    def validate():
        selected = combo.get()

        slot_assignments[slot_id] = selected

        # colorer le rectangle
        color = "#aaffaa" if selected != "None" else "#dddddd"
        canvas.itemconfig(slot_rects[slot_id], fill=color)

        # texte dans le slot
        text_id = OUTIL_SLOTS[slot_id]["text_id"]
        canvas.itemconfig(text_id, text=selected)

        close_window(slot_id)

    btn = ctk.CTkButton(window, text="Valider", command=validate)
    btn.pack(pady=10)


def close_window(slot_id):
    if slot_id in slot_windows:
        slot_windows[slot_id].destroy()
        del slot_windows[slot_id]

def bind_slot(slot_id):
    def handler(event):
        select_outil(slot_id)
    canvas.tag_bind(f"outil_{slot_id}", "<Button-1>", handler)

#fonction pour mettre a jour le texte dans le parc à OUTIL
def update_slot_display(slot_id):
    assigned = slot_assignments[slot_id]

    color = "#aaffaa" if assigned != "None" else "#dddddd"
    canvas.itemconfig(slot_rects[slot_id], fill=color)

    txt_id = canvas_slot_text_ids[slot_id]
    canvas.itemconfig(txt_id, text=assigned)


# ---------- CANVAS ----------
canvas_frame = ctk.CTkFrame(app)
canvas_frame.pack(side="right", expand=True, fill="both", padx=12, pady=12)

canvas = tk.Canvas(canvas_frame, bg="#111213", highlightthickness=0)
canvas.pack(expand=True, fill="both")

# ---------- EVENTS ----------
app.bind("<Delete>", delete_object_under_cursor)

# ---------- CANVAS CLICK TO PLACE ----------
 #securité pour ne pas poser d'objet en dehors du plateau avec assez de marge
def is_inside_plateau(x1, y1, w, h):
    px1, py1, px2, py2 = canvas.coords(canvas_plateau)

    if x1 < px1 + MARGIN_BORDER_PX: return False
    if y1 < py1 + MARGIN_BORDER_PX: return False
    if x1 + w > px2 - MARGIN_BORDER_PX: return False
    if y1 + h > py2 - MARGIN_BORDER_PX: return False

    return True

    # Vérifie qu'il n'y a pas de chevauchement avec les autres objets
def is_free_space(x1, y1, w, h, ignore_id=None):
    x2 = x1 + w
    y2 = y1 + h

    for other in placed_objects:
        if other.id == ignore_id:
            continue

        ox1, oy1, ox2, oy2 = canvas.coords(other.id)

        # On élargit l’autre objet par la marge
        ox1 -= MARGIN_BETWEEN_OBJECTS_PX
        oy1 -= MARGIN_BETWEEN_OBJECTS_PX
        ox2 += MARGIN_BETWEEN_OBJECTS_PX
        oy2 += MARGIN_BETWEEN_OBJECTS_PX

        # Collision rectangle AABB
        if not (x2 < ox1 or x1 > ox2 or y2 < oy1 or y1 > oy2):
            return False

    return True


def on_canvas_click(event):
    global selected_tool_name
    if selected_tool_name is None:
        return
      # conversion mm → pixels
    w_mm = TOOLS[selected_tool_name]["w_mm"]
    h_mm = TOOLS[selected_tool_name]["h_mm"]
    w_px = w_mm * MM_TO_PIX
    h_px = h_mm * MM_TO_PIX

    x = event.x - w_px/2
    y = event.y - h_px/2

    if not is_inside_plateau(x, y, w_px, h_px):
        print("Placement impossible : Hors des limites du plateau.")
        return # On arrête tout ici

    # Check 2: Est-ce que l'espace est libre ?
    if not is_free_space(x, y, w_px, h_px):
        print("Placement impossible : Espace déjà occupé.")
        return # On arrête tout ici
    create_placed_item(selected_tool_name, x, y, w_px, h_px)

    # reset selection
    selected_tool_name = None
    lbl_selected.configure(text="Outil sélectionné:\nAucun")

    # Réinitialiser la sélection après placement
    selected_tool_name = None
    lbl_selected.configure(text="Outil sélectionné:\nAucun")

canvas.bind("<Button-1>", on_canvas_click)

# ---------- GRID (optional) ----------
GRID_SPACING = 20

# création du plateau (une seule fois)
# Plateau principal (arrière-plan)
# Plateau (fond)
canvas_plateau = canvas.create_rectangle(
    0, 0,
    PLATEAU_W,
    PLATEAU_H,
    fill="white",
    outline="#888888",
    width=2,
    tags="__background__"
)


slot_rects = {}  # Pour garder la référence des rectangles
canvas_slot_text_ids = {}


for slot_id, pos in OUTIL_SLOTS.items():
 
    tag_nom = f"outil_{slot_id}"
    rect = canvas.create_rectangle(
        pos["x"], pos["y"],
        pos["x"] + 60, pos["y"] + 90,
        fill="#dddddd",
        outline="#888",
        width=2,
        tags=(tag_nom, "slot_outil_rect")
    )
    slot_rects[slot_id] = rect
    OUTIL_SLOTS[slot_id]["rect_id"] = rect

    # 2. Création du texte
    txt = canvas.create_text(
        pos["x"] + 30,
        pos["y"] + 25,
        text=slot_assignments[slot_id],
        fill="black",
        font=("Arial", 10, "bold"),
        tags=(f"slot_text_{slot_id}", "slot_outil_text")
    )
    canvas_slot_text_ids[slot_id] = txt
    OUTIL_SLOTS[slot_id]["text_id"] = txt

    # 3. Gestion de l'ordre d'affichage (Z-index)
    # On s'assure que le texte est TOUJOURS au-dessus du rectangle
    canvas.tag_raise(txt)

# Suppression des lignes tag_lower(outils) et tag_raise(slot_id) qui causaient l'erreur
for slot_id in OUTIL_SLOTS.keys():
    bind_slot(slot_id)
    

# Marges (rectangle pointillé à l'intérieur du plateau)
canvas_marge = canvas.create_rectangle(
    0, 0, 0, 0,  # coordonnées initiales seront mises à jour dans draw_grid
    fill="",                    
    outline="red",              
    width=2,
    dash=(4, 4),                
    tags="plateau_marge"
)

# Assure que le plateau est derrière tout et la marge juste au-dessus du plateau
canvas.tag_lower(canvas_plateau)
canvas.tag_raise(canvas_marge)  # la marge reste visible au-dessus du plateau

def draw_grid(event=None):
    canvas.delete("__grid__")
    width = canvas.winfo_width()
    height = canvas.winfo_height()

    # repositionner le plateau au centre
    cx = width/2
    cy = height/2
    x1 = cx - PLATEAU_W/2
    y1 = cy - PLATEAU_H/2
    x2 = cx + PLATEAU_W/2
    y2 = cy + PLATEAU_H/2
    canvas.coords(canvas_plateau, x1, y1, x2, y2)
    canvas.coords(canvas_marge, x1 + MARGIN_BORDER_PX, y1 + MARGIN_BORDER_PX, x2 - MARGIN_BORDER_PX, y2 - MARGIN_BORDER_PX)

    # dessiner la grille
    for x in range(0, width, GRID_SPACING):
        canvas.create_line(x, 0, x, height, fill="#1b1b1b", tags="__grid__")
    for y in range(0, height, GRID_SPACING):
        canvas.create_line(0, y, width, y, fill="#1b1b1b", tags="__grid__")


canvas.bind("<Configure>", draw_grid)

# ---------- START APP ----------
app.mainloop()
