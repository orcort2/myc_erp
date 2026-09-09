import { Redirect } from 'expo-router';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Alert, ScrollView, StyleSheet, Text } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { useAuth } from '@/src/auth/AuthProvider';
import {
  AdministrativeButton,
  AlertBanner,
  BackButton,
  Card,
  EmptyState,
  LoadingState,
  OperationalActionStack,
  PrimaryButton,
  Screen,
  SecondaryButton,
  Section,
  StatusBadge,
} from '@/src/design/primitives';
import { colors, spacing } from '@/src/design/tokens';
import { deriveMobileCapabilities } from '@/src/permissions/mobile-capabilities';
import {
  BluetoothDisabledError,
  BluetoothPermissionDeniedError,
  buildQaDiagnosticRaster,
  buildQaPrintJobPackets,
  buildTestPrintPayload,
  printLabel,
  printerManager,
  runNelkoDiagnostics,
  type RowHeaderVariant,
} from '@/src/services/label-print-service';
import { readPreferredPrinter } from '@/src/services/labels/printers/preferred-printer-storage';
import type { DeviceClassification, PreferredPrinter } from '@/src/services/labels/printers/types';

const SCAN_TIMEOUT_MS = 8_000;

/** Sólo dispositivos reconocidos (con family) llegan a la lista visible --
 * ver startScan: un `unknown` se descarta antes de guardarse en estado,
 * nunca se ofrece como impresora (mission section 17). */
type RecognizedDevice = Extract<DeviceClassification, { kind: 'recognized' }>;

/**
 * Configuración de impresora de etiquetas -- ver mission section 19/21.
 * Configuración puramente local del dispositivo (qué impresora física está
 * emparejada en ESTE teléfono/tablet): no requiere un permiso LAB de
 * negocio, mismo criterio ya usado por otras preferencias locales de la
 * app (ver auditoría previa a este cambio, "Permisos / autorización").
 * Visible a cualquiera que ya pueda capturar hojas de campo -- es la misma
 * gente que usaría el botón "Imprimir etiqueta" en LabTechnicalCapture.
 */
export default function LabelPrinterSetupScreen() {
  const { isLoading, user } = useAuth();
  const capabilities = deriveMobileCapabilities(user);
  const [preferred, setPreferred] = useState<PreferredPrinter | null>(null);
  const [connected, setConnected] = useState(printerManager.isReady());
  const [scanning, setScanning] = useState(false);
  const [devices, setDevices] = useState<RecognizedDevice[]>([]);
  const [busyDeviceId, setBusyDeviceId] = useState<string | null>(null);
  const [testPrinting, setTestPrinting] = useState(false);
  const [qaTesting, setQaTesting] = useState<RowHeaderVariant | null>(null);
  const [error, setError] = useState('');
  const seenDeviceIds = useRef(new Set<string>());

  useEffect(() => {
    readPreferredPrinter().then(setPreferred).catch(() => setPreferred(null));
  }, []);

  // AUDITORÍA 2026-09-08: si la pantalla se desmonta mientras hay un scan
  // en curso (el usuario navega fuera), el escaneo nativo debe cortarse
  // limpiamente en vez de seguir corriendo en segundo plano indefinidamente
  // -- printerManager.stopScan() es seguro de llamar incluso sin un scan
  // activo (no-op), ver scan-lifecycle.test.ts.
  useEffect(() => () => {
    printerManager.stopScan().catch(() => undefined);
  }, []);

  const startScan = useCallback(async () => {
    setError('');
    setDevices([]);
    seenDeviceIds.current = new Set();
    setScanning(true);

    try {
      await printerManager.scan((classification) => {
        if (classification.kind === 'unknown') return;
        if (seenDeviceIds.current.has(classification.device.id)) return;

        seenDeviceIds.current.add(classification.device.id);
        setDevices((current) => [...current, classification]);
      }, SCAN_TIMEOUT_MS);
    } catch (scanError) {
      if (scanError instanceof BluetoothPermissionDeniedError) {
        setError('MYC necesita permiso de Bluetooth para buscar la impresora.');
      } else if (scanError instanceof BluetoothDisabledError) {
        setError('Enciende Bluetooth para buscar la impresora.');
      } else {
        setError(
          scanError instanceof Error
            ? scanError.message
            : 'No fue posible buscar impresoras.',
        );
      }
    } finally {
      setScanning(false);
    }
  }, []);

  const connectTo = useCallback(async (classification: RecognizedDevice) => {
    if (classification.family.supportStatus !== 'supported') return;

    setBusyDeviceId(classification.device.id);
    setError('');

    try {
      await printerManager.connectAndRemember(
        classification.family.adapterId,
        classification.device,
      );

      setConnected(true);
      setPreferred(await readPreferredPrinter());
    } catch (connectError) {
      setError(
        connectError instanceof Error
          ? connectError.message
          : 'No fue posible conectar la impresora.',
      );
    } finally {
      setBusyDeviceId(null);
    }
  }, []);

  const runDiagnostics = useCallback(async (classification: RecognizedDevice) => {
    setBusyDeviceId(classification.device.id);
    setError('');

    try {
      const bleModule = await import(
        '@/src/services/labels/printers/ble-manager-transport'
      );

      const report = await runNelkoDiagnostics(
        new bleModule.BleManagerTransport(),
        classification.device,
      );

      Alert.alert(
        `Diagnóstico ${classification.device.name ?? classification.device.id}`,
        JSON.stringify(report, null, 2).slice(0, 3000),
      );
    } catch (diagnosticError) {
      setError(
        diagnosticError instanceof Error
          ? diagnosticError.message
          : 'No fue posible diagnosticar el dispositivo.',
      );
    } finally {
      setBusyDeviceId(null);
    }
  }, []);

  const testPrint = useCallback(async () => {
    setTestPrinting(true);
    setError('');

    try {
      await printLabel(buildTestPrintPayload());

      Alert.alert(
        'Prueba enviada',
        'Revisa la impresora física para confirmar el resultado.',
      );
    } catch (printError) {
      Alert.alert(
        'No fue posible imprimir',
        printError instanceof Error
          ? printError.message
          : 'Intenta nuevamente',
      );
    } finally {
      setTestPrinting(false);
    }
  }, []);

  const forget = useCallback(async () => {
    await printerManager.forget();
    setConnected(false);
    setPreferred(null);
  }, []);

  /**
   * SOLO QA/desarrollo.
   *
   * La prueba física anterior usaba únicamente una barra negra sólida.
   * Después de inspeccionar el SDK oficial V3 sabemos que esa prueba no
   * distingue correctamente:
   *
   *   zero_count
   *
   * de:
   *
   *   official_v3_white_counts
   *
   * porque una fila completamente negra produce contadores 00 00 00 en
   * ambos casos.
   *
   * Ahora usamos un raster diagnóstico de 384x64 que contiene:
   *
   * - negro completo;
   * - blanco completo;
   * - izquierda negra / derecha blanca;
   * - izquierda blanca / derecha negra.
   *
   * De esta forma la variante oficial genera contadores distintos de cero
   * y la comparación física sí puede discriminar el header.
   *
   * NUNCA pasa por printLabel()/printerManager.print().
   */
  const runQaRowHeaderTest = useCallback(
    async (variant: RowHeaderVariant) => {
      setQaTesting(variant);
      setError('');

      try {
        const raster = buildQaDiagnosticRaster();

        const packets = buildQaPrintJobPackets(
          raster,
          variant,
          { density: 3 },
        );

        await printerManager.printQaPacketSequence(packets);

        const variantDescription =
          variant === 'official_v3_white_counts'
            ? 'header oficial V3: conteos blancos por segmentos 192/192'
            : 'header legado: tres conteos en cero';

        Alert.alert(
          'Prueba de QA enviada',
          `Variante: ${variantDescription}.\n\n` +
            'Patrón esperado: cuatro bandas horizontales de 16 px cada una:\n\n' +
            '1. negra completa\n' +
            '2. blanca completa\n' +
            '3. izquierda negra / derecha blanca\n' +
            '4. izquierda blanca / derecha negra\n\n' +
            'Observa si aparece tinta y si las mitades se imprimen correctamente.',
        );
      } catch (qaError) {
        Alert.alert(
          'No fue posible enviar la prueba de QA',
          qaError instanceof Error
            ? qaError.message
            : 'Intenta nuevamente',
        );
      } finally {
        setQaTesting(null);
      }
    },
    [],
  );

  if (isLoading) return <LoadingState label="Cargando…" />;
  if (!user) return <Redirect href="/(auth)/login" />;
  if (!capabilities.canCaptureFieldSheets) {
    return <Redirect href="/(technician)" />;
  }

  return (
    <SafeAreaView style={styles.container}>
      <Screen>
        <BackButton />

        <ScrollView contentContainerStyle={styles.content}>
          <Text style={styles.title}>Impresora de etiquetas</Text>

          <Text style={styles.subtitle}>
            Etiqueta térmica 50×30 mm -- NIIMBOT B1 (soportada) y NELKO PM220
            (en validación).
          </Text>

          {!!error && (
            <AlertBanner tone="danger">
              {error}
            </AlertBanner>
          )}

          <Section title="Impresora guardada">
            {preferred ? (
              <Card>
                <Text style={styles.deviceName}>
                  {preferred.deviceName ?? preferred.deviceId}
                </Text>

                <StatusBadge
                  label={
                    connected
                      ? 'Conectada'
                      : 'Guardada, sin conectar'
                  }
                  tone={
                    connected
                      ? 'success'
                      : 'neutral'
                  }
                />

                <OperationalActionStack>
                  {!connected && (
                    <SecondaryButton
                      label="Reconectar"
                      icon="bluetooth-connect"
                      onPress={async () => {
                        setError('');

                        try {
                          const reconnected =
                            await printerManager.connectPreferred();

                          setConnected(reconnected);

                          if (!reconnected) {
                            setError(
                              'No fue posible reconectar la impresora guardada.',
                            );
                          }
                        } catch (reconnectError) {
                          setError(
                            reconnectError instanceof Error
                              ? reconnectError.message
                              : 'No fue posible reconectar.',
                          );
                        }
                      }}
                    />
                  )}

                  {connected && (
                    <PrimaryButton
                      label="Prueba de impresión"
                      icon="printer-check"
                      loading={testPrinting}
                      onPress={testPrint}
                    />
                  )}

                  {connected &&
                    preferred.adapterId === 'niimbot-b1' &&
                    user.actor_type === 'internal' && (
                      <>
                        <SecondaryButton
                          label="QA V3: header legado (dev)"
                          icon="flask-outline"
                          loading={qaTesting === 'zero_count'}
                          disabled={qaTesting !== null}
                          onPress={() =>
                            runQaRowHeaderTest('zero_count')
                          }
                        />

                        <SecondaryButton
                          label="QA V3: header oficial (dev)"
                          icon="flask-outline"
                          loading={
                            qaTesting ===
                            'official_v3_white_counts'
                          }
                          disabled={qaTesting !== null}
                          onPress={() =>
                            runQaRowHeaderTest(
                              'official_v3_white_counts',
                            )
                          }
                        />
                      </>
                    )}

                  <AdministrativeButton
                    label="Olvidar impresora"
                    icon="delete-outline"
                    onPress={forget}
                  />
                </OperationalActionStack>
              </Card>
            ) : (
              <EmptyState
                title="Sin impresora guardada"
                description="Busca y conecta una impresora para empezar a imprimir etiquetas."
              />
            )}
          </Section>

          <Section title="Buscar impresoras">
            <OperationalActionStack>
              <PrimaryButton
                label={
                  scanning
                    ? 'Buscando…'
                    : 'Buscar impresoras'
                }
                icon="magnify"
                loading={scanning}
                disabled={scanning}
                onPress={startScan}
              />
            </OperationalActionStack>

            {devices.map((classification) => (
              <Card key={classification.device.id}>
                <Text style={styles.deviceName}>
                  {classification.device.name ??
                    classification.device.id}
                </Text>

                <StatusBadge
                  label={
                    classification.family.supportStatus === 'supported'
                      ? `${classification.family.displayName} · Soportada`
                      : `${classification.family.displayName} · Driver pendiente`
                  }
                  tone={
                    classification.family.supportStatus === 'supported'
                      ? 'success'
                      : 'warning'
                  }
                />

                <OperationalActionStack>
                  {classification.family.supportStatus === 'supported' && (
                    <PrimaryButton
                      label="Conectar"
                      icon="bluetooth-connect"
                      loading={
                        busyDeviceId === classification.device.id
                      }
                      onPress={() =>
                        connectTo(classification)
                      }
                    />
                  )}

                  {classification.family.supportStatus ===
                    'protocol_pending' &&
                    user.actor_type === 'internal' && (
                      <SecondaryButton
                        label="Diagnóstico (dev)"
                        icon="stethoscope"
                        loading={
                          busyDeviceId === classification.device.id
                        }
                        onPress={() =>
                          runDiagnostics(classification)
                        }
                      />
                    )}
                </OperationalActionStack>
              </Card>
            ))}

            {!scanning && devices.length === 0 && (
              <EmptyState
                title="Sin resultados todavía"
                description="Enciende la impresora y mantenla cerca antes de buscar."
              />
            )}
          </Section>
        </ScrollView>
      </Screen>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  content: {
    padding: spacing.lg,
    gap: spacing.md,
  },
  title: {
    color: colors.text,
    fontSize: 22,
    fontWeight: '800',
  },
  subtitle: {
    color: colors.textSubtle,
  },
  deviceName: {
    color: colors.text,
    fontSize: 16,
    fontWeight: '700',
  },
});