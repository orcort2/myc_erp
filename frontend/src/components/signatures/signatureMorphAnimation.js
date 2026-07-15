export const SIGNATURE_CLOSE_DURATION = 780;
export const SIGNATURE_ICON_FADE_DURATION = 240;

const SIGNATURE_SPRING_FREQUENCY = 9.5;
const SIGNATURE_SPRING_FRAMES = 56;

function interpolatingSpring(time) {
  const frequency = SIGNATURE_SPRING_FREQUENCY;
  const value = 1 - (1 + frequency * time) * Math.exp(-frequency * time);
  const endValue = 1 - (1 + frequency) * Math.exp(-frequency);

  return Math.min(Math.max(value / endValue, 0), 1);
}

function smoothstep(value) {
  const clamped = Math.min(Math.max(value, 0), 1);
  return clamped * clamped * (3 - 2 * clamped);
}

// Shared verbatim close trajectory used by the signature morph and LAB dialogs.
export function createGenieSpringKeyframes({
  closeX,
  closeY,
  finalScaleX,
  finalScaleY,
}) {
  return Array.from({ length: SIGNATURE_SPRING_FRAMES }, (_, index) => {
    const time = index / (SIGNATURE_SPRING_FRAMES - 1);
    const progress = interpolatingSpring(time);
    const widthProgress = progress ** 1.25;
    const heightProgress = progress ** 1.65;
    const fadeProgress = smoothstep((time - 0.78) / 0.22);
    const scaleX = 1 + (finalScaleX - 1) * widthProgress;
    const scaleY = 1 + (finalScaleY - 1) * heightProgress;
    const borderRadius = 28 + (20 - 28) * progress;

    return {
      offset: time,
      opacity: 1 - fadeProgress,
      borderRadius: `${borderRadius}px`,
      transform: `translate3d(${closeX * progress}px, ${
        closeY * progress
      }px, 0) scale3d(${scaleX}, ${scaleY}, 1)`,
    };
  });
}
