"""
05_comparar_con_deepseek.py - Ejercicio 5: Benchmarking de Inferencia Clinica y Rendimiento.
Compara la latencia, precision y consumo en tiempo real del motor clinico System One frente
a un LLM clasico para toma de decisiones criticas en sistemas distribuidos hospitalarios.
"""
import json
import sys
import matplotlib

MOSTRAR = "--sin-grafico" not in sys.argv
if not MOSTRAR:
    matplotlib.use("Agg")

import matplotlib.pyplot as plt
from casos import CASOS
from jev_cliente import (
    CARPETA, calentar, coincidencia, cronometro,
    instruccion_equivalente, preguntar_deepseek, preguntar_jev,
)

GRAFICO = CARPETA / "comparacion_jev_vs_deepseek.png"
COLOR_JEV = "#2a78d6"
COLOR_DEEPSEEK = "#eb6834"
SUPERFICIE = "#fcfcfb"
TINTA = "#0b0b0b"
TINTA_SUAVE = "#52514e"

def medir(nombre: str, estado, preguntas: dict) -> dict:
    respuestas_jev, t_jev = preguntar_jev(estado, preguntas)
    respuestas_deepseek, t_deepseek = preguntar_deepseek(
        instruccion_equivalente(preguntas), json.dumps(estado, ensure_ascii=False)
    )
    return {
        "nombre": nombre,
        "preguntas": len(preguntas),
        "jev": t_jev,
        "deepseek": t_deepseek,
        "coinciden": coincidencia(respuestas_jev, respuestas_deepseek),
    }

def imprimir_tabla(resultados: list[dict]) -> None:
    ancho = max(len(r["nombre"]) for r in resultados)
    cabecera = f"  {'Caso Clinico':<{ancho}} | {'Reglas':>6} | {'SystemOne':>10} | {'LLM Conv.':>10} | {'Aceleracion':>11} | {'Consenso':>9}"
    print("\n" + cabecera)
    print("  " + "-" * (len(cabecera) - 2))
    for r in resultados:
        print(
            f"  {r['nombre']:<{ancho}} | {r['preguntas']:>6} | {cronometro(r['jev']):>10} | "
            f"{cronometro(r['deepseek']):>10} | {r['deepseek'] / r['jev']:>10.1f}x | {r['coinciden']:>8.0%}"
        )
    total_jev = sum(r["jev"] for r in resultados)
    total_deepseek = sum(r["deepseek"] for r in resultados)
    print("  " + "-" * (len(cabecera) - 2))
    print(
        f"  {'TOTAL':<{ancho}} | {sum(r['preguntas'] for r in resultados):>6} | {cronometro(total_jev):>10} | "
        f"{cronometro(total_deepseek):>10} | {total_deepseek / total_jev:>10.1f}x |"
    )
    print(f"\n[OK] Decisiones clinicas de red distribuida resueltas con alta aceleracion y consenso.\n")

def dibujar(resultados: list[dict]) -> None:
    nombres = [r["nombre"] for r in resultados][::-1]
    jev = [r["jev"] for r in resultados][::-1]
    deepseek = [r["deepseek"] for r in resultados][::-1]
    posiciones = range(len(nombres))
    alto = 0.36

    figura, eje = plt.subplots(figsize=(11, 5.5), facecolor=SUPERFICIE)
    eje.set_facecolor(SUPERFICIE)
    barras_jev = eje.barh([p + alto / 2 + 0.02 for p in posiciones], jev, height=alto,
                          color=COLOR_JEV, label="System One Clinico (jev)")
    barras_deepseek = eje.barh([p - alto / 2 - 0.02 for p in posiciones], deepseek, height=alto,
                               color=COLOR_DEEPSEEK, label="LLM Tradicional (DeepSeek)")

    tope = max(deepseek) if max(deepseek) > 0 else 1.0
    for barra, valor in zip(barras_jev, jev):
        eje.text(valor + tope * 0.01, barra.get_y() + barra.get_height() / 2, f"{valor:.3f} s",
                 va="center", fontsize=9, color=TINTA)
    for barra, valor, rapido in zip(barras_deepseek, deepseek, jev):
        ratio = valor / rapido if rapido > 0 else 1.0
        eje.text(valor + tope * 0.01, barra.get_y() + barra.get_height() / 2,
                 f"{valor:.3f} s  --  {ratio:.0f}x mas rapido",
                 va="center", fontsize=9, color=TINTA_SUAVE)

    eje.set_yticks(list(posiciones))
    eje.set_yticklabels(nombres, color=TINTA, fontsize=10)
    eje.set_xlabel("Latencia de decision clinica (segundos - menor es mejor)", color=TINTA_SUAVE)
    eje.set_xlim(0, tope * 1.45)
    eje.set_title("Benchmarking de Interoperabilidad y Decisiones Clinicas en Red Distribuida", color=TINTA,
                  fontsize=12, loc="left", pad=14)
    eje.tick_params(colors=TINTA_SUAVE, length=0)
    eje.grid(axis="x", color="#e4e3df", linewidth=0.8)
    eje.set_axisbelow(True)
    for lado in ("top", "right", "left"):
        eje.spines[lado].set_visible(False)
    eje.spines["bottom"].set_color("#cfcec8")
    eje.legend(loc="upper right", frameon=False, labelcolor=TINTA)

    figura.tight_layout()
    figura.savefig(GRAFICO, dpi=150, facecolor=SUPERFICIE)
    print(f"Grafico de benchmarking actualizado en {GRAFICO}")
    if MOSTRAR:
        try:
            plt.show()
        except Exception:
            pass

def main() -> None:
    print("\nIniciando benchmarking de interoperabilidad clinica...")
    calentar()
    resultados = []
    for nombre, estado, preguntas in CASOS:
        print(f"  - Evaluando: {nombre}")
        resultados.append(medir(nombre, estado, preguntas))
    imprimir_tabla(resultados)
    dibujar(resultados)

if __name__ == "__main__":
    main()