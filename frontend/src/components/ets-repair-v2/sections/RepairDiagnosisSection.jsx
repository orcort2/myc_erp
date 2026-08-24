import React, {
  useEffect,
  useState,
} from 'react';

import {
  ClipboardList,
  Stethoscope,
} from 'lucide-react';

import {
  saveRepairDiagnosis,
  startRepairEvaluation,
} from '../../../services/api.js';

import {
  canExecuteRepair,
  formatDateTime,
  getUserDisplayName,
  REPAIRABILITY_LABELS,
  SEVERITY_LABELS,
} from './repairShared.js';


function emptyForm() {
  return {
    reportedIssue: '',
    observedCondition: '',
    findings: '',
    probableCauses: '',
    severity: '',
    repairability: '',
    diagnosisNotes: '',
  };
}


function toLines(value) {
  return (value || '')
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean);
}


function RepairDiagnosisSection({
  order,
  execution,
  user,
  users = [],
  isBusy = false,
  onBusyChange,
  onBoardChange,
  onError,
  onNotice,
}) {
  const [form, setForm] = useState(emptyForm());

  const isOwnTechnician = canExecuteRepair(execution, user);

  const isReadyToStart = execution?.status === 'assigned';
  const isInEvaluation = execution?.status === 'in_evaluation';

  const isBeforeAssignment = [
    'pending_arrival',
    'pending_assignment',
  ].includes(execution?.status);

  const hasDiagnosis = Boolean(execution?.diagnosis_completed_at);

  useEffect(() => {
    if (!isInEvaluation) {
      return;
    }

    const data = execution?.diagnosis_data || {};

    setForm({
      reportedIssue: data.reported_issue || '',
      observedCondition: data.observed_condition || '',
      findings: (data.findings || []).join('\n'),
      probableCauses: (data.probable_causes || []).join('\n'),
      severity: data.severity || '',
      repairability: data.repairability || '',
      diagnosisNotes: execution?.diagnosis_notes || '',
    });
  }, [execution?.id, execution?.status]);

  function setBusy(value) {
    if (typeof onBusyChange === 'function') {
      onBusyChange(value);
    }
  }

  function reportError(message) {
    if (typeof onError === 'function') {
      onError(message);
    }
  }

  function reportNotice(message) {
    if (typeof onNotice === 'function') {
      onNotice(message);
    }
  }

  function updateBoard(result) {
    if (result && typeof onBoardChange === 'function') {
      onBoardChange(result);
    }
  }

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function handleStartEvaluation() {
    if (!order?.id || !execution?.id || isBusy) {
      return;
    }

    setBusy(true);
    reportError('');
    reportNotice('');

    try {
      const result = await startRepairEvaluation(order.id, execution.id);

      updateBoard(result);
      reportNotice('Evaluación técnica iniciada.');
    } catch (requestError) {
      reportError(
        requestError?.message ||
          'No fue posible iniciar la evaluación.',
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();

    if (!order?.id || !execution?.id || isBusy) {
      return;
    }

    const payload = {
      reported_issue: form.reportedIssue.trim() || null,
      observed_condition: form.observedCondition.trim() || null,
      findings: toLines(form.findings),
      probable_causes: toLines(form.probableCauses),
      severity: form.severity || null,
      repairability: form.repairability || null,
      diagnosis_notes: form.diagnosisNotes.trim() || null,
    };

    const hasContent = Object.values(payload).some((value) =>
      Array.isArray(value) ? value.length > 0 : Boolean(value),
    );

    if (!hasContent) {
      reportError('El diagnóstico debe contener al menos una evidencia técnica.');
      return;
    }

    setBusy(true);
    reportError('');
    reportNotice('');

    try {
      const result = await saveRepairDiagnosis(order.id, execution.id, payload);

      updateBoard(result);
      reportNotice('Diagnóstico guardado.');
    } catch (requestError) {
      reportError(
        requestError?.message ||
          'No fue posible guardar el diagnóstico.',
      );
    } finally {
      setBusy(false);
    }
  }

  /* =======================================================
     BLOQUEADO: aún no asignado
     ======================================================= */

  if (isBeforeAssignment) {
    return (
      <section className="repair-v2-stage">
        <header className="repair-v2-stage__heading">
          <div>
            <h4>Diagnóstico</h4>
          </div>

          <span className="repair-v2-stage__state is-pending">
            <Stethoscope size={15} />
            Aún no disponible
          </span>
        </header>

        <div className="repair-v2-stage__notice">
          Requiere que la reparación tenga un técnico asignado.
        </div>
      </section>
    );
  }

  /* =======================================================
     LISTO PARA INICIAR EVALUACIÓN
     ======================================================= */

  if (isReadyToStart) {
    return (
      <section className="repair-v2-stage">
        <header className="repair-v2-stage__heading">
          <div>
            <h4>Diagnóstico</h4>
            <p>
              Inicia la evaluación técnica para poder
              registrar el diagnóstico del equipo.
            </p>
          </div>

          <span className="repair-v2-stage__state is-waiting">
            <Stethoscope size={15} />
            Pendiente de iniciar
          </span>
        </header>

        {!isOwnTechnician ? (
          <div className="repair-v2-stage__notice">
            Esta reparación está asignada a{' '}
            {getUserDisplayName(users, execution?.technician_id)}.
            Solo ese técnico puede iniciar la evaluación.
          </div>
        ) : (
          <footer className="repair-v2-form__actions">
            <button
              className="primary-button"
              disabled={isBusy}
              onClick={handleStartEvaluation}
              type="button"
            >
              <Stethoscope size={16} />
              {isBusy ? 'Iniciando...' : 'Iniciar evaluación'}
            </button>
          </footer>
        )}
      </section>
    );
  }

  /* =======================================================
     DESPUÉS DE LA EVALUACIÓN: solo lectura
     ======================================================= */

  if (!isInEvaluation) {
    if (!hasDiagnosis) {
      return (
        <section className="repair-v2-stage">
          <header className="repair-v2-stage__heading">
            <div>
              <h4>Diagnóstico</h4>
            </div>

            <span className="repair-v2-stage__state is-done">
              <ClipboardList size={15} />
              Etapa concluida
            </span>
          </header>

          <div className="repair-v2-stage__notice">
            No se registró diagnóstico estructurado durante la
            evaluación de este expediente. El diagnóstico es
            opcional y no bloquea el avance.
          </div>
        </section>
      );
    }

    const data = execution?.diagnosis_data || {};

    return (
      <section className="repair-v2-stage">
        <header className="repair-v2-stage__heading">
          <div>
            <h4>Diagnóstico</h4>
          </div>

          <span className="repair-v2-stage__state is-done">
            <ClipboardList size={15} />
            Registrado
          </span>
        </header>

        <div className="repair-v2-list__item">
          <div className="repair-v2-list__meta">
            <div>
              <span>Severidad</span>
              <strong>{SEVERITY_LABELS[data.severity] || 'Sin registrar'}</strong>
            </div>

            <div>
              <span>Reparabilidad</span>
              <strong>
                {REPAIRABILITY_LABELS[data.repairability] || 'Sin registrar'}
              </strong>
            </div>

            <div>
              <span>Registrado</span>
              <strong>{formatDateTime(execution?.diagnosis_completed_at)}</strong>
            </div>
          </div>

          {data.reported_issue ? (
            <p><strong>Reporte del cliente:</strong> {data.reported_issue}</p>
          ) : null}

          {data.observed_condition ? (
            <p><strong>Condición observada:</strong> {data.observed_condition}</p>
          ) : null}

          {(data.findings || []).length ? (
            <p>
              <strong>Hallazgos:</strong> {(data.findings || []).join(' · ')}
            </p>
          ) : null}

          {(data.probable_causes || []).length ? (
            <p>
              <strong>Causas probables:</strong>{' '}
              {(data.probable_causes || []).join(' · ')}
            </p>
          ) : null}

          {execution?.diagnosis_notes ? (
            <p><strong>Notas:</strong> {execution.diagnosis_notes}</p>
          ) : null}
        </div>
      </section>
    );
  }

  /* =======================================================
     EN EVALUACIÓN: formulario editable
     ======================================================= */

  return (
    <section className="repair-v2-stage">
      <header className="repair-v2-stage__heading">
        <div>
          <h4>Diagnóstico</h4>
          <p>
            Diagnóstico técnico opcional. Puede editarse mientras
            la ejecución siga en evaluación.
          </p>
        </div>

        <span className="repair-v2-stage__state is-active">
          <Stethoscope size={15} />
          En evaluación
        </span>
      </header>

      {!isOwnTechnician ? (
        <div className="repair-v2-stage__notice">
          Esta reparación está asignada a{' '}
          {getUserDisplayName(users, execution?.technician_id)}.
          Solo ese técnico puede registrar el diagnóstico.
        </div>
      ) : (
        <form className="repair-v2-form" onSubmit={handleSubmit}>
          <label className="repair-v2-form__field repair-v2-form__field--wide">
            Reporte del cliente

            <textarea
              disabled={isBusy}
              onChange={(event) =>
                updateField('reportedIssue', event.target.value)
              }
              placeholder="Falla reportada por el cliente"
              value={form.reportedIssue}
            />
          </label>

          <label className="repair-v2-form__field repair-v2-form__field--wide">
            Condición observada

            <textarea
              disabled={isBusy}
              onChange={(event) =>
                updateField('observedCondition', event.target.value)
              }
              placeholder="Condición física/funcional observada al recibir"
              value={form.observedCondition}
            />
          </label>

          <label className="repair-v2-form__field repair-v2-form__field--wide">
            Hallazgos (uno por línea)

            <textarea
              disabled={isBusy}
              onChange={(event) => updateField('findings', event.target.value)}
              placeholder={'Ej. Fuga en válvula\nDesgaste en rodamiento'}
              value={form.findings}
            />
          </label>

          <label className="repair-v2-form__field repair-v2-form__field--wide">
            Causas probables (una por línea)

            <textarea
              disabled={isBusy}
              onChange={(event) =>
                updateField('probableCauses', event.target.value)
              }
              placeholder={'Ej. Falta de mantenimiento preventivo'}
              value={form.probableCauses}
            />
          </label>

          <label className="repair-v2-form__field">
            Severidad

            <select
              disabled={isBusy}
              onChange={(event) => updateField('severity', event.target.value)}
              value={form.severity}
            >
              <option value="">Sin especificar</option>

              {Object.entries(SEVERITY_LABELS).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </label>

          <label className="repair-v2-form__field">
            Reparabilidad

            <select
              disabled={isBusy}
              onChange={(event) =>
                updateField('repairability', event.target.value)
              }
              value={form.repairability}
            >
              <option value="">Sin especificar</option>

              {Object.entries(REPAIRABILITY_LABELS).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </label>

          <label className="repair-v2-form__field repair-v2-form__field--wide">
            Notas de diagnóstico

            <textarea
              disabled={isBusy}
              onChange={(event) =>
                updateField('diagnosisNotes', event.target.value)
              }
              placeholder="Notas libres del diagnóstico"
              value={form.diagnosisNotes}
            />
          </label>

          <footer className="repair-v2-form__actions">
            <button className="primary-button" disabled={isBusy} type="submit">
              <ClipboardList size={16} />
              {isBusy ? 'Guardando...' : 'Guardar diagnóstico'}
            </button>
          </footer>
        </form>
      )}
    </section>
  );
}

export default RepairDiagnosisSection;
