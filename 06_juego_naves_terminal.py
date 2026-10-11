import os
import sys
import time

from naves import ALTO, ANCHO, DURACION, FILA_NAVE, PASO, VIDAS, Partida, Piloto, argumentos

INICIO = "\x1b[H"
LIMPIAR = "\x1b[2J"
OCULTAR_CURSOR = "\x1b[?25l"
MOSTRAR_CURSOR = "\x1b[?25h"
AZUL = "\x1b[94m"
NARANJA = "\x1b[38;5;208m"
MAGENTA = "\x1b[95m"
VIOLETA = "\x1b[38;5;141m"
GRIS = "\x1b[90m"
CIAN = "\x1b[96m"
AMARILLO = "\x1b[93m"
VERDE = "\x1b[92m"
ROJO = "\x1b[91m"
NEGRITA = "\x1b[1m"
FIN = "\x1b[0m"
FPS_TERMINAL = 15
DURACION_CHISPA = 0.25
SIMBOLO_ENEMIGO = {"caza": f"{NARANJA}▼{FIN} ", "kamikaze": f"{ROJO}{NEGRITA}V{FIN} ", "bombardero": f"{VIOLETA}W{FIN} "}
COLOR_JEFE = {1: MAGENTA, 2: VIOLETA}
FLECHAS = {"izquierda": "← IZQUIERDA", "quieto": "QUIETO", "derecha": "DERECHA →"}


def color_latencia(segundos: float) -> str:
    return VERDE if segundos <= 0.4 else AMARILLO if segundos <= 0.8 else ROJO


def reloj_texto(valor: float) -> str:
    return f"{int(valor // 60)}:{int(valor % 60):02d}"


def rejilla(partida: Partida, chispas: dict, ahora: float) -> list[list[str]]:
    celdas = [["  "] * ANCHO for _ in range(ALTO)]

    def poner(x: float, y: float, texto: str) -> None:
        columna, fila = round(x), round(y)
        if 0 <= columna < ANCHO and 0 <= fila < ALTO:
            celdas[fila][columna] = texto

    for asteroide in partida.asteroides:
        poner(asteroide.x, asteroide.y, f"{GRIS}●{FIN} ")
    for bala in partida.balas:
        poner(bala.x, bala.y, f"{CIAN}│{FIN} ")
    for enemigo in partida.enemigos:
        simbolo = SIMBOLO_ENEMIGO[enemigo.tipo]
        if enemigo.estado == "apuntando" and int(ahora * 8) % 2:
            simbolo = f"{AMARILLO}{NEGRITA}!{FIN} "
        poner(enemigo.x, enemigo.y, simbolo)
    jefe = partida.jefe
    if jefe is not None:
        color = COLOR_JEFE[jefe.numero]
        for desplazamiento in (-1, 0, 1):
            poner(jefe.x + desplazamiento, jefe.y, f"{color}██{FIN}")
        poner(jefe.x, jefe.y + 1, f"{color}▼▼{FIN}")
    for bala in partida.balas_enemigas:
        poner(bala.x, bala.y, f"{MAGENTA if bala.del_jefe else NARANJA}•{FIN} ")
    if partida.vidas > 0 and (partida.invulnerable <= 0 or int(ahora * 10) % 2):
        poner(partida.nave_visual, FILA_NAVE, f"{AZUL}{NEGRITA}▲{FIN} ")
    for (columna, fila), hasta in chispas.items():
        if hasta > ahora:
            poner(columna, fila, f"{AMARILLO}✸{FIN} ")
    return celdas


def dibujar(partida: Partida, piloto: Piloto, chispas: dict, ahora: float, por_segundo: float) -> None:
    borde = "─" * (ANCHO * 2)
    peligro = piloto.ultima is not None and piloto.ultima.peligro
    marco = ROJO if peligro else ""
    lineas = [f"  {marco}╭{borde}╮{FIN}   {NEGRITA}jev pilota la nave en tiempo real{FIN}"]
    for fila in rejilla(partida, chispas, ahora):
        lineas.append(f"  {marco}│{FIN}{''.join(fila)}{marco}│{FIN}")
    lineas.append(f"  {marco}╰{borde}╯{FIN}")

    corazones = f"{ROJO}{'♥' * partida.vidas}{GRIS}{'♡' * (VIDAS - partida.vidas)}{FIN}"
    decision = piloto.ultima
    if decision is None:
        texto_decision = f"{GRIS}esperando la primera respuesta{FIN}"
        latencia = f"{GRIS}sin datos{FIN}"
    else:
        disparo = f" + {CIAN}DISPARA{FIN}" if decision.disparar else ""
        aviso = f"   {ROJO}peligro{FIN}" if decision.peligro else ""
        texto_decision = f"{NEGRITA}{FLECHAS[decision.movimiento]}{FIN}{disparo}{aviso}"
        latencia = f"{color_latencia(decision.segundos)}{decision.segundos:.3f} s{FIN}"
    jefe = partida.jefe
    if jefe is not None:
        lleno = round(20 * jefe.vida / jefe.vida_max)
        color = COLOR_JEFE[jefe.numero]
        texto_jefe = f"Jefe {jefe.numero}: {color}{'█' * lleno}{GRIS}{'░' * (20 - lleno)}{FIN} {round(100 * jefe.vida / jefe.vida_max)} %"
    elif partida.proximo_jefe() is not None:
        texto_jefe = f"Próximo jefe en {int(partida.proximo_jefe()) + 1} s"
    else:
        texto_jefe = f"Jefes derribados: {partida.jefes_derribados} de {partida.jefes_vistos}"
    error = f"   {ROJO}conexión: {piloto.error}{FIN}" if piloto.error else ""
    lineas += [
        f"  Piloto: {NEGRITA}{piloto.nombre}{FIN}   mapa {partida.semilla}   tiempo {reloj_texto(partida.tiempo)} / {reloj_texto(DURACION)}",
        f"  Vidas {corazones}   Puntos {NEGRITA}{partida.puntos}{FIN}   Derribados {partida.derribados}   "
        f"Impactos recibidos {partida.impactos}",
        f"  Decisión: {texto_decision}",
        f"  Latencia {latencia} · media {piloto.media:.3f} s · {por_segundo:.1f} decisiones/s · {len(piloto.latencias)} decisiones",
        f"  {texto_jefe}{error}",
        f"  {GRIS}Ctrl+C para salir{FIN}",
    ]
    sys.stdout.write(INICIO + "\n".join(linea + "\x1b[K" for linea in lineas) + "\n")
    sys.stdout.flush()


def resumen(partida: Partida, piloto: Piloto, duracion: float) -> None:
    otro = "deepseek" if piloto.cerebro == "jev" else ""
    por_segundo = len(piloto.latencias) / duracion if duracion else 0.0
    final = "sobrevivió" if partida.vidas > 0 else f"nave destruida a los {reloj_texto(partida.tiempo)}"
    print(f"\n  {NEGRITA}Fin de la partida{FIN}: {final}  ({piloto.nombre}, mapa {partida.semilla})")
    print(f"  Puntos {partida.puntos} · enemigos derribados {partida.derribados} · "
          f"jefes derribados {partida.jefes_derribados} de {partida.jefes_vistos} · impactos recibidos {partida.impactos}")
    print(f"  {len(piloto.latencias)} decisiones en {duracion:.1f} s ({por_segundo:.1f} por segundo) · "
          f"latencia media {piloto.media:.3f} s")
    comando = " ".join(parte for parte in ("python", os.path.basename(__file__), otro, "--semilla", str(partida.semilla)) if parte)
    print(f"\n  Mismo mapa con el otro piloto:  {comando}\n")


def main() -> None:
    cerebro, semilla, velocidad = argumentos()
    if os.name == "nt":
        os.system("")
    partida = Partida(semilla)
    piloto = Piloto(partida, cerebro)
    print(f"Calentando la conexión con {piloto.nombre}...")
    piloto.start()
    piloto.listo.wait()

    chispas: dict[tuple[int, int], float] = {}
    comienzo = anterior = time.perf_counter()
    proximo_dibujo = comienzo
    acumulado = 0.0
    sys.stdout.write(LIMPIAR + OCULTAR_CURSOR)
    try:
        while not partida.terminada:
            ahora = time.perf_counter()
            dt, anterior = ahora - anterior, ahora
            acumulado += min(dt, 0.1) * velocidad
            while acumulado >= PASO and not partida.terminada:
                partida.avanzar(PASO)
                acumulado -= PASO
            for evento in partida.sacar_eventos():
                if evento[0] in ("explosion", "golpe", "jefe_cae"):
                    chispas[(round(evento[1]), round(evento[2]))] = ahora + DURACION_CHISPA * 2
                elif evento[0] == "chispa":
                    chispas[(round(evento[1]), round(evento[2]))] = ahora + DURACION_CHISPA
            if ahora >= proximo_dibujo or partida.terminada:
                ventana = max(0.5, min(3.0, ahora - comienzo))
                dibujar(partida, piloto, chispas, ahora, piloto.por_segundo(ahora, ventana))
                chispas = {clave: hasta for clave, hasta in chispas.items() if hasta > ahora}
                proximo_dibujo = ahora + 1 / FPS_TERMINAL
            time.sleep(0.004)
    except KeyboardInterrupt:
        pass
    finally:
        piloto.parar()
        sys.stdout.write(MOSTRAR_CURSOR)
    resumen(partida, piloto, time.perf_counter() - comienzo)


if __name__ == "__main__":
    main()
