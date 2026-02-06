import customtkinter as ctk
import tkinter as tk
import json
#crétion du plan dxf pour lazer cut
import ezdxf
import math

#convertir les milimetres en pixels
MM_TO_PIX = 3 
#dimension plateau
PLATEAU_W = 305 * MM_TO_PIX
PLATEAU_H = 305 * MM_TO_PIX

# Conversion pixels → mm 
# a ajuster
PX_TO_MM = 0.25      # exemple : 1px = 0.25 mm


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
    for obj in placed_objects:
        x1, y1, x2, y2 = canvas.coords(obj.id)
        out.append({"type": obj.name, "coords": [x1, y1, x2, y2], "angle": obj.angle})
    with open("workspace_export.json", "w") as f:
        json.dump(out, f, indent=4)
    print("Exporté → workspace_export.json")

def load_json():
    try:
        with open("workspace_export.json", "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("Aucun fichier workspace_export.json trouvé.")
        return
    for item in canvas.find_all():
        tags = canvas.gettags(item)
        if "__background__" not in tags and "__grid__" not in tags:
            canvas.delete(item)
    placed_objects.clear()
    for obj in data:
        x1, y1, x2, y2 = obj["coords"]
        w = x2 - x1
        h = y2 - y1
        create_placed_item(obj["type"], x1, y1, w, h, obj.get("angle",0))

def clear_canvas():
     # supprime tous les objets sauf le plateau (__background__) et la grille (__grid__)
    for item in canvas.find_all():
        tags = canvas.gettags(item)
        if "__background__" not in tags and "__grid__" not in tags:
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


#Ficher pour Lazer cut
def export_to_dxf(json_file="workspace_export.json", out="plan.dxf"):
    # ---- Charger le JSON ----
    try:
        data = json.load(open(json_file))
    except:
        print("Impossible d’ouvrir", json_file)
        return

    # ---- Nouveau DXF ----
    doc = ezdxf.new(dxfversion="R2010")
    msp = doc.modelspace()

    # ---- Fonction : dessiner rectangle ----
    def draw_rectangle(x1, y1, x2, y2, angle_deg=0, layer="default"):
        # Conversion px → mm
        x1 *= PX_TO_MM
        y1 *= PX_TO_MM
        x2 *= PX_TO_MM
        y2 *= PX_TO_MM

        w = x2 - x1
        h = y2 - y1

        # Centre
        cx = x1 + w/2
        cy = y1 + h/2

        # Sommets avant rotation
        pts = [
            (x1 - cx, y1 - cy),
            (x2 - cx, y1 - cy),
            (x2 - cx, y2 - cy),
            (x1 - cx, y2 - cy),
        ]

        # Rotation
        a = math.radians(angle_deg)
        rot = [(cx + px*math.cos(a) - py*math.sin(a),
                cy + px*math.sin(a) + py*math.cos(a)) for (px, py) in pts]

        msp.add_lwpolyline(rot, close=True, dxfattribs={"layer": layer})

    # ---- Parcourir les objets JSON ----
    for obj in data:
        t = obj.get("type")
        if "coords" in obj:
            x1, y1, x2, y2 = obj["coords"]
            angle = obj.get("angle", 0)

            # Plateau
            if t == "__background__":
                draw_rectangle(x1, y1, x2, y2, angle, layer="plateau")

            # Grille
            elif t == "grid":
                pass  # tu veux peut-être dessiner des lignes → possible aussi

            # Labwares & objets
            else:
                draw_rectangle(x1, y1, x2, y2, angle, layer=t)

    # ---- Sauvegarde ----
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

# ---------- CANVAS ----------
canvas_frame = ctk.CTkFrame(app)
canvas_frame.pack(side="right", expand=True, fill="both", padx=12, pady=12)

canvas = tk.Canvas(canvas_frame, bg="#111213", highlightthickness=0)
canvas.pack(expand=True, fill="both")

# ---------- EVENTS ----------
app.bind("<Delete>", delete_object_under_cursor)

# ---------- CANVAS CLICK TO PLACE ----------
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

canvas_plateau = canvas.create_rectangle(0, 0, PLATEAU_W, PLATEAU_H, fill="white", outline="#888888", width=2,  tags="__background__")
canvas.tag_lower(canvas_plateau)  # derrière tous les objets

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

    # dessiner la grille
    for x in range(0, width, GRID_SPACING):
        canvas.create_line(x, 0, x, height, fill="#1b1b1b", tags="__grid__")
    for y in range(0, height, GRID_SPACING):
        canvas.create_line(0, y, width, y, fill="#1b1b1b", tags="__grid__")

canvas.bind("<Configure>", draw_grid)

# ---------- START APP ----------
app.mainloop()
