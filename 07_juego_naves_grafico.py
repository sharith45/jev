import math
import os
import random
import time

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ.setdefault("SDL_RENDER_SCALE_QUALITY", "linear")

import pygame
from pygame._sdl2.video import WINDOWPOS_CENTERED, Renderer, Texture, Window

from naves import (
    ALTO,
    ANCHO,
    DURACION,
    FILA_NAVE,
    MOMENTOS_JEFE,
    PASO,
    VIDAS,
    Decision,
    Partida,
    Piloto,
    argumentos,
)

CELDA = 46
MARGEN = 30
CAMPO_ANCHO = ANCHO * CELDA
CAMPO_ALTO = ALTO * CELDA
PANEL_X = MARGEN + CAMPO_ANCHO + 26
PANEL_ANCHO = 500
LOGICO = (PANEL_X + PANEL_ANCHO + MARGEN, CAMPO_ALTO + MARGEN * 2)
FPS = 60
ESCALA_LATENCIA = 1.5

BANDAS = (0, 0, 0)
FONDO = (8, 11, 24)
CAMPO = (10, 15, 33)
REJILLA = (22, 30, 56)
TARJETA = (18, 25, 49)
BORDE = (36, 46, 80)
TEXTO = (236, 238, 244)
TEXTO_SUAVE = (150, 158, 182)
APAGADO = (70, 78, 104)
VERDE = (72, 199, 116)
AMARILLO = (240, 184, 64)
ROJO = (232, 72, 72)
CIAN = (110, 232, 240)
LLAMA = (255, 176, 64)
CAZA = (238, 110, 52)
KAMIKAZE = (236, 60, 100)
BOMBARDERO = (176, 104, 236)
ASTEROIDE = (132, 138, 150)
BALA_ENEMIGA = (255, 130, 60)
BALA_JEFE = (255, 84, 200)
COLOR_PILOTO = {"jev": (70, 150, 245), "deepseek": (60, 200, 170)}
COLOR_JEFE = {1: (206, 52, 92), 2: (138, 72, 232)}
COLOR_CLASE = {"caza": CAZA, "kamikaze": KAMIKAZE, "bombardero": BOMBARDERO, "asteroide": ASTEROIDE}
FLECHAS = {"izquierda": "← IZQUIERDA", "quieto": "QUIETO", "derecha": "DERECHA →"}

CASCO_NAVE = [(0, -22), (-8, -6), (-20, 14), (-7, 9), (0, 15), (7, 9), (20, 14), (8, -6)]
CASCO_JEFE = [(-80, -16), (-56, -38), (56, -38), (80, -16), (70, 14), (38, 30), (16, 44), (-16, 44), (-38, 30), (-70, 14)]


def px(x: float) -> float:
    return x * CELDA + CELDA / 2


def py(y: float) -> float:
    return y * CELDA + CELDA / 2


def segundos(valor: float, decimales: int = 3) -> str:
    return f"{valor:.{decimales}f} s".replace(".", ",")


def reloj_texto(valor: float) -> str:
    valor = max(0.0, valor)
    return f"{int(valor // 60)}:{int(valor % 60):02d}"


def color_latencia(valor: float) -> tuple[int, int, int]:
    return VERDE if valor <= 0.4 else AMARILLO if valor <= 0.8 else ROJO


def mezclar(color: tuple, otro: tuple, t: float) -> tuple[int, int, int]:
    t = max(0.0, min(1.0, t))
    return tuple(int(a + (b - a) * t) for a, b in zip(color, otro))


def escribir(superficie: pygame.Surface, fuente: pygame.font.Font, texto: str, color: tuple,
             posicion: tuple[float, float], ancla: str = "topleft") -> pygame.Rect:
    imagen = fuente.render(texto, True, color)
    rect = imagen.get_rect(**{ancla: (round(posicion[0]), round(posicion[1]))})
    superficie.blit(imagen, rect)
    return rect


def tarjeta(superficie: pygame.Surface, rect: pygame.Rect, borde: tuple = BORDE) -> None:
    pygame.draw.rect(superficie, TARJETA, rect, border_radius=10)
    pygame.draw.rect(superficie, borde, rect, 1, border_radius=10)


def barra(superficie: pygame.Surface, rect: pygame.Rect, fraccion: float, color: tuple) -> None:
    pygame.draw.rect(superficie, (34, 42, 70), rect, border_radius=rect.height // 2)
    lleno = rect.copy()
    lleno.width = round(rect.width * max(0.0, min(1.0, fraccion)))
    if lleno.width > 0:
        pygame.draw.rect(superficie, color, lleno, border_radius=rect.height // 2)


def corazon(superficie: pygame.Surface, color: tuple, centro: tuple[float, float], tamano: float) -> None:
    x, y = centro
    radio = tamano * 0.28
    pygame.draw.circle(superficie, color, (x - radio, y - radio * 0.4), radio)
    pygame.draw.circle(superficie, color, (x + radio, y - radio * 0.4), radio)
    pygame.draw.polygon(superficie, color, [(x - radio * 2, y - radio * 0.1), (x + radio * 2, y - radio * 0.1),
                                            (x, y + tamano * 0.52)])


def insignia(superficie: pygame.Surface, fuente: pygame.font.Font, texto: str, color: tuple, activa: bool,
             posicion: tuple[int, int]) -> int:
    imagen = fuente.render(texto, True, FONDO if activa else APAGADO)
    rect = pygame.Rect(posicion, (imagen.get_width() + 20, imagen.get_height() + 8))
    if activa:
        pygame.draw.rect(superficie, color, rect, border_radius=rect.height // 2)
    else:
        pygame.draw.rect(superficie, APAGADO, rect, 1, border_radius=rect.height // 2)
    superficie.blit(imagen, (rect.x + 10, rect.y + 4))
    return rect.right


def tamano_inicial() -> tuple[int, int]:
    escritorios = pygame.display.get_desktop_sizes()
    ancho, alto = escritorios[0] if escritorios else (1280, 800)
    escala = min(1.0, alto * 0.85 / LOGICO[1], ancho * 0.9 / LOGICO[0])
    return round(LOGICO[0] * escala), round(LOGICO[1] * escala)


class Pantalla:
    def __init__(self) -> None:
        self.ventana = Window("jev", size=tamano_inicial(), position=WINDOWPOS_CENTERED, resizable=True)
        self.render = Renderer(self.ventana)
        self.render.logical_size = LOGICO
        self.logico = pygame.Surface(LOGICO, pygame.SRCALPHA)
        self.textura = Texture(self.render, LOGICO, depth=32, streaming=True)
        self.completa = False

    def titular(self, texto: str) -> None:
        self.ventana.title = texto

    def alternar(self) -> None:
        if self.completa:
            self.ventana.set_windowed()
        else:
            self.ventana.set_fullscreen(desktop=True)
        self.completa = not self.completa

    def presentar(self) -> None:
        self.textura.update(self.logico)
        self.render.draw_color = (*BANDAS, 255)
        self.render.clear()
        self.textura.draw()
        self.render.present()


class Escena:
    def __init__(self, cerebro: str) -> None:
        self.color = COLOR_PILOTO[cerebro]
        self.campo = pygame.Surface((CAMPO_ANCHO, CAMPO_ALTO))
        self.vista = pygame.Surface((CELDA * 5, CAMPO_ALTO), pygame.SRCALPHA)
        self.vista.fill((*self.color, 16))
        self.estrellas = [
            [random.uniform(0, CAMPO_ANCHO), random.uniform(0, CAMPO_ALTO), random.uniform(0.3, 1.6)]
            for _ in range(150)
        ]
        self.particulas: list[list] = []
        self.formas: dict[int, list[tuple[float, float]]] = {}
        self.temblor = 0.0
        self.destello = 0.0
        self.aviso = ""
        self.color_aviso = TEXTO
        self.tiempo_aviso = 0.0
        self.flecha = "quieto"
        self.tiempo_flecha = 0.0
        self.reloj = 0.0

    def nueva_decision(self, decision: Decision) -> None:
        self.flecha = decision.movimiento
        self.tiempo_flecha = 0.3

    def avisar(self, texto: str, color: tuple, duracion: float = 2.2) -> None:
        self.aviso, self.color_aviso, self.tiempo_aviso = texto, color, duracion

    def explotar(self, x: float, y: float, cantidad: int, color: tuple, rapidez: float = 220, vida: float = 0.7,
                 radio: float = 5) -> None:
        for _ in range(cantidad):
            angulo = random.uniform(0, math.tau)
            fuerza = random.uniform(0.25, 1.0) * rapidez
            duracion = random.uniform(0.5, 1.0) * vida
            self.particulas.append([x, y, math.cos(angulo) * fuerza, math.sin(angulo) * fuerza, duracion, duracion,
                                    color, radio])

    def recoger(self, eventos: list[tuple]) -> None:
        for evento in eventos:
            tipo = evento[0]
            if tipo == "explosion":
                _, x, y, tamano, clase = evento
                color = COLOR_CLASE.get(clase, CAZA)
                self.explotar(px(x), py(y), int(26 * tamano), color)
                self.explotar(px(x), py(y), int(12 * tamano), AMARILLO, rapidez=140, vida=0.5, radio=4)
            elif tipo == "chispa":
                self.explotar(px(evento[1]), py(evento[2]), 5, AMARILLO, rapidez=120, vida=0.25, radio=3)
            elif tipo == "golpe":
                self.explotar(px(evento[1]), py(evento[2]), 40, ROJO, rapidez=260)
                self.explotar(px(evento[1]), py(evento[2]), 20, AMARILLO, rapidez=160, vida=0.5, radio=4)
                self.temblor = 0.45
                self.destello = 0.35
            elif tipo == "jefe":
                self.avisar(f"¡JEFE {evento[1]}!", COLOR_JEFE[evento[1]])
            elif tipo == "retirada":
                self.avisar(f"El jefe {evento[1]} se retira", AMARILLO)
            elif tipo == "jefe_cae":
                _, x, y, numero = evento
                for desplazamiento in (-1.2, -0.4, 0.4, 1.2):
                    self.explotar(px(x + desplazamiento), py(y + random.uniform(-0.4, 0.4)), 30, COLOR_JEFE[numero],
                                  rapidez=300, vida=1.1, radio=6)
                self.explotar(px(x), py(y), 50, AMARILLO, rapidez=380, vida=1.2, radio=5)
                self.temblor = 0.7
                self.avisar(f"JEFE {numero} DERRIBADO", VERDE)

    def actualizar(self, dt: float) -> None:
        self.reloj += dt
        for estrella in self.estrellas:
            estrella[1] += estrella[2] * 45 * dt
            if estrella[1] > CAMPO_ALTO:
                estrella[0], estrella[1] = random.uniform(0, CAMPO_ANCHO), 0.0
        for particula in self.particulas:
            particula[0] += particula[2] * dt
            particula[1] += particula[3] * dt
            particula[2] *= 0.97
            particula[3] *= 0.97
            particula[4] -= dt
        self.particulas = [p for p in self.particulas if p[4] > 0]
        self.temblor = max(0.0, self.temblor - dt)
        self.destello = max(0.0, self.destello - dt)
        self.tiempo_aviso = max(0.0, self.tiempo_aviso - dt)
        self.tiempo_flecha = max(0.0, self.tiempo_flecha - dt)

    def forma(self, clave: int) -> list[tuple[float, float]]:
        if clave not in self.formas:
            azar = random.Random(clave)
            self.formas[clave] = [(i / 10 * math.tau, azar.uniform(0.72, 1.0)) for i in range(10)]
        return self.formas[clave]


def dibujar_asteroide(campo: pygame.Surface, escena: Escena, asteroide) -> None:
    cx, cy = px(asteroide.x), py(asteroide.y)
    giro = escena.reloj * (0.6 + (asteroide.ident % 5) * 0.25)
    radio = CELDA * 0.44
    puntos = [(cx + math.cos(a + giro) * radio * r, cy + math.sin(a + giro) * radio * r)
              for a, r in escena.forma(asteroide.ident)]
    pygame.draw.polygon(campo, ASTEROIDE, puntos)
    pygame.draw.polygon(campo, (96, 100, 112), puntos, 2)
    pygame.draw.circle(campo, (110, 115, 128), (cx - radio * 0.25, cy - radio * 0.2), radio * 0.2)


def dibujar_enemigo(campo: pygame.Surface, escena: Escena, enemigo) -> None:
    cx, cy = px(enemigo.x), py(enemigo.y)
    blanco = enemigo.golpe > 0
    if enemigo.tipo == "caza":
        color = TEXTO if blanco else CAZA
        pygame.draw.polygon(campo, color, [(cx, cy + 17), (cx - 18, cy - 10), (cx - 6, cy - 4), (cx, cy - 15),
                                           (cx + 6, cy - 4), (cx + 18, cy - 10)])
        pygame.draw.circle(campo, FONDO, (cx, cy + 1), 4)
    elif enemigo.tipo == "kamikaze":
        if enemigo.estado == "apuntando":
            intensidad = 0.5 + 0.5 * math.sin(escena.reloj * 28)
            linea = pygame.Surface((4, CAMPO_ALTO), pygame.SRCALPHA)
            linea.fill((*KAMIKAZE, int(40 + 60 * intensidad)))
            campo.blit(linea, (cx - 2, cy))
            pygame.draw.circle(campo, mezclar(KAMIKAZE, TEXTO, intensidad), (cx, cy), 20, 2)
        color = TEXTO if blanco else KAMIKAZE
        pygame.draw.polygon(campo, color, [(cx, cy + 19), (cx - 11, cy - 13), (cx, cy - 6), (cx + 11, cy - 13)])
    else:
        color = TEXTO if blanco else BOMBARDERO
        pygame.draw.polygon(campo, color, [(cx - 21, cy - 8), (cx - 12, cy - 16), (cx + 12, cy - 16), (cx + 21, cy - 8),
                                           (cx + 14, cy + 12), (cx - 14, cy + 12)])
        pygame.draw.rect(campo, FONDO, (cx - 9, cy - 4, 18, 7), border_radius=3)
        for indice in range(enemigo.vida):
            pygame.draw.circle(campo, AMARILLO, (cx - 8 + indice * 8, cy + 18), 2)


def dibujar_jefe(campo: pygame.Surface, escena: Escena, jefe) -> None:
    cx, cy = px(jefe.x), py(jefe.y)
    base = COLOR_JEFE[jefe.numero]
    color = mezclar(base, TEXTO, 0.8) if jefe.golpe > 0 else base
    puntos = [(cx + dx, cy + dy) for dx, dy in CASCO_JEFE]
    pygame.draw.polygon(campo, color, puntos)
    pygame.draw.polygon(campo, mezclar(base, TEXTO, 0.45), puntos, 3)
    for lado in (-1, 1):
        pygame.draw.rect(campo, (40, 30, 60), (cx + lado * 60 - 7, cy + 12, 14, 26), border_radius=4)
        pygame.draw.circle(campo, BALA_JEFE, (cx + lado * 60, cy + 36), 4)
    pulso = 0.5 + 0.5 * math.sin(escena.reloj * 6)
    pygame.draw.circle(campo, mezclar(AMARILLO, TEXTO, pulso), (cx, cy + 4), 12 + 3 * pulso)
    pygame.draw.circle(campo, FONDO, (cx, cy + 4), 6)
    pygame.draw.polygon(campo, mezclar(base, FONDO, 0.5), [(cx - 40, cy - 30), (cx + 40, cy - 30), (cx + 24, cy - 16),
                                                           (cx - 24, cy - 16)])


def dibujar_nave(campo: pygame.Surface, escena: Escena, partida: Partida) -> None:
    cx, cy = px(partida.nave_visual), py(FILA_NAVE)
    if partida.invulnerable > 0:
        pygame.draw.circle(campo, mezclar(escena.color, TEXTO, 0.5), (cx, cy), 28, 2)
        if int(escena.reloj * 14) % 2:
            return
    llama = 9 + 7 * abs(math.sin(escena.reloj * 25))
    pygame.draw.polygon(campo, LLAMA, [(cx - 6, cy + 13), (cx + 6, cy + 13), (cx, cy + 13 + llama)])
    pygame.draw.polygon(campo, escena.color, [(cx + dx, cy + dy) for dx, dy in CASCO_NAVE])
    pygame.draw.polygon(campo, mezclar(escena.color, TEXTO, 0.5), [(cx + dx, cy + dy) for dx, dy in CASCO_NAVE], 2)
    pygame.draw.circle(campo, (210, 230, 255), (cx, cy - 2), 4)
    if escena.tiempo_flecha > 0 and escena.flecha != "quieto":
        lado = -1 if escena.flecha == "izquierda" else 1
        alfa = escena.tiempo_flecha / 0.3
        punta = cx + lado * 40
        color = mezclar(CAMPO, TEXTO, alfa)
        pygame.draw.polygon(campo, color, [(punta, cy), (punta - lado * 10, cy - 8), (punta - lado * 10, cy + 8)])


def dibujar_campo(logico: pygame.Surface, escena: Escena, partida: Partida, piloto: Piloto, fuentes: dict) -> None:
    campo = escena.campo
    campo.fill(CAMPO)
    for x, y, brillo in escena.estrellas:
        tono = int(80 + brillo * 90)
        lado = 2 if brillo > 1.2 else 1
        campo.fill((tono, tono, min(255, tono + 25)), (x, y, lado, lado))
    for columna in range(1, ANCHO):
        pygame.draw.line(campo, REJILLA, (columna * CELDA, 0), (columna * CELDA, CAMPO_ALTO))
    campo.blit(escena.vista, (px(partida.nave_visual) - CELDA * 2.5, 0))

    for asteroide in partida.asteroides:
        dibujar_asteroide(campo, escena, asteroide)
    for enemigo in partida.enemigos:
        dibujar_enemigo(campo, escena, enemigo)
    if partida.jefe is not None:
        dibujar_jefe(campo, escena, partida.jefe)
    for bala in partida.balas:
        x, y = px(bala.x), py(bala.y)
        pygame.draw.rect(campo, CIAN, (x - 2, y - 11, 4, 20), border_radius=2)
        pygame.draw.rect(campo, TEXTO, (x - 1, y - 9, 2, 12))
    for bala in partida.balas_enemigas:
        x, y = px(bala.x), py(bala.y)
        color = BALA_JEFE if bala.del_jefe else BALA_ENEMIGA
        pygame.draw.circle(campo, mezclar(color, CAMPO, 0.55), (x, y), 9)
        pygame.draw.circle(campo, color, (x, y), 6)
        pygame.draw.circle(campo, TEXTO, (x, y), 2)
    if partida.vidas > 0:
        dibujar_nave(campo, escena, partida)
    for x, y, _, _, vida, total, color, radio in escena.particulas:
        fraccion = vida / total
        pygame.draw.circle(campo, mezclar(CAMPO, color, 0.3 + 0.7 * fraccion), (x, y), max(1, round(radio * fraccion)))

    jefe = partida.jefe
    if jefe is not None:
        rect = pygame.Rect(16, 12, CAMPO_ANCHO - 32, 10)
        barra(campo, rect, jefe.vida / jefe.vida_max, COLOR_JEFE[jefe.numero])
        escribir(campo, fuentes["mini"], f"JEFE {jefe.numero}", TEXTO, (16, 26))
    if escena.tiempo_aviso > 0:
        alfa = min(1.0, escena.tiempo_aviso / 0.5)
        imagen = fuentes["enorme"].render(escena.aviso, True, escena.color_aviso)
        imagen.set_alpha(int(255 * alfa))
        campo.blit(imagen, imagen.get_rect(center=(CAMPO_ANCHO / 2, CAMPO_ALTO * 0.42)))
    if escena.destello > 0:
        velo = pygame.Surface((CAMPO_ANCHO, CAMPO_ALTO), pygame.SRCALPHA)
        velo.fill((*ROJO, int(90 * escena.destello / 0.35)))
        campo.blit(velo, (0, 0))

    logico.fill(FONDO)
    sacudida = escena.temblor * 14
    desvio = (random.uniform(-sacudida, sacudida), random.uniform(-sacudida, sacudida)) if sacudida else (0, 0)
    logico.blit(campo, (MARGEN + desvio[0], MARGEN + desvio[1]))
    peligro = piloto.ultima is not None and piloto.ultima.peligro and not partida.terminada
    marco = pygame.Rect(MARGEN - 2, MARGEN - 2, CAMPO_ANCHO + 4, CAMPO_ALTO + 4)
    pygame.draw.rect(logico, ROJO if peligro else BORDE, marco, 2, border_radius=6)


def piloto_color(piloto: Piloto) -> tuple[int, int, int]:
    return COLOR_PILOTO[piloto.cerebro]


def dibujar_decision(logico: pygame.Surface, fuentes: dict, piloto: Piloto, ahora: float, y: int) -> int:
    rect = pygame.Rect(PANEL_X, y, PANEL_ANCHO, 176)
    tarjeta(logico, rect)
    x = PANEL_X + 18
    escribir(logico, fuentes["mini"], "ÚLTIMA DECISIÓN", TEXTO_SUAVE, (x, y + 12))
    decision = piloto.ultima
    if decision is None:
        escribir(logico, fuentes["enorme"], "…", TEXTO_SUAVE, (x, y + 30))
        escribir(logico, fuentes["pequena"], "esperando la primera respuesta", TEXTO_SUAVE, (x, y + 96))
        return rect.bottom
    edad = max(0.0, ahora - decision.momento)
    escribir(logico, fuentes["mini"], f"hace {segundos(edad, 2)}", TEXTO_SUAVE, (rect.right - 18, y + 12), "topright")
    escribir(logico, fuentes["enorme"], FLECHAS[decision.movimiento], TEXTO, (x, y + 28))
    derecha = insignia(logico, fuentes["mini"], "DISPARA" if decision.disparar else "no dispara", CIAN,
                       decision.disparar, (x, y + 90))
    insignia(logico, fuentes["mini"], "PELIGRO" if decision.peligro else "sin peligro", ROJO, decision.peligro,
             (derecha + 10, y + 90))
    escribir(logico, fuentes["pequena"], f"respondió en {segundos(decision.segundos)}", color_latencia(decision.segundos),
             (rect.right - 18, y + 92), "topright")
    if decision.probabilidades:
        ancho = (PANEL_ANCHO - 36 - 20) // 3
        for indice, opcion in enumerate(("izquierda", "quieto", "derecha")):
            valor = float(decision.probabilidades.get(opcion, 0.0))
            columna = x + indice * (ancho + 10)
            escribir(logico, fuentes["mini"], f"{opcion} {round(valor * 100)} %", TEXTO_SUAVE, (columna, y + 128))
            color = piloto_color(piloto) if opcion == decision.movimiento else APAGADO
            barra(logico, pygame.Rect(columna, y + 150, ancho, 8), valor, color)
    else:
        escribir(logico, fuentes["mini"], "DeepSeek devuelve texto JSON: sin probabilidades", TEXTO_SUAVE, (x, y + 136))
    return rect.bottom


def dibujar_metricas(logico: pygame.Surface, fuentes: dict, piloto: Piloto, por_segundo: float, y: int) -> int:
    ancho = (PANEL_ANCHO - 20) // 3
    datos = [
        (f"{por_segundo:.1f}".replace(".", ","), "decisiones por segundo", TEXTO),
        (segundos(piloto.media), "latencia media", color_latencia(piloto.media) if piloto.latencias else TEXTO),
        (str(len(piloto.latencias)), "decisiones tomadas", TEXTO),
    ]
    for indice, (valor, etiqueta, color) in enumerate(datos):
        rect = pygame.Rect(PANEL_X + indice * (ancho + 10), y, ancho, 74)
        tarjeta(logico, rect)
        escribir(logico, fuentes["valor"], valor, color, (rect.centerx, y + 8), "midtop")
        escribir(logico, fuentes["mini"], etiqueta, TEXTO_SUAVE, (rect.centerx, y + 48), "midtop")
    return y + 74


def dibujar_estado_jefe(logico: pygame.Surface, fuentes: dict, partida: Partida, y: int) -> int:
    rect = pygame.Rect(PANEL_X, y, PANEL_ANCHO, 58)
    jefe = partida.jefe
    x = PANEL_X + 18
    if jefe is not None:
        color = COLOR_JEFE[jefe.numero]
        tarjeta(logico, rect, color)
        estado = "se retira" if jefe.estado == "retirada" else f"{round(100 * jefe.vida / jefe.vida_max)} % de vida"
        escribir(logico, fuentes["titulo"], f"Jefe {jefe.numero}", color, (x, y + 8))
        escribir(logico, fuentes["pequena"], estado, TEXTO, (rect.right - 18, y + 11), "topright")
        barra(logico, pygame.Rect(x, y + 38, PANEL_ANCHO - 36, 10), jefe.vida / jefe.vida_max, color)
        return rect.bottom
    tarjeta(logico, rect)
    falta = partida.proximo_jefe()
    if partida.terminada or falta is None:
        texto = f"Jefes derribados: {partida.jefes_derribados} de {partida.jefes_vistos}"
    else:
        texto = f"Próximo jefe en {math.ceil(falta)} s"
    escribir(logico, fuentes["titulo"], texto, TEXTO_SUAVE, (x, y + 15))
    return rect.bottom


def dibujar_latencias(logico: pygame.Surface, fuentes: dict, piloto: Piloto, y: int, alto: int) -> int:
    rect = pygame.Rect(PANEL_X, y, PANEL_ANCHO, alto)
    tarjeta(logico, rect)
    escribir(logico, fuentes["mini"], "LATENCIA DE CADA DECISIÓN", TEXTO_SUAVE, (PANEL_X + 18, y + 12))
    zona = pygame.Rect(PANEL_X + 18, y + 36, PANEL_ANCHO - 36 - 44, alto - 50)
    for referencia in (0.25, 1.0):
        altura = zona.bottom - zona.height * referencia / ESCALA_LATENCIA
        pygame.draw.line(logico, BORDE, (zona.left, altura), (zona.right, altura))
        texto = segundos(referencia, 2) if referencia < 1 else "1 s"
        escribir(logico, fuentes["mini"], texto, TEXTO_SUAVE, (zona.right + 6, altura), "midleft")
    pygame.draw.line(logico, BORDE, (zona.left, zona.bottom), (zona.right, zona.bottom))
    paso = 7
    recientes = piloto.latencias[-(zona.width // paso):]
    for indice, valor in enumerate(recientes):
        altura = max(2, min(zona.height, zona.height * valor / ESCALA_LATENCIA))
        pygame.draw.rect(logico, color_latencia(valor), (zona.left + indice * paso, zona.bottom - altura, paso - 2, altura),
                         border_radius=2)
    return rect.bottom


def dibujar_panel(logico: pygame.Surface, fuentes: dict, partida: Partida, piloto: Piloto, ahora: float,
                  por_segundo: float, esperando: bool) -> None:
    color = piloto_color(piloto)
    x = PANEL_X
    escribir(logico, fuentes["grande"], piloto.nombre, color, (x, MARGEN - 6))
    escribir(logico, fuentes["pequena"], f"mapa {partida.semilla}", TEXTO_SUAVE, (x + PANEL_ANCHO, MARGEN + 4), "topright")
    escribir(logico, fuentes["pequena"], "pilota en tiempo real: el mundo no le espera", TEXTO_SUAVE, (x, MARGEN + 34))

    y = MARGEN + 66
    for vida in range(VIDAS):
        corazon(logico, ROJO if vida < partida.vidas else APAGADO, (x + 14 + vida * 34, y + 18), 26)
    escribir(logico, fuentes["mini"], "PUNTOS", TEXTO_SUAVE, (x + PANEL_ANCHO, y - 2), "topright")
    escribir(logico, fuentes["valor"], str(partida.puntos), TEXTO, (x + PANEL_ANCHO, y + 12), "topright")

    y += 52
    escribir(logico, fuentes["mini"], f"TIEMPO {reloj_texto(partida.tiempo)} / {reloj_texto(DURACION)}", TEXTO_SUAVE, (x, y))
    tiempo = pygame.Rect(x, y + 20, PANEL_ANCHO, 8)
    barra(logico, tiempo, partida.tiempo / DURACION, color)
    for numero, momento in enumerate(MOMENTOS_JEFE, start=1):
        marca = tiempo.left + tiempo.width * momento / DURACION
        pygame.draw.rect(logico, COLOR_JEFE[numero], (marca - 2, tiempo.top - 4, 4, tiempo.height + 8), border_radius=2)

    y = dibujar_decision(logico, fuentes, piloto, ahora, y + 42) + 12
    y = dibujar_metricas(logico, fuentes, piloto, por_segundo, y) + 12
    y = dibujar_estado_jefe(logico, fuentes, partida, y) + 12
    pie = LOGICO[1] - MARGEN - 16
    y = dibujar_latencias(logico, fuentes, piloto, y, pie - 44 - y) + 10

    resumen = (f"Derribados {partida.derribados}   ·   Jefes {partida.jefes_derribados}   ·   "
               f"Impactos recibidos {partida.impactos}   ·   Precisión {round(partida.precision * 100)} %")
    escribir(logico, fuentes["pequena"], resumen, TEXTO, (x, y))
    if piloto.error:
        escribir(logico, fuentes["mini"], f"Aviso de conexión: {piloto.error[:60]}", ROJO, (x, pie))
    else:
        escribir(logico, fuentes["mini"], "Esc salir   ·   F11 pantalla completa", TEXTO_SUAVE, (x, pie))
    if esperando:
        velo = pygame.Surface((CAMPO_ANCHO, CAMPO_ALTO), pygame.SRCALPHA)
        velo.fill((5, 8, 18, 170))
        logico.blit(velo, (MARGEN, MARGEN))
        escribir(logico, fuentes["titulo"], f"Calentando la conexión con {piloto.corto}…", TEXTO,
                 (MARGEN + CAMPO_ANCHO / 2, MARGEN + CAMPO_ALTO / 2), "center")


def dibujar_final(logico: pygame.Surface, fuentes: dict, partida: Partida, piloto: Piloto, duracion: float) -> None:
    velo = pygame.Surface(LOGICO, pygame.SRCALPHA)
    velo.fill((4, 6, 14, 200))
    logico.blit(velo, (0, 0))
    rect = pygame.Rect(0, 0, 600, 520)
    rect.center = (LOGICO[0] // 2, LOGICO[1] // 2)
    tarjeta(logico, rect, piloto_color(piloto))
    vivo = partida.vidas > 0
    titulo = "¡Sobrevivió!" if vivo else f"Nave destruida a los {reloj_texto(partida.tiempo)}"
    escribir(logico, fuentes["enorme"], titulo, VERDE if vivo else ROJO, (rect.centerx, rect.top + 22), "midtop")
    escribir(logico, fuentes["titulo"], f"{piloto.nombre} · mapa {partida.semilla}", piloto_color(piloto),
             (rect.centerx, rect.top + 92), "midtop")
    por_segundo = len(piloto.latencias) / duracion if duracion else 0.0
    filas = [
        ("Puntos", str(partida.puntos)),
        ("Tiempo en vuelo", f"{reloj_texto(partida.tiempo)} de {reloj_texto(DURACION)}"),
        ("Enemigos derribados", str(partida.derribados)),
        ("Jefes derribados", f"{partida.jefes_derribados} de {partida.jefes_vistos} que aparecieron"),
        ("Impactos recibidos", str(partida.impactos)),
        ("Decisiones", f"{len(piloto.latencias)}  ({por_segundo:.1f} por segundo)".replace(".", ",")),
        ("Latencia media", segundos(piloto.media)),
        ("Precisión de disparo", f"{round(partida.precision * 100)} %"),
    ]
    y = rect.top + 142
    for etiqueta, valor in filas:
        escribir(logico, fuentes["normal"], etiqueta, TEXTO_SUAVE, (rect.left + 60, y))
        escribir(logico, fuentes["normal"], valor, TEXTO, (rect.right - 60, y), "topright")
        y += 36
    otro = "DeepSeek" if piloto.cerebro == "jev" else "jev"
    teclas = [("R", "repetir"), ("C", f"mismo mapa con {otro}"), ("Esc", "salir")]
    anchos = [fuentes["mini"].size(tecla)[0] + 18 + 8 + fuentes["normal"].size(texto)[0] for tecla, texto in teclas]
    x = rect.centerx - (sum(anchos) + 28 * (len(teclas) - 1)) / 2
    for (tecla, texto), ancho in zip(teclas, anchos):
        caja = pygame.Rect(round(x), rect.bottom - 52, fuentes["mini"].size(tecla)[0] + 18, 26)
        pygame.draw.rect(logico, BORDE, caja, border_radius=6)
        pygame.draw.rect(logico, TEXTO_SUAVE, caja, 1, border_radius=6)
        escribir(logico, fuentes["mini"], tecla, TEXTO, caja.center, "center")
        escribir(logico, fuentes["normal"], texto, TEXTO, (caja.right + 8, caja.centery), "midleft")
        x += ancho + 28


def cargar_fuentes() -> dict:
    return {
        "enorme": pygame.font.SysFont("segoeui", 44, bold=True),
        "grande": pygame.font.SysFont("segoeui", 30, bold=True),
        "valor": pygame.font.SysFont("segoeui", 26, bold=True),
        "titulo": pygame.font.SysFont("segoeui", 21, bold=True),
        "normal": pygame.font.SysFont("segoeui", 19),
        "pequena": pygame.font.SysFont("segoeui", 16),
        "mini": pygame.font.SysFont("segoeui", 13, bold=True),
    }


def imprimir_resumen(partida: Partida, piloto: Piloto, duracion: float) -> None:
    por_segundo = len(piloto.latencias) / duracion if duracion else 0.0
    print(f"\n{piloto.nombre} · mapa {partida.semilla}: {partida.puntos} puntos, "
          f"{partida.derribados} enemigos y {partida.jefes_derribados} de {partida.jefes_vistos} jefes derribados, "
          f"{partida.impactos} impactos recibidos, {partida.tiempo:.1f} s en vuelo, "
          f"{len(piloto.latencias)} decisiones ({por_segundo:.2f} por segundo), "
          f"latencia media {piloto.media:.3f} s.", flush=True)


def jugar(pantalla: Pantalla, fuentes: dict, cerebro: str, semilla: int, velocidad: float) -> str | None:
    partida = Partida(semilla)
    piloto = Piloto(partida, cerebro)
    escena = Escena(cerebro)
    otro = "deepseek" if cerebro == "jev" else "jev"
    pantalla.titular(f"jev pilota la nave en tiempo real · {piloto.nombre} · mapa {semilla}")
    piloto.start()
    reloj = pygame.time.Clock()
    acumulado = 0.0
    comienzo: float | None = None
    final: float | None = None
    try:
        while True:
            dt = reloj.tick(FPS) / 1000
            for evento in pygame.event.get():
                if evento.type in (pygame.QUIT, pygame.WINDOWCLOSE):
                    return None
                if evento.type != pygame.KEYDOWN:
                    continue
                if evento.key == pygame.K_ESCAPE:
                    return None
                if evento.key == pygame.K_F11:
                    pantalla.alternar()
                elif final is not None and evento.key == pygame.K_r:
                    return cerebro
                elif final is not None and evento.key == pygame.K_c:
                    return otro

            ahora = time.perf_counter()
            if piloto.listo.is_set() and final is None:
                if comienzo is None:
                    comienzo = ahora
                decision = piloto.tomar()
                if decision is not None:
                    escena.nueva_decision(decision)
                acumulado += min(dt, 0.1) * velocidad
                while acumulado >= PASO and not partida.terminada:
                    partida.avanzar(PASO)
                    acumulado -= PASO
                if partida.terminada:
                    final = ahora
                    imprimir_resumen(partida, piloto, final - comienzo)

            escena.recoger(partida.sacar_eventos())
            escena.actualizar(dt)
            momento = final if final is not None else ahora
            ventana = max(0.5, min(3.0, momento - comienzo)) if comienzo is not None else 3.0
            dibujar_campo(pantalla.logico, escena, partida, piloto, fuentes)
            dibujar_panel(pantalla.logico, fuentes, partida, piloto, momento, piloto.por_segundo(momento, ventana),
                          comienzo is None)
            if final is not None:
                dibujar_final(pantalla.logico, fuentes, partida, piloto, final - comienzo)
            pantalla.presentar()
    finally:
        piloto.parar()


def main() -> None:
    cerebro, semilla, velocidad = argumentos()
    pygame.init()
    pantalla = Pantalla()
    fuentes = cargar_fuentes()
    siguiente: str | None = cerebro
    while siguiente is not None:
        siguiente = jugar(pantalla, fuentes, siguiente, semilla, velocidad)
    pygame.quit()


if __name__ == "__main__":
    main()
