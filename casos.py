"""
casos.py - Banco de Datos Clinicos, Topologia Multisede y Esquemas FHIR R4.
Red Distribuida de 3 Sedes Hospitalarias:
  - Sede 1: Hospital Universitario de Sincelejo (Vendor HIS: Meditech)
  - Sede 2: Clinica del Caribe Cartagena (Vendor HIS: Cerner)
  - Sede 3: Centro Medico Asistencial Corozal (Vendor HIS: EMR SaaS Regional)
Integrado con HAPI FHIR R4, Master Patient Index (MPI), Mirth Connect / NiFi,
y Health Service Bus para interoperabilidad clinica transaccional.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

SEDES_DISTRIBUIDAS = {
    1: {
        "id_sede": 1,
        "nombre_ciudad": "Sincelejo",
        "institucion": "Hospital Universitario de Sincelejo",
        "codigo_reps": "700010012301",
        "vendor_his": "Meditech",
        "vendor_emr": "Meditech v6.1",
        "vendor_lis_pacs": "Carestream PACS / Roche Cobas",
        "host": "localhost",
        "port_db": 5432,
        "db_name": "sede_sincelejo_db",
        "fhir_endpoint": "http://localhost:8080/fhir",
        "queue_in": "hospital.sincelejo.inbound",
        "queue_out": "hospital.sincelejo.outbound",
        "divipola": "70001",
        "departamento": "Sucre",
    },
    2: {
        "id_sede": 2,
        "nombre_ciudad": "Cartagena",
        "institucion": "Clinica Especializada del Caribe",
        "codigo_reps": "130010045601",
        "vendor_his": "Cerner Millennium",
        "vendor_emr": "Cerner Millennium 2023",
        "vendor_lis_pacs": "Agfa HealthCare / Sysmex XN",
        "host": "localhost",
        "port_db": 5432,
        "db_name": "sede_cartagena_db",
        "fhir_endpoint": "http://localhost:8080/fhir",
        "queue_in": "hospital.cartagena.inbound",
        "queue_out": "hospital.cartagena.outbound",
        "divipola": "13001",
        "departamento": "Bolivar",
    },
    3: {
        "id_sede": 3,
        "nombre_ciudad": "Corozal",
        "institucion": "Centro Medico Asistencial Corozal",
        "codigo_reps": "702150078901",
        "vendor_his": "EMR SaaS Regional",
        "vendor_emr": "SaludCloud EMR v3.4",
        "vendor_lis_pacs": "Ortho Clinical / Mindray PACS",
        "host": "localhost",
        "port_db": 5432,
        "db_name": "sede_corozal_db",
        "fhir_endpoint": "http://localhost:8080/fhir",
        "queue_in": "hospital.corozal.inbound",
        "queue_out": "hospital.corozal.outbound",
        "divipola": "70215",
        "departamento": "Sucre",
    },
}

NODO_CENTRAL = {
    "nombre": "CDR Federado & MPI Inter-Hospitalario",
    "servidor_hapi_fhir": "http://localhost:8080/fhir",
    "mpi_service_url": "http://localhost:8081/api/mpi",
    "vista_unificada_url": "http://localhost:5000",
    "rabbitmq_broker": "amqp://guest:guest@localhost:5672/",
    "umbral_mpi": 0.90,
}

@dataclass
class SedeInfo:
    id_sede: int
    nombre_ciudad: str
    vendor_his: str
    vendor_emr: str
    vendor_lis_pacs: str
    codigo_reps: Optional[str] = None
    institucion: Optional[str] = None

@dataclass
class PacienteRegistro:
    id_paciente: str
    documento_identidad: str
    tipo_documento: str
    nombre_completo: str
    fecha_nacimiento: str
    sexo: str
    id_sede: int
    fhir_patient_id: Optional[str] = None
    pais_nacionalidad: str = "CO"
    municipio_residencia: str = "70001"
    nombre_municipio: str = "Sincelejo"
    zona_residencia: str = "U"
    pertenencia_etnica: str = "6"
    eapb_codigo: str = "EPS001"
    eapb_nombre: str = "Nueva EPS"

@dataclass
class ObservacionClinica:
    id_observacion: str
    codigo_loinc: str
    descripcion: str
    valor: float
    unidad: str
    fecha_medicion: str
    rango_referencia: str = ""
    estado: str = "final"

@dataclass
class CondicionClinica:
    id_condicion: str
    codigo_cie10: str
    descripcion: str
    fecha_diagnostico: str
    tipo_diagnostico: str = "principal"
    estado_clinico: str = "active"

@dataclass
class EncuentroClinico:
    id_encuentro: str
    paciente: PacienteRegistro
    id_sede: int
    fecha_atencion: str
    tipo_encuentro: str
    condiciones: List[CondicionClinica] = field(default_factory=list)
    observaciones: List[ObservacionClinica] = field(default_factory=list)
    estado_migracion: str = "PENDIENTE"
    fecha_fin: Optional[str] = None
    via_ingreso: str = "Urgencias"
    causa_atencion: str = "Enfermedad general"
    destino_egreso: str = "Alta a domicilio"
    profesional_tipo_doc: str = "CC"
    profesional_num_doc: str = "73123456"
    profesional_nombre: str = "Dr. Roberto Mendoza - Especialista Medicina Interna"

TICKET = {
    "mensaje": "Paciente masculino de 58 anos remitido de Sede Corozal a Urgencias Sincelejo con dolor toracico opresivo de 2 horas de evolucion, diaforesis y disnea en reposo. Antecedente de diabetes mellitus tipo 2 e hipertension. Troponina T ultrasensible elevada (120 ng/L), ECG con elevacion de segmento ST. Requiere activacion urgente de codigo infarto y cateterismo cardiaco en hemodinamia Sede Central.",
    "id_sede_origen": 3,
    "id_sede_destino": 1,
    "tipo_evento": "REMISION_URGENTE",
}

PREGUNTAS_TICKET = {
    "categoria": {
        "type": "choice",
        "instructions": "A que especialidad y area de admision hospitalaria corresponde el evento clinico remitido?",
        "criteria": {
            "urgencias_hemodinamia": "Emergencia cardiovascular critica, codigo infarto o cateterismo",
            "hospitalizacion": "Ingreso clinico no critico a piso de hospitalizacion general",
            "consulta_externa": "Atencion ambulatoria programada o medicina especializada",
            "soporte_laboratorio": "Validacion de muestras biologicas, cultivo o prueba diagnostica",
        },
    },
    "prioridad_triage": {
        "type": "choice",
        "instructions": "Que nivel de Triage Manchester / Resolucion 5596 le corresponde al paciente?",
        "criteria": {
            "triage_1_critico": "Triage I: Resucitacion / Atencion inmediata critica (riesgo vital)",
            "triage_2_emergencia": "Triage II: Emergencia con espera menor a 30 minutos",
            "triage_3_urgencia": "Triage III: Urgencia medica con espera menor a 120 minutos",
            "triage_4_menor": "Triage IV/V: Urgencia menor o atencion diferible",
        },
    },
    "riesgo_vital": {"type": "noul", "instructions": "El paciente presenta riesgo vital inminente que requiere traslado inmediato a UCI o Hemodinamia?"},
    "urgencia": {
        "type": "score",
        "instructions": "Cual es la severidad del evento clinico segun escala de criticidad?",
        "criteria": ["baja", "media", "alta", "critica"],
    },
}

RESENA = {
    "resena": (
        "Atencion medica hospitalaria en Sede 1 Sincelejo: Paciente femenina de 42 anos ingresa por urgencias con cuadro de dolor abdominal agudo en fosa iliaca derecha y fiebre de 38.5 C. "
        "Se diagnostica Apendicitis Aguda (CIE-10: K35.8). Se realiza apendicectomia laparoscopica sin complicaciones bajo anestesia general. "
        "Pruebas de laboratorio LIS: Leucocitos 14,500 /uL (LOINC: 6690-2), Neutrofilos 82% (LOINC: 770-8), Hemoglobina 13.2 g/dL (LOINC: 718-7), Proteina C Reactiva 48 mg/L (LOINC: 1988-5). "
        "Presion arterial 120/80 mmHg (LOINC: 85354-9), Frecuencia cardiaca 88 lpm (LOINC: 8867-4), Temperatura 37.1 C al egreso. "
        "Evolucion clinica satisfactoria; tolerancia adecuada a via oral. Se otorga egreso hospitalario a domicilio con prescripcion de analgesicos, cita de control postquirurgico en 7 dias "
        "y signos de alarma explicados a la paciente y su familia. Documento Composition y Bundle document FHIR validados al 100%."
    )
}

_TEMAS_RESENA = [
    "Presenta diagnostico CIE-10 documentado?", "Contiene signos vitales registrados?", "Registra dolor abdominal agudo?", "Se realizo intervencion quirurgica?",
    "Menciona resultados de laboratorio clinico?", "Reporta conteo de leucocitos?", "Tiene medicion de Proteina C Reactiva?",
    "Especifica codigos LOINC estandar?", "Identifica el profesional tratante?", "Registra temperatura corporal?", "Presenta fiebre al ingreso?",
    "Especifica la via de ingreso por urgencias?", "Documenta evolucion postoperatoria?", "Menciona tolerancia a la via oral?", "Registra presion arterial?",
    "Registra frecuencia cardiaca?", "Se otorgo alta a domicilio?", "Incluye recomendaciones y signos de alarma?", "Menciona control medico postquirurgico?",
    "Cuenta con identificador de sede hospitalaria?", "Registra codigo REPS del prestador?", "Genero recurso Composition FHIR?", "Genero Bundle document FHIR?",
    "La evolucion clinica fue favorable?", "Requirio estancia en UCI?", "Se reporto alguna complicacion mayor?",
    "Especifica aseguradora o EAPB?", "Registra procedencia y municipio?", "Valida identificador de paciente?",
    "Presenta fecha y periodo de atencion?", "Cumple con resolucion 866 de interoperabilidad?", "Cumple directrices de historia clinica electronica?",
    "Presenta prescripcion farmacologica al alta?", "El paciente comprendio las instrucciones de egreso?", "Contiene firma o identificador digital?",
    "Se encuentra migrado en HAPI FHIR?", "Registra tipo de atencion hospitalaria?", "Reporta hemoglobina en rango aceptable?",
    "Existe congruencia entre CIE-10 y procedimiento?", "Es apto para consulta federada entre sedes?",
]

def preguntas_resena(cantidad: int) -> dict:
    temas = _TEMAS_RESENA[:cantidad]
    return {f"p{i:02d}": {"type": "noul", "instructions": tema} for i, tema in enumerate(temas, 1)}

PETICION = {
    "peticion": "Solicitud urgente de interoperabilidad: Enviar resultado critico de troponina T (120 ng/L) y electrocardiograma de 12 derivaciones para paciente CC 1007654321 remitido de Sede Corozal a hemodinamia y cardiologia intervencionista de Sede Sincelejo.",
}

_DEPARTAMENTOS = {
    "cardiologia_hemodinamia": "Cateterismo, angioplastia, infarto agudo y urgencias cardiovasculares",
    "urgencias_triaje": "Recepcion, clasificacion inicial y estabilizacion hemodinamica",
    "uci_adultos": "Cuidado intensivo con monitoreo invasivo y soporte ventilatorio",
    "laboratorio_hematologia": "Hemogramas, tiempos de coagulacion y frotis sanguineo",
    "laboratorio_bioquimica": "Enzimas cardiacas, funcion renal, electrolitos y gases arteriales",
    "laboratorio_microbiologia": "Cultivos bacterianos, antibiogramas y hemocultivos",
    "imagenes_rayos_x": "Radiografia convencional de torax, abdomen y extremidades",
    "imagenes_tomografia": "TAC helicoidal de craneo, torax, abdomen y angiotomografia",
    "imagenes_resonancia": "Resonancia magnetica de alto campo y espectroscopia",
    "banco_sangre": "Hemocomponentes, plasma, plaquetas y pruebas cruzadas",
    "quirofano_central": "Procedimientos quirurgicos programados y cirugia de urgencia",
    "cirugia_pediatrica": "Intervenciones quirurgicas infantiles especializadas",
    "hospitalizacion_medicina_interna": "Camas de manejo integral para pacientes adultos",
    "hospitalizacion_cirugia": "Cuidado postoperatorio de piso quirurgico",
    "pediatria_urgencias": "Atencion medica de urgencia para pacientes pediatricos",
    "ginecobstetricia": "Partos, cesareas y urgencias ginecologicas",
    "farmacia_dispensacion": "Entrega y trazabilidad de medicamentos intrahospitalarios",
    "oncologia_quimioterapia": "Protocolos antineoplasicos y atencion hematologica",
    "nefrologia_dialisis": "Terapia de reemplazo renal y hemodialisis aguda",
    "neumologia_espirometria": "Funcion pulmonar y terapia respiratoria hospitalaria",
    "gastroenterologia_endoscopia": "Endoscopia digestiva alta, colonoscopia y control de sangrado",
    "neurologia_electroencefalografia": "Monitoreo cerebral, ACV agudo y videotelemetria",
    "traumatologia_ortopedia": "Reduccion de fracturas, yesos y cirugia ortopedica",
    "infectologia_aislamiento": "Control de infecciones intrahospitalarias y aislamiento",
    "trabajo_social_remisiones": "Gestion social de remisiones inter-institucionales",
    "facturacion_radicacion": "Liquidacion SOAT, convenios EPS y paquetes tarifarios",
    "autorizaciones_eps": "Verificacion de derechos y radicacion de anexos tecnicos",
    "auditoria_concurrente": "Revision de pertinencia medica e historia clinica en linea",
    "referencia_contrarreferencia": "Coordinacion de ambulancias y traslado entre las 3 sedes",
    "archivo_clinico_central": "Custodia y expedicion legal de historiales clinicos",
}

PREGUNTAS_ENRUTAR = {
    "departamento": {
        "type": "choice",
        "instructions": "A que servicio medico/clinico de destino debe enrutar el pipeline NiFi/Mirth el mensaje?",
        "criteria": _DEPARTAMENTOS,
    }
}

COMENTARIOS = [
    "[OK] FC 72 lpm, PA 118/76 mmHg, SpO2 98%, Temp 36.6 C - Paciente estable en observacion.",
    "[ANOMALIA] FC 240 lpm con SpO2 0% y PA 300/200 mmHg - Ruido por electrodo desconectado o artefacto de movimiento.",
    "[OK] Glucemia basal 94 mg/dL tomada en ayunas por LIS Sede Cartagena. Normal.",
    "[ANOMALIA] Temp 15.2 C en paciente consciente hablando con medico - Sonda termica descalibrada o en ambiente frio.",
    "[OK] Leucocitos 7,200 /uL, Hb 14.1 g/dL, Plaquetas 245,000 /uL. Hemograma validado.",
    "[ANOMALIA] Troponina 999999 ng/L con formato corrupto sin identificador de lote ni paciente.",
    "[OK] Electrocardiograma ritmo sinusal normal sin alteraciones de repolarizacion.",
    "[ANOMALIA] Registro duplicado exacto reenviado 50 veces en 1 segundo por timeout de socket.",
    "[OK] Creatinina 0.9 mg/dL y BUN 14 mg/dL - Funcion renal conservada Sede Corozal.",
    "[ANOMALIA] Mensaje HL7 v2 corrupto con caracteres binarios y segmento PID sin numero de cedula.",
    "[OK] Ecografia obstetrica confirma feto unico con latido cardiaco regular.",
    "[ANOMALIA] Payload JSON malformado con corchete sin cerrar recibido en endpoint FHIR /Observation.",
    "[OK] Paciente CC 1007654321 presenta evolucion postoperatoria normal sin signos de sangrado.",
    "[ANOMALIA] Lectura de presion negativa -45 mmHg generada por falla electrica en tensiometro digital.",
    "[OK] Resumen Digital de Atencion consolidado y firmado electronicamente por medico especialista.",
]

ESTADO_COMENTARIOS = {f"comentario_{i:02d}": texto for i, texto in enumerate(COMENTARIOS, 1)}

PREGUNTAS_SPAM = {
    f"spam_{i:02d}": {
        "type": "noul",
        "instructions": f"El comentario_{i:02d} corresponde a una anomalia, artefacto tecnico, lectura corrupta o ruido?",
    }
    for i in range(1, len(COMENTARIOS) + 1)
}

CASOS_MPI_FEDERACION = [
    {
        "descripcion": "Paciente federado en las 3 sedes con error de digitacion en Sede 3 (Caso de la Guia)",
        "registros": [
            {
                "sede": 1,
                "documento_identidad": "1007654321",
                "tipo_documento": "CC",
                "nombre_completo": "CARLOS ANDRES MENDOZA PEREZ",
                "fecha_nacimiento": "1985-04-12",
                "sexo": "M",
            },
            {
                "sede": 2,
                "documento_identidad": "1007654321",
                "tipo_documento": "CC",
                "nombre_completo": "CARLOS A MENDOZA PEREZ",
                "fecha_nacimiento": "1985-04-12",
                "sexo": "M",
            },
            {
                "sede": 3,
                "documento_identidad": "1007654312",
                "tipo_documento": "CC",
                "nombre_completo": "CARLOS ANDRES MENDOZA P",
                "fecha_nacimiento": "1985-04-12",
                "sexo": "M",
            },
        ],
        "debe_federar": True,
    },
    {
        "descripcion": "Homonimos con diferente cedula y fecha (No deben federarse jamas)",
        "registros": [
            {
                "sede": 1,
                "documento_identidad": "64587123",
                "tipo_documento": "CC",
                "nombre_completo": "MARIA JOSE GUTIERREZ BLANCO",
                "fecha_nacimiento": "1990-08-25",
                "sexo": "F",
            },
            {
                "sede": 2,
                "documento_identidad": "4567890",
                "tipo_documento": "CC",
                "nombre_completo": "MARIA JOSE GUTIERREZ BLANCO",
                "fecha_nacimiento": "1975-11-14",
                "sexo": "F",
            },
        ],
        "debe_federar": False,
    },
]

CASOS = [
    ("Triage y Admision Clinica Inter-Sede (3 Decisiones)", TICKET, PREGUNTAS_TICKET),
    ("Auditoria RDA / Resolucion 866 (40 Criterios)", RESENA, preguntas_resena(40)),
    ("Enrutamiento Mediado Mirth/NiFi (30 Servicios)", PETICION, PREGUNTAS_ENRUTAR),
    ("Deteccion de Ruido y Anomalias en Telemetria (15 Muestras)", ESTADO_COMENTARIOS, PREGUNTAS_SPAM),
]
