"""Pruebas de las vistas Django nativas de Mensajes, Foro y Novedades."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "campus_django.settings")

import django

django.setup()

from django.test import Client, override_settings
from django.urls import clear_url_caches

from app.servicios import autenticacion
from . import escenario


class ComunicacionNativaTests(unittest.TestCase):
    def setUp(self):
        escenario.cargar()
        autenticacion.actuar_como(1)
        self.urls = override_settings(ROOT_URLCONF="campus_django.comunicacion")
        self.urls.enable()
        clear_url_caches()
        self.client = Client()

    def tearDown(self):
        autenticacion.actuar_como(None)
        self.urls.disable()
        clear_url_caches()

    def test_listados_autenticados_y_metodos(self):
        for ruta in (
            "/api/mensajes",
            "/api/mensajes/contactos",
            "/api/foro",
            "/api/novedades",
        ):
            with self.subTest(ruta=ruta):
                respuesta = self.client.get(ruta)
                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual(respuesta["Content-Type"], "application/json")
                self.assertIsNotNone(respuesta.get("Content-Length"))

        respuesta = self.client.head("/api/foro")
        self.assertEqual(respuesta.status_code, 405)
        self.assertEqual(respuesta["Content-Length"], "30")
        self.assertNotIn("Allow", respuesta.headers)

    def test_body_validation_precedes_auth_and_ids_are_validated(self):
        with patch.dict(os.environ, {"PERMITIR_USUARIO_SIN_TOKEN": "no"}):
            autenticacion.actuar_como(None)
            respuesta = self.client.post(
                "/api/foro", data="{", content_type="application/json"
            )
            self.assertEqual(respuesta.status_code, 400)
            self.assertEqual(
                respuesta.json(),
                {"error": "Los datos enviados no son válidos"},
            )

            respuesta = self.client.get("/api/foro")
            self.assertEqual(respuesta.status_code, 401)
            self.assertEqual(respuesta.json(), {"error": "Hay que iniciar sesión"})

        autenticacion.actuar_como(1)
        respuesta = self.client.get("/api/foro/no-es-un-id")
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(
            respuesta.json(),
            {"error": "Los datos enviados no son válidos"},
        )
        respuesta = self.client.get("/api/foro/1.0")
        self.assertEqual(respuesta.status_code, 400)
        respuesta = self.client.post(
            "/api/mensajes/contactos",
            data={"paraId": 19},
            content_type="application/json",
        )
        self.assertEqual(respuesta.status_code, 400)

    def test_forum_create_read_and_reply(self):
        respuesta = self.client.post(
            "/api/foro",
            data={"cursoId": 1, "titulo": "Consulta de prueba", "texto": "¿Cómo se resuelve?"},
            content_type="application/json",
        )
        self.assertEqual(respuesta.status_code, 201)
        tema_id = respuesta.json()["id"]

        detalle = self.client.get(f"/api/foro/{tema_id}")
        self.assertEqual(detalle.status_code, 200)
        respuesta = self.client.post(
            f"/api/foro/{tema_id}",
            data={"texto": "Con un ejemplo"},
            content_type="application/json",
        )
        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(respuesta.json()["texto"], "Con un ejemplo")

    def test_mensajes_open_send_and_read(self):
        respuesta = self.client.post(
            "/api/mensajes",
            data={"paraId": 19},
            content_type="application/json",
        )
        self.assertEqual(respuesta.status_code, 200)
        conversacion_id = respuesta.json()["id"]

        respuesta = self.client.post(
            f"/api/mensajes/{conversacion_id}",
            data={"texto": "Mensaje de prueba"},
            content_type="application/json",
        )
        self.assertEqual(respuesta.status_code, 201)
        mensaje_id = respuesta.json()["id"]

        autenticacion.actuar_como(19)
        respuesta = self.client.patch(
            f"/api/mensajes/{conversacion_id}/mensajes/{mensaje_id}",
            data={"texto": "Intento ajeno"},
            content_type="application/json",
        )
        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(
            respuesta.json(),
            {"error": "Solo podés editar tus propios mensajes"},
        )

        autenticacion.actuar_como(1)
        respuesta = self.client.get(f"/api/mensajes/{conversacion_id}")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["mensajes"][0]["id"], mensaje_id)
        respuesta = self.client.get("/api/mensajes/999999")
        self.assertEqual(respuesta.status_code, 404)
        self.assertEqual(respuesta.json(), {"error": "Conversación no encontrada"})

    def test_novedad_create_edit_react_and_remove(self):
        respuesta = self.client.post(
            "/api/novedades",
            data={"titulo": "No permitido", "cuerpo": "Texto"},
            content_type="application/json",
        )
        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(
            respuesta.json(),
            {"error": "Solo los docentes pueden publicar novedades"},
        )

        autenticacion.actuar_como(2)
        respuesta = self.client.post(
            "/api/novedades",
            data={
                "titulo": "Aviso de prueba",
                "cuerpo": "Texto de prueba",
                "ambito": "Institucional",
            },
            content_type="application/json",
        )
        self.assertEqual(respuesta.status_code, 201)
        publicacion_id = respuesta.json()["id"]

        respuesta = self.client.put(
            f"/api/novedades/{publicacion_id}",
            data={"titulo": "Aviso editado", "cuerpo": "Texto actualizado"},
            content_type="application/json",
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["titulo"], "Aviso editado")

        autenticacion.actuar_como(1)
        respuesta = self.client.post(
            f"/api/novedades/{publicacion_id}/reaccion",
            data={"tipo": "util"},
            content_type="application/json",
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["miReaccion"], "util")

        autenticacion.actuar_como(2)
        respuesta = self.client.delete(f"/api/novedades/{publicacion_id}")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json(), {"retirada": publicacion_id})


if __name__ == "__main__":
    unittest.main()
