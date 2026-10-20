import { StyleSheet, Text, View } from 'react-native';

import {
  Card,
  PrimaryButton,
  ReadOnlyField,
  SecondaryButton,
  StatusBadge,
} from '@/src/design/primitives';
import { colors, spacing } from '@/src/design/tokens';
import {
  describeTechnicalReportCard,
  technicalReportAction,
} from '@/src/services/technical-report';
import type { LabEquipment } from '@/src/types/lab-work-order';

type Props = {
  equipment: LabEquipment;
  canCaptureReports: boolean;
  canReadReports: boolean;
  /** Cliente de la OT: Servicio General no tiene cliente documental por equipo. */
  clientName: string;
  /** Entrega registrada + reporte listo: puede generarse el documento final. */
  canFinalize?: boolean;
  finalizing?: boolean;
  onFinalize?(equipment: LabEquipment): void;
  onViewPdf?(equipment: LabEquipment): void;
  onDownloadPdf?(equipment: LabEquipment): void;
  onEdit?(equipment: LabEquipment): void;
  onOpenReport(equipment: LabEquipment): void;
  onSelectReport(equipment: LabEquipment): void;
};

/**
 * Tarjeta de equipo/producto de una OT de Servicio General. Misma anatomía que
 * la tarjeta de calibración (Card + título + badge + acción primaria), pero
 * su documento es un TechnicalReport: nunca modalidad, certificado ni hoja.
 */
export function LabTechnicalReportCard({
  canCaptureReports,
  canFinalize = false,
  canReadReports,
  clientName,
  equipment,
  finalizing = false,
  onDownloadPdf,
  onEdit,
  onFinalize,
  onViewPdf,
  onOpenReport,
  onSelectReport,
}: Props) {
  const state = describeTechnicalReportCard(equipment);
  const action = technicalReportAction(equipment, { canCapture: canCaptureReports, canRead: canReadReports });
  const identity = [equipment.brand, equipment.model, equipment.serial_number].filter(Boolean).join(' · ');

  return (
    <Card>
      <View style={styles.header}>
        <View style={styles.flex}>
          <Text style={styles.title}>{equipment.position}. {equipment.instrument}</Text>
          <Text style={styles.meta}>{identity}</Text>
        </View>
        <StatusBadge label={state.badgeLabel} tone={state.badgeTone} />
      </View>
      <Text style={styles.meta}>Servicio general{state.typeLabel ? ` · ${state.typeLabel}` : ''}</Text>
      <ReadOnlyField label="Cliente" value={clientName} />
      {state.folio && <ReadOnlyField label="Folio del reporte" value={state.folio} />}
      {action && (
        <PrimaryButton
          icon="clipboard-text-outline"
          label={state.actionLabel}
          onPress={() => (action === 'open' ? onOpenReport(equipment) : onSelectReport(equipment))}
        />
      )}
      {canFinalize && (
        <PrimaryButton
          disabled={finalizing}
          icon="file-document-check-outline"
          label="Generar reporte final"
          loading={finalizing}
          onPress={() => onFinalize?.(equipment)}
        />
      )}
      {equipment.technical_report_status === 'completed' && canReadReports && (
        <>
          <PrimaryButton icon="file-pdf-box" label="Ver reporte" onPress={() => onViewPdf?.(equipment)} />
          <SecondaryButton icon="download" label="Descargar reporte" onPress={() => onDownloadPdf?.(equipment)} />
        </>
      )}
      {onEdit && (
        <SecondaryButton icon="pencil-outline" label="Editar datos" onPress={() => onEdit(equipment)} />
      )}
    </Card>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  header: { alignItems: 'flex-start', flexDirection: 'row', gap: spacing.sm, justifyContent: 'space-between' },
  meta: { color: colors.textSubtle },
  title: { color: colors.text, fontSize: 17, fontWeight: '800' },
});
