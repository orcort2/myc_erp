from typing import Literal


AccreditationScope = Literal[
    "accredited_iso_17025",
    "traceable",
    "accredited_linked_lab",
]

ServiceScope = Literal[
    "accredited_iso_17025",
    "traceable",
    "accredited_linked_lab",
    "preventive",
    "corrective",
    "onsite",
    "online",
    "hybrid",
    "documentary",
    "protocol",
    "installation",
    "operation",
    "performance",
    "technical",
    "regulatory",
    "implementation",
]

ACCREDITATION_SCOPE_VALUES = (
    "accredited_iso_17025",
    "traceable",
    "accredited_linked_lab",
)

SERVICE_SCOPE_VALUES_BY_CATEGORY = {
    "Calibracion": frozenset(ACCREDITATION_SCOPE_VALUES),
    "Mantenimiento": frozenset({"preventive", "corrective"}),
    "Capacitacion": frozenset({"onsite", "online", "hybrid"}),
    "Validacion": frozenset({"documentary", "onsite", "protocol"}),
    "Calificacion": frozenset({"installation", "operation", "performance"}),
    "Consultoria": frozenset({"technical", "regulatory", "implementation"}),
}

SERVICE_SCOPE_LEGENDS = {
    "accredited_iso_17025": "Servicio acreditado ISO/IEC 17025:2017",
    "traceable": "Servicio trazable",
    "accredited_linked_lab": "Servicio acreditado ISO/IEC 17025:2017, laboratorio vinculado",
    "preventive": "Mantenimiento preventivo",
    "corrective": "Mantenimiento correctivo",
    "onsite": "Servicio presencial",
    "online": "Servicio en linea",
    "hybrid": "Servicio mixto",
    "documentary": "Validacion documental",
    "protocol": "Validacion de protocolo",
    "installation": "Calificacion de instalacion",
    "operation": "Calificacion de operacion",
    "performance": "Calificacion de desempeno",
    "technical": "Consultoria tecnica",
    "regulatory": "Consultoria normativa",
    "implementation": "Consultoria de implementacion",
}
