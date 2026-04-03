import customtkinter as ctk
import tkinter as tk
import json
import os
from constants import *
from models import DraggableObject
import exporter

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Configuration fenêtre
        self.title("Jubilee Bioreactor — Workspace & LED Control")
        self.geometry(f"{PLATEAU_W + 500}x{PLATEAU_H + 200}")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # État Deck (Original)
        self.selected_tool_name = None
        self.placed_objects = []
        self.slot_assignments = {slot_id: "None" for slot_id in OUTIL_SLOTS}
        self.slot_rects = {}
        self.slot_text_ids = {}
        self.slot_windows = {}

        # État LEDs (Internement 0-23 pour correspondre aux pins du PCA9685)
        self.light_values = {i: 0 for i in range(24)}
        self.led_sliders = {}
        self.led_vars = {}

        self.setup_ui()
        
    def setup_ui(self):
        # --- SIDEBAR (Banque d'outils) ---
        self.sidebar = ctk.CTkFrame(self, width=260)
        self.sidebar.pack(side="left", fill="y", padx=12, pady=12)

        ctk.CTkLabel(self.sidebar, text="Banque d'outils", font=("Arial", 18, "bold")).pack(pady=(6, 12))
        
        self.lbl_selected = ctk.CTkLabel(self.sidebar, text="Outil sélectionné:\nAucun", font=("Arial", 12))
        self.lbl_selected.pack(pady=(12, 8))

        for tname in LABWARE.keys():
            ctk.CTkButton(self.sidebar, text=tname, command=lambda n=tname: self.select_tool(n)).pack(fill="x", pady=4, padx=10)

        ctk.CTkLabel(self.sidebar, text="--- Actions ---").pack(pady=(20, 5))
        
        # --- BOUTON PLATEAU LUMINEUX ---
        ctk.CTkButton(self.sidebar, text="PLATEAU LUMINEUX", fg_color="#2e7d32", hover_color="#1b5e20", font=("Arial", 13, "bold"),
                      command=lambda: self.tabview.set("Contrôle Lumineux")).pack(fill="x", pady=10, padx=10)

        # Boutons originaux
        ctk.CTkButton(self.sidebar, text="Exporter JSON Deck", command=self.save_json, fg_color="#1976d2").pack(fill="x", pady=4, padx=10)
        ctk.CTkButton(self.sidebar, text="Charger JSON Deck", command=self.load_json).pack(fill="x", pady=4, padx=10)
        ctk.CTkButton(self.sidebar, text="Plan Lazer Cut", command=lambda: exporter.export_to_dxf()).pack(fill="x", pady=4, padx=10)
        ctk.CTkButton(self.sidebar, text="Plan gcode stylo", command=lambda: exporter.json_to_gcode("test1.json", "plan_jubilee.txt")).pack(fill="x", pady=4, padx=10)
        ctk.CTkButton(self.sidebar, text="Vider plateau", command=self.clear_canvas, fg_color="#c62828").pack(fill="x", pady=4, padx=10)

        # --- ZONE DROITE (Système d'onglets) ---
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(side="right", expand=True, fill="both", padx=12, pady=12)
        
        self.tab_workspace = self.tabview.add("Plan du Plateau")
        self.tab_leds = self.tabview.add("Contrôle Lumineux")

        self.setup_workspace_tab()
        self.setup_led_tab()

    def setup_workspace_tab(self):
        """Réintègre ton Canvas original dans le premier onglet"""
        self.canvas = tk.Canvas(self.tab_workspace, bg="#111213", highlightthickness=0)
        self.canvas.pack(expand=True, fill="both")

        self.canvas_plateau = self.canvas.create_rectangle(0, 0, PLATEAU_W, PLATEAU_H, fill="white", outline="#888888", width=2, tags="__background__")
        self.canvas_marge = self.canvas.create_rectangle(0, 0, 0, 0, fill="", outline="red", width=2, dash=(4, 4), tags="plateau_marge")

        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<Configure>", self.draw_grid)
        self.bind("<Delete>", self.delete_object_under_cursor)
        self.setup_tool_slots()

    def setup_led_tab(self):
        """L'onglet des 24 jauges (Grille 4x6)"""
        grid_container = ctk.CTkFrame(self.tab_leds, fg_color="transparent")
        grid_container.pack(expand=True, fill="both", padx=10, pady=10)

        for i in range(24):
            row, col = divmod(i, 6)
            card = ctk.CTkFrame(grid_container, border_width=1, border_color="#444")
            card.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")

            # MODIFICATION ICI : On affiche Bac {i+1} pour débuter à 1 et finir à 24
            ctk.CTkLabel(card, text=f"Bac {i + 1}", font=("Arial", 12, "bold")).pack(pady=(5, 0))

            # Champ texte (synchronisé avec l'index i)
            v = ctk.StringVar(value="0")
            self.led_vars[i] = v
            entry = ctk.CTkEntry(card, textvariable=v, width=60, justify="center")
            entry.pack(pady=2)
            entry.bind("<Return>", lambda e, idx=i: self.sync_entry_to_slider(idx))

            # Slider (synchronisé avec l'index i)
            slider = ctk.CTkSlider(card, from_=0, to=MAX_ILLUMINANCE, number_of_steps=MAX_ILLUMINANCE, width=120,
                                   command=lambda val, idx=i: self.sync_slider_to_entry(idx, val))
            slider.set(0)
            slider.pack(pady=(0, 10), padx=5)
            self.led_sliders[i] = slider

        # Bouton Export LED
        ctk.CTkButton(self.tab_leds, text="EXPORTER CONFIGURATION LED (ESP32)", fg_color="#2e7d32", 
                      height=40, font=("Arial", 14, "bold"), command=self.export_led_config).pack(pady=20)

    # --- SYNCHRONISATION LED ---
    def sync_slider_to_entry(self, idx, val):
        self.light_values[idx] = int(val)
        self.led_vars[idx].set(str(int(val)))

    def sync_entry_to_slider(self, idx):
        try:
            val = int(self.led_vars[idx].get())
            val = max(0, min(MAX_ILLUMINANCE, val))
            self.light_values[idx] = val
            self.led_sliders[idx].set(val)
            self.led_vars[idx].set(str(val))
        except:
            self.led_vars[idx].set(str(int(self.led_sliders[idx].get())))

    def export_led_config(self):
        # On exporte le dictionnaire (0-23) pour que l'ESP32 sache quel pin piloter
        exporter.export_led_pattern(self.light_values)
        tk.messagebox.showinfo("Succès", "Pattern LED exporté pour l'ESP32 !")

    # --- LOGIQUE DECK ORIGINALE ---
    def select_tool(self, name):
        self.selected_tool_name = name
        self.lbl_selected.configure(text=f"Outil sélectionné:\n{name}")
        self.tabview.set("Plan du Plateau")

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

    def on_canvas_click(self, event):
        if self.selected_tool_name is None: return
        json_file = LABWARE[self.selected_tool_name]["json"]
        from models import load_labware_dims
        data = load_labware_dims(json_file)
        if not data: return
        w_px, h_px = data["dimensions"]["xDimension"] * MM_TO_PIX, data["dimensions"]["yDimension"] * MM_TO_PIX
        x, y = event.x - w_px/2, event.y - h_px/2
        if not self.is_inside_plateau(x, y, w_px, h_px) or not self.is_free_space(x, y, w_px, h_px): return
        color = "#1f6aa5" if "Plaque" in self.selected_tool_name else ("#2e7d32" if "eau" in self.selected_tool_name.lower() else "#c2185b")
        obj = DraggableObject(self.canvas, x, y, json_file, color, self.selected_tool_name, self.is_free_space, self.is_inside_plateau)
        self.placed_objects.append(obj)
        self.selected_tool_name = None
        self.lbl_selected.configure(text="Outil sélectionné:\nAucun")

    def is_inside_plateau(self, x1, y1, w, h):
        px1, py1, px2, py2 = self.canvas.coords(self.canvas_plateau)
        return (x1 >= px1 + MARGIN_BORDER_PX and y1 >= py1 + MARGIN_BORDER_PX and 
                x1 + w <= px2 - MARGIN_BORDER_PX and y1 + h <= py2 - MARGIN_BORDER_PX)

    def is_free_space(self, x1, y1, w, h, ignore_id=None):
        for other in self.placed_objects:
            if other.id == ignore_id: continue
            ox1, oy1, ox2, oy2 = self.canvas.coords(other.id)
            if not (x1 + w < ox1 - MARGIN_BETWEEN_OBJECTS_PX or x1 > ox2 + MARGIN_BETWEEN_OBJECTS_PX or 
                    y1 + h < oy1 - MARGIN_BETWEEN_OBJECTS_PX or y1 > oy2 + MARGIN_BETWEEN_OBJECTS_PX):
                return False
        return True

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
        if slot_id in self.slot_windows: self.slot_windows[slot_id].lift(); return
        win = ctk.CTkToplevel(self)
        win.title(f"Config Slot {slot_id}"); win.geometry("200x150")
        self.slot_windows[slot_id] = win
        combo = ctk.CTkComboBox(win, values=OUTILS_LISTE)
        combo.set(self.slot_assignments[slot_id]); combo.pack(pady=10)
        def validate():
            val = combo.get()
            self.slot_assignments[slot_id] = val
            self.canvas.itemconfig(self.slot_text_ids[slot_id], text=val)
            self.canvas.itemconfig(self.slot_rects[slot_id], fill="#aaffaa" if val != "None" else "#dddddd")
            win.destroy(); del self.slot_windows[slot_id]
        ctk.CTkButton(win, text="Valider", command=validate).pack(pady=5)

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
        self.canvas.tag_lower("__grid__"); self.canvas.tag_lower(self.canvas_plateau)

    def clear_canvas(self):
        for obj in self.placed_objects:
            for item in obj.items: self.canvas.delete(item)
        self.placed_objects.clear()

    def save_json(self):
        exporter.export_layout(self.placed_objects, self.slot_assignments, self.canvas, self.canvas_plateau)

    def load_json(self):
        pass

if __name__ == "__main__":
    app = App()
    app.mainloop()