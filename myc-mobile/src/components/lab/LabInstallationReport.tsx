import { useEffect, useRef, useState } from 'react';
import { Alert, Pressable, StyleSheet, Text, View } from 'react-native';

import { LabEvidenceGallery } from '@/src/components/lab/LabEvidenceGallery';

import {
  AlertBanner,
  Card,
  EmptyState,
  Field,
  LoadingState,
  PrimaryButton,
  ReadOnlyField,
  SecondaryButton,
  Section,
  StatusBadge,
} from '@/src/design/primitives';
import { MycDatePickerField } from '@/src/design/MycDatePickerField';
import { colors, spacing } from '@/src/design/tokens';
import {
  applyInstallationChange,
  EFFECTIVENESS_OPTIONS,
  EVIDENCE_TYPE_LABELS,
  installationCaptureFromServer,
  LONG_TEXT_MAX,
  SECTION_EVIDENCE_TYPE,
  SHORT_TEXT_MAX,
  showsEffectivenessFields,
  showsIncidentFields,
  textOrNull,
  type InstallationSectionKey,
} from '@/src/services/technical-report-installation';
import {
  createTechnicalReportAutosave,
  type TechnicalReportAutosave,
  type TechnicalReportAutosaveStatus,
} from '@/src/services/technical-report-autosave';
import type { TechnicalReportApi } from '@/src/services/technical-report-api';
import {
  getEvidenceMediaProvider,
  MAX_EVIDENCE_PER_REPORT,
  type EvidenceMediaProvider,
  type EvidenceSource,
} from '@/src/services/technical-report-media';
import {
  describeTechnicalReportCard,
  EDITABLE_REPORT_STATUSES,
} from '@/src/services/technical-report';
import type { LabEquipment } from '@/src/types/lab-work-order';
import type {
  InstallationCaptureField,
  InstallationCaptureValues,
  InstallationTextField,
  TechnicalReportEvidence,
  TechnicalReportEvidenceType,
  TechnicalReportRead,
} from '@/src/types/technical-report';

type Props = {
  api: TechnicalReportApi;
  canCapture: boolean;
  clientName: string;
  equipment: LabEquipment;
  /** Se invoca al salir con todo guardado, para refrescar la OT una sola vez. */
  onClose(): void;
  /** Cambio relevante (primera captura, foto subida/eliminada). Nunca por tecla. */
  onChanged?(): void;
  workOrderFolio: number;
  /** Inyectable para pruebas; por defecto el proveedor registrado en la app. */
  mediaProvider?: EvidenceMediaProvider | null;
};

const INCIDENT_EVIDENCE_BLOCKS_NO_MESSAGE = 'Elimina primero las evidencias de incidencia para indicar que no hubo incidencias.';

const LEAVE_FAILED_MESSAGE = 'No se pudo guardar tu captura; revisa la conexión y reintenta antes de salir del reporte.';

const AUTOSAVE_STATUS_LABELS: Record<TechnicalReportAutosaveStatus, string> = {
  idle: '',
  dirty: 'Cambios sin guardar…',
  saving: 'Guardando…',
  saved: 'Guardado',
  error: 'No se pudo guardar automáticamente; se reintentará al seguir editando.',
};

const SOURCE_LABELS: Record<EvidenceSource, string> = { camera: 'Tomar foto', library: 'Elegir de galería' };

function snapshotText(snapshot: TechnicalReportRead['document_snapshot'], group: string, key: string): string | null {
  const section = snapshot?.[group];
  if (section && typeof section === 'object') {
    const value = (section as Record<string, unknown>)[key];
    if (typeof value === 'string' && value) return value;
  }
  return null;
}

/**
 * Formulario del reporte de Instalación (SG-4A/B/C). Las secciones, el
 * autosave y la evidencia viven aquí; work-orders.tsx sólo aloja el overlay.
 * Cliente/equipo/folio se muestran desde el snapshot y NUNCA entran a
 * capture_values.
 */
export function LabInstallationReport({
  api,
  canCapture,
  clientName,
  equipment,
  mediaProvider,
  onChanged,
  onClose,
  workOrderFolio,
}: Props) {
  const [report, setReport] = useState<TechnicalReportRead | null>(null);
  const [values, setValues] = useState<InstallationCaptureValues | null>(null);
  const [loadError, setLoadError] = useState('');
  const [formError, setFormError] = useState('');
  const [autosaveStatus, setAutosaveStatus] = useState<TechnicalReportAutosaveStatus>('idle');
  const [photoBusy, setPhotoBusy] = useState(false);
  const [confirming, setConfirming] = useState(false);

  const apiRef = useRef(api);
  apiRef.current = api;
  const onChangedRef = useRef(onChanged);
  onChangedRef.current = onChanged;
  const valuesRef = useRef<InstallationCaptureValues | null>(null);
  valuesRef.current = values;

  const autosaveRef = useRef<TechnicalReportAutosave<InstallationCaptureValues> | null>(null);
  if (autosaveRef.current === null) {
    autosaveRef.current = createTechnicalReportAutosave<InstallationCaptureValues, TechnicalReportRead>({
      save: (next) => apiRef.current.saveCapture({ capture_values: next }),
      // Sólo estado/evidencia del servidor: lo que el técnico sigue escribiendo
      // (values) es la autoridad local y no se pisa.
      onSaved: (saved) => {
        setReport((current) => (current && current.id === saved.id
          ? { ...current, status: saved.status, evidence: saved.evidence }
          : current));
      },
      onStatusChange: setAutosaveStatus,
    });
  }
  const autosave = autosaveRef.current;

  useEffect(() => {
    let active = true;
    api.load()
      .then((loaded) => {
        if (!active) return;
        setReport(loaded);
        setValues(installationCaptureFromServer(loaded.capture_values));
      })
      .catch((error) => {
        if (active) setLoadError(error instanceof Error ? error.message : 'No fue posible cargar el reporte.');
      });
    return () => { active = false; };
  // Un reporte por equipo: sólo se recarga si cambia el equipo.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [equipment.id]);

  // Salir de la pantalla con captura pendiente: flush best-effort.
  useEffect(() => () => { void autosave.flush(); }, [autosave]);

  const editable = canCapture && !!report && EDITABLE_REPORT_STATUSES.has(report.status);
  const card = describeTechnicalReportCard({
    technical_report_id: report?.id ?? equipment.technical_report_id,
    technical_report_type: report?.report_type ?? equipment.technical_report_type,
    technical_report_folio: report?.folio ?? equipment.technical_report_folio,
    technical_report_status: report?.status ?? equipment.technical_report_status,
  });
  const snapshot = report?.document_snapshot ?? null;

  function change<K extends InstallationCaptureField>(field: K, value: InstallationCaptureValues[K]) {
    if (!editable || !valuesRef.current) return;
    // Consistencia documental: el reporte no puede declarar "sin incidencias"
    // mientras conserve evidencia clasificada como incidencia. No se borra ni
    // se reclasifica nada automáticamente.
    if (field === 'has_incidents' && value === false && report?.evidence.some((item) => item.evidence_type === 'incident')) {
      Alert.alert('No se puede cambiar', INCIDENT_EVIDENCE_BLOCKS_NO_MESSAGE);
      return;
    }
    const next = applyInstallationChange(valuesRef.current, field, value);
    valuesRef.current = next;
    setValues(next);
    autosave.change(next);
  }

  function changeText(field: InstallationTextField, text: string) {
    change(field, textOrNull(text));
  }

  // ------------------------------------------------------- confirmar captura
  // Transición explícita y separada del autosave. Backend revalida TODO (Mobile
  // no es autoridad) y fija al técnico responsable; aquí sólo se pide la
  // confirmación y se muestran sus errores completos.
  function requestConfirmation() {
    if (!editable || confirming) return;
    Alert.alert(
      '¿Confirmar captura?',
      'Al confirmar, la captura y las fotografías quedarán bloqueadas y no podrás modificarlas. Quedarás registrado como técnico responsable.',
      [
        { text: 'Cancelar', style: 'cancel' },
        { text: 'Confirmar captura', onPress: () => { void confirmCapture(); } },
      ],
    );
  }

  async function confirmCapture() {
    setConfirming(true);
    setFormError('');
    try {
      // Lo último escrito debe estar en el servidor antes de validar.
      if (!(await autosave.flush())) {
        setFormError('No se pudo guardar tu captura; revisa la conexión y reintenta antes de confirmar.');
        return;
      }
      const confirmed = await api.confirmCapture();
      setReport(confirmed);
      onChangedRef.current?.();
    } catch (error) {
      Alert.alert('No se puede confirmar la captura', error instanceof Error ? error.message : 'Intenta nuevamente');
    } finally {
      setConfirming(false);
    }
  }

  async function leave() {
    if (!(await autosave.leave())) {
      setFormError(LEAVE_FAILED_MESSAGE);
      return;
    }
    onClose();
  }

  // ------------------------------------------------------------- evidencia
  async function addPhoto(evidenceType: TechnicalReportEvidenceType, source: EvidenceSource, provider: EvidenceMediaProvider) {
    setFormError('');
    setPhotoBusy(true);
    try {
      const image = await provider.capture(source);
      if (!image) return;
      const uploaded = await api.uploadEvidence(image, evidenceType);
      setReport((current) => current && ({
        ...current,
        status: current.status === 'draft' ? 'in_progress' : current.status,
        evidence: [...current.evidence, uploaded],
      }));
      onChangedRef.current?.();
    } catch (error) {
      Alert.alert('No fue posible agregar la foto', error instanceof Error ? error.message : 'Intenta nuevamente');
    } finally {
      setPhotoBusy(false);
    }
  }

  function requestPhoto(evidenceType: TechnicalReportEvidenceType) {
    const provider = mediaProvider === undefined ? getEvidenceMediaProvider() : mediaProvider;
    if (!provider || provider.availableSources.length === 0) return;
    if (provider.availableSources.length === 1) {
      void addPhoto(evidenceType, provider.availableSources[0], provider);
      return;
    }
    Alert.alert('Agregar foto', EVIDENCE_TYPE_LABELS[evidenceType], [
      ...provider.availableSources.map((source) => ({
        text: SOURCE_LABELS[source],
        onPress: () => { void addPhoto(evidenceType, source, provider); },
      })),
      { text: 'Cancelar', style: 'cancel' as const },
    ]);
  }

  /** Baja de una evidencia desde el visor. Sólo actualiza estado/evidencia del
   * reporte: nunca recarga ni pisa los valores locales del formulario. */
  async function deleteEvidence(item: TechnicalReportEvidence): Promise<void> {
    setPhotoBusy(true);
    try {
      const updated = await api.deleteEvidence(item.id);
      setReport((current) => current && ({ ...current, status: updated.status, evidence: updated.evidence }));
      onChangedRef.current?.();
    } catch (error) {
      Alert.alert('No fue posible eliminar la foto', error instanceof Error ? error.message : 'Intenta nuevamente');
      throw error;
    } finally {
      setPhotoBusy(false);
    }
  }

  const provider = mediaProvider === undefined ? getEvidenceMediaProvider() : mediaProvider;
  const canAddPhotos = editable && !!provider && provider.availableSources.length > 0
    && (report?.evidence.length ?? 0) < MAX_EVIDENCE_PER_REPORT;

  function renderPhotos(section: InstallationSectionKey) {
    const evidenceType = SECTION_EVIDENCE_TYPE[section];
    if (!evidenceType || !report) return null;
    const items = report.evidence
      .filter((item) => item.evidence_type === evidenceType)
      .sort((left, right) => left.position - right.position);
    if (!items.length && !canAddPhotos) {
      return editable ? null : <Text style={styles.meta}>Sin fotografías.</Text>;
    }
    return (
      <LabEvidenceGallery
        addLabel={`Agregar foto · ${EVIDENCE_TYPE_LABELS[evidenceType]}`}
        busy={photoBusy}
        canAdd={canAddPhotos}
        canDelete={editable}
        imageSource={api.evidenceImageSource}
        items={items}
        onAdd={() => requestPhoto(evidenceType)}
        onDelete={deleteEvidence}
      />
    );
  }

  // ------------------------------------------------------------- controles
  function textField(field: InstallationTextField, label: string, options: { multiline?: boolean; max?: number; required?: boolean } = {}) {
    const current = values?.[field] ?? '';
    if (!editable) return <ReadOnlyField key={field} label={label} value={current} />;
    return (
      <Field
        key={field}
        label={label}
        maxLength={options.max ?? LONG_TEXT_MAX}
        multiline={options.multiline ?? true}
        onBlur={() => void autosave.flush()}
        onChange={(text) => changeText(field, text)}
        required={options.required}
        value={current}
      />
    );
  }

  function yesNo(field: 'has_incidents' | 'functional_test_performed', label: string) {
    const current = values?.[field] ?? null;
    if (!editable) return <ReadOnlyField label={label} value={current === null ? '' : current ? 'Sí' : 'No'} />;
    return (
      <View style={styles.choiceField}>
        <Text style={styles.choiceLabel}>{label}</Text>
        <View style={styles.choiceRow}>
          {([true, false] as const).map((option) => (
            <Pressable
              accessibilityLabel={`${label}: ${option ? 'Sí' : 'No'}`}
              accessibilityRole="radio"
              accessibilityState={{ checked: current === option }}
              key={String(option)}
              onPress={() => { change(field, option); void autosave.flush(); }}
              style={[styles.choice, current === option && styles.choiceActive]}
            >
              <Text style={[styles.choiceText, current === option && styles.choiceTextActive]}>{option ? 'Sí' : 'No'}</Text>
            </Pressable>
          ))}
        </View>
      </View>
    );
  }

  if (loadError) {
    return (
      <View style={styles.panel}>
        <AlertBanner tone="danger">{loadError}</AlertBanner>
        <SecondaryButton icon="arrow-left" label="Volver a equipos" onPress={onClose} />
      </View>
    );
  }
  if (!report || !values) return <LoadingState label="Cargando reporte…" />;

  return (
    <View style={styles.panel}>
      <Text style={styles.eyebrow}>OT {workOrderFolio} · EQUIPO {equipment.position}</Text>
      <Text style={styles.title}>Reporte de instalación</Text>

      <Card>
        <View style={styles.header}>
          <Text style={styles.folio}>{report.folio}</Text>
          <StatusBadge label={card.badgeLabel} tone={card.badgeTone} />
        </View>
        <ReadOnlyField label="Cliente" value={snapshotText(snapshot, 'client', 'name') ?? clientName} />
        <ReadOnlyField label="Equipo / producto" value={snapshotText(snapshot, 'equipment', 'instrument') ?? equipment.instrument} />
        <ReadOnlyField label="Marca" value={snapshotText(snapshot, 'equipment', 'brand') ?? equipment.brand} />
        <ReadOnlyField label="Modelo" value={snapshotText(snapshot, 'equipment', 'model') ?? equipment.model ?? ''} />
        <ReadOnlyField label="Serie" value={snapshotText(snapshot, 'equipment', 'serial_number') ?? equipment.serial_number} />
        <ReadOnlyField label="Identificación" value={snapshotText(snapshot, 'equipment', 'identification') ?? equipment.identification} />
      </Card>

      {!editable && (
        <AlertBanner tone="info">
          {report.status === 'ready_for_signatures'
            ? 'Captura confirmada: el reporte quedó bloqueado y está listo para firmas.'
            : canCapture ? 'Este reporte ya no es editable.' : 'Tu perfil permite consultar este reporte, pero no capturarlo.'}
        </AlertBanner>
      )}
      {!!report.performed_by_name_snapshot && (
        <Card>
          <ReadOnlyField label="Técnico responsable" value={report.performed_by_name_snapshot} />
          {!!report.performed_at && <ReadOnlyField label="Captura confirmada" value={report.performed_at.replace('T', ' ').slice(0, 16)} />}
        </Card>
      )}
      {editable && autosaveStatus !== 'idle' && (
        <Text style={autosaveStatus === 'error' ? styles.autosaveError : styles.autosaveHint}>
          {AUTOSAVE_STATUS_LABELS[autosaveStatus]}
        </Text>
      )}
      {!!formError && <AlertBanner tone="danger">{formError}</AlertBanner>}

      <Section title="Datos de instalación">
        {editable ? (
          <MycDatePickerField
            label="Fecha de instalación"
            onChange={(date) => { change('installation_date', date || null); void autosave.flush(); }}
            value={values.installation_date ?? ''}
          />
        ) : (
          <ReadOnlyField label="Fecha de instalación" value={values.installation_date ?? ''} />
        )}
        {textField('installation_location', 'Lugar de instalación', { multiline: false, max: SHORT_TEXT_MAX })}
      </Section>

      <Section title="Condición inicial">
        {textField('initial_condition', 'Condición inicial del equipo')}
        {renderPhotos('initial_condition')}
      </Section>

      <Section title="Trabajo realizado">
        {textField('installation_description', 'Descripción de la instalación')}
        {textField('activities_performed', 'Actividades realizadas')}
        {renderPhotos('work_performed')}
      </Section>

      <Section title="Incidencias / anomalías">
        {yesNo('has_incidents', '¿Hubo incidencias?')}
        {showsIncidentFields(values) && (
          <>
            {textField('incident_description', 'Descripción de la incidencia', { required: true })}
            {textField('corrective_action', 'Acción correctiva')}
            {renderPhotos('incidents')}
          </>
        )}
      </Section>

      <Section title="Verificación de funcionamiento">
        {yesNo('functional_test_performed', '¿Se realizó prueba funcional?')}
        {showsEffectivenessFields(values) && (
          <>
            <View style={styles.choiceField}>
              <Text style={styles.choiceLabel}>Resultado de efectividad</Text>
              {EFFECTIVENESS_OPTIONS.map((option) => (
                editable ? (
                  <Pressable
                    accessibilityLabel={`Efectividad: ${option.label}`}
                    accessibilityRole="radio"
                    accessibilityState={{ checked: values.effectiveness_result === option.value }}
                    key={option.value}
                    onPress={() => { change('effectiveness_result', option.value); void autosave.flush(); }}
                    style={[styles.choice, styles.choiceStacked, values.effectiveness_result === option.value && styles.choiceActive]}
                  >
                    <Text style={[styles.choiceText, values.effectiveness_result === option.value && styles.choiceTextActive]}>{option.label}</Text>
                  </Pressable>
                ) : values.effectiveness_result === option.value ? (
                  <ReadOnlyField key={option.value} label="Resultado de efectividad" value={option.label} />
                ) : null
              ))}
            </View>
            {textField('effectiveness_description', 'Descripción de la verificación')}
            {textField('effectiveness_notes', 'Notas de efectividad')}
          </>
        )}
        {renderPhotos('functional_verification')}
      </Section>

      <Section title="Observaciones finales">
        {textField('final_observations', 'Observaciones finales')}
      </Section>

      <Section title="Evidencia fotográfica">
        {report.evidence.length === 0 ? (
          <EmptyState
            title="Sin fotografías"
            description={canAddPhotos
              ? 'Agrega fotos desde cada sección: Condición inicial, Trabajo realizado, Incidencias o Verificación.'
              : 'Aún no hay fotografías en este reporte.'}
          />
        ) : (
          <Text style={styles.meta}>
            {report.evidence.length} de {MAX_EVIDENCE_PER_REPORT} fotografías
            {' · '}
            {(['before', 'during', 'incident', 'after'] as const)
              .map((type) => [type, report.evidence.filter((item) => item.evidence_type === type).length] as const)
              .filter(([, count]) => count > 0)
              .map(([type, count]) => `${EVIDENCE_TYPE_LABELS[type]} ${count}`)
              .join(' · ')}
          </Text>
        )}
        {editable && !provider && (
          <Text style={styles.meta}>La captura de fotos requiere actualizar la app.</Text>
        )}
      </Section>

      {editable && (
        <Section title="Confirmar captura">
          <Text style={styles.meta}>
            El autosave guarda tu borrador, pero no finaliza el reporte. Al confirmar se valida que esté completo, se
            bloquea la captura y quedas como técnico responsable.
          </Text>
          <PrimaryButton
            disabled={confirming || photoBusy}
            icon="check-circle"
            label="Confirmar captura"
            loading={confirming}
            onPress={requestConfirmation}
          />
        </Section>
      )}

      <SecondaryButton icon="arrow-left" label="Volver a equipos" onPress={() => { void leave(); }} />
    </View>
  );
}

const styles = StyleSheet.create({
  autosaveError: { color: colors.danger, fontSize: 12 },
  autosaveHint: { color: colors.textSubtle, fontSize: 12 },
  choice: { alignItems: 'center', borderColor: colors.border, borderRadius: 9, borderWidth: 1, flex: 1, paddingVertical: spacing.sm },
  choiceActive: { backgroundColor: colors.primarySoft, borderColor: colors.primary },
  choiceField: { gap: spacing.xs },
  choiceLabel: { color: colors.text, fontWeight: '700' },
  choiceRow: { flexDirection: 'row', gap: spacing.sm },
  choiceStacked: { flex: 0, marginBottom: spacing.xs },
  choiceText: { color: colors.text, fontWeight: '600' },
  choiceTextActive: { color: colors.primary },
  eyebrow: { color: colors.accent, fontSize: 12, fontWeight: '800', letterSpacing: 1 },
  folio: { color: colors.text, fontSize: 18, fontWeight: '800' },
  header: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between' },
  meta: { color: colors.textSubtle },
  panel: { gap: spacing.md, paddingBottom: spacing.xl },
  title: { color: colors.text, fontSize: 22, fontWeight: '800' },
});
