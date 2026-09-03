import { useEffect, useRef } from 'react';
import { Animated, StyleSheet, Text, View } from 'react-native';

/**
 * Confirmación visual breve compartida por cualquier wizard de firma/paso
 * (MobileSignatureFlow, LabDeliveryFlow, ...): checkmark en círculo +
 * título + subtítulo, con fade-in. Se muestra DESPUÉS de que el backend ya
 * confirmó -- nunca antes -- y el padre decide cuánto dura antes de
 * cerrarse (ver SUCCESS_CONFIRMATION_MS en cada wizard).
 */
export function SuccessTransition({ title, subtitle }: { title: string; subtitle: string }) {
  const opacity = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    opacity.setValue(0);
    Animated.timing(opacity, { duration: 220, toValue: 1, useNativeDriver: true }).start();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <Animated.View style={[styles.transition, { opacity }]}>
      <View style={[styles.transitionMark, styles.successMark]}>
        <Text style={styles.successCheck}>✓</Text>
      </View>
      <Text style={styles.transitionTitle}>{title}</Text>
      <Text style={styles.transitionText}>{subtitle}</Text>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  successCheck: { color: '#fff', fontSize: 52, fontWeight: '900' },
  successMark: { backgroundColor: '#08756f' },
  transition: { alignItems: 'center', justifyContent: 'center', minHeight: 390, padding: 30 },
  transitionMark: {
    alignItems: 'center',
    backgroundColor: '#082d35',
    borderRadius: 24,
    height: 130,
    justifyContent: 'center',
    marginBottom: 24,
    width: 170,
  },
  transitionText: { color: '#637280', fontSize: 14, marginTop: 8, textAlign: 'center' },
  transitionTitle: { color: '#173746', fontSize: 21, fontWeight: '900' },
});
