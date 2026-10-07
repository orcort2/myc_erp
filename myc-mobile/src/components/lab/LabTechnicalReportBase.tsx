import { useEffect, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import {
  AlertBanner,
  Card,
  LoadingState,
  ReadOnlyField,
  SecondaryButton,
  StatusBadge,
} from '@/src/design/primitives';
import { colors, spacing } from '@/src/design/tokens';
import {
  describeTechnicalReportCard,
  technicalReportPath,
  technicalReportTypeLabel,
} from '@/src/services/technical-report';
import type { LabEquipment, LabWorkOrder, TechnicalReportRead } from '@/src/types/lab-work-order';

type Request = <T>(path: string, init?: RequestInit) => Promise<T>;

type Props = {
  equipment: LabEquipment;
  onClose(): void;
  request: Request;
  workOrder: Pick<LabWorkOrder, 'id' | 'folio' | 'client_name'>;
};

/**
 * Vista base del TechnicalReport (SG-3E). Sólo identifica el documento:
 * encabezado de OT, equipo/producto, tipo, folio, estado, revisión y cliente.
 * La captura de Instalación llega en la siguiente fase.
 */
export function LabTechnicalReportBase({ equipment, onClose, request, workOrder }: Props) {
  const [report, setReport] = useState<TechnicalReportRead | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const state = describeTechnicalReportCard(equipment);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    request<TechnicalReportRead>(technicalReportPath(workOrder.id, equipment.id))
      .then((loaded) => { if (active) setReport(loaded); })
      .catch((failure) => {
        if (active) setError(failure instanceof Error ? failure.message : 'No fue posible cargar el reporte.');
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [equipment.id, request, workOrder.id]);

  const revision = report?.revision_number ?? Math.max(equipment.technical_report_revision_count, 1);

  return (
    <View style={styles.panel}>
      <Text style={styles.eyebrow}>OT {workOrder.folio} · EQUIPO {equipment.position}</Text>
      <Text style={styles.title}>{technicalReportTypeLabel(report?.report_type ?? equipment.technical_report_type)}</Text>

      {loading && <LoadingState label="Cargando reporte…" />}
      {!!error && <AlertBanner tone="danger">{error}</AlertBanner>}

      <Card>
        <View style={styles.header}>
          <Text style={styles.folio}>{report?.folio ?? state.folio ?? '—'}</Text>
          <StatusBadge label={state.badgeLabel} tone={state.badgeTone} />
        </View>
        <ReadOnlyField label="Revisión" value={String(revision)} />
        <ReadOnlyField label="Cliente" value={workOrder.client_name} />
      </Card>

      <Card>
        <ReadOnlyField label="Equipo / producto" value={equipment.instrument} />
        <ReadOnlyField label="Marca" value={equipment.brand} />
        <ReadOnlyField label="Modelo" value={equipment.model ?? ''} />
        <ReadOnlyField label="Identificación" value={equipment.identification} />
        <ReadOnlyField label="Número de serie" value={equipment.serial_number} />
      </Card>

      <AlertBanner tone="info">
        La captura del reporte de instalación estará disponible en la siguiente fase.
      </AlertBanner>

      <SecondaryButton icon="arrow-left" label="Volver a equipos" onPress={onClose} />
    </View>
  );
}

const styles = StyleSheet.create({
  eyebrow: { color: colors.accent, fontSize: 12, fontWeight: '800', letterSpacing: 1 },
  folio: { color: colors.text, fontSize: 18, fontWeight: '800' },
  header: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between' },
  panel: { gap: spacing.md, paddingBottom: spacing.xl },
  title: { color: colors.text, fontSize: 22, fontWeight: '800' },
});
