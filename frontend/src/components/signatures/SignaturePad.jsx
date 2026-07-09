import { useRef } from 'react';

export default function SignaturePad({
  label,
  name,
  signedAt,
  onNameChange,
  onSignatureChange,
}) {
  const canvasRef = useRef(null);
  const drawingRef = useRef(false);

  function getPoint(event) {
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const source = event.touches?.[0] ?? event;

    return {
      x: (source.clientX - rect.left) * (canvas.width / rect.width),
      y: (source.clientY - rect.top) * (canvas.height / rect.height),
    };
  }

  function beginDrawing(event) {
    event.preventDefault();

    const canvas = canvasRef.current;
    const context = canvas.getContext('2d');
    const point = getPoint(event);

    drawingRef.current = true;

    context.strokeStyle = '#0f172a';
    context.lineWidth = 2;
    context.lineCap = 'round';
    context.lineJoin = 'round';
    context.beginPath();
    context.moveTo(point.x, point.y);
  }

  function draw(event) {
    if (!drawingRef.current) return;

    event.preventDefault();

    const context = canvasRef.current.getContext('2d');
    const point = getPoint(event);

    context.lineTo(point.x, point.y);
    context.stroke();
  }

  function endDrawing() {
    if (!drawingRef.current) return;

    drawingRef.current = false;
    onSignatureChange(canvasRef.current.toDataURL('image/png'));
  }

  function clearSignature() {
    const canvas = canvasRef.current;
    canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height);
    onSignatureChange('');
  }

  return (
    <article className="ets-signature-card signature-pad-card">
      <div className="ets-signature-card__header">
        <div className="signature-pad-card__status">
          <span>{label}</span>
          <strong>
            {signedAt ? new Date(signedAt).toLocaleString('es-MX') : 'Pendiente'}
          </strong>
        </div>

        <button className="table-button" onClick={clearSignature} type="button">
          Limpiar
        </button>
      </div>

      <label className="signature-name-field">
        <span>Nombre</span>
        <input
          className="signature-name-input"
          onChange={(event) => onNameChange(event.target.value)}
          type="text"
          value={name}
        />
      </label>

      <div className="signature-canvas-field">
        <canvas
          aria-label={label}
          className="ets-signature-canvas signature-real-canvas"
          height="220"
          onMouseDown={beginDrawing}
          onMouseLeave={endDrawing}
          onMouseMove={draw}
          onMouseUp={endDrawing}
          onTouchCancel={endDrawing}
          onTouchEnd={endDrawing}
          onTouchMove={draw}
          onTouchStart={beginDrawing}
          ref={canvasRef}
          width="620"
        />
      </div>
    </article>
  );
}
