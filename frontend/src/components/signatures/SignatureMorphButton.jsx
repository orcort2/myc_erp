import { useState } from 'react';
import './signature.css';

export default function SignatureMorphButton({
  onOpen,
  disabled = false,
}) {
  const [isAnimating, setIsAnimating] = useState(false);

  function handleClick() {
    if (disabled || isAnimating) {
      return;
    }

    setIsAnimating(true);

    window.setTimeout(() => {
      onOpen?.();

      window.setTimeout(() => {
        setIsAnimating(false);
      }, 250);
    }, 430);
  }

  return (
    <button
      type="button"
      className={`signature-morph-button ${isAnimating ? 'active' : ''}`}
      onClick={handleClick}
      disabled={disabled}
      aria-label="Firmar orden de trabajo"
      title="Firmar orden de trabajo"
    >
      <svg
        className="signature-track-svg"
        viewBox="0 0 72 72"
        aria-hidden="true"
      >
        <rect
          className="signature-track-base"
          x="8"
          y="8"
          width="56"
          height="56"
          rx="16"
          ry="16"
        />

        <rect
          className="signature-track-progress"
          x="8"
          y="8"
          width="56"
          height="56"
          rx="16"
          ry="16"
          pathLength="101"
        />

        <circle
          className="signature-track-runner"
          r="4"
        />
      </svg>

      <svg
        className="signature-draw-icon"
        viewBox="0 0 72 72"
        aria-hidden="true"
      >
        <path
          className="signature-draw-path"
          d="M17 39
             C22 26, 29 24, 27 34
             C25 45, 35 27, 38 36
             C41 46, 48 32, 55 38"
        />

        <path
          className="signature-draw-underline"
          d="M18 50 H55"
        />
      </svg>
    </button>
  );
}