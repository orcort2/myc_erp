"""PENDIENTE 7 (encargo de corrección LAB): "LAB EXTERNO" -- la hoja de campo
que corresponde a un equipo con ``service_type == "linked"`` (subcontratado a
un laboratorio externo, en vez de calibrado internamente por MYC). A
diferencia de las plantillas institucionales fijas (ver
``app/services/field_sheet_templates.py``), su estructura -- grupos de
tablas, cada uno con su propia orientación Patrón->IBC / IBC->Patrón, y cada
tabla con sus propias filas/columnas -- la define el técnico al capturar,
para ESTA hoja en particular. Vive sobre el mismo ``FieldSheet``/
``FieldSheetResult`` y el mismo ciclo de revisiones/auditoría/PDF que
cualquier otra hoja LAB; no es un motor nuevo, sólo una plantilla cuya
estructura se autoriza en lugar de venir de un catálogo institucional.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

LabExternalOrientation = Literal["pattern_to_ibc", "ibc_to_pattern"]

# Límites técnicos (no arbitrarios): evitan que una hoja mal capturada genere
# un documento/objeto JSON desproporcionado -- no representan una regla de
# negocio ("no más de N grupos porque sí").
MAX_LAB_EXTERNAL_GROUPS = 20
MAX_LAB_EXTERNAL_TABLES_PER_GROUP = 20
MAX_LAB_EXTERNAL_COLUMNS_PER_TABLE = 30
MAX_LAB_EXTERNAL_ROWS_PER_TABLE = 200

_ID_PATTERN = r"^[a-z0-9_]+$"


class LabExternalColumnWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1, max_length=40, pattern=_ID_PATTERN)
    label: str = Field(min_length=1, max_length=120)


class LabExternalTableWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=40, pattern=_ID_PATTERN)
    title: str = Field(min_length=1, max_length=180)
    columns: list[LabExternalColumnWrite] = Field(
        min_length=1, max_length=MAX_LAB_EXTERNAL_COLUMNS_PER_TABLE
    )
    row_count: int = Field(ge=1, le=MAX_LAB_EXTERNAL_ROWS_PER_TABLE)

    @field_validator("columns")
    @classmethod
    def unique_column_keys(cls, value: list[LabExternalColumnWrite]) -> list[LabExternalColumnWrite]:
        keys = [item.key for item in value]
        if len(keys) != len(set(keys)):
            raise ValueError("Las columnas de una tabla deben tener keys únicas")
        return value


class LabExternalGroupWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=40, pattern=_ID_PATTERN)
    title: str = Field(min_length=1, max_length=180)
    # Sección "Orientación" del encargo: la orientación se comparte por TODO
    # el grupo -- no se repite tabla por tabla.
    orientation: LabExternalOrientation
    tables: list[LabExternalTableWrite] = Field(
        min_length=1, max_length=MAX_LAB_EXTERNAL_TABLES_PER_GROUP
    )

    @field_validator("tables")
    @classmethod
    def unique_table_ids(cls, value: list[LabExternalTableWrite]) -> list[LabExternalTableWrite]:
        ids = [item.id for item in value]
        if len(ids) != len(set(ids)):
            raise ValueError("Los ids de tabla deben ser únicos dentro del grupo")
        return value


class LabExternalStructureWrite(BaseModel):
    """Reemplaza la estructura completa (grupos/tablas/columnas) de una hoja
    LAB EXTERNO en un solo paso atómico -- igual que la edición de equipo
    (sección "una sola transacción"), nunca mutaciones parciales
    encadenadas. Los valores capturados (row_data) no viajan aquí -- se
    editan con el PATCH .../field-sheet ya existente, exactamente igual que
    cualquier otra plantilla."""

    model_config = ConfigDict(extra="forbid")

    groups: list[LabExternalGroupWrite] = Field(
        default_factory=list, max_length=MAX_LAB_EXTERNAL_GROUPS
    )

    @field_validator("groups")
    @classmethod
    def unique_group_and_table_ids(cls, value: list[LabExternalGroupWrite]) -> list[LabExternalGroupWrite]:
        group_ids = [item.id for item in value]
        if len(group_ids) != len(set(group_ids)):
            raise ValueError("Los ids de grupo deben ser únicos")
        table_ids = [table.id for group in value for table in group.tables]
        if len(table_ids) != len(set(table_ids)):
            raise ValueError("Los ids de tabla deben ser únicos en toda la hoja")
        return value
