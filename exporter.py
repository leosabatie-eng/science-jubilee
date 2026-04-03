import json
import ezdxf
import math
from constants import *

# exporter.py (Ajout)
def export_led_pattern(light_data, filename="pattern_lumiere.json"):
    """Exporte les 24 valeurs des LEDs pour l'ESP32"""
    pattern = {str(k): v for k, v in light_data.items()}
    data = {"pattern": pattern}
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    print(f"✅ Pattern LED exporté -> {filename}")
    
def export_layout(placed_objects, slot_assignments, canvas, canvas_plateau, filename="test1.json"):
    x0_px, y0_px, x1_px, y1_px = canvas.coords(canvas_plateau)
    plateau_w_px = x1_px - x0_px
    plateau_h_px = y1_px - y0_px
    scale_x = PLATEAU_W_MM / plateau_w_px
    scale_y = PLATEAU_H_MM / plateau_h_px
    bl_x_px, bl_y_px = x0_px, y0_px + plateau_h_px

    data = {
        "name": "Experience1", "type": "SLAS", "deck_offset": [0.0, 0.0],
        "slots": {}, "tool_slots": {}
    }

    for idx, obj in enumerate(placed_objects):
        x1, y1, x2, y2 = canvas.coords(obj.id)
        y_mm = (x1 - x0_px) * scale_x
        x_mm = (y1 - y0_px) * scale_y
        
        # Calcul des dimensions
        w_mm = (x2 - x1) * scale_x
        h_mm = (y2 - y1) * scale_y
        

        data["slots"][str(idx)] = {
            "coordinates": [round(x_mm, 2), round(y_mm, 2)],
            "shape": "rectangle", "width": round(w_mm, 2), "length": round(h_mm, 2),
            "has_labware": True, "labware": LABWARE[obj.name]["json"] if obj.name in LABWARE else None
        }

    for slot_id, tool in slot_assignments.items():
        if tool != "None": data["tool_slots"][str(slot_id-1)] = tool        #-1 car les slot commence à 0

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"Export JSON OK -> {filename}")


def export_to_dxf(json_file="test1.json"):
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Erreur lecture JSON: {e}")
        return

    # Le milieu reste basé sur la largeur utile du plateau
    milieu_x = PLATEAU_W_MM / 2
    jeu = 0.25 

    # On définit les deux fichiers
    # x_min/max_zone incluent désormais l'OFFSET_CONTOUR pour ne pas couper le tracé du contour
    parties = [
        {
             "name": "plan_entier.dxf", 
            "x_min_zone": -OFFSET_CONTOUR, 
            "x_max_zone": PLATEAU_W_MM + 2*OFFSET_CONTOUR, 
            "offset_x": -OFFSET_CONTOUR
        },
        {
            "name": "plan_left.dxf",  
            "x_min_zone": -OFFSET_CONTOUR, 
            "x_max_zone": milieu_x, 
            "offset_x": -OFFSET_CONTOUR # On commence le fichier à l'extrémité gauche du contour
        },
        {
            "name": "plan_right.dxf", 
            "x_min_zone": milieu_x, 
            "x_max_zone": PLATEAU_W_MM + 2*OFFSET_CONTOUR, 
            "offset_x": milieu_x
        }
    ]
    doc = ezdxf.new(dxfversion="R2010")
    doc.header["$INSUNITS"] = 4  # millimètres
    msp = doc.modelspace()

        # ===============================
        # Fonctions utilitaires
        # ===============================
    def draw_rectangle(x1, y1, x2, y2, layer="default"):
        msp.add_lwpolyline(
            [(x1, y1), (x2, y1), (x2, y2), (x1, y2)],
            close=True,
            dxfattribs={"layer": layer}
        )

    def trous_de_fixation(x1, y1, x2, y2):
        r = DIAMETRE_TROU / 2

        trous_positions = [
            (-OFFSET_TROU_LEFT_X, OFFSET_TROU_LEFT_Y),                          # Bas Gauche
            (-OFFSET_TROU_LEFT_X, PLATEAU_H_MM - OFFSET_TROU_LEFT_Y),           # Bas Droite
            (PLATEAU_W_MM + OFFSET_TROU_RIGHT_X, OFFSET_TROU_RIGHT_Y),         # Haut Gauche
            (PLATEAU_W_MM + OFFSET_TROU_RIGHT_X, PLATEAU_H_MM - OFFSET_TROU_RIGHT_Y) # Haut Droite
        ]

        for x, y in trous_positions:
            msp.add_circle(
                center=(x, y),
                radius=r,
                dxfattribs={"layer": "fixation_holes"}
                )

    # ===============================
    # 1) PLATEAU
    # ===============================
    x1, y1 = 0, 0
    x2, y2 = PLATEAU_W_MM, PLATEAU_H_MM

    #draw_rectangle(x1, y1, x2, y2, layer="plateau") rectangle plateau
    draw_rectangle(x1, y1-2*OFFSET_CONTOUR, x2, y2+2*OFFSET_CONTOUR, layer="plateau")
    trous_de_fixation(x1, y1, x2, y2)

        # ===============================
        # 2) LABWARES
        # ===============================
    slots = data.get("slots", {})

    for slot in slots.values():
        if not slot.get("has_labware", False):
            continue

        cx, cy = slot["coordinates"]
        w = slot.get("width", 0)
        h = slot.get("length", 0)

            # centre → coins
        x1 = cx - w / 2
        y1 = cy - h / 2
        x2 = cx + w / 2
        y2 = cy + h / 2

        draw_rectangle(x1, y1, x2, y2, layer="labware")

        # ===============================
        # Sauvegarde
        # ===============================
    doc.saveas('entier')
    print(f"DXF exporté → {'entier'}")
    
    #plan couper en deux pour laser cut
    for p in parties:
        doc = ezdxf.new(dxfversion="R2010")
        doc.header["$INSUNITS"] = 4 
        msp = doc.modelspace()
        
        off = p["offset_x"]

        def draw_rect(x1, y1, x2, y2, layer="default"):
            # Application de l'offset X pour que le point le plus à gauche de la zone soit à X=0 dans le DXF
            pts = [(x1 - off, y1), (x2 - off, y1), (x2 - off, y2), (x1 - off, y2)]
            msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": layer})

        # 1) CONTOUR DU PLATEAU
        # Ici, l'offset est appliqué en X (élargissement latéral)
        # On dessine de x_min_zone à x_max_zone pour que la ligne de coupe soit propre
        draw_rect(p["x_min_zone"], 0, p["x_max_zone"], PLATEAU_H_MM, layer="plateau")

        # 2) TROUS DE FIXATION
        r = DIAMETRE_TROU / 2
        trous_positions = [
            (-OFFSET_TROU_LEFT_X, OFFSET_TROU_LEFT_Y),                          # Bas Gauche
            (-OFFSET_TROU_LEFT_X, PLATEAU_H_MM - OFFSET_TROU_LEFT_Y),           # Bas Droite
            (PLATEAU_W_MM + OFFSET_TROU_RIGHT_X, OFFSET_TROU_RIGHT_Y),         # Haut Gauche
            (PLATEAU_W_MM + OFFSET_TROU_RIGHT_X, PLATEAU_H_MM - OFFSET_TROU_RIGHT_Y) # Haut Droite
        ]
        
        for tx, ty in trous_positions:
            # On vérifie si le centre du trou tombe dans la zone découpée
            if p["x_min_zone"] <= tx <= p["x_max_zone"]:
                msp.add_circle(center=(tx - off, ty), radius=r, dxfattribs={"layer": "fixation_holes"})

        # 3) LABWARES (À CHEVAL)
        slots = data.get("slots", {})
        
        for slot in slots.values():
            if not slot.get("has_labware", False): continue
            
            cx, cy = slot["coordinates"]
            w, h = slot.get("width", 0), slot.get("length", 0)
            
            # Coordonnées réelles avec jeu
            lx1, lx2 = cx - jeu, cx + w + jeu
            ly1, ly2 = cy - jeu, cy + h + jeu


            
            # Si l'objet touche ou traverse la zone
            if lx2 > p["x_min_zone"] and lx1 < p["x_max_zone"]:
                # Clipping horizontal strict sur les limites de la zone
                draw_x1 = max(lx1, p["x_min_zone"])
                draw_x2 = min(lx2, p["x_max_zone"])
                
                draw_rect(draw_x1, ly1, draw_x2, ly2, layer="labware")

        doc.saveas(p["name"])
        print(f"Export {p['name']} terminé.")


#tracer plan avec stylo
def json_to_gcode(json_file, gcode_file, z_up=30.0, z_down=27.0, feedrate=4000):
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Erreur lecture JSON: {e}")
        return

    with open(gcode_file, 'w', encoding='utf-8') as g:
        # --- INITIALISATION MACHINE ---
        g.write("; G-code genere directement depuis JSON\n")
        g.write("G21 ; Unites en mm\n")
        g.write("G90 ; Positionnement absolu\n")
        g.write("G28 ; Home\n")
        g.write(f"G0 Z{z_up} F600 ; Lever le stylo\n\n")

        #lock outil à enelver
        param = "P"
        g.write(f"G4 {param}{4000}\n")
        #
        #tool lock
        g.write("G91\n")   
        g.write("G1 U10 F6000 H0\n") 
        g.write("G1 U200 F6000 H1\n") 
        g.write("G90\n") 
        #
        
#Z=26 limite pour ecrire

      
        # --- 1) DESSIN DU CONTOUR (PLATEAU) ---
        # On dessine le rectangle extérieur
        x_0_0 = -4
        y_0_0 = -43.5
        offset_stylo = 2
        points_contour = [#coin 0,0 -> -4;-43.5
            (x_0_0 + offset_stylo, y_0_0 + offset_stylo), (PLATEAU_W_MM + x_0_0 - offset_stylo, y_0_0 + offset_stylo), 
            (PLATEAU_W_MM + x_0_0 - offset_stylo, PLATEAU_H_MM + y_0_0 - offset_stylo), (x_0_0 + offset_stylo, PLATEAU_H_MM + y_0_0 - offset_stylo), (x_0_0 + offset_stylo, y_0_0 + offset_stylo)
        ]
        g.write("; --- Contour Plateau ---\n")
        g.write(f"G0 X{points_contour[0][0]} Y{points_contour[0][1]} F{feedrate}\n")
        g.write(f"G1 Z{z_down} F800\n")
        for x, y in points_contour[1:]:
            g.write(f"G1 X{x:.3f} Y{y:.3f}\n")
        g.write(f"G1 Z{z_up} F600\n\n")

        # --- 2) TROUS DE FIXATION (CERCLES) --
        g.write("; --- Trous de Fixation ---\n")
        r_hole = DIAMETRE_TROU / 2
        trous_pos =[ #position des trous pas logique, difference entre réeel et code, pour moi ca fonctionne comme ca 
            (OFFSET_TROU_LEFT_Y + x_0_0, -OFFSET_TROU_LEFT_X + y_0_0),
            (PLATEAU_H_MM - OFFSET_TROU_LEFT_Y + x_0_0, - OFFSET_TROU_LEFT_X + y_0_0),
            (PLATEAU_W_MM - OFFSET_TROU_RIGHT_Y + x_0_0, PLATEAU_H_MM + OFFSET_TROU_RIGHT_X + y_0_0),
            (OFFSET_TROU_RIGHT_Y + x_0_0, PLATEAU_H_MM + OFFSET_TROU_RIGHT_X + y_0_0)
        ]
        
        for tx, ty in trous_pos:
            # Aller au bord du cercle
            g.write(f"G0 X{tx + r_hole:.3f} Y{ty:.3f} F{feedrate}\n")
            g.write(f"G1 Z{z_down} F800\n")
            # Approximation du cercle en 32 segments
            for i in range(1, 33):
                angle = math.radians(i * (360/32))
                px = tx + r_hole * math.cos(angle)
                py = ty + r_hole * math.sin(angle)
                g.write(f"G1 X{px:.3f} Y{py:.3f}\n")
            g.write(f"G1 Z{z_up} F600\n\n")

        # --- 3) LABWARES (RECTANGLES) ---
        g.write("; --- Labwares ---\n")
        slots = data.get("slots", {})
        
        for slot in slots.values():
            if not slot.get("has_labware", False): continue
            
            x1, y1 = slot["coordinates"]
            w, h = slot.get("width", 0), slot.get("length", 0)
            
            # Calcul des coins (Bas-Gauche -> Bas-Droit -> Haut-Droit -> Haut-Gauche)
            x2 = x1 + h
            y2 = y1 + w
            
            pts = [(x1+x_0_0, y1+y_0_0), (x2+x_0_0, y1+y_0_0), (x2+x_0_0, y2+y_0_0), (x1+x_0_0, y2+y_0_0), (x1+x_0_0, y1+y_0_0)]
            
            g.write(f"G0 X{pts[0][0]:.3f} Y{pts[0][1]:.3f} F{feedrate}\n")
            g.write(f"G1 Z{z_down} F800\n")
            for px, py in pts[1:]:
                g.write(f"G1 X{px:.3f} Y{py:.3f}\n")
            g.write(f"G1 Z{z_up} F600\n\n")

        # --- FIN ---
        #g.write("G1 Z20 F600 ; Monter haut\n")
        g.write("G28 X0 Y0 ; Parking\n")
        g.write("M84 ; Stop moteurs\n")

    print(f"G-code généré : {gcode_file}")