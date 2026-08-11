# SPDX-License-Identifier: Apache-2.0
"""Gardes sur l'ingestion d'images.

Les images de test sont **fabriquees a la main**, en-tete par en-tete. C'est
volontaire : ca teste le decodeur sans dependre de la bibliotheque qu'il sert
justement a eviter.
"""

import struct
import zlib

from gamb_engine import project
from gamb_engine.ingest import images


def _png(largeur: int, hauteur: int) -> bytes:
    """Un PNG reduit a sa signature et son chunk IHDR — suffisant pour les dimensions."""
    ihdr = struct.pack(">IIBBBBB", largeur, hauteur, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + struct.pack(">I", len(ihdr))
        + b"IHDR"
        + ihdr
        + struct.pack(">I", zlib.crc32(b"IHDR" + ihdr))
    )


def _jpeg(largeur: int, hauteur: int) -> bytes:
    """Un JPEG avec un APP0 avant le SOF0, pour verifier que le saut de segment marche."""
    app0 = (
        b"\xff\xe0"
        + struct.pack(">H", 16)
        + b"JFIF\x00\x01\x01\x00"
        + struct.pack(">HH", 1, 1)
        + b"\x00\x00"
    )
    sof0 = (
        b"\xff\xc0"
        + struct.pack(">H", 17)
        + b"\x08"
        + struct.pack(">HH", hauteur, largeur)
        + b"\x03\x01\x11\x00\x02\x11\x01\x03\x11\x01"
    )
    return b"\xff\xd8" + app0 + sof0 + b"\xff\xd9"


def _ecrire(dossier, nom: str, contenu: bytes):
    chemin = dossier / nom
    chemin.write_bytes(contenu)
    return chemin


# --- Mesure des dimensions ---------------------------------------------------


def test_dimensions_png(tmp_path):
    chemin = _ecrire(tmp_path, "a.png", _png(800, 600))
    assert images.dimensions(chemin) == (800, 600)


def test_dimensions_jpeg_en_sautant_le_segment_app0(tmp_path):
    chemin = _ecrire(tmp_path, "a.jpg", _jpeg(1920, 1080))
    assert images.dimensions(chemin) == (1920, 1080)


def test_un_format_non_mesurable_ne_leve_pas(tmp_path):
    """Une dimension illisible n'est pas une erreur : le fichier entre quand meme."""
    chemin = _ecrire(tmp_path, "a.webp", b"RIFF????WEBPVP8 ")
    assert images.dimensions(chemin) is None


def test_un_fichier_absent_ne_leve_pas(tmp_path):
    assert images.dimensions(tmp_path / "fantome.png") is None


# --- Decouverte --------------------------------------------------------------


def test_trouver_separe_les_images_du_reste(tmp_path):
    _ecrire(tmp_path, "b.png", _png(4, 4))
    _ecrire(tmp_path, "a.JPG", _jpeg(4, 4))
    _ecrire(tmp_path, "notes.txt", b"rien")

    retenus, ecartes = images.trouver(tmp_path)

    assert [c.name for c in retenus] == ["a.JPG", "b.png"]  # trie, extension insensible a la casse
    assert [c.name for c in ecartes] == ["notes.txt"]


# --- Ingestion ---------------------------------------------------------------


def test_ingerer_copie_et_journalise(tmp_path):
    source = tmp_path / "photos"
    source.mkdir()
    _ecrire(source, "a.png", _png(800, 600))
    _ecrire(source, "b.png", _png(800, 600))
    _ecrire(source, "notes.txt", b"rien")

    projet = project.creer(tmp_path / "scan")
    rapport = images.ingerer(source, projet)

    assert rapport.nombre == 2
    assert (projet.images / "a.png").is_file()
    assert rapport.resolutions == {(800, 600): 2}
    assert len(rapport.ignorees) == 1
    assert any(e["action"] == "ingestion_images" for e in projet.historique)


def test_ingerer_sans_copier_laisse_les_fichiers_en_place(tmp_path):
    source = tmp_path / "photos"
    source.mkdir()
    _ecrire(source, "a.png", _png(640, 480))

    projet = project.creer(tmp_path / "scan")
    rapport = images.ingerer(source, projet, copier=False)

    assert rapport.nombre == 1
    assert not (projet.images / "a.png").exists()
    assert rapport.ingerees[0].parent == source


def test_les_resolutions_heterogenes_sont_signalees(tmp_path):
    source = tmp_path / "photos"
    source.mkdir()
    _ecrire(source, "a.png", _png(800, 600))
    _ecrire(source, "b.png", _png(1024, 768))

    projet = project.creer(tmp_path / "scan")
    rapport = images.ingerer(source, projet)

    assert rapport.resolutions_multiples
    assert "hétérogènes" in rapport.resume()


def test_le_journal_est_ecrit_sur_disque(tmp_path):
    source = tmp_path / "photos"
    source.mkdir()
    _ecrire(source, "a.png", _png(10, 10))

    projet = project.creer(tmp_path / "scan")
    images.ingerer(source, projet)

    recharge = project.charger(projet.racine)
    assert any(e["action"] == "ingestion_images" for e in recharge.historique)
