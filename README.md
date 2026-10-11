# Red Distribuida de Interoperabilidad en Salud (HL7 FHIR R4)

Sistema distribuido de interoperabilidad clinica, mediacion de protocolos y federacion de datos de salud entre 3 sedes hospitalarias de la region Caribe colombiana, desarrollado conforme a estandares internacionales **HL7 FHIR R4**, la **Resolucion 866 de 2021** (Resumen Digital de Atencion - RDA) y patrones de integracion empresarial (EIP).

---

## 1. Arquitectura del Sistema

El sistema conecta tres instituciones prestadoras de servicios de salud (IPS) con sistemas de informacion heterogeneos (HIS, EMR, LIS, PACS) a traves de un **Health Service Bus** distribuido, resolucion federada de identidades (**MPI**) y un repositorio clinico centralizado (**HAPI FHIR R4 CDR**):

```
+---------------------------------------------------------------------------------------------------+
|                                 REPOSITORIO CLINICO CENTRAL (CDR)                                 |
|                            HAPI FHIR R4 Server (http://localhost:8080/fhir)                       |
|                         Master Patient Index (MPI Federado - Fellegi/Sunter)                      |
+---------------------------------------------------------------------------------------------------+
                                                  ^
                                                  |
+-------------------------------------------------+-------------------------------------------------+
|                        HEALTH SERVICE BUS (Bus de Integracion)                                    |
|      Topics: hospital.sincelejo.inbound | hospital.cartagena.inbound | hospital.corozal.inbound    |
|      Garantias: Idempotencia por message_id, desduplicacion y correlacion de transacciones        |
+---------------------------------------------------------------------------------------------------+
         ^                                        ^                                        ^
         |                                        |                                        |
+-----------------------+                +-----------------------+                +-----------------------+
|   SEDE 1: SINCELEJO   |                |   SEDE 2: CARTAGENA   |                |    SEDE 3: COROZAL    |
| Hosp. Univ. Sincelejo |                | Clinica del Caribe    |                | C.M.A. Corozal        |
| REPS: 700010012301    |                | REPS: 130010045601    |                | REPS: 702150078901    |
| HIS: Meditech v6.1    |                | HIS: Cerner Millenn.  |                | HIS: SaludCloud SaaS  |
| DB: sede_sincelejo_db |                | DB: sede_cartagena_db |                | DB: sede_corozal_db   |
+-----------------------+                +-----------------------+                +-----------------------+
```

### Componentes Principales
1. **Topologia de 3 Sedes Hospitalarias**:
   - **Sede 1 (Sincelejo)**: Hospital Universitario de Sincelejo (Meditech, Carestream PACS, Roche Cobas).
   - **Sede 2 (Cartagena)**: Clinica Especializada del Caribe (Cerner Millennium, Agfa HealthCare, Sysmex XN).
   - **Sede 3 (Corozal)**: Centro Medico Asistencial Corozal (SaludCloud EMR SaaS, Ortho Clinical, Mindray).
2. **Health Service Bus**:
   - Bus de mensajeria asincrona con colas dedicadas por sede hospitalaria.
   - Enrutamiento basado en contenido y garantia de idempotencia (evita procesar duplicados ante reintentos de red).
3. **Master Patient Index (MPI) Hibrido**:
   - Resolucion probabilistica y deterministica de identidades de pacientes basada en el modelo **Fellegi-Sunter**.
   - Pesos de concordancia: Documento de identidad (0.45, tolerando transposicion de hasta 2 digitos), Nombres normalizados por tokens (0.30), Fecha de nacimiento (0.15), Tipo de documento (0.05), Sexo (0.05).
   - Umbral de federacion: `score >= 0.90`.
4. **Pipelines de Mediacion (Mirth Connect / Apache NiFi)**:
   - Normalizacion, filtrado de calidad y enrutamiento inteligente entre 30 servicios hospitalarios de especialidad.

---

## 2. Descripcion Detallada de los Scripts

| Script | Proposito y Alcance |
|---|---|
| `casos.py` | **Banco de Datos y Topologia Multisede**: Define las 3 sedes clinicas, los esquemas de datos relacionales/FHIR, casos de admision y triage de urgencias, bateria de 40 criterios para auditoria de historias clinicas (RDA), catalogo de 30 especialidades medicas para mediacion NiFi/Mirth, muestras de telemetria clinica y casos de prueba de federacion MPI. |
| `jev_cliente.py` | **Nucleo de Interoperabilidad y Motor Clinico**: Implementa el `HealthServiceBus`, el algoritmo de resolucion de identidades MPI Fellegi-Sunter, los generadores de recursos FHIR R4 (`Patient`, `Encounter`, `Observation`, `Condition`, `Composition`, `Bundle document` y `Bundle transaction`), y el motor de inferencia System One para decisiones clinicas en tiempo real. |
| `01_ticket_soporte.py` | **Ejercicio 1: Triage Clinico y Remision Inter-Hospitalaria**: Modela la admision de pacientes remitidos entre sedes, categorizacion segun Triage Manchester / Resolucion 5596, evaluacion de riesgo vital y despacho automatico del evento hacia el bus distribuido. |
| `02_muchas_preguntas.py` | **Ejercicio 2: Auditoria Integral RDA (Resolucion 866/2021)**: Evalua concurrentemente 40 reglas de calidad e interoperabilidad sobre un expediente clinico en formato Composition/Bundle FHIR en menos de 1 milisegundo. |
| `03_enrutar_30_opciones.py` | **Ejercicio 3: Enrutador Inteligente Mirth Connect / Apache NiFi**: Emula la mediacion y enrutamiento automatico de mensajes clinicos complejos hacia el servicio hospitalario adecuado entre 30 especialidades medicas. |
| `04_filtro_spam.py` | **Ejercicio 4: Filtro de Calidad y Anomalias en Telemetria**: Analiza muestras de signos vitales, telemetria y mensajes HL7/FHIR, identificando lecturas descalibradas o payloads corruptos antes de su persistencia en el CDR. |
| `05_comparar_con_deepseek.py` | **Ejercicio 5: Benchmarking de Inferencia Clinica**: Compara la latencia, aceleracion y consenso de decisiones clinicas en tiempo real entre el motor System One y un LLM tradicional, generando graficas de rendimiento. |
| `naves.py` / `06_...` / `07_...` | **Simulador de Despacho y Transporte Asistencial**: Modelado reactivo en tiempo real de coordinacion de traslados y ambulancias inter-hospitalarias. |

---

## 3. Requisitos de Instalacion

El proyecto requiere **Python 3.10 o superior** y las siguientes bibliotecas:

```bash
pip install httpx python-dotenv matplotlib
```

*(Opcional para el simulador grafico: `pip install pygame`)*

El archivo `.env` ya viene configurado con las rutas de los servicios y los endpoints locales y remotos de FHIR.

---

## 4. Guia de Ejecucion

Todos los ejercicios son ejecutables de manera autonoma desde la terminal:

### Ejercicio 1: Triage Clinico y Remision Inter-Sede
```bash
python 01_ticket_soporte.py
```
*Salida esperada*: Evaluacion de riesgo vital, categoria hemodinamica, nivel de triage Manchester y confirmacion de envio al bus `hospital.sincelejo.inbound`.

### Ejercicio 2: Auditoria de RDA (40 Criterios)
```bash
python 02_muchas_preguntas.py
```
*Salida esperada*: Dictamen de los 40 criterios evaluados sobre el RDA (Composition FHIR) con porcentaje de conformidad.

### Ejercicio 3: Enrutamiento Mirth Connect / NiFi (30 Servicios)
```bash
python 03_enrutar_30_opciones.py
```
*Salida esperada*: Clasificacion y enrutamiento del mensaje clinico hacia la especialidad medica correspondiente entre 30 opciones.

### Ejercicio 4: Filtro de Calidad y Telemetria
```bash
python 04_filtro_spam.py
```
*Salida esperada*: Separacion de muestras validas para ingesta al CDR frente a lecturas con ruido, artefactos o payloads malformados.

### Ejercicio 5: Benchmarking de Decisiones Clinicas
```bash
python 05_comparar_con_deepseek.py --sin-grafico
```
*(Omita `--sin-grafico` si desea visualizar la ventana interactiva de Matplotlib)*.
*Salida esperada*: Tabla comparativa de tiempos de respuesta, factores de aceleracion y guardado de la grafica en `comparacion_jev_vs_deepseek.png`.

---

## 5. Estandares y Cumplimiento Normativo

- **HL7 FHIR Release 4**: Recursos `Patient`, `Encounter`, `Observation`, `Condition`, `Composition`, `Organization`, `Bundle`.
- **Resolucion 866 de 2021 (Minsalud Colombia)**: Resumen Digital de Atencion (RDA) y campos estructurados de identificacion.
- **Sistemas de Codificacion**: CIE-10 (diagnosticos), LOINC (laboratorios y signos vitales), REPS (prestadores de salud), DIVIPOLA (municipios) y UCUM (unidades de medida).
