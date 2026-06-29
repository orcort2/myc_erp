from __future__ import annotations

import ast
import math
from datetime import datetime, timezone
from statistics import mean

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.calibration_procedure import CalibrationProcedure
from app.models.equipment import Equipment
from app.models.field_sheet import FieldSheet, FieldSheetResult
from app.models.reference_standard import FieldSheetReferenceStandard
from app.models.reference_standard_certificate import ReferenceStandardCertificate
from app.models.uncertainty import (
    UncertaintyCalculation,
    UncertaintyComponent,
    UncertaintyFormula,
    UncertaintyModel,
    UncertaintyModelException,
    UncertaintyModelVersion,
)
from app.schemas.uncertainty import (
    UncertaintyComponentCreate,
    UncertaintyComponentUpdate,
    UncertaintyFormulaCreate,
    UncertaintyFormulaUpdate,
    UncertaintyModelCreate,
    UncertaintyModelExceptionCreate,
    UncertaintyModelUpdate,
    UncertaintyModelVersionCreate,
    UncertaintyModelVersionUpdate,
    UncertaintyPreview,
)
from app.services.audit_logs import write_audit_log
from app.services.metrology_engine import (
    absolute_error,
    combined_uncertainty,
    expanded_uncertainty,
    repeatability_uncertainty,
    resolution_uncertainty,
)
from app.services.reference_standard_certificates import get_applicable_uncertainty


APPROVED_VERSION_STATUS = "approved"
EDITABLE_VERSION_STATUSES = {"draft"}
TERMINAL_VERSION_STATUSES = {"obsolete", "archived"}
ALLOWED_FUNCTIONS = {
    "abs": abs,
    "average": lambda *values: mean(values),
    "combined": lambda *values: combined_uncertainty(list(values)),
    "expanded": expanded_uncertainty,
    "max": max,
    "min": min,
    "pow": pow,
    "round": round,
    "sqrt": math.sqrt,
}
ALLOWED_AST_NODES = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Call,
    ast.Name,
    ast.Load,
    ast.Constant,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Pow,
    ast.Mod,
    ast.USub,
    ast.UAdd,
)


def _as_float(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_expression(expression: str, variables: dict[str, float]) -> float:
    parsed = ast.parse(expression, mode="eval")
    for node in ast.walk(parsed):
        if not isinstance(node, ALLOWED_AST_NODES):
            raise ValueError(f"Expresion no permitida: {node.__class__.__name__}")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in ALLOWED_FUNCTIONS:
                raise ValueError("Funcion no permitida en formula")
        if isinstance(node, ast.Name):
            if node.id not in variables and node.id not in ALLOWED_FUNCTIONS:
                raise ValueError(f"Variable no disponible: {node.id}")
    return float(
        eval(
            compile(parsed, "<uncertainty_expression>", "eval"),
            {"__builtins__": {}},
            {**ALLOWED_FUNCTIONS, **variables},
        )
    )


def _json_safe(value):
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def _model_options():
    return (
        selectinload(UncertaintyModel.versions)
        .selectinload(UncertaintyModelVersion.components),
        selectinload(UncertaintyModel.versions)
        .selectinload(UncertaintyModelVersion.formulas),
        selectinload(UncertaintyModel.components),
        selectinload(UncertaintyModel.formulas),
    )


def _version_options():
    return (
        selectinload(UncertaintyModelVersion.model),
        selectinload(UncertaintyModelVersion.components),
        selectinload(UncertaintyModelVersion.formulas),
    )


def _serialize_model(item: UncertaintyModel) -> dict:
    return {
        "code": item.code,
        "name": item.name,
        "magnitude": item.magnitude,
        "equipment_family": item.equipment_family,
        "status": item.status,
    }


def _serialize_version(item: UncertaintyModelVersion) -> dict:
    return {
        "id": item.id,
        "model_id": item.model_id,
        "version_number": item.version_number,
        "status": item.status,
        "default_coverage_factor": item.default_coverage_factor,
        "components": len([row for row in item.components if row.is_active]),
        "formulas": len([row for row in item.formulas if row.is_active_formula]),
    }


def _assert_unique_model(db: Session, code: str, model_id: int | None = None) -> None:
    existing = db.scalar(
        select(UncertaintyModel.id).where(
            UncertaintyModel.code == code,
            UncertaintyModel.is_active.is_(True),
            UncertaintyModel.id != (model_id or 0),
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Ya existe un modelo activo con ese codigo.")


def _assert_unique_version(
    db: Session,
    model_id: int,
    version_number: str,
    version_id: int | None = None,
) -> None:
    existing = db.scalar(
        select(UncertaintyModelVersion.id).where(
            UncertaintyModelVersion.model_id == model_id,
            UncertaintyModelVersion.version_number == version_number,
            UncertaintyModelVersion.is_active.is_(True),
            UncertaintyModelVersion.id != (version_id or 0),
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail="Ya existe una version activa con ese numero para el modelo.",
        )


def list_uncertainty_models(
    db: Session,
    *,
    include_inactive: bool = False,
    magnitude: str | None = None,
    status_value: str | None = None,
) -> list[UncertaintyModel]:
    query = select(UncertaintyModel).options(*_model_options()).order_by(
        UncertaintyModel.updated_at.desc(), UncertaintyModel.id.desc()
    )
    if not include_inactive:
        query = query.where(UncertaintyModel.is_active.is_(True))
    if magnitude:
        query = query.where(UncertaintyModel.magnitude == magnitude)
    if status_value:
        query = query.where(UncertaintyModel.status == status_value)
    return list(db.scalars(query).all())


def get_uncertainty_model(db: Session, model_id: int) -> UncertaintyModel:
    model = db.scalar(
        select(UncertaintyModel)
        .where(UncertaintyModel.id == model_id)
        .options(*_model_options())
    )
    if model is None or not model.is_active:
        raise HTTPException(status_code=404, detail="Modelo de incertidumbre no encontrado")
    return model


def get_uncertainty_model_version(db: Session, version_id: int) -> UncertaintyModelVersion:
    version = db.scalar(
        select(UncertaintyModelVersion)
        .where(UncertaintyModelVersion.id == version_id)
        .options(*_version_options())
    )
    if version is None or not version.is_active:
        raise HTTPException(status_code=404, detail="Version de modelo no encontrada")
    return version


def _ensure_editable_version(version: UncertaintyModelVersion) -> None:
    if version.status not in EDITABLE_VERSION_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo una version en borrador puede modificarse directamente.",
        )


def create_uncertainty_model(
    db: Session,
    payload: UncertaintyModelCreate,
    *,
    user_id: int | None = None,
) -> UncertaintyModel:
    _assert_unique_model(db, payload.code)
    model = UncertaintyModel(
        **payload.model_dump(exclude={"components", "formulas", "version", "default_coverage_factor"})
    )
    db.add(model)
    db.flush()
    version = UncertaintyModelVersion(
        model_id=model.id,
        version_number=payload.version,
        default_coverage_factor=payload.default_coverage_factor,
        status="draft",
    )
    version.components = [
        UncertaintyComponent(model_id=model.id, **item.model_dump())
        for item in payload.components
    ]
    version.formulas = [
        UncertaintyFormula(model_id=model.id, **item.model_dump())
        for item in payload.formulas
    ]
    db.add(version)
    db.flush()
    write_audit_log(
        db,
        action="uncertainty_model.created",
        entity="uncertainty_models",
        entity_id=model.id,
        user_id=user_id,
        new_values={**_serialize_model(model), "initial_version_id": version.id},
    )
    db.commit()
    return get_uncertainty_model(db, model.id)


def update_uncertainty_model(
    db: Session,
    model_id: int,
    payload: UncertaintyModelUpdate,
    *,
    user_id: int | None = None,
) -> UncertaintyModel:
    model = get_uncertainty_model(db, model_id)
    previous = _serialize_model(model)
    updates = payload.model_dump(exclude_unset=True, exclude={"version", "default_coverage_factor"})
    code = updates.get("code", model.code)
    _assert_unique_model(db, code, model_id)
    for key, value in updates.items():
        setattr(model, key, value)
    write_audit_log(
        db,
        action="uncertainty_model.updated",
        entity="uncertainty_models",
        entity_id=model.id,
        user_id=user_id,
        previous_values=previous,
        new_values=_serialize_model(model),
    )
    db.commit()
    return get_uncertainty_model(db, model.id)


def list_uncertainty_model_versions(db: Session, model_id: int) -> list[UncertaintyModelVersion]:
    get_uncertainty_model(db, model_id)
    return list(
        db.scalars(
            select(UncertaintyModelVersion)
            .where(
                UncertaintyModelVersion.model_id == model_id,
                UncertaintyModelVersion.is_active.is_(True),
            )
            .options(*_version_options())
            .order_by(UncertaintyModelVersion.created_at.desc(), UncertaintyModelVersion.id.desc())
        ).all()
    )


def create_uncertainty_model_version(
    db: Session,
    model_id: int,
    payload: UncertaintyModelVersionCreate,
    *,
    user_id: int | None = None,
) -> UncertaintyModelVersion:
    model = get_uncertainty_model(db, model_id)
    _assert_unique_version(db, model.id, payload.version_number)
    version = UncertaintyModelVersion(
        **payload.model_dump(exclude={"components", "formulas"}),
        model_id=model.id,
        status="draft",
    )
    version.components = [
        UncertaintyComponent(model_id=model.id, **item.model_dump())
        for item in payload.components
    ]
    version.formulas = [
        UncertaintyFormula(model_id=model.id, **item.model_dump())
        for item in payload.formulas
    ]
    db.add(version)
    db.flush()
    write_audit_log(
        db,
        action="uncertainty_model_version.created",
        entity="uncertainty_model_versions",
        entity_id=version.id,
        user_id=user_id,
        new_values=_serialize_version(version),
    )
    db.commit()
    return get_uncertainty_model_version(db, version.id)


def update_uncertainty_model_version(
    db: Session,
    version_id: int,
    payload: UncertaintyModelVersionUpdate,
    *,
    user_id: int | None = None,
) -> UncertaintyModelVersion:
    version = get_uncertainty_model_version(db, version_id)
    _ensure_editable_version(version)
    previous = _serialize_version(version)
    updates = payload.model_dump(exclude_unset=True)
    if "version_number" in updates:
        _assert_unique_version(db, version.model_id, updates["version_number"], version.id)
    for key, value in updates.items():
        setattr(version, key, value)
    write_audit_log(
        db,
        action="uncertainty_model_version.updated",
        entity="uncertainty_model_versions",
        entity_id=version.id,
        user_id=user_id,
        previous_values=previous,
        new_values=_serialize_version(version),
    )
    db.commit()
    return get_uncertainty_model_version(db, version.id)


def change_uncertainty_model_version_status(
    db: Session,
    version_id: int,
    action: str,
    *,
    user_id: int | None = None,
) -> UncertaintyModelVersion:
    version = get_uncertainty_model_version(db, version_id)
    previous = _serialize_version(version)
    now = datetime.now(timezone.utc)
    if action == "submit-review":
        if version.status != "draft":
            raise HTTPException(status_code=409, detail="Solo una version draft puede enviarse a revision.")
        version.status = "in_review"
        version.submitted_at = now
        version.submitted_by_id = user_id
    elif action == "approve":
        if version.status not in {"draft", "in_review"}:
            raise HTTPException(status_code=409, detail="Solo versiones draft o in_review pueden aprobarse.")
        if not [item for item in version.components if item.is_active]:
            raise HTTPException(status_code=422, detail="La version no tiene componentes activos.")
        version.status = "approved"
        version.approved_at = now
        version.approved_by_id = user_id
    elif action == "obsolete":
        if version.status != "approved":
            raise HTTPException(status_code=409, detail="Solo una version approved puede obsoletarse.")
        version.status = "obsolete"
        version.obsolete_at = now
    elif action == "archive":
        if version.status not in {"obsolete", "draft", "in_review"}:
            raise HTTPException(status_code=409, detail="Solo versiones draft, in_review u obsolete pueden archivarse.")
        version.status = "archived"
        version.archived_at = now
        version.is_active = False
    else:
        raise HTTPException(status_code=422, detail="Accion de version no soportada.")
    write_audit_log(
        db,
        action=f"uncertainty_model_version.{action.replace('-', '_')}",
        entity="uncertainty_model_versions",
        entity_id=version.id,
        user_id=user_id,
        previous_values=previous,
        new_values=_serialize_version(version),
    )
    db.commit()
    return get_uncertainty_model_version(db, version.id)


def clone_uncertainty_model_version(
    db: Session,
    version_id: int,
    payload: UncertaintyModelVersionCreate | None = None,
    *,
    user_id: int | None = None,
) -> UncertaintyModelVersion:
    source = get_uncertainty_model_version(db, version_id)
    version_number = payload.version_number if payload else f"{source.version_number}.1"
    _assert_unique_version(db, source.model_id, version_number)
    clone = UncertaintyModelVersion(
        model_id=source.model_id,
        version_number=version_number,
        change_summary=(payload.change_summary if payload else None) or f"Clon de version {source.version_number}",
        default_coverage_factor=(payload.default_coverage_factor if payload else source.default_coverage_factor),
        status="draft",
    )
    clone.components = [
        UncertaintyComponent(
            model_id=source.model_id,
            key=item.key,
            name=item.name,
            description=item.description,
            source_type=item.source_type,
            distribution=item.distribution,
            divisor=item.divisor,
            sensitivity_coefficient=item.sensitivity_coefficient,
            value_expression=item.value_expression,
            required=item.required,
            sort_order=item.sort_order,
            metadata_json=item.metadata_json,
        )
        for item in source.components
        if item.is_active
    ]
    clone.formulas = [
        UncertaintyFormula(
            model_id=source.model_id,
            key=item.key,
            name=item.name,
            expression=item.expression,
            result_key=item.result_key,
            description=item.description,
            sort_order=item.sort_order,
            is_active_formula=item.is_active_formula,
        )
        for item in source.formulas
        if item.is_active_formula
    ]
    db.add(clone)
    db.flush()
    write_audit_log(
        db,
        action="uncertainty_model_version.cloned",
        entity="uncertainty_model_versions",
        entity_id=clone.id,
        user_id=user_id,
        previous_values={"source_version_id": source.id},
        new_values=_serialize_version(clone),
    )
    db.commit()
    return get_uncertainty_model_version(db, clone.id)


def add_uncertainty_component(
    db: Session,
    version_id: int,
    payload: UncertaintyComponentCreate,
    *,
    user_id: int | None = None,
) -> UncertaintyModelVersion:
    version = get_uncertainty_model_version(db, version_id)
    _ensure_editable_version(version)
    component = UncertaintyComponent(
        model_id=version.model_id,
        model_version_id=version.id,
        **payload.model_dump(),
    )
    db.add(component)
    db.flush()
    write_audit_log(
        db,
        action="uncertainty_model_version.component_added",
        entity="uncertainty_model_versions",
        entity_id=version.id,
        user_id=user_id,
        new_values=payload.model_dump(),
    )
    db.commit()
    return get_uncertainty_model_version(db, version.id)


def update_uncertainty_component(
    db: Session,
    component_id: int,
    payload: UncertaintyComponentUpdate,
    *,
    user_id: int | None = None,
) -> UncertaintyComponent:
    component = db.get(UncertaintyComponent, component_id)
    if component is None or not component.is_active:
        raise HTTPException(status_code=404, detail="Componente no encontrado")
    version = get_uncertainty_model_version(db, component.model_version_id)
    _ensure_editable_version(version)
    previous = {"key": component.key, "name": component.name, "source_type": component.source_type}
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(component, key, value)
    write_audit_log(
        db,
        action="uncertainty_component.updated",
        entity="uncertainty_components",
        entity_id=component.id,
        user_id=user_id,
        previous_values=previous,
        new_values=payload.model_dump(exclude_unset=True),
    )
    db.commit()
    db.refresh(component)
    return component


def delete_uncertainty_component(
    db: Session,
    component_id: int,
    *,
    user_id: int | None = None,
) -> None:
    component = db.get(UncertaintyComponent, component_id)
    if component is None or not component.is_active:
        raise HTTPException(status_code=404, detail="Componente no encontrado")
    version = get_uncertainty_model_version(db, component.model_version_id)
    _ensure_editable_version(version)
    component.is_active = False
    component.deleted_at = datetime.now(timezone.utc)
    component.deleted_by = user_id
    write_audit_log(
        db,
        action="uncertainty_component.deactivated",
        entity="uncertainty_components",
        entity_id=component.id,
        user_id=user_id,
        previous_values={"is_active": True},
        new_values={"is_active": False},
    )
    db.commit()


def add_uncertainty_formula(
    db: Session,
    version_id: int,
    payload: UncertaintyFormulaCreate,
    *,
    user_id: int | None = None,
) -> UncertaintyModelVersion:
    version = get_uncertainty_model_version(db, version_id)
    _ensure_editable_version(version)
    formula = UncertaintyFormula(
        model_id=version.model_id,
        model_version_id=version.id,
        **payload.model_dump(),
    )
    db.add(formula)
    db.flush()
    write_audit_log(
        db,
        action="uncertainty_model_version.formula_added",
        entity="uncertainty_model_versions",
        entity_id=version.id,
        user_id=user_id,
        new_values=payload.model_dump(),
    )
    db.commit()
    return get_uncertainty_model_version(db, version.id)


def update_uncertainty_formula(
    db: Session,
    formula_id: int,
    payload: UncertaintyFormulaUpdate,
    *,
    user_id: int | None = None,
) -> UncertaintyFormula:
    formula = db.get(UncertaintyFormula, formula_id)
    if formula is None:
        raise HTTPException(status_code=404, detail="Formula no encontrada")
    version = get_uncertainty_model_version(db, formula.model_version_id)
    _ensure_editable_version(version)
    previous = {"key": formula.key, "expression": formula.expression, "result_key": formula.result_key}
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(formula, key, value)
    write_audit_log(
        db,
        action="uncertainty_formula.updated",
        entity="uncertainty_formulas",
        entity_id=formula.id,
        user_id=user_id,
        previous_values=previous,
        new_values=payload.model_dump(exclude_unset=True),
    )
    db.commit()
    db.refresh(formula)
    return formula


def delete_uncertainty_formula(
    db: Session,
    formula_id: int,
    *,
    user_id: int | None = None,
) -> None:
    formula = db.get(UncertaintyFormula, formula_id)
    if formula is None:
        raise HTTPException(status_code=404, detail="Formula no encontrada")
    version = get_uncertainty_model_version(db, formula.model_version_id)
    _ensure_editable_version(version)
    formula.is_active_formula = False
    write_audit_log(
        db,
        action="uncertainty_formula.deactivated",
        entity="uncertainty_formulas",
        entity_id=formula.id,
        user_id=user_id,
        previous_values={"is_active_formula": True},
        new_values={"is_active_formula": False},
    )
    db.commit()


def _approved_version_for_model(db: Session, model_id: int) -> UncertaintyModelVersion | None:
    return db.scalar(
        select(UncertaintyModelVersion)
        .where(
            UncertaintyModelVersion.model_id == model_id,
            UncertaintyModelVersion.status == APPROVED_VERSION_STATUS,
            UncertaintyModelVersion.is_active.is_(True),
        )
        .options(*_version_options())
        .order_by(UncertaintyModelVersion.approved_at.desc(), UncertaintyModelVersion.id.desc())
    )


def create_uncertainty_exception(
    db: Session,
    payload: UncertaintyModelExceptionCreate,
    *,
    user_id: int | None = None,
) -> UncertaintyModelException:
    alternate_version = get_uncertainty_model_version(db, payload.alternate_model_version_id)
    if alternate_version.status != APPROVED_VERSION_STATUS:
        raise HTTPException(status_code=409, detail="La excepcion requiere una version alterna approved.")
    if alternate_version.model_id != payload.alternate_model_id:
        raise HTTPException(status_code=422, detail="La version alterna no pertenece al modelo indicado.")
    if payload.base_model_version_id is not None:
        base_version = get_uncertainty_model_version(db, payload.base_model_version_id)
        if payload.base_model_id is not None and base_version.model_id != payload.base_model_id:
            raise HTTPException(status_code=422, detail="La version base no pertenece al modelo base indicado.")
    exception = UncertaintyModelException(
        **payload.model_dump(),
        authorized_by_id=user_id,
        authorized_at=datetime.now(timezone.utc),
    )
    db.add(exception)
    db.flush()
    write_audit_log(
        db,
        action="uncertainty_model.exception_created",
        entity="uncertainty_model_exceptions",
        entity_id=exception.id,
        user_id=user_id,
        new_values=payload.model_dump(),
    )
    db.commit()
    db.refresh(exception)
    return exception


def list_uncertainty_exceptions(db: Session, *, include_inactive: bool = False) -> list[UncertaintyModelException]:
    query = select(UncertaintyModelException).order_by(
        UncertaintyModelException.updated_at.desc(), UncertaintyModelException.id.desc()
    )
    if not include_inactive:
        query = query.where(
            UncertaintyModelException.is_active.is_(True),
            UncertaintyModelException.status == "active",
        )
    return list(db.scalars(query).all())


def _get_field_sheet_for_calculation(db: Session, field_sheet_id: int) -> FieldSheet:
    field_sheet = db.scalar(
        select(FieldSheet)
        .where(FieldSheet.id == field_sheet_id)
        .options(
            selectinload(FieldSheet.equipment).selectinload(Equipment.service_order),
            selectinload(FieldSheet.calibration_procedure),
            selectinload(FieldSheet.results_rows),
            selectinload(FieldSheet.reference_standard_links)
            .selectinload(FieldSheetReferenceStandard.reference_standard),
            selectinload(FieldSheet.reference_standard_links)
            .selectinload(FieldSheetReferenceStandard.reference_standard_certificate)
            .selectinload(ReferenceStandardCertificate.uncertainties),
            selectinload(FieldSheet.reference_standard_links).selectinload(
                FieldSheetReferenceStandard.selected_uncertainty
            ),
        )
    )
    if field_sheet is None or not field_sheet.is_active:
        raise HTTPException(status_code=404, detail="Hoja de campo no encontrada")
    return field_sheet


def _resolve_model_version(
    db: Session,
    field_sheet: FieldSheet,
) -> tuple[UncertaintyModel | None, UncertaintyModelVersion | None, dict | None, list[str]]:
    warnings: list[str] = []
    procedure: CalibrationProcedure | None = field_sheet.calibration_procedure
    equipment = field_sheet.equipment
    base_model_id = procedure.uncertainty_model_id if procedure else None
    base_version_id = procedure.uncertainty_model_version_id if procedure else None
    base_version = get_uncertainty_model_version(db, base_version_id) if base_version_id else None
    base_model = get_uncertainty_model(db, base_version.model_id if base_version else base_model_id) if (base_version or base_model_id) else None
    if base_version is None and base_model is not None:
        base_version = _approved_version_for_model(db, base_model.id)
        if base_version is None:
            warnings.append("El modelo de incertidumbre no tiene version aprobada.")

    exception = db.scalar(
        select(UncertaintyModelException)
        .where(
            UncertaintyModelException.is_active.is_(True),
            UncertaintyModelException.status == "active",
            or_(UncertaintyModelException.base_model_id.is_(None), UncertaintyModelException.base_model_id == (base_model.id if base_model else None)),
            or_(UncertaintyModelException.base_model_version_id.is_(None), UncertaintyModelException.base_model_version_id == (base_version.id if base_version else None)),
            or_(UncertaintyModelException.procedure_id.is_(None), UncertaintyModelException.procedure_id == field_sheet.calibration_procedure_id),
            or_(UncertaintyModelException.profile_key.is_(None), UncertaintyModelException.profile_key == (procedure.profile_key if procedure else None)),
            or_(UncertaintyModelException.magnitude.is_(None), UncertaintyModelException.magnitude == (procedure.magnitude if procedure else None)),
            or_(UncertaintyModelException.equipment_type.is_(None), UncertaintyModelException.equipment_type == equipment.name),
            or_(UncertaintyModelException.equipment_model.is_(None), UncertaintyModelException.equipment_model == equipment.model),
        )
        .order_by(
            UncertaintyModelException.procedure_id.desc(),
            UncertaintyModelException.equipment_model.desc(),
            UncertaintyModelException.equipment_type.desc(),
            UncertaintyModelException.id.desc(),
        )
    )
    if exception is not None:
        version = get_uncertainty_model_version(db, exception.alternate_model_version_id)
        if version.status != APPROVED_VERSION_STATUS:
            warnings.append("La excepcion apunta a una version no aprobada y no puede usarse.")
            return base_model, base_version, None, warnings
        return version.model, version, {
            "exception_id": exception.id,
            "base_model_id": exception.base_model_id,
            "base_model_version_id": exception.base_model_version_id,
            "alternate_model_id": exception.alternate_model_id,
            "alternate_model_version_id": exception.alternate_model_version_id,
            "reason": exception.reason,
        }, warnings
    return base_model, base_version, None, warnings


def _row_readings(row: FieldSheetResult) -> list[float]:
    return [
        value
        for value in [_as_float(row.ibc_value_1), _as_float(row.ibc_value_2), _as_float(row.ibc_value_3)]
        if value is not None
    ]


def _best_reference_link(field_sheet: FieldSheet) -> FieldSheetReferenceStandard | None:
    links = sorted(field_sheet.reference_standard_links, key=lambda item: (item.usage_role != "primary", item.id))
    return links[0] if links else None


def _uncertainty_for_row(
    link: FieldSheetReferenceStandard | None,
    *,
    reference_value: float | None,
    unit: str | None,
):
    if link is None:
        return None
    if link.selected_uncertainty is not None and link.selected_uncertainty.is_active:
        return link.selected_uncertainty
    certificate = link.reference_standard_certificate
    if certificate is None:
        return None
    return get_applicable_uncertainty(certificate, value=reference_value, unit=unit)


def _input_snapshot(
    field_sheet: FieldSheet,
    model: UncertaintyModel | None,
    version: UncertaintyModelVersion | None,
    model_exception: dict | None,
) -> dict:
    equipment = field_sheet.equipment
    procedure = field_sheet.calibration_procedure
    link = _best_reference_link(field_sheet)
    certificate = link.reference_standard_certificate if link is not None else None
    standard = link.reference_standard if link is not None else None
    return {
        "field_sheet": {
            "id": field_sheet.id,
            "status": field_sheet.status,
            "template_key": field_sheet.template_key,
            "units": field_sheet.units,
            "calibration_date": field_sheet.calibration_date.isoformat() if field_sheet.calibration_date else None,
            "work_order_number": field_sheet.work_order_number,
        },
        "equipment": {
            "id": equipment.id,
            "name": equipment.name,
            "model": equipment.model,
            "serial_number": equipment.serial_number,
            "range_or_capacity": equipment.range_or_capacity,
        },
        "procedure": {
            "id": procedure.id if procedure else None,
            "code": procedure.code if procedure else None,
            "magnitude": procedure.magnitude if procedure else None,
            "profile_key": procedure.profile_key if procedure else None,
            "certificate_type": procedure.certificate_type if procedure else None,
            "uncertainty_model_id": procedure.uncertainty_model_id if procedure else None,
            "uncertainty_model_version_id": procedure.uncertainty_model_version_id if procedure else None,
        },
        "uncertainty_model": {
            "id": model.id if model else None,
            "code": model.code if model else None,
            "name": model.name if model else None,
            "status": model.status if model else None,
            "version_id": version.id if version else None,
            "version_number": version.version_number if version else None,
            "version_status": version.status if version else None,
        },
        "model_exception": model_exception,
        "reference_standard": {
            "link_id": link.id if link else None,
            "id": standard.id if standard else None,
            "code": standard.internal_code if standard else None,
            "name": standard.name if standard else None,
            "resolution": _as_float(standard.resolution) if standard else None,
            "certificate_id": certificate.id if certificate else None,
            "certificate_number": certificate.certificate_number if certificate else None,
            "certificate_expiration_date": certificate.expiration_date.isoformat()
            if certificate and certificate.expiration_date
            else None,
        },
    }


def _component_value(component: UncertaintyComponent, variables: dict[str, float], row_context: dict) -> tuple[float | None, dict]:
    metadata = component.metadata_json or {}
    raw_value = None
    source_detail = {}
    if component.source_type == "standard_uncertainty":
        uncertainty = row_context.get("selected_uncertainty")
        if uncertainty is not None:
            k_factor = _as_float(uncertainty.k_factor) or 1.0
            raw_value = float(uncertainty.uncertainty_value) / k_factor
            source_detail = {"uncertainty_id": uncertainty.id, "uncertainty_value": float(uncertainty.uncertainty_value), "k_factor": k_factor}
    elif component.source_type == "standard_resolution":
        standard_resolution = row_context.get("standard_resolution")
        raw_value = resolution_uncertainty(standard_resolution) if standard_resolution else None
        source_detail = {"resolution": standard_resolution}
    elif component.source_type == "ibc_resolution":
        ibc_resolution = _as_float(metadata.get("resolution"))
        raw_value = resolution_uncertainty(ibc_resolution) if ibc_resolution else None
        source_detail = {"resolution": ibc_resolution, "source": "component.metadata_json.resolution"}
    elif component.source_type == "repeatability":
        readings = row_context.get("readings") or []
        raw_value = repeatability_uncertainty(readings) if readings else None
        source_detail = {"readings": readings}
    elif component.source_type == "fixed":
        raw_value = _as_float(metadata.get("value"))
        source_detail = {"value": raw_value}
    elif component.source_type == "expression" and component.value_expression:
        raw_value = _safe_expression(component.value_expression, variables)
        source_detail = {"expression": component.value_expression}
    if raw_value is None:
        return None, source_detail
    divisor = component.divisor or 1.0
    value = float(raw_value) / divisor * component.sensitivity_coefficient
    return value, {**source_detail, "raw_value": raw_value, "divisor": divisor}


def preview_uncertainty_calculation(db: Session, field_sheet_id: int) -> UncertaintyPreview:
    field_sheet = _get_field_sheet_for_calculation(db, field_sheet_id)
    model, version, model_exception, resolve_warnings = _resolve_model_version(db, field_sheet)
    warnings: list[str] = list(resolve_warnings)
    errors: list[str] = []
    if model is None:
        errors.append("La hoja no tiene procedimiento con modelo de incertidumbre asociado.")
    if version is None:
        errors.append("El modelo de incertidumbre no tiene version aprobada.")
        return UncertaintyPreview(
            field_sheet_id=field_sheet_id,
            uncertainty_model_id=model.id if model else None,
            uncertainty_model_version_id=None,
            status="error",
            input_snapshot=_input_snapshot(field_sheet, model, None, model_exception),
            component_results=[],
            formula_results={},
            calculation_snapshot={},
            warnings=warnings,
            errors=errors,
        )
    if version.status != APPROVED_VERSION_STATUS:
        errors.append("Solo versiones approved pueden usarse en calculos automaticos.")
    active_components = [item for item in version.components if item.is_active]
    active_formulas = [item for item in version.formulas if item.is_active_formula]
    if not active_components:
        errors.append("La version del modelo no tiene componentes activos.")

    link = _best_reference_link(field_sheet)
    if link is None:
        errors.append("La hoja no tiene patron seleccionado.")
    elif link.reference_standard_certificate is None:
        errors.append("El patron no tiene certificado vigente asociado a la hoja.")
    standard = link.reference_standard if link else None
    row_results = []
    for row in field_sheet.results_rows:
        readings = _row_readings(row)
        reference_value = _as_float(row.pattern_value)
        if reference_value is None and not readings:
            continue
        selected_uncertainty = _uncertainty_for_row(link, reference_value=reference_value, unit=row.unit or field_sheet.units)
        if selected_uncertainty is None:
            warnings.append(f"No hay incertidumbre aplicable al rango medido en fila {row.row_number}.")
        average_value = mean(readings) if readings else None
        error_value = absolute_error(average_value, reference_value) if average_value is not None and reference_value is not None else None
        variables = {
            "reference": reference_value or 0.0,
            "average": average_value or 0.0,
            "error": error_value or 0.0,
            "correction": -error_value if error_value is not None else 0.0,
            "k": version.default_coverage_factor,
        }
        row_context = {
            "row_id": row.id,
            "section_key": row.section_key,
            "row_number": row.row_number,
            "readings": readings,
            "selected_uncertainty": selected_uncertainty,
            "standard_resolution": _as_float(standard.resolution) if standard else None,
        }
        component_results = []
        component_values = []
        for component in active_components:
            try:
                value, source_detail = _component_value(component, variables, row_context)
            except ValueError as exc:
                value = None
                source_detail = {"error": str(exc)}
            if value is None:
                message = f"Sin valor para componente {component.key} en fila {row.row_number}."
                if component.required:
                    errors.append(message)
                else:
                    warnings.append(message)
                continue
            variables[component.key] = value
            component_values.append(value)
            component_results.append(
                {
                    "component_id": component.id,
                    "key": component.key,
                    "name": component.name,
                    "source_type": component.source_type,
                    "value": value,
                    "distribution": component.distribution,
                    "sensitivity_coefficient": component.sensitivity_coefficient,
                    "source_detail": source_detail,
                }
            )
        if component_values:
            variables.setdefault("combined_uncertainty", combined_uncertainty(component_values))
            variables.setdefault("expanded_uncertainty", expanded_uncertainty(variables["combined_uncertainty"], version.default_coverage_factor))
        formula_results = {
            "average": average_value,
            "error": error_value,
            "correction": -error_value if error_value is not None else None,
            "combined_uncertainty": variables.get("combined_uncertainty"),
            "expanded_uncertainty": variables.get("expanded_uncertainty"),
        }
        for formula in active_formulas:
            try:
                formula_results[formula.result_key] = _safe_expression(formula.expression, variables)
                variables[formula.result_key] = formula_results[formula.result_key]
            except ValueError as exc:
                errors.append(f"Formula {formula.key} no pudo evaluarse en fila {row.row_number}: {exc}")
        row_results.append(
            {
                "row_id": row.id,
                "section_key": row.section_key,
                "row_number": row.row_number,
                "reference_value": reference_value,
                "readings": readings,
                "unit": row.unit or field_sheet.units,
                "selected_uncertainty": {
                    "id": selected_uncertainty.id if selected_uncertainty else None,
                    "uncertainty_value": float(selected_uncertainty.uncertainty_value) if selected_uncertainty else None,
                    "k_factor": float(selected_uncertainty.k_factor) if selected_uncertainty and selected_uncertainty.k_factor is not None else None,
                    "confidence_level": selected_uncertainty.confidence_level if selected_uncertainty else None,
                },
                "components": component_results,
                "results": formula_results,
            }
        )
    if not row_results:
        errors.append("No hay resultados capturados en hoja de campo.")

    formula_results = {"rows": [{"row_number": item["row_number"], **item["results"]} for item in row_results]}
    input_snapshot = _input_snapshot(field_sheet, model, version, model_exception)
    calculation_snapshot = {
        "uncertainty_model_id": model.id,
        "uncertainty_model_code": model.code,
        "uncertainty_model_version_id": version.id,
        "uncertainty_model_version_number": version.version_number,
        "uncertainty_model_version_status": version.status,
        "model_formula_keys": [item.key for item in active_formulas],
        "component_keys": [item.key for item in active_components],
        "rows": row_results,
        "warnings": warnings,
        "errors": errors,
        "explanation": (
            "Calculo basado en hoja de campo, version aprobada del modelo de incertidumbre, "
            "patron seleccionado, certificado vigente e incertidumbre aplicable por rango/unidad."
        ),
    }
    return UncertaintyPreview(
        field_sheet_id=field_sheet.id,
        uncertainty_model_id=model.id,
        uncertainty_model_version_id=version.id,
        status="error" if errors else "preview",
        input_snapshot=input_snapshot,
        component_results=row_results,
        formula_results=formula_results,
        calculation_snapshot=_json_safe(calculation_snapshot),
        warnings=warnings,
        errors=errors,
    )


def calculate_and_store_uncertainty(
    db: Session,
    field_sheet_id: int,
    *,
    user_id: int | None = None,
) -> UncertaintyCalculation:
    preview = preview_uncertainty_calculation(db, field_sheet_id)
    if preview.uncertainty_model_id is None or preview.uncertainty_model_version_id is None:
        raise HTTPException(status_code=409, detail={"message": "No fue posible calcular incertidumbre", "errors": preview.errors})
    calculation = UncertaintyCalculation(
        field_sheet_id=field_sheet_id,
        uncertainty_model_id=preview.uncertainty_model_id,
        uncertainty_model_version_id=preview.uncertainty_model_version_id,
        status="error" if preview.errors else "calculated",
        calculated_at=datetime.now(timezone.utc),
        input_snapshot=preview.input_snapshot,
        component_results=preview.component_results,
        formula_results=preview.formula_results,
        calculation_snapshot=preview.calculation_snapshot,
        warnings=preview.warnings,
        errors=preview.errors,
    )
    db.add(calculation)
    db.flush()
    write_audit_log(
        db,
        action="uncertainty_calculation.calculated",
        entity="uncertainty_calculations",
        entity_id=calculation.id,
        user_id=user_id,
        new_values={
            "field_sheet_id": field_sheet_id,
            "uncertainty_model_id": preview.uncertainty_model_id,
            "uncertainty_model_version_id": preview.uncertainty_model_version_id,
            "status": calculation.status,
            "warnings": preview.warnings,
            "errors": preview.errors,
        },
    )
    return calculation
