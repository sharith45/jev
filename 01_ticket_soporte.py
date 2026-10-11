"""
01_ticket_soporte.py - Ejercicio 1: Triage Clinico y Remision Inter-Hospitalaria.
Modela el flujo de admision y clasificacion de urgencias segun Triage Manchester / Res. 5596,
y evaluacion de riesgo vital para paciente remitido entre sedes clinicas distribuidas.
"""
import sys
from casos import PREGUNTAS_TICKET, SEDES_DISTRIBUIDAS, TICKET
from jev_cliente import BUS_CLINICO_GLOBAL, calentar_jev, cronometro, mostrar, preguntar_jev

def main() -> None:
    estado = dict(TICKET)
    if len(sys.argv) > 1:
        estado["mensaje"] = " ".join(sys.argv[1:])

    calentar_jev()
    respuestas, segundos = preguntar_jev(estado, PREGUNTAS_TICKET)

    sede_origen = SEDES_DISTRIBUIDAS.get(estado.get("id_sede_origen", 3), {})
    sede_destino = SEDES_DISTRIBUIDAS.get(estado.get("id_sede_destino", 1), {})

    print("\n" + "=" * 75)
    print("  RED DISTRIBUIDA DE SALUD - ADMISION Y TRIAGE CLINICO INTER-SEDE")
    print("=" * 75)
    print(f"  Sede Origen : Sede {sede_origen.get('id_sede')} - {sede_origen.get('institucion')} ({sede_origen.get('nombre_ciudad')})")
    print(f"  Sede Destino: Sede {sede_destino.get('id_sede')} - {sede_destino.get('institucion')} ({sede_destino.get('nombre_ciudad')})")
    print(f"  HIS Origen  : {sede_origen.get('vendor_his')}  --> HIS Destino: {sede_destino.get('vendor_his')}")
    print(f"\nEvento Clinico / Cuadro Medico:\n  {estado['mensaje']}\n")
    print("Decisiones de Interoperabilidad Clinica:")
    for nombre, respuesta in respuestas.items():
        print(f"  - {nombre:<20} -> {mostrar(respuesta)}")

    evento_bus = {"tipo": "TRIAGE_COMPLETADO", "sede_origen": sede_origen.get("id_sede"), "sede_destino": sede_destino.get("id_sede"), "decisiones": {k: mostrar(v) for k, v in respuestas.items()}}
    BUS_CLINICO_GLOBAL.publicar("hospital.sincelejo.inbound", evento_bus)

    print(f"\n[OK] Notificacion distribuida despachada al topico hospital.sincelejo.inbound")
    print(f"[OK] Motor clinico tomo {len(respuestas)} decisiones en {cronometro(segundos)}\n")

if __name__ == "__main__":
    main()