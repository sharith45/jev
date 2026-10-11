"""
04_filtro_spam.py - Ejercicio 4: Filtro de Calidad, Deteccion de Ruido y Artefactos en Telemetria.
Detecta lecturas descalibradas, payloads HL7/FHIR corruptos o datos erroneos de monitoreo clinico
antes de su persistencia en el Repositorio de Datos Clinicos (CDR HAPI FHIR).
"""
from casos import COMENTARIOS, ESTADO_COMENTARIOS, PREGUNTAS_SPAM
from jev_cliente import calentar_jev, cronometro, preguntar_jev, valor_jev

def main() -> None:
    calentar_jev()
    respuestas, segundos = preguntar_jev(ESTADO_COMENTARIOS, PREGUNTAS_SPAM)

    print("\n" + "=" * 75)
    print("  FILTRO DE CALIDAD Y ANOMALIAS EN TELEMETRIA CLINICA DISTRIBUIDA")
    print("=" * 75)
    print(f"Total de senales/muestras auditadas en el pipeline: {len(COMENTARIOS)}\n")
    anomalias = 0
    for numero, texto in enumerate(COMENTARIOS, 1):
        respuesta = respuestas[f"spam_{numero:02d}"]
        es_anomalia = valor_jev(respuesta)
        anomalias += 1 if es_anomalia else 0
        marca = "ANOMALIA " if es_anomalia else "VALIDO   "
        print(f"  [{marca}] {texto[:75]}")

    print(f"\n  Muestras validas para ingesta CDR: {len(COMENTARIOS) - anomalias}")
    print(f"  Muestras filtradas / descartadas : {anomalias}")
    print(f"\n[OK] Ingesta y filtrado de senales completado en {cronometro(segundos)}\n")

if __name__ == "__main__":
    main()