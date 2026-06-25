from __future__ import annotations


METROLOGY_PROFILES: dict[str, dict] = {
    "pressure": {
        "profile_key": "pressure",
        "display_name": "Presion",
        "magnitude": "pressure",
        "required_inputs": ["reference_value", "indications", "resolution", "pattern_uncertainty", "k"],
        "supported_units": ["psi", "bar", "kPa", "MPa"],
        "uncertainty_components": ["repeatability", "resolution", "pattern"],
        "result_columns": ["average", "error", "expanded_uncertainty"],
        "notes": "Perfil base para vista previa interna del motor metrologico.",
    },
    "temperature": {
        "profile_key": "temperature",
        "display_name": "Temperatura",
        "magnitude": "temperature",
        "required_inputs": ["reference_value", "indications", "resolution", "pattern_uncertainty", "k"],
        "supported_units": ["C", "F", "K"],
        "uncertainty_components": ["repeatability", "resolution", "pattern"],
        "result_columns": ["average", "error", "expanded_uncertainty"],
        "notes": "Perfil inicial para termometria y plantillas futuras.",
    },
    "humidity": {
        "profile_key": "humidity",
        "display_name": "Humedad",
        "magnitude": "humidity",
        "required_inputs": ["reference_value", "indications"],
        "supported_units": ["%RH"],
        "uncertainty_components": ["repeatability", "pattern"],
        "result_columns": ["average", "error"],
        "notes": "Reservado para ampliacion posterior.",
    },
    "mass": {
        "profile_key": "mass",
        "display_name": "Masa",
        "magnitude": "mass",
        "required_inputs": ["reference_value", "indications"],
        "supported_units": ["g", "kg", "mg"],
        "uncertainty_components": ["repeatability", "pattern"],
        "result_columns": ["average", "error"],
        "notes": "Reservado para ampliacion posterior.",
    },
    "dimensional": {
        "profile_key": "dimensional",
        "display_name": "Dimensional",
        "magnitude": "dimensional",
        "required_inputs": ["reference_value", "indications"],
        "supported_units": ["mm", "cm", "m", "in"],
        "uncertainty_components": ["repeatability", "resolution", "pattern"],
        "result_columns": ["average", "error"],
        "notes": "Reservado para ampliacion posterior.",
    },
    "torque": {
        "profile_key": "torque",
        "display_name": "Torque",
        "magnitude": "torque",
        "required_inputs": ["reference_value", "indications"],
        "supported_units": ["N·m", "lbf·ft"],
        "uncertainty_components": ["repeatability", "pattern"],
        "result_columns": ["average", "error"],
        "notes": "Reservado para ampliacion posterior.",
    },
    "electrical": {
        "profile_key": "electrical",
        "display_name": "Electrica",
        "magnitude": "electrical",
        "required_inputs": ["reference_value", "indications"],
        "supported_units": ["V", "A", "Ohm", "Hz"],
        "uncertainty_components": ["repeatability", "resolution", "pattern"],
        "result_columns": ["average", "error"],
        "notes": "Reservado para ampliacion posterior.",
    },
    "time": {
        "profile_key": "time",
        "display_name": "Tiempo",
        "magnitude": "time",
        "required_inputs": ["reference_value", "indications"],
        "supported_units": ["s", "min", "h"],
        "uncertainty_components": ["repeatability", "pattern"],
        "result_columns": ["average", "error"],
        "notes": "Reservado para ampliacion posterior.",
    },
    "velocity": {
        "profile_key": "velocity",
        "display_name": "Velocidad",
        "magnitude": "velocity",
        "required_inputs": ["reference_value", "indications"],
        "supported_units": ["m/s", "km/h", "rpm"],
        "uncertainty_components": ["repeatability", "pattern"],
        "result_columns": ["average", "error"],
        "notes": "Reservado para ampliacion posterior.",
    },
    "sound": {
        "profile_key": "sound",
        "display_name": "Sonido",
        "magnitude": "sound",
        "required_inputs": ["reference_value", "indications"],
        "supported_units": ["dB"],
        "uncertainty_components": ["repeatability", "pattern"],
        "result_columns": ["average", "error"],
        "notes": "Reservado para ampliacion posterior.",
    },
    "gas": {
        "profile_key": "gas",
        "display_name": "Gas",
        "magnitude": "gas",
        "required_inputs": ["reference_value", "indications"],
        "supported_units": ["ppm", "%LEL", "%vol"],
        "uncertainty_components": ["repeatability", "pattern"],
        "result_columns": ["average", "error"],
        "notes": "Reservado para ampliacion posterior.",
    },
    "angle": {
        "profile_key": "angle",
        "display_name": "Angulo",
        "magnitude": "angle",
        "required_inputs": ["reference_value", "indications"],
        "supported_units": ["deg", "rad"],
        "uncertainty_components": ["repeatability", "pattern"],
        "result_columns": ["average", "error"],
        "notes": "Reservado para ampliacion posterior.",
    },
}


def list_metrology_profiles() -> list[dict]:
    return list(METROLOGY_PROFILES.values())


def get_metrology_profile(profile_key: str) -> dict:
    profile = METROLOGY_PROFILES.get(profile_key)
    if profile is None:
        raise KeyError(profile_key)
    return profile
