import cv2
import numpy as np
import requests
from datetime import datetime

# Adresse IP du serveur OctoPi (à personnaliser selon l'infrastructure réseau)
OCTOPI_IP = "___IP_OCTOPI___"  # ex: "192.168.X.X"


class Detection_erreur:
    """
    Classe de détection d'erreurs basée sur l'analyse d'images issues d'un système OctoPi.
    
    Fonctionnalités :
    - Capture d'image depuis une webcam distante
    - Détection d'une lentille verte dans une zone spécifique de l'image
    
    Auteur : FLORENT Quentin
    Date : 10/04/2026
    Version : 1.0
    """

    def capture_octopi_image(
        url=f"http://{OCTOPI_IP}/webcam/?action=snapshot",
    ):
        """
        Capture une image depuis le flux webcam OctoPi et la sauvegarde localement.

        Paramètres :
        ----------
        url : str
            URL de snapshot du serveur OctoPi.

        Retour :
        -------
        None

        Exceptions :
        ----------
        Gère les erreurs réseau (timeout, connexion impossible, etc.)
        """

        # Génération d'un nom de fichier par défaut    
        output_file = f"lens_picture.jpg"

        try:
            print("Connexion à OctoPi...")
            response = requests.get(url, timeout=5)

            if response.status_code == 200:
                with open(output_file, "wb") as f:
                    f.write(response.content)
                print(f"Image capturée et enregistrée : {output_file}")
            else:
                print(f"Erreur HTTP : statut {response.status_code}")

        except requests.exceptions.RequestException as e:
            print(f"Erreur de connexion : {e}")


    def detect_lens():
        """
        Détecte la présence d'une lentille verte dans une image capturée.

        Principe :
        ----------
        1. Chargement de l'image
        2. Extraction d'une région d'intérêt (ROI) centrée sur le puit
        3. Amélioration du contraste (espace LAB + CLAHE)
        4. Détection du vert en espace HSV
        5. Nettoyage du masque (morphologie)
        6. Détection de contours correspondant à la lentille

        Retour :
        -------
        bool :
            True  -> lentille détectée
            False -> aucune lentille détectée

        Remarques :
        ----------
        - Les seuils doivent être calibrés selon les conditions d'éclairage
        - La ROI est définie empiriquement et dépend du positionnement caméra
        """

        # Chargement de l'image
        img = cv2.imread("lens_picture.jpg")

        if img is None:
            raise ValueError("Image non chargée (chemin invalide ou fichier absent)")

        # ============================================================
        # EXTRACTION DE LA ZONE D'INTERET (ROI)
        # ============================================================
        # Objectif : réduire la zone analysée pour améliorer performance et robustesse

        height, width = img.shape[:2]

        # Coordonnées empiriques (à adapter selon installation)
        x_start = int(width * 0.39)   # ex: 0.39
        x_end   = int(width * 0.58)   # ex: 0.58
        y_start = int(height * 0.52)  # ex: 0.52
        y_end   = int(height * 0.84)  # ex: 0.84

        img_reduite = img[y_start:y_end, x_start:x_end]

        # ============================================================
        # AMELIORATION DU CONTRASTE (ESPACE LAB)
        # ============================================================
        # Permet de mieux faire ressortir la lentille malgré les reflets

        lab = cv2.cvtColor(img_reduite, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)

        # CLAHE : amélioration locale du contraste
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))  # ex: 3.0
        l = clahe.apply(l)

        lab = cv2.merge((l, a, b))
        img_ameliore = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

        # ============================================================
        # DETECTION DE LA COULEUR VERTE (ESPACE HSV)
        # ============================================================
        # HSV est plus robuste aux variations de luminosité que RGB

        hsv = cv2.cvtColor(img_ameliore, cv2.COLOR_BGR2HSV)

        # Seuils de détection du vert (à calibrer selon caméra)
        lower_green = np.array([40, 50, 50])  # ex: [40, 50, 50]
        upper_green = np.array([85, 255, 255])  # ex: [85, 255, 255]

        green_mask = cv2.inRange(hsv, lower_green, upper_green)

        # ============================================================
        # NETTOYAGE DU MASQUE (MORPHOLOGIE)
        # ============================================================
        # Objectif : supprimer le bruit et combler les trous

        kernel = np.ones((3, 3), np.uint8)  # ex: (3, 3)

        green_mask = cv2.morphologyEx(green_mask, cv2.MORPH_OPEN, kernel)
        green_mask = cv2.morphologyEx(green_mask, cv2.MORPH_CLOSE, kernel)

        # ============================================================
        # DETECTION DES CONTOURS (OBJETS VERTS)
        # ============================================================

        contours, _ = cv2.findContours(
            green_mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        lens_found = False
        valid_lenses = 0  # compteur réel

        for cnt in contours:
            area = cv2.contourArea(cnt)

            # Filtrage par taille (évite le bruit)
            if area > 5:  # ex: 5 à adapter selon résolution
                lens_found = True
                valid_lenses += 1

                x, y, w, h = cv2.boundingRect(cnt)

                # Dessin de la zone détectée (debug / visualisation)
                cv2.rectangle(img_reduite, (x, y), (x + w, y + h), (0, 255, 0), 2)

        
        #============================================================
        #Visualisation pour debug (à commenter en production)
        #============================================================
        """
        cv2.imshow("Image originale", img)
        cv2.imshow("Zone d'interet", img_reduite)
        cv2.imshow("Espace LAB", lab)
        cv2.imshow("Espace HSV", hsv)
        cv2.imshow("Image amelioree", img_ameliore)
        cv2.imshow("Masque vert", green_mask)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        """

        # ============================================================
        # RESULTAT FINAL
        # ============================================================

        if lens_found:
            print(f"✅ Lentille détectée - Nombre : {valid_lenses}")
            return True
        else:
            print("❌ Aucune lentille détectée")
            return False
        

if __name__ == "__main__":
    Detection_erreur.detect_lens()
        
