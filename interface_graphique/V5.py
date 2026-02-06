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

slot_assignments = {slot_id: "None" for slot_id in OUTIL_SLOTS}

slot_windows = {}
# -------------------- CONFIG --------------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Dimensions par défaut des outils (en pixels sur le Canvas)
TOOLS = {
    "Plaque 24 puits": {"w_mm": 127.76, "h_mm": 85.48},
    "Réservoir eau": {"w_mm": 50, "h_mm": 30},
    "Réservoir lentilles": {"w_mm": 30, "h_mm": 30}
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
            for item in self.items:
                self.canvas.move(item, dx, dy)
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

def export_layout():
    out = []
    x0, y0, x1, y1 = canvas.coords(canvas_plateau)
    out.append({"type": "__background__", "coords_mm": [0, 0, PLATEAU_W_MM, PLATEAU_H_MM], "angle": 0})
    for obj in placed_objects:
        x1_px, y1_px, x2_px, y2_px = canvas.coords(obj.id)
        #conversion en mm
        x1_mm = (x1_px -x0) * PLATEAU_W_MM / (x1-x0)
        y1_mm = (y1_px -y0) * PLATEAU_H_MM / (y1-y0)
        x2_mm = (x2_px -x0) * PLATEAU_W_MM / (x1-x0)
        y2_mm = (y2_px -y0) * PLATEAU_H_MM / (y1-y0)

        w_px = x2_px - x1_px
        h_px = y2_px - y1_px

        # Vérification des contraintes au moment de l’export
        if not is_inside_plateau(x1_px, y1_px, w_px, h_px):
            print(f"{obj.name} en dehors du plateau → ignoré à l’export")
            continue

        if not is_free_space(x1_px, y1_px, w_px, h_px, ignore_id=obj.id):
            print(f"{obj.name} chevauche un autre objet → ignoré à l’export")
            continue



        out.append({"type": obj.name, "coords": [x1_mm, y1_mm, x2_mm, y2_mm], "angle": obj.angle})
    # Export des slots avec l’outil choisi
    for slot_id in OUTIL_SLOTS:
        out.append({
            "type": "slot_tool",
            "slot": slot_id,
            "tool": slot_assignments[slot_id]
        })
    
    with open("test1.json", "w") as f:
        json.dump(out, f, indent=4)
    print("Exporté → test1.json")

def load_json():
    try:
        with open("test1.json", "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("Aucun fichier test1_export.json trouvé.")
        return

    # --- Nettoyage du canvas ---
    for item in canvas.find_all():
        tags = canvas.gettags(item)
        if any(tag in TAGS_PROTEGES for tag in tags):
            continue
        canvas.delete(item)

    placed_objects.clear()

    # --- Récupération dimensions plateau ---
    x0_px, y0_px, x1_px, y1_px = canvas.coords(canvas_plateau)
    PLATEAU_W_PX = x1_px - x0_px
    PLATEAU_H_PX = y1_px - y0_px

    SCALE_X = PLATEAU_W_PX / PLATEAU_W_MM
    SCALE_Y = PLATEAU_H_PX / PLATEAU_H_MM

    # --- Réinitialiser les slots avant d'importer ---
    for slot_id in OUTIL_SLOTS:
        slot_assignments[slot_id] = "None"
        update_slot_display(slot_id)

    # --- Parcours du JSON ---
    for obj in data:
        obj_type = obj["type"]

        # --- Le plateau ---
        if obj_type == "__background__":
            coords_mm = obj["coords_mm"]
            x2 = x0_px + coords_mm[2] * SCALE_X
            y2 = y0_px + coords_mm[3] * SCALE_Y
            canvas.coords(canvas_plateau, x0_px, y0_px, x2, y2)
            continue

        # --- Import des Outils 
        if obj_type == "slot_tool":
             slot_id = obj.get("slot")
             outil_name = obj.get("tool", "None")

             if slot_id in OUTIL_SLOTS:
                    slot_assignments[slot_id] = outil_name
                    update_slot_display(slot_id)
             continue


        # --- Labwares / objets placés ---
        x1_mm, y1_mm, x2_mm, y2_mm = obj["coords"]

        x1_px = x0_px + x1_mm * SCALE_X
        y1_px = y0_px + y1_mm * SCALE_Y
        x2_px = x0_px + x2_mm * SCALE_X
        y2_px = y0_px + y2_mm * SCALE_Y

        w = x2_px - x1_px
        h = y2_px - y1_px

        create_placed_item(obj_type, x1_px, y1_px, w, h, obj.get("angle", 0))

       
            

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


def export_to_dxf(json_file="test1.json", out="plan.dxf"): #ne pas avoir le logciel deja ouvet sinon erreur
    try:
        data = json.load(open(json_file))
    except:
        print("Impossible d’ouvrir", json_file)
        return

    doc = ezdxf.new(dxfversion="R2010")
    doc.header['$INSUNITS'] = 4   # <--- IMPORTANT : millimètres !

    msp = doc.modelspace()

    def draw_rectangle(x1, y1, x2, y2, angle_deg=0, layer="default"):
        w = x2 - x1
        h = y2 - y1
        cx = x1 + w/2
        cy = y1 + h/2

        pts = [
            (x1 - cx, y1 - cy),
            (x2 - cx, y1 - cy),
            (x2 - cx, y2 - cy),
            (x1 - cx, y2 - cy)
        ]

        a = math.radians(angle_deg)
        rot = [
            (cx + px*math.cos(a) - py*math.sin(a),
             cy + px*math.sin(a) + py*math.cos(a))
            for (px, py) in pts
        ]

        msp.add_lwpolyline(rot, close=True, dxfattribs={"layer": layer})

    for obj in data:
        t = obj.get("type")
        coords = obj.get("coords_mm", obj.get("coords"))
        if coords is None:
            continue

        x1, y1, x2, y2 = coords
        angle = obj.get("angle", 0)

        if t == "__background__":
            draw_rectangle(x1, y1, x2, y2, angle, layer="plateau")
        elif t == "grid":
            pass
        else:
            draw_rectangle(x1, y1, x2, y2, angle, layer=t)

    doc.saveas(out)
    print(f"DXF exporté → {out}")

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
    
    # rectangle du slot
    rect = canvas.create_rectangle(
        pos["x"], pos["y"],
        pos["x"] + 60, pos["y"] + 90,
        fill="#dddddd",
        outline="#888",
        width=2,
        tags=f"outil_{slot_id}"
    )
    slot_rects[slot_id] = rect
    OUTIL_SLOTS[slot_id]["rect_id"] = rect

    # texte du slot
    txt = canvas.create_text(
        pos["x"] + 30,
        pos["y"] + 25,
        text=slot_assignments[slot_id],
        fill="black",
        tags=f"slot_text_{slot_id}"
    )
    canvas_slot_text_ids[slot_id] = txt
    OUTIL_SLOTS[slot_id]["text_id"] = txt

    # clic pour ouvrir la sélection d’outil
    canvas.tag_bind(f"slot_{slot_id}", "<Button-1>", lambda e, s=slot_id: select_outil(s))

    #baisse pour ne pas pouvoir l'enlever
    canvas.tag_lower(outils)#le rectangle
    canvas.tag_raise(slot_id)#le texte

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
