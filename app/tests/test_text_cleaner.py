# app/tests/test_text_cleaner.py
"""Tests del parser multi-fuente del Plan Bronce. No consumen tokens."""
from app.services.analysis.text_cleaner import limpiar_comentarios


def test_facebook():
    texto = """José Pérez · 2 h
Excelente iniciativa, felicitaciones al equipo por el trabajo realizado
Me gusta
Responder
María Gómez · 1 h
No me convence para nada, espero que lo revisen pronto
Me gusta
Responder"""
    comentarios, red = limpiar_comentarios(texto)
    assert red == "facebook"
    assert len(comentarios) == 2
    assert comentarios[0]["usuario"] == "José Pérez"
    assert "felicitaciones" in comentarios[0]["texto"]


def test_instagram():
    texto = """usuario1 2d
Qué buena foto, me encanta el lugar elegido!
Me gusta Responder
usuario2 1d
Hermoso, quiero volver muy pronto
Me gusta Responder"""
    comentarios, red = limpiar_comentarios(texto)
    assert red == "instagram"
    assert len(comentarios) == 2
    assert comentarios[0]["usuario"] == "usuario1"


def test_x():
    texto = """@usuario1 · 3h
Gran anuncio del gobierno, era muy necesario
100 Me gusta · 20 Retweets
@usuario2 · 2h
No creo que funcione en la práctica diaria
50 Me gusta · 10 Retweets"""
    comentarios, red = limpiar_comentarios(texto)
    assert red == "x"
    assert len(comentarios) == 2
    assert comentarios[0]["usuario"] == "@usuario1"
    assert "Retweets" not in comentarios[0]["texto"]


def test_whatsapp():
    texto = """10/5/26 14:32 - José: Hola, ¿cómo estás? Hace mucho no hablábamos
10/5/26 14:33 - María: Bien, ¡y vos! Qué alegría saludarte de nuevo
10/5/26 14:35 - José: Todo bien, trabajando en el proyecto nuevo
como siempre, sin novedades"""
    comentarios, red = limpiar_comentarios(texto)
    assert red == "whatsapp"
    assert len(comentarios) == 3
    assert comentarios[0]["usuario"] == "José"
    assert comentarios[0]["texto"].startswith("Hola")


def test_transcripcion():
    texto = """Bueno, entonces lo que yo creo es que tenemos que avanzar con el proyecto, porque la propuesta me parece muy interesante y no sé qué opinan los demás."""
    comentarios, red = limpiar_comentarios(texto)
    assert red == "transcripcion"
    assert len(comentarios) >= 1
    assert comentarios[0]["usuario"].startswith("Fragmento")