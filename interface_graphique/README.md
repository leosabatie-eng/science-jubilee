# 🖥️ Interface Graphique – Conception de Layout Jubilee

## 📌 Description

Ce module contient l’interface graphique permettant de concevoir le layout expérimental sur le plateau de la machine Jubilee.

L’objectif est de permettre à l’utilisateur (ingénieur / technicien) de :

- Positionner visuellement des labwares
- Assigner des outils scientifiques
- Générer un fichier JSON structuré
- Exporter un DXF pour fabrication d’un gabarit physique

---

## 🎯 Rôle dans le projet global

L’interface constitue la brique centrale de conception.

Elle assure la cohérence entre :

- La représentation graphique
- Les dimensions réelles en millimètres
- Le fichier d’export utilisé par le système

Elle garantit ainsi une correspondance fidèle entre le design numérique et l’implantation physique sur la Jubilee.

---

## ⚙️ Fonctionnalités principales

### 1️⃣ Gestion du Plateau

- Représentation aux dimensions réelles (mm)
- Conversion pixels ↔ millimètres
- Origine située en bas à gauche
- Gestion d’une grille optionnelle

---

### 2️⃣ Placement des Labwares

- Ajout et suppression d’éléments
- Positionnement précis
- Stockage des :
  - coordonnées
  - dimensions
  - type de labware

Les données sont exportées dans une structure JSON normalisée.

---

### 3️⃣ Gestion des Outils

- Assignation d’outils scientifiques à des slots dédiés
- Conversion automatique des valeurs `"None"` en `null` lors de l’export JSON
- Séparation claire entre labwares et outils

---

### 4️⃣ Export JSON

Le fichier exporté contient :

- Les dimensions du plateau
- Les slots occupés
- Les labwares associés
- Les outils assignés

Ce fichier peut être utilisé pour :

- Pilotage machine
- Simulation
- Automatisation expérimentale

---

### 5️⃣ Export DXF

Génération d’un fichier DXF contenant :

- Un cadre extérieur de fixation
- 4 trous de fixation positionnés aux coins
- Les contours des éléments placés

Unités utilisées : **millimètres (INSUNITS = 4)**.

Le DXF peut être utilisé pour :

- Découpe laser
- CNC
- Fabrication d’un gabarit

---

## 🧠 Architecture

- Interface développée avec CustomTkinter
- Canvas central pour la gestion graphique
- Séparation claire entre :
  - Affichage
  - Logique métier
  - Export

---

## 📦 Dépendances

```bash
pip install customtkinter ezdxf
