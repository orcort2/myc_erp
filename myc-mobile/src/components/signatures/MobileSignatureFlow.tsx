import { useEffect, useRef, useState } from 'react';
import {
  Animated,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import {
  ActionRow,
  PrimaryButton,
  SecondaryButton,
} from '@/src/design/primitives';
import { MobileSignaturePad } from './MobileSignaturePad';
import { SuccessTransition } from './StepTransition';
import {
  canContinueSignature,
  createSignaturePayload,
  SignatureSubmissionLock,
  type SignatureFlowState,
  type SignaturePayload,
  validateSignatureSubmission,
} from './signature-flow-state';

type Props = {
  currentContextId: number | null;
  onComplete(): void;
  onDrawingChange(active: boolean): void;
  onStateChange(state: SignatureFlowState): void;
  onSubmit(
    payload: SignaturePayload,
    capturedContextId: number,
  ): Promise<void>;
  state: SignatureFlowState;
};

const SUCCESS_CONFIRMATION_MS = 900;

export function MobileSignatureFlow({
  currentContextId,
  onComplete,
  onDrawingChange,
  onStateChange,
  onSubmit,
  state,
}: Props) {
  const [transitioning, setTransitioning] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const transitionOpacity = useRef(
    new Animated.Value(0),
  ).current;

  const submissionLock = useRef(
    new SignatureSubmissionLock(),
  );

  const transitioningRef = useRef(false);

  const transitionTimer =
    useRef<ReturnType<typeof setTimeout> | null>(null);

  const successTimer =
    useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(
    () => () => {
      if (transitionTimer.current) {
        clearTimeout(transitionTimer.current);
      }

      if (successTimer.current) {
        clearTimeout(successTimer.current);
      }

      onDrawingChange(false);
    },
    [onDrawingChange],
  );

  function continueToTechnician() {
    if (transitioningRef.current) return;

    if (
      !canContinueSignature(
        state.clientName,
        state.clientCapture,
      )
    ) {
      setError(
        !state.clientName.trim()
          ? 'Escribe el nombre del cliente.'
          : 'Captura la firma del cliente.',
      );

      return;
    }

    setError('');
    transitioningRef.current = true;

    onStateChange({
      ...state,
      step: 'technician',
    });

    setTransitioning(true);
    transitionOpacity.setValue(0);

    Animated.sequence([
      Animated.timing(transitionOpacity, {
        duration: 220,
        toValue: 1,
        useNativeDriver: true,
      }),
      Animated.delay(260),
      Animated.timing(transitionOpacity, {
        duration: 180,
        toValue: 0,
        useNativeDriver: true,
      }),
    ]).start();

    transitionTimer.current = setTimeout(() => {
      transitioningRef.current = false;
      setTransitioning(false);
    }, 680);
  }

  function returnToClient() {
    if (submitting) return;

    setError('');

    onStateChange({
      ...state,
      step: 'client',
    });
  }

  async function submit() {
    const validationError =
      validateSignatureSubmission({
        capturedContextId: state.rootWorkOrderId,
        clientCapture: state.clientCapture,
        clientName: state.clientName,
        currentContextId,
        isSubmitting:
          submissionLock.current.isSubmitting,
        technicianCapture:
          state.technicianCapture,
        technicianName:
          state.technicianName,
      });

    if (validationError) {
      setError(validationError);
      return;
    }

    if (!submissionLock.current.begin()) {
      return;
    }

    setError('');
    setSubmitting(true);

    try {
      /*
       * Cuando onSubmit resuelve, backend ya confirmó y
       * persistió ambas firmas.
       *
       * Conservamos una confirmación visual breve antes de
       * avisar al padre mediante onComplete para evitar que
       * el flujo desaparezca abruptamente.
       */
      await onSubmit(
        createSignaturePayload(
          state.clientName,
          state.clientCapture,
          state.technicianName,
          state.technicianCapture,
        ),
        state.rootWorkOrderId,
      );

      submissionLock.current.finish();
      setSubmitting(false);

      setSuccess(true);

      successTimer.current = setTimeout(() => {
        onComplete();
      }, SUCCESS_CONFIRMATION_MS);

      return;
    } catch (submitError) {
      setError(
        submitError instanceof Error
          ? submitError.message
          : 'No fue posible guardar las firmas. Intenta nuevamente.',
      );
    }

    submissionLock.current.finish();
    setSubmitting(false);
  }

  if (success) {
    return (
      <SuccessTransition
        subtitle="El cierre del grupo se aplicó correctamente."
        title="Firmas guardadas"
      />
    );
  }

  if (transitioning) {
    return (
      <View style={styles.transition}>
        <Animated.View
          style={[
            styles.transitionMark,
            { opacity: transitionOpacity },
          ]}
        >
          <Text style={styles.penStroke}>
            〰
          </Text>

          <View style={styles.transitionLine} />
        </Animated.View>

        <Text style={styles.transitionTitle}>
          Firma del cliente lista
        </Text>

        <Text style={styles.transitionText}>
          Preparando la firma del técnico…
        </Text>
      </View>
    );
  }

  const isClient = state.step === 'client';

  const name = isClient
    ? state.clientName
    : state.technicianName;

  const capture = isClient
    ? state.clientCapture
    : state.technicianCapture;

  const clientReady = canContinueSignature(
    state.clientName,
    state.clientCapture,
  );

  const technicianReady = canContinueSignature(
    state.technicianName,
    state.technicianCapture,
  );

  return (
    <View>
      <View style={styles.intro}>
        <Text style={styles.eyebrow}>
          CIERRE DEL GRUPO · PASO{' '}
          {isClient ? '1' : '2'} DE 2
        </Text>

        <Text style={styles.title}>
          Firma del{' '}
          {isClient ? 'cliente' : 'técnico'}
        </Text>

        <Text style={styles.description}>
          {isClient
            ? 'La firma del cliente confirma la recepción del grupo de OT LAB.'
            : 'Firma interna del técnico responsable. El guardado final enviará ambas firmas.'}
        </Text>
      </View>

      <View style={styles.nameCard}>
        <Text style={styles.nameLabel}>
          Nombre{' '}
          {isClient
            ? 'del cliente'
            : 'del técnico'}{' '}
          *
        </Text>

        <TextInput
          editable={!submitting}
          onChangeText={(value) => {
            setError('');

            onStateChange(
              isClient
                ? {
                    ...state,
                    clientName: value,
                  }
                : {
                    ...state,
                    technicianName: value,
                  },
            );
          }}
          placeholder={
            isClient
              ? 'Persona que recibe'
              : 'Técnico responsable'
          }
          style={styles.nameInput}
          value={name}
        />
      </View>

      <MobileSignaturePad
        capture={capture}
        disabled={submitting}
        key={
          isClient
            ? 'client-signature'
            : 'technician-signature'
        }
        label={
          isClient
            ? 'Firma Cliente'
            : 'Firma Técnico'
        }
        onChange={(nextCapture) => {
          setError('');

          onStateChange(
            isClient
              ? {
                  ...state,
                  clientCapture: nextCapture,
                }
              : {
                  ...state,
                  technicianCapture:
                    nextCapture,
                },
          );
        }}
        onDrawingChange={onDrawingChange}
      />

      {!!error && (
        <Text
          accessibilityRole="alert"
          style={styles.error}
        >
          {error}
        </Text>
      )}

      {isClient ? (
        <ActionRow>
          <PrimaryButton
            disabled={submitting || !clientReady}
            icon="arrow-right-circle"
            label="Continuar con técnico"
            onPress={continueToTechnician}
          />
        </ActionRow>
      ) : (
        <ActionRow>
          <SecondaryButton
            disabled={submitting}
            icon="arrow-left"
            label="Volver"
            onPress={returnToClient}
          />

          <PrimaryButton
            disabled={!technicianReady}
            icon="signature-freehand"
            label="Guardar firmas"
            loading={submitting}
            onPress={() => {
              void submit();
            }}
          />
        </ActionRow>
      )}

      <Text style={styles.groupNotice}>
        Una sola sesión se aplicará a todas las OT del
        grupo.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  description: {
    color: '#637280',
    fontSize: 15,
    lineHeight: 21,
  },

  error: {
    backgroundColor: '#fff0f0',
    borderRadius: 10,
    color: '#9b2637',
    marginTop: 12,
    padding: 12,
  },

  eyebrow: {
    color: '#08756f',
    fontSize: 12,
    fontWeight: '900',
    letterSpacing: 1,
    marginBottom: 7,
  },

  groupNotice: {
    color: '#5c6c76',
    fontSize: 12,
    marginTop: 14,
    textAlign: 'center',
  },

  intro: {
    marginBottom: 18,
  },

  nameCard: {
    backgroundColor: '#fff',
    borderColor: '#d6e1e6',
    borderRadius: 16,
    borderWidth: 1,
    marginBottom: 12,
    padding: 14,
  },

  nameInput: {
    backgroundColor: '#f8fafb',
    borderColor: '#aebfc8',
    borderRadius: 11,
    borderWidth: 1,
    fontSize: 16,
    minHeight: 50,
    paddingHorizontal: 14,
  },

  nameLabel: {
    color: '#344553',
    fontSize: 14,
    fontWeight: '800',
    marginBottom: 8,
  },

  penStroke: {
    color: '#46d8c4',
    fontSize: 58,
    fontWeight: '300',
  },

  title: {
    color: '#142b3a',
    fontSize: 26,
    fontWeight: '900',
    marginBottom: 8,
  },

  transition: {
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 390,
    padding: 30,
  },

  transitionLine: {
    backgroundColor: '#08756f',
    borderRadius: 2,
    height: 3,
    marginTop: -10,
    width: 110,
  },

  transitionMark: {
    alignItems: 'center',
    backgroundColor: '#082d35',
    borderRadius: 24,
    height: 130,
    justifyContent: 'center',
    marginBottom: 24,
    width: 170,
  },

  transitionText: {
    color: '#637280',
    fontSize: 14,
    marginTop: 8,
  },

  transitionTitle: {
    color: '#173746',
    fontSize: 21,
    fontWeight: '900',
  },
});