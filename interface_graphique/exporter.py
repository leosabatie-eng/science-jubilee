import json
import ezdxf
from constants import *

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
        cx_px, cy_px = (x1 + x2) / 2, (y1 + y2) / 2
        x_mm = (cx_px - bl_x_px) * scale_x
        y_mm = (bl_y_px - cy_px) * scale_y
        w_mm, h_mm = (x2 - x1) * scale_x, (y2 - y1) * scale_y

        data["slots"][str(idx)] = {
            "coordinates": [round(x_mm, 2), round(y_mm, 2)],
            "shape": "rectangle", "width": round(w_mm, 2), "length": round(h_mm, 2),
            "has_labware": True, "labware": TOOLS[obj.name]["json"] if obj.name in TOOLS else None
        }

    for slot_id, tool in slot_assignments.items():
        if tool != "None": data["tool_slots"][str(slot_id)] = tool

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"Export JSON OK -> {filename}")

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