"""
02_muchas_preguntas.py - Ejercicio 2: Auditoria Integral del Resumen Digital de Atencion (RDA).
Evalua 40 criterios de interoperabilidad y calidad de la Resolucion 866/2021 sobre un documento
clinico Composition / Bundle document FHIR R4 en una sola pasada de inferencia paralela.
"""
from casos import RESENA, preguntas_resena
from jev_cliente import calentar_jev, cronometro, mostrar, preguntar_jev

CANTIDADES = (1, 10, 20, 40)

def main() -> None:
    calentar_jev()
    print("\n" + "=" * 75)
    print("  AUDITORIA DISTRIBUIDA DE CALIDAD CLINICA - RDA & RESOLUCION 866/2021")
    print("=" * 75)
    print("Evaluacion del mismo expediente clinico RDA aumentando el rigor de auditoria:\n")
    print(f"  {'Criterios':>10} | {'Tiempo':>9} | {'Por Criterio':>14}")
    print(f"  {'-' * 10}-+-{'-' * 9}-+-{'-' * 14}")

    respuestas, preguntas = {}, {}
    for cantidad in CANTIDADES:
        preguntas = preguntas_resena(cantidad)
        respuestas, segundos = preguntar_jev(RESENA, preguntas)
        print(f"  {cantidad:>10} | {cronometro(segundos):>9} | {segundos / cantidad * 1000:>11.2f} ms")

    print(f"\nDictamen de los {len(respuestas)} criterios evaluados sobre el RDA (Composition FHIR):\n")
    cumplidos = 0
    for nombre, respuesta in respuestas.items():
        texto_pregunta = preguntas[nombre]['instructions']
        valor_str = mostrar(respuesta)
        if "SI" in valor_str:
            cumplidos += 1
        print(f"  [{nombre}] {texto_pregunta:<60} {valor_str}")

    tasa = cumplidos / len(respuestas) * 100
    print(f"\n[RESULTADO] Conformidad del RDA con estandar FHIR R4: {cumplidos}/{len(respuestas)} ({tasa:.1f}%)")
    print("[OK] La evaluacion de 40 reglas clinicas en paralelo minimiza el overhead en redes distribuidas.\n")

if __name__ == "__main__":
    main()