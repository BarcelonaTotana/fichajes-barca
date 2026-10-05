# -*- coding: utf-8 -*-
"""Tests de los filtros y de las alertas con titulares REALES vistos en producción.
Cada caso nuevo de ruido o de noticia perdida debería acabar aquí como regresión.

Ejecutar (desde la raíz del repo):  python -m unittest discover -s tests -v
"""
import unittest
from unittest import mock

from bot import recolector as R
from bot import telegram_alertas as T
from bot import analisis as A

MD_FICHAJES = "Mundo Deportivo · Fichajes"


class Relevancia(unittest.TestCase):
    def test_fichaje_del_barca_entra(self):
        self.assertTrue(R._es_relevante("Bierhoff coloca a Florian Wirtz en el Barça: interés"))

    def test_jugador_de_la_plantilla_cuenta_como_barca(self):
        self.assertTrue(R._es_relevante("Cinco grandes de la Premier, interés en Koundé"))

    def test_otras_secciones_fuera(self):
        for t in ["El Barça de baloncesto ficha a un pívot",
                  "Joventut de Badalona - Barça: Se escapa la Supercopa (101-87)",
                  "32-28: el Barça gana y ficha confianza"]:
            self.assertFalse(R._es_relevante(t), t)

    def test_vida_institucional_fuera(self):
        # Se guardaban como OFICIAL (tier 0) desde la búsqueda de fcbarcelona.com.
        for t in ["La Asamblea ratifica los acuerdos con Ohana Development y Babylon Park",
                  "Preventa Entradas FC BARCELONA - ASTON VILLA FC - UEFA Champions League",
                  "Si eres socio o socia compromisario, ¡accede y vota!"]:
            self.assertFalse(R._valida_por_titulo(t) and R._es_relevante(t + " acuerdo"), t)

    def test_femenino_sin_decir_femenino(self):
        self.assertTrue(R._es_femenino(
            "El Barça incorpora a la delantera italiana Giulia Galli hasta 2030"))


class FeedsGenerales(unittest.TestCase):
    def test_jugador_como_referencia_no_cuenta(self):
        for t in ["Oficial: un clásico del fútbol europeo jugará junto a Ter Stegen",
                  "Oficial: a falta de Gordon, el Newcastle anuncia a este delantero"]:
            self.assertFalse(R._apto_feed_general(MD_FICHAJES, t), t)

    def test_barca_protagonista_si_cuenta(self):
        self.assertTrue(R._apto_feed_general(MD_FICHAJES, "El Barça ficha a un central"))
        self.assertTrue(R._apto_feed_general(MD_FICHAJES, "El Liverpool quiere a Koundé"))

    def test_ex_del_barca_no_cuenta(self):
        self.assertFalse(R._apto_feed_general(MD_FICHAJES,
                                              "El ex del Barça Riqui Puig firma por el Cádiz"))

    def test_feed_del_barca_no_se_filtra(self):
        self.assertTrue(R._apto_feed_general("Mundo Deportivo · Barça", "Cualquier titular"))


class Titulos(unittest.TestCase):
    def test_google_news_quita_el_medio(self):
        self.assertEqual(R._limpia_titulo("Gavi renueva - Mundo Deportivo",
                                          "https://news.google.com/rss/search?q=x"),
                         ("Gavi renueva", "Mundo Deportivo"))

    def test_rss_directo_no_parte_el_titular(self):
        t = "Barça - Madrid: Flick ya piensa en fichar un lateral"
        self.assertEqual(R._limpia_titulo(t, "https://www.sport.es/es/rss/x.xml"), (t, ""))

    def test_id_estable_con_acentos_y_puntuacion(self):
        self.assertEqual(R._id_noticia("¡Cubarsí renueva!"), R._id_noticia("cubarsi renueva"))


class Telegram(unittest.TestCase):
    def noticia(self, **kw):
        n = {"id": "x1", "titulo": "El Barça ficha a Florian Wirtz por 120 millones",
             "medio": "SPORT", "tier": 2, "categoria": "primer_equipo", "estado": "rumor",
             "enlace": "https://www.sport.es/a?utm_source=rss&utm_medium=feed"}
        n.update(kw)
        return n

    def test_enlace_con_ampersand_escapado(self):
        msg = T.construir_mensaje(self.noticia())
        self.assertIn("utm_source=rss&amp;utm_medium=feed", msg)
        self.assertNotIn("rss&utm", msg)

    def test_punto_de_control(self):
        self.assertTrue(R.apto_para_telegram(self.noticia()))
        self.assertFalse(R.apto_para_telegram(self.noticia(tier=3)))
        self.assertFalse(R.apto_para_telegram(self.noticia(titulo="Análisis del Barça")))

    def _enviar(self, codigo):
        resp = mock.Mock(status_code=codigo, text="")
        with mock.patch.dict("os.environ", {"TELEGRAM_TOKEN": "t", "TELEGRAM_CHAT_ID": "1"}), \
                mock.patch.object(T.requests, "post", return_value=resp):
            return T.enviar_alertas([self.noticia()])

    def test_solo_se_consumen_las_enviadas_o_invalidas(self):
        self.assertEqual(self._enviar(200), {"x1"})
        self.assertEqual(self._enviar(400), {"x1"})    # mensaje inválido: no reintentar
        self.assertEqual(self._enviar(429), set())     # rate-limit: reintentar
        self.assertEqual(self._enviar(401), set())     # token mal: no perder la alerta

    def test_sin_credenciales_no_consume(self):
        with mock.patch.dict("os.environ", {"TELEGRAM_TOKEN": "", "TELEGRAM_CHAT_ID": ""}):
            self.assertEqual(T.enviar_alertas([self.noticia()]), set())


class Analisis(unittest.TestCase):
    def test_club_no_es_jugador(self):
        # 'aston villa' acabó en 'cerradas' y bloqueaba alertas futuras.
        self.assertIsNone(A.extraer_jugador("Oficial: Aston Villa anuncia su fichaje"))

    def test_jugador_e_importe(self):
        t = "Florian Wirtz, objetivo del Barça por 120 millones"
        self.assertEqual(A.extraer_jugador(t), "Florian Wirtz")
        self.assertEqual(A.extraer_importe(t), "120M")


if __name__ == "__main__":
    unittest.main()
