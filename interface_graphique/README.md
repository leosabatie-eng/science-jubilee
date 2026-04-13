# 🖥️ Graphical User Interface – Jubilee Layout Designer

## 📌 Description

This module contains the graphical user interface (GUI) designed to create and manage experimental layouts on the Jubilee machine bed. 

The primary goal is to allow users (engineers and technicians) to:
* **Visually position labware** on the workspace.
* **Assign scientific tools** to specific slots.
* **Generate structured JSON files** for machine automation.
* **Export DXF files** for the physical fabrication of custom mounting plates.
* **Export G-code (.txt)** to physically trace the layout on the machine.

---

## 🧪 Key Concepts: Labware vs. Tools

To use this interface effectively, it is important to distinguish between these two fundamental elements of the Jubilee ecosystem:

### 1. What is a Labware?
In laboratory automation, **Labware** refers to any disposable or reusable container that holds biological or chemical samples. 
* **Examples:** 24 or 96-well plates, Petri dishes, microcentrifuge tube racks, or liquid reservoirs.
* **In this software:** A Labware is defined by its physical footprint (Width x Length) and its internal geometry (well positions, depths, and diameters). The interface uses standardized JSON definition files (compatible with Opentrons V2) to ensure that the robot knows exactly where the center of every well is located.

### 2. What is a Tool?
A **Tool** is the active hardware component picked up by the Jubilee's robotic head to perform an action. Jubilee is a "tool-changing" platform, meaning it can switch functions mid-experiment.
* **Examples:** A P200 pipette for liquid handling, a camera for monitoring, a syringe pump, or an inoculation loop.
* **In this software:** Tools are assigned to specific **Parking Slots** located at the back of the machine. The interface manages which tool is currently "parked" in which slot, ensuring the generated experimental protocol uses the correct instrument for the right task.

---

## 🎯 Role in the Global Project

The interface serves as the central design brick of the workflow. It ensures perfect synchronization between:
* **The Graphical Representation:** Real-time visual feedback on the screen.
* **Real-World Dimensions:** Precise measurements in millimeters.
* **Export Files:** Data used by the machine controller for motion planning.

It guarantees a 1:1 correspondence between the digital design and the physical implementation on the Jubilee deck.

---

## ⚙️ Core Features

### 1️⃣ Deck Management
* **Real-scale representation:** Based on the 305x305 mm workspace.
* **Dynamic scaling:** Automatic Pixel ↔ Millimeter conversion ($3px = 1mm$).
* **Coordinate origin:** Located at the top-left for display, mapped to machine coordinates.

### 2️⃣ Labware Placement
* **Drag-and-Drop:** Intuitive placement of elements on the canvas.
* **Rotation:** 90° rotation support with automatic dimension swapping and coordinate updates.
* **Collision Detection:** Prevents overlapping objects to ensure experiment safety.

### 3️⃣ Tool Management
* **Slot Assignment:** Link scientific tools to their physical parking hardware.
* **Data Sanitization:** Automatically converts `"None"` selection to `null` during JSON export for software compatibility.
* **Modular approach:** Clear separation between labware (on-deck) and tools (off-deck).

### 4️⃣ JSON Export & Fabrication
* **JSON Export:** Generates the "Source of Truth" for machine automation.
* **DXF Export:** Professional file for laser cutting or CNC milling a custom plate.
* **G-code Trace (.txt):** Generates a G-code file that allows the Jubilee to physically trace the outlines of the labwares on the bed (using a pen tool), ensuring the physical setup matches the digital design.

### 5️⃣ DXF Export
Generates a professional DXF file for manufacturing a physical plate:
* Includes an outer mounting frame with 4 corner fixation holes.
* Accurate contours of all placed labware for precise machining.
* **Units:** Millimeters (INSUNITS = 4).
* **Applications:** Laser cutting, CNC milling, or 3D printing custom baseplates.

---

## 🧠 Architecture

* **GUI Framework:** Developed with `CustomTkinter` for a modern, responsive UI.
* **Graphics Engine:** Central Canvas for real-time object manipulation and layering.
* **Software Design:** Strict separation between:
    * **Display:** Canvas rendering and user events.
    * **Business Logic:** Unit conversion, collision rules, and dimension management.
    * **Export Modules:** Formatting data for JSON and DXF standards.

---

## 🚀 How to Run (Execution)

To launch the graphical interface, follow these steps:

1. **Open your terminal** (Command Prompt, PowerShell, or Bash).
2. **Navigate to the project directory** (where `main.py` is located):
   ```bash
   cd path/to/science-jubilee/interface_graphique
3. **Execute the script:**
   ```bash
   python main.py

---

To ensure the interface loads and saves configurations correctly, you must verify that the following files are located in the correct directory:

Files: plan_jubilee.json and test1.json

Target Directory: science-jubilee/src/science_jubilee/decks/deck_definitions/

[!IMPORTANT]
The software looks for these specific paths to initialize the deck layout and tool positions. If these files are missing or in the wrong folder, the interface may fail to load the default workspace.

---

## 📦 Dependencies

To run the interface, ensure the following libraries are installed:

```bash
pip install customtkinter ezdxf
