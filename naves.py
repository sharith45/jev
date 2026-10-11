import json
import math
import random
import sys
import threading
import time
from dataclasses import dataclass, field

from jev_cliente import (
    calentar_deepseek,
    calentar_jev,
    instruccion_equivalente,
    preguntar_deepseek,
    preguntar_jev,
    valor_jev,
)

ANCHO = 13
ALTO = 16
FILA_NAVE = ALTO - 1
DURACION = 100.0
PASO = 1 / 60
VIDAS = 5
INVULNERABLE = 1.5
CADENCIA = 0.2
DESLIZ = 11.0
VELOCIDAD_BALA = 24.0
ALCANCE_VISTA = 10
MOMENTOS_JEFE = (24.0, 58.0)
VIDA_JEFE = (22, 32)
PUNTOS_JEFE = 250
PUNTOS_ENEMIGO = {"caza": 10, "kamikaze": 15, "bombardero": 25}
VIDA_ENEMIGO = {"caza": 1, "kamikaze": 1, "bombardero": 3}
NOMBRE_ENEMIGO = {"caza": "enemigo caza", "kamikaze": "enemigo kamikaze", "bombardero": "enemigo bombardero"}

MOVIMIENTOS = {
    "izquierda": (
        "Pasar a la columna de la izquierda: para esquivar lo que viene muy cerca por tu columna si la izquierda "
        "está libre o lo suyo está más lejos, o para ir a por el blanco cuando está a la izquierda y no hay peligro."
    ),
    "quieto": (
        "Quedarte en tu columna: lo correcto si ya tienes un enemigo o el jefe a tiro encima y no viene nada muy "
        "cerca, o si moverte te pondría delante de algo muy cerca. Si no tienes nada a tiro, quedarte no sirve de nada."
    ),
    "derecha": (
        "Pasar a la columna de la derecha: para esquivar lo que viene muy cerca por tu columna si la derecha "
        "está libre o lo suyo está más lejos, o para ir a por el blanco cuando está a la derecha y no hay peligro."
    ),
}

PREGUNTAS = {
    "movimiento": {
        "type": "choice",
        "instructions": (
            "Pilotas una nave en la fila de abajo. Todo lo que baja hacia ti se describe con las filas que le faltan "
            "para llegar a tu fila: si llega a tu fila en tu columna, te golpea. Las balas y los asteroides no se "
            "pueden parar: se esquivan. Esquivar va SIEMPRE antes que disparar: si por tu columna viene algo muy "
            "cerca, pásate a la columna vecina más libre. Si por tu columna no viene nada y no tienes nada a tiro, "
            "ve hacia el blanco, pero nunca te pases a una columna donde algo te va a golpear. "
            "¿Hacia dónde mueves la nave ahora?"
        ),
        "criteria": MOVIMIENTOS,
    },
    "disparar": {
        "type": "noul",
        "instructions": "¿Hay un enemigo o el jefe a tiro justo encima de la nave?",
    },
    "peligro": {
        "type": "noul",
        "instructions": "¿Viene algo muy cerca por tu columna que te va a golpear si no te apartas?",
    },
}

INSTRUCCION_DEEPSEEK = instruccion_equivalente(PREGUNTAS)


@dataclass
class Bala:
    x: float
    y: float
    vx: float
    vy: float
    del_jefe: bool = False


@dataclass
class Asteroide:
    ident: int
    x: float
    y: float
    vy: float


@dataclass
class Enemigo:
    tipo: str
    x: float
    y: float
    azar: random.Random
    vida: int = 1
    estado: str = "entrando"
    fila_espera: float = 3.0
    patrulla: float = 7.0
    destino: float = 0.0
    vy: float = 0.0
    reloj: float = 0.0
    proximo_giro: float = 0.0
    proximo_disparo: float = 0.0
    golpe: float = 0.0


@dataclass
class Jefe:
    numero: int
    x: float
    y: float
    vida: int
    vida_max: int
    azar: random.Random
    estado: str = "entrando"
    fase: float = 0.0
    proximo_patron: float = 0.0
    cola: list = field(default_factory=list)
    golpe: float = 0.0


def _limitar(valor: float, minimo: float, maximo: float) -> float:
    return max(minimo, min(maximo, valor))


def _bajada(enemigo: Enemigo) -> float:
    return 1.4 if enemigo.tipo == "bombardero" else 2.0


def _filas(distancia: float) -> str:
    filas = max(0, int(distancia))
    return "1 fila" if filas == 1 else f"{filas} filas"


class Partida:
    def __init__(self, semilla: int) -> None:
        self.semilla = semilla
        self.azar_mapa = random.Random(semilla)
        self.candado = threading.Lock()
        self.tiempo = 0.0
        self.nave_x = ANCHO // 2
        self.nave_visual = float(self.nave_x)
        self.vidas = VIDAS
        self.puntos = 0
        self.disparando = False
        self.proximo_disparo = 0.0
        self.invulnerable = 0.0
        self.balas: list[Bala] = []
        self.balas_enemigas: list[Bala] = []
        self.asteroides: list[Asteroide] = []
        self.enemigos: list[Enemigo] = []
        self.jefe: Jefe | None = None
        self.jefes_vistos = 0
        self.proxima_aparicion = 1.2
        self.apariciones = 0
        self.eventos: list[tuple] = []
        self.derribados = 0
        self.jefes_derribados = 0
        self.impactos = 0
        self.disparos = 0
        self.aciertos = 0

    @property
    def terminada(self) -> bool:
        return self.vidas <= 0 or self.tiempo >= DURACION

    @property
    def precision(self) -> float:
        return self.aciertos / self.disparos if self.disparos else 0.0

    def proximo_jefe(self) -> float | None:
        if self.jefes_vistos >= len(MOMENTOS_JEFE):
            return None
        return max(0.0, MOMENTOS_JEFE[self.jefes_vistos] - self.tiempo)

    def sacar_eventos(self) -> list[tuple]:
        with self.candado:
            eventos, self.eventos = self.eventos, []
            return eventos

    def ordenar(self, movimiento: str, disparar: bool) -> None:
        with self.candado:
            if self.terminada:
                return
            if movimiento == "izquierda":
                self.nave_x = max(0, self.nave_x - 1)
            elif movimiento == "derecha":
                self.nave_x = min(ANCHO - 1, self.nave_x + 1)
            self.disparando = disparar

    def avanzar(self, dt: float) -> None:
        with self.candado:
            if self.terminada:
                return
            self.tiempo += dt
            self._mover_nave(dt)
            self._disparar()
            self._aparecer()
            self._llamar_jefe()
            self._mover_asteroides(dt)
            self._mover_enemigos(dt)
            self._mover_jefe(dt)
            self._mover_balas(dt)
            self._choques()
            if self.terminada:
                self.eventos.append(("fin", self.vidas > 0))

    def _mover_nave(self, dt: float) -> None:
        paso = DESLIZ * dt
        diferencia = self.nave_x - self.nave_visual
        if abs(diferencia) <= paso:
            self.nave_visual = float(self.nave_x)
        else:
            self.nave_visual += math.copysign(paso, diferencia)
        self.invulnerable = max(0.0, self.invulnerable - dt)

    def _disparar(self) -> None:
        if self.disparando and self.tiempo >= self.proximo_disparo:
            self.balas.append(Bala(self.nave_visual, FILA_NAVE - 0.6, 0.0, -VELOCIDAD_BALA))
            self.proximo_disparo = self.tiempo + CADENCIA
            self.disparos += 1

    def _ritmo(self, momento: float) -> float:
        return 1.2 - 0.5 * min(1.0, momento / DURACION)

    def _tipo_aparicion(self, momento: float, tirada: float) -> str:
        avance = min(1.0, momento / DURACION)
        if tirada < 0.4 - 0.08 * avance:
            return "asteroide"
        if tirada < 0.74 - 0.1 * avance or momento < 6:
            return "caza"
        if tirada < 0.9 or momento < 14:
            return "kamikaze"
        return "bombardero"

    def _aparecer(self) -> None:
        while self.tiempo >= self.proxima_aparicion:
            azar = self.azar_mapa
            momento = self.proxima_aparicion
            intervalo = azar.uniform(0.7, 1.3) * self._ritmo(momento)
            tirada, columna, extra, semilla = azar.random(), azar.randrange(ANCHO), azar.random(), azar.randrange(1 << 30)
            self.proxima_aparicion += intervalo
            self.apariciones += 1
            tipo = self._tipo_aparicion(momento, tirada)
            calma = any(llegada - 4.0 <= momento < llegada for llegada in MOMENTOS_JEFE)
            if (self.jefe is not None or calma) and (tipo != "asteroide" or extra < 0.45):
                continue
            if tipo == "asteroide":
                self.asteroides.append(Asteroide(self.apariciones, float(columna), -1.0, 2.2 + extra * 1.4))
            elif tipo == "caza" and extra < 0.28:
                for desplazamiento in (-1, 0, 1):
                    x = _limitar(columna + desplazamiento, 0, ANCHO - 1)
                    self._nuevo_enemigo("caza", float(x), semilla + desplazamiento)
            else:
                self._nuevo_enemigo(tipo, float(columna), semilla)

    def _nuevo_enemigo(self, tipo: str, x: float, semilla: int) -> None:
        azar = random.Random(semilla)
        enemigo = Enemigo(tipo, x, -1.0, azar, VIDA_ENEMIGO[tipo])
        if tipo == "caza":
            enemigo.fila_espera = azar.uniform(1.5, 5.5)
            enemigo.patrulla = azar.uniform(4.0, 7.0)
        elif tipo == "kamikaze":
            enemigo.fila_espera = azar.uniform(2.0, 4.5)
        else:
            enemigo.fila_espera = azar.uniform(1.0, 3.0)
            enemigo.patrulla = azar.uniform(8.0, 12.0)
        enemigo.destino = x
        enemigo.proximo_disparo = azar.uniform(0.6, 1.8)
        self.enemigos.append(enemigo)

    def _llamar_jefe(self) -> None:
        if self.jefes_vistos >= len(MOMENTOS_JEFE) or self.tiempo < MOMENTOS_JEFE[self.jefes_vistos]:
            return
        if self.jefe is None:
            numero = self.jefes_vistos + 1
            vida = VIDA_JEFE[numero - 1]
            self.jefe = Jefe(numero, (ANCHO - 1) / 2, -3.0, vida, vida, random.Random(self.semilla * 31 + numero))
            self.jefes_vistos += 1
            self.eventos.append(("jefe", numero))
            for enemigo in self.enemigos:
                if enemigo.estado in ("entrando", "patrulla"):
                    enemigo.estado = "huida"
        elif self.jefe.estado != "retirada":
            self.jefe.estado = "retirada"
            self.eventos.append(("retirada", self.jefe.numero))

    def _apuntar(self, x: float, y: float, vy: float, limite: float) -> float:
        llegada = max(0.3, (FILA_NAVE - y) / vy)
        return _limitar((self.nave_visual - x) / llegada, -limite, limite)

    def _mover_asteroides(self, dt: float) -> None:
        for asteroide in self.asteroides:
            asteroide.y += asteroide.vy * dt
        quedan = [a for a in self.asteroides if a.y <= ALTO + 1]
        self.puntos += len(self.asteroides) - len(quedan)
        self.asteroides = quedan

    def _mover_enemigos(self, dt: float) -> None:
        for enemigo in self.enemigos:
            enemigo.reloj += dt
            enemigo.golpe = max(0.0, enemigo.golpe - dt)
            if enemigo.estado == "huida":
                enemigo.y -= 3.0 * dt
            elif enemigo.tipo == "kamikaze":
                self._mover_kamikaze(enemigo, dt)
            else:
                self._mover_patrulla(enemigo, dt)
        self.enemigos = [e for e in self.enemigos if e.vida > 0 and -1.5 <= e.y <= ALTO + 1]

    def _mover_patrulla(self, enemigo: Enemigo, dt: float) -> None:
        pesado = enemigo.tipo == "bombardero"
        if enemigo.estado == "entrando":
            enemigo.y += (1.6 if pesado else 2.4) * dt
            if enemigo.y >= enemigo.fila_espera:
                enemigo.estado = "patrulla"
                enemigo.reloj = 0.0
            return
        enemigo.proximo_giro -= dt
        if enemigo.proximo_giro <= 0:
            paso = enemigo.azar.choice((-1, 1))
            enemigo.destino = _limitar(round(enemigo.x) + paso, 0, ANCHO - 1)
            enemigo.proximo_giro = enemigo.azar.uniform(1.1, 1.6) if pesado else enemigo.azar.uniform(0.7, 1.2)
        rapidez = (2.0 if pesado else 3.0) * dt
        enemigo.x += _limitar(enemigo.destino - enemigo.x, -rapidez, rapidez)
        if enemigo.estado == "patrulla" and enemigo.reloj >= enemigo.patrulla:
            enemigo.estado = "bajando"
        if enemigo.estado == "bajando":
            enemigo.y += _bajada(enemigo) * dt
        enemigo.proximo_disparo -= dt
        if enemigo.proximo_disparo <= 0 and enemigo.y < FILA_NAVE - 4:
            y = enemigo.y + 0.5
            if pesado:
                for vx in (-1.4, 0.0, 1.4):
                    self.balas_enemigas.append(Bala(enemigo.x, y, vx, 4.2))
                enemigo.proximo_disparo = enemigo.azar.uniform(2.4, 3.4)
            else:
                avance = min(1.0, self.tiempo / DURACION)
                rapidez = 4.4 + 1.2 * avance
                apuntada = enemigo.azar.random() < 0.25 + 0.3 * avance
                vx = self._apuntar(enemigo.x, y, rapidez, 2.0) if apuntada else 0.0
                self.balas_enemigas.append(Bala(enemigo.x, y, vx, rapidez))
                enemigo.proximo_disparo = enemigo.azar.uniform(1.6, 2.8)

    def _mover_kamikaze(self, enemigo: Enemigo, dt: float) -> None:
        if enemigo.estado == "entrando":
            enemigo.y += 2.8 * dt
            if enemigo.y >= enemigo.fila_espera:
                enemigo.estado = "apuntando"
                enemigo.reloj = 0.0
        elif enemigo.estado == "apuntando":
            rapidez = 3.5 * dt
            enemigo.x += _limitar(self.nave_visual - enemigo.x, -rapidez, rapidez)
            if enemigo.reloj >= 1.1:
                enemigo.estado = "picado"
                enemigo.x = float(round(enemigo.x))
                enemigo.vy = 3.0
        else:
            enemigo.vy = min(10.0, enemigo.vy + 14.0 * dt)
            enemigo.y += enemigo.vy * dt

    def _mover_jefe(self, dt: float) -> None:
        jefe = self.jefe
        if jefe is None:
            return
        jefe.golpe = max(0.0, jefe.golpe - dt)
        if jefe.estado == "entrando":
            jefe.y += 2.2 * dt
            if jefe.y >= 1.6:
                jefe.y = 1.6
                jefe.estado = "combate"
                jefe.proximo_patron = self.tiempo + 1.0
            return
        if jefe.estado == "retirada":
            jefe.y -= 3.0 * dt
            if jefe.y < -4:
                self.jefe = None
            return
        jefe.fase += dt * (0.35 + 0.15 * jefe.numero)
        jefe.x = (ANCHO - 1) / 2 + 4.3 * math.sin(jefe.fase)
        jefe.y = 1.6 + 0.35 * math.sin(jefe.fase * 2.3)
        while jefe.cola and jefe.cola[0][0] <= self.tiempo:
            _, desplazamiento, vx, vy, apuntada = jefe.cola.pop(0)
            x, y = jefe.x + desplazamiento, jefe.y + 1.1
            if apuntada:
                vx = self._apuntar(x, y, vy, 3.5)
            self.balas_enemigas.append(Bala(x, y, vx, vy, True))
        if not jefe.cola and self.tiempo >= jefe.proximo_patron:
            self._patron(jefe)

    def _patron(self, jefe: Jefe) -> None:
        patrones = ("abanico", "rafaga", "cortina")
        if jefe.numero > 1:
            patrones += ("doble_abanico",)
        patron = jefe.azar.choice(patrones)
        ahora = self.tiempo
        cola = []
        if patron == "abanico":
            cantidad = 5 if jefe.numero == 1 else 7
            cola = [(ahora, 0.0, -2.6 + 5.2 * i / (cantidad - 1), 4.2, False) for i in range(cantidad)]
        elif patron == "rafaga":
            cola = [(ahora + i * 0.22, 0.0, 0.0, 5.5, True) for i in range(1 + 2 * jefe.numero)]
        elif patron == "cortina":
            cola = [(ahora + i * 0.4, lado, 0.0, 5.0, False) for i in range(3) for lado in (-1.3, 1.3)]
        else:
            for tanda in range(2):
                cola += [(ahora + tanda * 0.6, 0.0, -2.8 + 5.6 * (i + tanda * 0.5) / 5.5, 4.4, False) for i in range(6)]
        cola.sort(key=lambda disparo: disparo[0])
        jefe.cola = cola
        jefe.proximo_patron = cola[-1][0] + (2.0 if jefe.numero == 1 else 1.5)

    def _mover_balas(self, dt: float) -> None:
        for bala in self.balas + self.balas_enemigas:
            bala.x += bala.vx * dt
            bala.y += bala.vy * dt
        vivas = []
        for bala in self.balas:
            if bala.y >= -1.5 and not self._impacta(bala):
                vivas.append(bala)
        self.balas = vivas
        self.balas_enemigas = [b for b in self.balas_enemigas if b.y <= ALTO + 1 and -1.5 <= b.x <= ANCHO + 0.5]

    def _impacta(self, bala: Bala) -> bool:
        for asteroide in self.asteroides:
            if abs(asteroide.x - bala.x) < 0.5 and abs(asteroide.y - bala.y) < 0.5:
                self.eventos.append(("chispa", bala.x, bala.y))
                return True
        for enemigo in self.enemigos:
            if enemigo.vida > 0 and abs(enemigo.x - bala.x) < 0.5 and abs(enemigo.y - bala.y) < 0.55:
                self.aciertos += 1
                enemigo.vida -= 1
                enemigo.golpe = 0.12
                if enemigo.vida <= 0:
                    self.derribados += 1
                    self.puntos += PUNTOS_ENEMIGO[enemigo.tipo]
                    self.eventos.append(("explosion", enemigo.x, enemigo.y, 1.0, enemigo.tipo))
                else:
                    self.eventos.append(("chispa", bala.x, bala.y))
                return True
        jefe = self.jefe
        if jefe is not None and jefe.estado != "retirada" and abs(jefe.x - bala.x) < 1.8 and abs(jefe.y - bala.y) < 1.1:
            self.aciertos += 1
            jefe.vida -= 1
            jefe.golpe = 0.08
            self.puntos += 2
            self.eventos.append(("chispa", bala.x, bala.y))
            if jefe.vida <= 0:
                self.jefes_derribados += 1
                self.puntos += PUNTOS_JEFE * jefe.numero
                self.balas_enemigas = [b for b in self.balas_enemigas if not b.del_jefe]
                self.eventos.append(("jefe_cae", jefe.x, jefe.y, jefe.numero))
                self.jefe = None
            return True
        return False

    def _choques(self) -> None:
        if self.invulnerable > 0:
            return
        x = self.nave_visual
        for bala in self.balas_enemigas:
            if abs(bala.x - x) < 0.42 and abs(bala.y - FILA_NAVE) < 0.45:
                self.balas_enemigas.remove(bala)
                self._golpe()
                return
        for asteroide in self.asteroides:
            if abs(asteroide.x - x) < 0.6 and abs(asteroide.y - FILA_NAVE) < 0.6:
                self.asteroides.remove(asteroide)
                self.eventos.append(("explosion", asteroide.x, asteroide.y, 0.8, "asteroide"))
                self._golpe()
                return
        for enemigo in self.enemigos:
            if abs(enemigo.x - x) < 0.65 and abs(enemigo.y - FILA_NAVE) < 0.6:
                enemigo.vida = 0
                self.eventos.append(("explosion", enemigo.x, enemigo.y, 1.0, enemigo.tipo))
                self._golpe()
                return

    def _golpe(self) -> None:
        self.vidas -= 1
        self.impactos += 1
        self.invulnerable = INVULNERABLE
        self.eventos.append(("golpe", self.nave_visual, float(FILA_NAVE)))

    def _amenazas(self) -> dict[int, list[tuple[float, float, str]]]:
        amenazas: dict[int, list[tuple[float, float, str]]] = {}

        def anotar(x: float, y: float, rapidez: float, que: str) -> None:
            distancia = FILA_NAVE - y
            if -0.5 < distancia <= ALCANCE_VISTA:
                amenazas.setdefault(round(x), []).append((distancia, max(0.0, distancia) / rapidez, que))

        for asteroide in self.asteroides:
            anotar(asteroide.x, asteroide.y, asteroide.vy, "asteroide")
        for bala in self.balas_enemigas:
            llegada = max(0.0, (FILA_NAVE - bala.y) / bala.vy)
            que = "bala del jefe" if bala.del_jefe else "bala enemiga"
            anotar(bala.x + bala.vx * llegada, bala.y, bala.vy, que)
        for enemigo in self.enemigos:
            if enemigo.estado == "picado":
                anotar(enemigo.x, enemigo.y, 8.0, "kamikaze cayendo en picado")
            elif enemigo.estado == "apuntando":
                anotar(enemigo.x, enemigo.y, 8.0, "kamikaze apuntándote, a punto de lanzarse")
            elif enemigo.estado == "bajando" and FILA_NAVE - enemigo.y <= 6:
                anotar(enemigo.x, enemigo.y, _bajada(enemigo), f"{NOMBRE_ENEMIGO[enemigo.tipo]} bajando hacia tu fila")
        return amenazas

    def _texto_columna(self, amenazas: dict, columna: int, desplazamiento: int) -> str:
        if columna < 0 or columna >= ANCHO:
            return "pared: no puedes ir ahí"
        cercanas = sorted(amenazas.get(columna, []))[:2]
        if not cercanas:
            return "libre: no baja nada por tu columna" if desplazamiento == 0 else "libre"
        partes = []
        for distancia, llegada, que in cercanas:
            aviso = ""
            if llegada <= 1.1 and desplazamiento == 0:
                aviso = " (muy cerca: si te quedas, te golpea)"
            elif llegada <= 1.1 and abs(desplazamiento) == 1:
                aviso = " (muy cerca: si te pasas ahí, te golpea)"
            partes.append(f"{que} a {_filas(distancia)}{aviso}")
        return " y ".join(partes)

    def _a_tiro(self, columna: int, amenazas: dict) -> str:
        jefe = self.jefe
        if jefe is not None and jefe.estado == "combate" and abs(jefe.x - columna) < 1.5:
            return "el JEFE está justo encima de ti: a tiro"
        encima = [e for e in self.enemigos if abs(e.x - columna) < 0.5 and -0.5 < e.y < FILA_NAVE - 0.5]
        if encima:
            blanco = max(encima, key=lambda e: e.y)
            return f"{NOMBRE_ENEMIGO[blanco.tipo]} justo encima, a {_filas(FILA_NAVE - blanco.y)}: a tiro"
        blancos = [(abs(e.x - columna), e.x, NOMBRE_ENEMIGO[e.tipo]) for e in self.enemigos if -0.5 < e.y < FILA_NAVE - 1]
        if jefe is not None and jefe.estado == "combate":
            blancos.append((max(0.0, abs(jefe.x - columna) - 1.5), jefe.x, "jefe"))
        if not blancos:
            return "nada a tiro y ningún enemigo en pantalla"
        distancia, x, nombre = min(blancos)
        columnas = max(1, round(distancia))
        lado = "izquierda" if x < columna else "derecha"
        plural = "columna" if columnas == 1 else "columnas"
        texto = f"nada a tiro encima; para dispararle al {nombre} tienes que ir {columnas} {plural} a la {lado}"
        vecina = columna - 1 if lado == "izquierda" else columna + 1
        if any(llegada <= 1.1 for _, llegada, _ in amenazas.get(vecina, [])):
            texto += f", pero pasarte ahora a la columna de la {lado} te haría chocar"
        return texto

    def describir(self) -> dict:
        with self.candado:
            columna = self.nave_x
            amenazas = self._amenazas()
            estado = {
                "nave": f"estás en la columna {columna} (de 0 a {ANCHO - 1}), en la fila de abajo",
                "tu_columna": self._texto_columna(amenazas, columna, 0),
                "columna_izquierda": self._texto_columna(amenazas, columna - 1, -1),
                "columna_derecha": self._texto_columna(amenazas, columna + 1, 1),
                "dos_columnas_a_la_izquierda": self._texto_columna(amenazas, columna - 2, -2),
                "dos_columnas_a_la_derecha": self._texto_columna(amenazas, columna + 2, 2),
                "a_tiro": self._a_tiro(columna, amenazas),
            }
            jefe = self.jefe
            if jefe is not None and jefe.estado == "combate":
                izquierda = max(0, round(jefe.x - 1.5))
                derecha = min(ANCHO - 1, round(jefe.x + 1.5))
                estado["jefe"] = (
                    f"jefe {jefe.numero} con {round(100 * jefe.vida / jefe.vida_max)} % de vida, "
                    f"encima de las columnas {izquierda} a {derecha}; dispara abanicos y ráfagas"
                )
            return estado


@dataclass
class Decision:
    movimiento: str
    disparar: bool
    peligro: bool
    segundos: float
    momento: float
    probabilidades: dict = field(default_factory=dict)


def _afirmativo(valor) -> bool:
    if isinstance(valor, bool):
        return valor
    return str(valor).strip().lower() in ("true", "sí", "si", "1", "yes")


class Piloto(threading.Thread):
    def __init__(self, partida: Partida, cerebro: str) -> None:
        super().__init__(daemon=True)
        self.partida = partida
        self.cerebro = cerebro
        self.latencias: list[float] = []
        self.momentos: list[float] = []
        self.ultima: Decision | None = None
        self.errores = 0
        self.error = ""
        self.listo = threading.Event()
        self._pendiente: Decision | None = None
        self._candado = threading.Lock()
        self._activo = True

    @property
    def nombre(self) -> str:
        return "jev (System One)" if self.cerebro == "jev" else "DeepSeek (LLM normal)"

    @property
    def corto(self) -> str:
        return "jev" if self.cerebro == "jev" else "DeepSeek"

    def calentar(self) -> None:
        calentar_jev() if self.cerebro == "jev" else calentar_deepseek()

    def _decidir(self, estado: dict) -> Decision:
        if self.cerebro == "jev":
            respuestas, segundos = preguntar_jev(estado, PREGUNTAS)
            movimiento = respuestas.get("movimiento", {})
            eleccion = valor_jev(movimiento)
            return Decision(
                eleccion if eleccion in MOVIMIENTOS else "quieto",
                bool(valor_jev(respuestas.get("disparar", {}))),
                bool(valor_jev(respuestas.get("peligro", {}))),
                segundos,
                time.perf_counter(),
                movimiento.get("probabilities") or {},
            )
        respuesta, segundos = preguntar_deepseek(INSTRUCCION_DEEPSEEK, json.dumps(estado, ensure_ascii=False), max_tokens=60)
        eleccion = str(respuesta.get("movimiento", "quieto")).strip().lower()
        return Decision(
            eleccion if eleccion in MOVIMIENTOS else "quieto",
            _afirmativo(respuesta.get("disparar")),
            _afirmativo(respuesta.get("peligro")),
            segundos,
            time.perf_counter(),
        )

    def run(self) -> None:
        try:
            self.calentar()
        except SystemExit as salida:
            self.error = str(salida)
            self.listo.set()
            return
        except Exception as fallo:
            self.error = f"calentamiento: {type(fallo).__name__}"
        self.listo.set()
        while self._activo and not self.partida.terminada:
            try:
                decision = self._decidir(self.partida.describir())
            except SystemExit as salida:
                self.error = str(salida)
                return
            except Exception as fallo:
                self.errores += 1
                self.error = type(fallo).__name__
                time.sleep(0.3)
                continue
            if not self._activo or self.partida.terminada:
                return
            self.partida.ordenar(decision.movimiento, decision.disparar)
            with self._candado:
                self.error = ""
                self._pendiente = decision
                self.ultima = decision
                self.latencias.append(decision.segundos)
                self.momentos.append(decision.momento)

    def tomar(self) -> Decision | None:
        with self._candado:
            decision, self._pendiente = self._pendiente, None
            return decision

    def parar(self) -> None:
        self._activo = False

    @property
    def media(self) -> float:
        return sum(self.latencias) / len(self.latencias) if self.latencias else 0.0

    def por_segundo(self, ahora: float, ventana: float = 3.0) -> float:
        with self._candado:
            recientes = [m for m in self.momentos if ahora - m <= ventana]
        return len(recientes) / ventana


def argumentos() -> tuple[str, int, float]:
    cerebro = "deepseek" if "deepseek" in sys.argv else "jev"
    if "--semilla" in sys.argv:
        semilla = int(sys.argv[sys.argv.index("--semilla") + 1])
    else:
        semilla = random.randrange(1, 1000)
    velocidad = 1.35 if "--rapido" in sys.argv else 1.0
    return cerebro, semilla, velocidad


if __name__ == "__main__":
    import runpy
    from pathlib import Path

    runpy.run_path(str(Path(__file__).with_name("07_juego_naves_grafico.py")), run_name="__main__")
