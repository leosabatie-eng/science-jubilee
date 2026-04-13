"""
=========================================================================================
Projet      : Jubilee Bioreactor GUI
Fichier     : app.py
Auteur      : [SABATIÉ Léo / Projet industriel ROB4]
Date        : 10 Avril 2026
Description : Point d'entrée principal de l'application. 
              Gère l'interface utilisateur (CustomTkinter), le placement des labwares 
              sur le deck et le contrôle individuel de l'intensité des 24 LEDs.
=========================================================================================
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import json
import os

# Imports locaux
from constants import *
from models import DraggableObject, load_labware_dims
import exporter

class App(ctk.CTk):
    """
    Application principale gérant le Workspace (Canvas) et le panneau de contrôle LED.
    """
    def __init__(self):
        super().__init__()
        
        # --- Configuration de la fenêtre ---
        self.title("Jubilee Bioreactor — Workspace & LED Control")
        self.geometry(f"{PLATEAU_W + 400}x{PLATEAU_H + 150}")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # --- État du Système (Backend de l'UI) ---
        self.selected_tool_name = None
        self.placed_objects = []
        self.slot_assignments = {slot_id: "None" for slot_id in OUTIL_SLOTS}
        
        # Références aux IDs graphiques
        self.slot_rects = {}
        self.slot_text_ids = {}
        self.slot_windows = {}

        # État des LEDs (Index 0-23 pour adressage direct PCA9685)
        self.light_values = {i: 0 for i in range(24)}
        self.led_sliders = {}
        self.led_vars = {}

        # Initialisation de l'interface
        self.setup_ui()
        
    def setup_ui(self):
        """Initialise la structure globale de l'interface (Sidebar + Onglets)."""
        
        # --- SIDEBAR (Banque d'outils et Actions) ---
        self.sidebar = ctk.CTkFrame(self, width=260)
        self.sidebar.pack(side="left", fill="y", padx=12, pady=12)

        ctk.CTkLabel(self.sidebar, text="Banque d'outils", font=("Arial", 18, "bold")).pack(pady=(6, 12))
        
        self.lbl_selected = ctk.CTkLabel(self.sidebar, text="Outil sélectionné:\nAucun", font=("Arial", 12))
        self.lbl_selected.pack(pady=(12, 8))

        # Génération dynamique des boutons de labware
        for tname in LABWARE.keys():
            ctk.CTkButton(self.sidebar, text=tname, 
                          command=lambda n=tname: self.select_tool(n)).pack(fill="x", pady=4, padx=10)

        ctk.CTkLabel(self.sidebar, text="--- Actions ---").pack(pady=(20, 5))
        
        # Boutons d'accès rapide et d'export
        ctk.CTkButton(self.sidebar, text="PLATEAU LUMINEUX", fg_color="#2e7d32", hover_color="#1b5e20", 
                      font=("Arial", 13, "bold"),
                      command=lambda: self.tabview.set("Contrôle Lumineux")).pack(fill="x", pady=10, padx=10)

        ctk.CTkButton(self.sidebar, text="Exporter Configuration", command=self.save_json, 
                      fg_color="#1976d2").pack(fill="x", pady=4, padx=10)
        
        ctk.CTkButton(self.sidebar, text="Charger Configuration", command=self.load_json).pack(fill="x", pady=4, padx=10)
        
        ctk.CTkButton(self.sidebar, text="Plan Laser Cut (DXF)", 
                      command=lambda: exporter.export_to_dxf("experience.json")).pack(fill="x", pady=4, padx=10)
        
        ctk.CTkButton(self.sidebar, text="G-code Dessin (Stylo)", 
                      command=lambda: exporter.json_to_gcode("experience.json", "plan_jubilee.txt")).pack(fill="x", pady=4, padx=10)
        
        ctk.CTkButton(self.sidebar, text="Vider plateau", command=self.clear_canvas, 
                      fg_color="#c62828").pack(fill="x", pady=4, padx=10)

        # Aide mémoire
        ctk.CTkLabel(self.sidebar, text="Raccourcis :\n- Clic gauche : Placer/Déplacer\n- Clic droit : Rotation 90°\n- Suppr : Supprimer l'objet",
                     wraplength=220, justify="left", font=("Arial", 10), text_color="gray").pack(pady=20)

        # --- ZONE PRINCIPALE (Navigation par onglets) ---
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(side="right", expand=True, fill="both", padx=12, pady=12)
        
        self.tab_workspace = self.tabview.add("Plan du Plateau")
        self.tab_leds = self.tabview.add("Contrôle Lumineux")

        self.setup_workspace_tab()
        self.setup_led_tab()

    def setup_workspace_tab(self):
        """Configure l'espace de travail interactif (Canvas)."""
        self.canvas = tk.Canvas(self.tab_workspace, bg="#111213", highlightthickness=0)
        self.canvas.pack(expand=True, fill="both")

        # Couches graphiques de base
        self.canvas_plateau = self.canvas.create_rectangle(0, 0, PLATEAU_W, PLATEAU_H, 
                                                           fill="white", outline="#888888", width=2, tags="__background__")
        self.canvas_marge = self.canvas.create_rectangle(0, 0, 0, 0, 
                                                         fill="", outline="red", width=2, dash=(4, 4), tags="plateau_marge")

        # Événements Canvas
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<Configure>", self.draw_grid)
        self.bind("<Delete>", self.delete_object_under_cursor)

        self.setup_tool_slots()

    def setup_led_tab(self):
        """Génère une grille de 24 contrôleurs (Entry + Slider) pour les LEDs."""
        grid_container = ctk.CTkFrame(self.tab_leds, fg_color="transparent")
        grid_container.pack(expand=True, fill="both", padx=10, pady=10)

        for i in range(24):
            row, col = divmod(i, 6)
            card = ctk.CTkFrame(grid_container, border_width=1, border_color="#444")
            card.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")

            ctk.CTkLabel(card, text=f"Puit {i + 1}", font=("Arial", 12, "bold")).pack(pady=(5, 0))

            # Synchronisation texte/valeur
            v = ctk.StringVar(value="0")
            self.led_vars[i] = v
            entry = ctk.CTkEntry(card, textvariable=v, width=60, justify="center")
            entry.pack(pady=2)
            entry.bind("<Return>", lambda e, idx=i: self.sync_entry_to_slider(idx))

            # Slider d'intensité
            slider = ctk.CTkSlider(card, from_=0, to=MAX_ILLUMINANCE, number_of_steps=MAX_ILLUMINANCE, width=120,
                                   command=lambda val, idx=i: self.sync_slider_to_entry(idx, val))
            slider.set(0)
            slider.pack(pady=(0, 10), padx=5)
            self.led_sliders[i] = slider

        ctk.CTkButton(self.tab_leds, text="EXPORTER CONFIGURATION LED (ESP32)", fg_color="#2e7d32", 
                      height=40, font=("Arial", 14, "bold"), command=self.export_led_config).pack(pady=20)

    # --- MÉTHODES DE SYNCHRONISATION ---

    def sync_slider_to_entry(self, idx, val):
        """Met à jour le champ texte lors du mouvement du slider."""
        self.light_values[idx] = int(val)
        self.led_vars[idx].set(str(int(val)))

    def sync_entry_to_slider(self, idx):
        """Met à jour le slider lors de la validation manuelle (Entrée) du champ texte."""
        try:
            val = int(self.led_vars[idx].get())
            val = max(0, min(MAX_ILLUMINANCE, val))
            self.light_values[idx] = val
            self.led_sliders[idx].set(val)
            self.led_vars[idx].set(str(val))
        except ValueError:
            # Reset à la dernière valeur valide du slider en cas de saisie incorrecte
            self.led_vars[idx].set(str(int(self.led_sliders[idx].get())))

    def export_led_config(self):
        """Déclenche l'exportation du pattern lumineux."""
        exporter.export_led_pattern(self.light_values)
        messagebox.showinfo("Exportation", "Le pattern LED a été exporté avec succès pour l'ESP32.")

    # --- LOGIQUE DU WORKSPACE (DECK) ---

    def select_tool(self, name):
        """Sélectionne un labware dans la banque et bascule sur l'onglet Plan."""
        self.selected_tool_name = name
        self.lbl_selected.configure(text=f"Outil sélectionné:\n{name}")
        self.tabview.set("Plan du Plateau")

    def setup_tool_slots(self):
        """Affiche les emplacements de stockage des outils (Tools) sur le côté."""
        for slot_id, pos in OUTIL_SLOTS.items():
            tag = f"outil_{slot_id}"
            # Décalage horizontal pour sortir du plateau principal
            rect = self.canvas.create_rectangle(pos["x"] + 1200, pos["y"], pos["x"] + 1260, pos["y"] + 90, 
                                                fill="#dddddd", outline="#888", width=2, tags=(tag, "slot_outil_rect"))
            txt = self.canvas.create_text(pos["x"] + 1230, pos["y"] + 25, text="None", fill="black", 
                                          font=("Arial", 10, "bold"), tags=(f"slot_text_{slot_id}", "slot_outil_text")) 
            
            self.slot_rects[slot_id] = rect
            self.slot_text_ids[slot_id] = txt
            self.canvas.tag_bind(tag, "<Button-1>", lambda e, s=slot_id: self.open_slot_config(s))

    def on_canvas_click(self, event):
        """Gère le placement d'un nouveau labware sur le plateau."""
        if self.selected_tool_name is None: return
        
        json_file = LABWARE[self.selected_tool_name]["json"]
        data = load_labware_dims(json_file)
        if not data: return

        # Conversion dimensions JSON -> Pixels
        w_px = data["dimensions"]["xDimension"] * MM_TO_PIX
        h_px = data["dimensions"]["yDimension"] * MM_TO_PIX
        
        # Positionnement centré sur le curseur
        x, y = event.x - w_px/2, event.y - h_px/2

        # Validation spatiale
        if not self.is_inside_plateau(x, y, w_px, h_px) or not self.is_free_space(x, y, w_px, h_px):
            return

        # Attribution couleur par type
        color = "#1f6aa5" if "Plaque" in self.selected_tool_name else ("#2e7d32" if "eau" in self.selected_tool_name.lower() else "#c2185b")
        
        obj = DraggableObject(self.canvas, x, y, json_file, color, self.selected_tool_name, 
                              self.is_free_space, self.is_inside_plateau)
        self.placed_objects.append(obj)
        
        # Reset sélection
        self.selected_tool_name = None
        self.lbl_selected.configure(text="Outil sélectionné:\nAucun")

    def is_inside_plateau(self, x1, y1, w, h):
        """Vérifie si le rectangle est à l'intérieur de la zone de sécurité (marge rouge)."""
        px1, py1, px2, py2 = self.canvas.coords(self.canvas_plateau)
        return (x1 >= px1 + MARGIN_BORDER_PX and y1 >= py1 + MARGIN_BORDER_PX and 
                x1 + w <= px2 - MARGIN_BORDER_PX and y1 + h <= py2 - MARGIN_BORDER_PX)

    def is_free_space(self, x1, y1, w, h, ignore_id=None):
        """Vérifie l'absence de collision avec les autres objets placés."""
        for other in self.placed_objects:
            if other.id == ignore_id: continue
            ox1, oy1, ox2, oy2 = self.canvas.coords(other.id)
            # Test d'intersection avec marge entre objets
            if not (x1 + w < ox1 - MARGIN_BETWEEN_OBJECTS_PX or x1 > ox2 + MARGIN_BETWEEN_OBJECTS_PX or 
                    y1 + h < oy1 - MARGIN_BETWEEN_OBJECTS_PX or y1 > oy2 + MARGIN_BETWEEN_OBJECTS_PX):
                return False
        return True

    def delete_object_under_cursor(self, event):
        """Supprime l'objet labware se trouvant sous le curseur de la souris."""
        x, y = self.winfo_pointerxy()
        cx = self.canvas.canvasx(x - self.canvas.winfo_rootx())
        cy = self.canvas.canvasy(y - self.canvas.winfo_rooty())
        
        items = self.canvas.find_overlapping(cx, cy, cx, cy)
        for obj in self.placed_objects:
            if obj.id in items:
                for item in obj.items: self.canvas.delete(item)
                self.placed_objects.remove(obj)
                break

    def open_slot_config(self, slot_id):
        """Ouvre une fenêtre contextuelle pour assigner un outil à un slot du changeur."""
        if slot_id in self.slot_windows: 
            self.slot_windows[slot_id].lift()
            return
        
        win = ctk.CTkToplevel(self)
        win.title(f"Config Slot {slot_id}")
        win.geometry("240x160")
        self.slot_windows[slot_id] = win
        
        ctk.CTkLabel(win, text="Outil à charger :").pack(pady=(10, 0))
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
        """Redessine la grille de fond et centre le plateau lors du redimensionnement."""
        self.canvas.delete("__grid__")
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        
        cx, cy = w/2, h/2
        x1, y1 = cx - PLATEAU_W/2, cy - PLATEAU_H/2
        x2, y2 = cx + PLATEAU_W/2, cy + PLATEAU_H/2
        
        self.canvas.coords(self.canvas_plateau, x1, y1, x2, y2)
        self.canvas.coords(self.canvas_marge, x1 + MARGIN_BORDER_PX, y1 + MARGIN_BORDER_PX, 
                           x2 - MARGIN_BORDER_PX, y2 - MARGIN_BORDER_PX)
        
        # Dessin des lignes de grille (pas de 20px)
        for i in range(0, w, 20): self.canvas.create_line(i, 0, i, h, fill="#1b1b1b", tags="__grid__")
        for i in range(0, h, 20): self.canvas.create_line(0, i, w, i, fill="#1b1b1b", tags="__grid__")
        
        self.canvas.tag_lower("__grid__")
        self.canvas.tag_lower(self.canvas_plateau)

    def clear_canvas(self):
        """Réinitialise complètement le plateau."""
        if messagebox.askyesno("Confirmation", "Voulez-vous vraiment vider tout le plateau ?"):
            for obj in self.placed_objects:
                for item in obj.items: self.canvas.delete(item)
            self.placed_objects.clear()

    def save_json(self):
        """Exporte l'état actuel du deck vers experience.json via le module exporter."""
        exporter.export_layout(self.placed_objects, self.slot_assignments, self.canvas, self.canvas_plateau)
        messagebox.showinfo("Exportation", "Configuration du deck sauvegardée.")

    def load_json(self):
        """Charge une configuration existante et recrée les objets sur le canvas."""
        try:
            with open("experience.json", "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de charger le fichier : {e}")
            return
        
        self.clear_canvas()
        x0, y0, x1, y1 = self.canvas.coords(self.canvas_plateau)
        scale = (x1 - x0) / PLATEAU_W_MM
        bl_y = y0 + (y1 - y0) # Base Line Y

        # Recréation des Labwares
        for s in data.get("slots", {}).values():
            if not s.get("has_labware"): continue
            
            # Repositionnement inverse (MM -> Pixels)
            x_px = x0 + (s["coordinates"][0] * scale) - (s["width"] * scale / 2)
            y_px = bl_y - (s["coordinates"][1] * scale) - (s["length"] * scale / 2)
            
            # Identification du nom d'affichage
            name = next((k for k, v in LABWARE.items() if v["json"] == s["labware"]), "Labware")
            
            obj = DraggableObject(self.canvas, x_px, y_px, s["labware"], "#1f6aa5", name, 
                                  self.is_free_space, self.is_inside_plateau)
            self.placed_objects.append(obj)

        # Recréation des Tool Slots
        for sid, tool in data.get("tool_slots", {}).items():
            sid_int = int(sid) + 1 # Compensation de l'index 0-based utilisé dans l'export
            if sid_int in self.slot_assignments:
                self.slot_assignments[sid_int] = tool
                self.canvas.itemconfig(self.slot_text_ids[sid_int], text=tool)
                self.canvas.itemconfig(self.slot_rects[sid_int], fill="#aaffaa" if tool != "None" else "#dddddd")

if __name__ == "__main__":
    app = App()
    app.mainloop()
