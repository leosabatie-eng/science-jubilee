import customtkinter as ctk
import tkinter as tk
import json
from constants import *
from models import DraggableObject
import exporter

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Configuration fenêtre
        self.title("Virtual Workspace — Interface complète")
        self.geometry(f"{PLATEAU_W + 400}x{PLATEAU_H + 150}")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # État de l'application
        self.selected_tool_name = None
        self.placed_objects = []
        self.slot_assignments = {slot_id: "None" for slot_id in OUTIL_SLOTS}
        self.slot_rects = {}
        self.slot_text_ids = {}
        self.slot_windows = {}

        self.setup_ui()
        
    def setup_ui(self):
        # --- SIDEBAR (Banque d'outils) ---
        self.sidebar = ctk.CTkFrame(self, width=260)
        self.sidebar.pack(side="left", fill="y", padx=12, pady=12)

        ctk.CTkLabel(self.sidebar, text="Banque d'outils", font=("Arial", 18)).pack(pady=(6, 12))
        
        self.lbl_selected = ctk.CTkLabel(self.sidebar, text="Outil sélectionné:\nAucun", font=("Arial", 12))
        self.lbl_selected.pack(pady=(12, 8))

        # Boutons des outils labware
        for tname in LABWARE.keys():
            ctk.CTkButton(self.sidebar, text=tname, 
                          command=lambda n=tname: self.select_tool(n)).pack(fill="x", pady=4)

        # Boutons d'actions
        ctk.CTkLabel(self.sidebar, text="--- Actions ---").pack(pady=(20, 5))
        ctk.CTkButton(self.sidebar, text="Exporter JSON", command=self.save_json, fg_color="#1976d2").pack(fill="x", pady=4)
        ctk.CTkButton(self.sidebar, text="Charger JSON", command=self.load_json).pack(fill="x", pady=4)
        ctk.CTkButton(self.sidebar, text="Plan Lazer Cut", command=lambda: exporter.export_to_dxf()).pack(fill="x", pady=4)
        ctk.CTkButton(self.sidebar, text="Plan gcode stylo", command=lambda: exporter.json_to_gcode("test1.json", "mon_plateau.gcode")).pack(fill="x", pady=4)
        ctk.CTkButton(self.sidebar, text="Vider plateau", command=self.clear_canvas, fg_color="#c62828").pack(fill="x", pady=4)

        ctk.CTkLabel(self.sidebar, text="Raccourcis:\n- Clic gauche: placer/déplacer\n- Clic droit: rotation 90°\n- Suppr: supprimer sous curseur",
                     wraplength=230, justify="left", font=("Arial", 10)).pack(pady=20)

        # --- CANVAS (Zone de travail) ---
        self.canvas_frame = ctk.CTkFrame(self)
        self.canvas_frame.pack(side="right", expand=True, fill="both", padx=12, pady=12)

        self.canvas = tk.Canvas(self.canvas_frame, bg="#111213", highlightthickness=0)
        self.canvas.pack(expand=True, fill="both")

        # Éléments fixes du canvas
        self.canvas_plateau = self.canvas.create_rectangle(0, 0, PLATEAU_W, PLATEAU_H, fill="white", outline="#888888", width=2, tags="__background__")
        self.canvas_marge = self.canvas.create_rectangle(0, 0, 0, 0, fill="", outline="red", width=2, dash=(4, 4), tags="plateau_marge")

        # Bindings
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<Configure>", self.draw_grid)
        self.bind("<Delete>", self.delete_object_under_cursor)

        # Création des slots outils (Parc à outils)
        self.setup_tool_slots()

    def setup_tool_slots(self):
        for slot_id, pos in OUTIL_SLOTS.items():
            tag = f"outil_{slot_id}"
            rect = self.canvas.create_rectangle(pos["x"] + 1200, pos["y"], pos["x"] + 1260, pos["y"] + 90, 
                                                fill="#dddddd", outline="#888", width=2, tags=(tag, "slot_outil_rect"))
            txt = self.canvas.create_text(pos["x"] + 1230, pos["y"] + 25, text="None", fill="black", 
                                          font=("Arial", 10, "bold"), tags=(f"slot_text_{slot_id}", "slot_outil_text"))
            
            self.slot_rects[slot_id] = rect
            self.slot_text_ids[slot_id] = txt
            self.canvas.tag_bind(tag, "<Button-1>", lambda e, s=slot_id: self.open_slot_config(s))

    # --- LOGIQUE MÉTIER ---

    def select_tool(self, name):
        self.selected_tool_name = name
        self.lbl_selected.configure(text=f"Outil sélectionné:\n{name}")

    def is_inside_plateau(self, x1, y1, w, h):
        px1, py1, px2, py2 = self.canvas.coords(self.canvas_plateau)
        return (x1 >= px1 + MARGIN_BORDER_PX and y1 >= py1 + MARGIN_BORDER_PX and 
                x1 + w <= px2 - MARGIN_BORDER_PX and y1 + h <= py2 - MARGIN_BORDER_PX)

    def is_free_space(self, x1, y1, w, h, ignore_id=None):
        for other in self.placed_objects:
            if other.id == ignore_id: continue
            ox1, oy1, ox2, oy2 = self.canvas.coords(other.id)
            # Collision avec marge de sécurité
            if not (x1 + w < ox1 - MARGIN_BETWEEN_OBJECTS_PX or x1 > ox2 + MARGIN_BETWEEN_OBJECTS_PX or 
                    y1 + h < oy1 - MARGIN_BETWEEN_OBJECTS_PX or y1 > oy2 + MARGIN_BETWEEN_OBJECTS_PX):
                return False
        return True

    def on_canvas_click(self, event):
        # On vérifie si un outil est sélectionné
        if self.selected_tool_name is None:
            return

        # 1. Conversion mm → pixels
        w_mm = LABWARE[self.selected_tool_name]["w_mm"]
        h_mm = LABWARE[self.selected_tool_name]["h_mm"]
        w_px = w_mm * MM_TO_PIX
        h_px = h_mm * MM_TO_PIX

        # Calcul de la position (centré sur la souris)
        x = event.x - w_px/2
        y = event.y - h_px/2

        if not self.is_inside_plateau(x, y, w_px, h_px):
            print("Placement impossible : Hors des limites du plateau.")
            return 
        
        if not self.is_free_space(x, y, w_px, h_px):
            print("Placement impossible : Espace déjà occupé.")
            return 

        color = "#1f6aa5" if "Plaque" in self.selected_tool_name else ("#2e7d32" if "eau" in self.selected_tool_name.lower() else "#c2185b")
        
        obj = DraggableObject(
            self.canvas, 
            x, y, 
            w_px, h_px, 
            color, 
            self.selected_tool_name, 
            self.is_free_space, 
            self.is_inside_plateau
        )
        self.placed_objects.append(obj)

        # 5. Reset de la sélection
        self.selected_tool_name = None
        self.lbl_selected.configure(text="Outil sélectionné:\nAucun")

    def delete_object_under_cursor(self, event):
        x, y = self.canvas.winfo_pointerxy()
        cx = self.canvas.canvasx(x - self.canvas.winfo_rootx())
        cy = self.canvas.canvasy(y - self.canvas.winfo_rooty())
        items = self.canvas.find_overlapping(cx, cy, cx, cy)
        for obj in self.placed_objects:
            if obj.id in items:
                for item in obj.items: self.canvas.delete(item)
                self.placed_objects.remove(obj)
                break

    def open_slot_config(self, slot_id):
        if slot_id in self.slot_windows: 
            self.slot_windows[slot_id].lift()
            return
        
        win = ctk.CTkToplevel(self)
        win.title(f"Config Slot {slot_id}")
        win.geometry("200x150")
        self.slot_windows[slot_id] = win
        
        combo = ctk.CTkComboBox(win, values=OUTILS_LISTE)
        combo.set(self.slot_assignments[slot_id])
        combo.pack(pady=10)

        def validate():
            val = combo.get()
            self.slot_assignments[slot_id] = val
            self.canvas.itemconfig(self.slot_text_ids[slot_id], text=val)
            self.canvas.itemconfig(self.slot_rects[slot_id], fill="#aaffaa" if val != "None" else "#dddddd")
            win.destroy()
            del self.slot_windows[slot_id]

        ctk.CTkButton(win, text="Valider", command=validate).pack(pady=5)
        win.protocol("WM_DELETE_WINDOW", lambda: self.slot_windows.pop(slot_id).destroy())

    def draw_grid(self, event=None):
        self.canvas.delete("__grid__")
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        cx, cy = w/2, h/2
        x1, y1 = cx - PLATEAU_W/2, cy - PLATEAU_H/2
        x2, y2 = cx + PLATEAU_W/2, cy + PLATEAU_H/2
        
        self.canvas.coords(self.canvas_plateau, x1, y1, x2, y2)
        self.canvas.coords(self.canvas_marge, x1 + MARGIN_BORDER_PX, y1 + MARGIN_BORDER_PX, x2 - MARGIN_BORDER_PX, y2 - MARGIN_BORDER_PX)
        
        for i in range(0, w, 20): self.canvas.create_line(i, 0, i, h, fill="#1b1b1b", tags="__grid__")
        for i in range(0, h, 20): self.canvas.create_line(0, i, w, i, fill="#1b1b1b", tags="__grid__")
        self.canvas.tag_lower("__grid__")
        self.canvas.tag_lower(self.canvas_plateau)

    def clear_canvas(self):
        for obj in self.placed_objects:
            for item in obj.items: self.canvas.delete(item)
        self.placed_objects.clear()

    def save_json(self):
        exporter.export_layout(self.placed_objects, self.slot_assignments, self.canvas, self.canvas_plateau)

    def load_json(self):
        try:
            with open("test1.json", "r", encoding="utf-8") as f:
                data = json.load(f)
        except: return
        
        self.clear_canvas()
        x0, y0, x1, y1 = self.canvas.coords(self.canvas_plateau)
        scale = (x1 - x0) / PLATEAU_W_MM
        bl_y = y0 + (y1 - y0)

        for s in data.get("slots", {}).values():
            if not s.get("has_labware"): continue
            x_px = x0 + (s["coordinates"][0] * scale) - (s["width"] * scale / 2)
            y_px = bl_y - (s["coordinates"][1] * scale) - (s["length"] * scale / 2)
            
            # Retrouver le nom via le JSON
            name = next((k for k, v in LABWARE.items() if v["json"] == s["labware"]), "Labware")
            obj = DraggableObject(self.canvas, x_px, y_px, s["width"]*scale, s["length"]*scale, "#1f6aa5", name, self.is_free_space, self.is_inside_plateau)
            self.placed_objects.append(obj)

        for sid, tool in data.get("tool_slots", {}).items():
            sid = int(sid)
            self.slot_assignments[sid] = tool
            self.canvas.itemconfig(self.slot_text_ids[sid], text=tool)
            self.canvas.itemconfig(self.slot_rects[sid], fill="#aaffaa" if tool != "None" else "#dddddd")

if __name__ == "__main__":
    app = App()
    app.mainloop()