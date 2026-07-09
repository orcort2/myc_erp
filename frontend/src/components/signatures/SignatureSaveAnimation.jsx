import './signature.css';

export default function SignatureSaveAnimation({ label = 'Guardando firma...' }) {
  return (
    <div className="signature-save-animation">
      <div className="signature-save-stage">
        <svg className="signature-save-pen" viewBox="0 0 120 80" aria-hidden="true">
          <path
            className="signature-save-stroke"
            d="M14 48 C26 25, 40 26, 36 45 C34 61, 52 29, 59 45 C66 61, 80 34, 100 48"
          />
          <path className="signature-save-line" d="M14 62 H104" />
        </svg>
      </div>

      <span>{label}</span>
    </div>
  );
}