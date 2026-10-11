"""
03_enrutar_30_opciones.py - Ejercicio 3: Enrutador Inteligente Mirth Connect / Apache NiFi.
Emula la mediacion, normalizacion y enrutamiento inteligente de mensajes y ordenes clinicas
entre 30 servicios hospitalarios especializados de la red de 3 sedes clinicas.
"""
import sys
from casos import PETICION, PREGUNTAS_ENRUTAR
from jev_cliente import calentar_jev, cronometro, preguntar_jev

TOP = 3

def main() -> None:
    estado = {"peticion": " ".join(sys.argv[1:])} if len(sys.argv) > 1 else dict(PETICION)
    calentar_jev()
    respuestas, segundos = preguntar_jev(estado, PREGUNTAS_ENRUTAR)
    decision = respuestas["departamento"]
    opciones = len(PREGUNTAS_ENRUTAR["departamento"]["criteria"])
    mejores = sorted(decision.get("probabilities", {}).items(), key=lambda par: par[1], reverse=True)[:TOP]

    print("\n" + "=" * 75)
    print("  PIPELINE DE MEDIACION E INTEGRACION MIRTH CONNECT / APACHE NiFi")
    print("=" * 75)
    print(f"Mensaje Clinico de Entrada:\n  {estado['peticion']}\n")
    print(f"  Servicio Hospitalario Seleccionado entre {opciones}: {decision['choice']}  ({decision.get('confidence', 0):.0%})\n")
    print(f"  Top {TOP} Servicios Clinicos Candidatos:")
    for servicio, probabilidad in mejores:
        barra = "#" * round(probabilidad * 30)
        print(f"    {servicio:<35} {probabilidad:6.1%}  {barra}")
    print(f"\n[OK] Enrutamiento de mensaje de interoperabilidad ejecutado en {cronometro(segundos)}\n")

if __name__ == "__main__":
    main()