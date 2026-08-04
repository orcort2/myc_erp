export function ModuleCard({ module, count, isLoading = false, onOpen }) {
  const Icon = module.icon;
  const hasCount = typeof count === 'number';
  const statusClass = String(module.status || '')
    .trim()
    .toLowerCase()
    .replace(/\s+/g, '-');

  return (
    <button
      aria-label={`Abrir ${module.name}`}
      className="module-card"
      id={module.key}
      onClick={onOpen}
      type="button"
    >
      <span className="module-card__shine" aria-hidden="true" />

      <div className="module-card__header">
        <span className="module-card__icon" aria-hidden="true">
          <Icon size={20} />
        </span>
        <span className={`module-card__status status-${statusClass}`}>{module.status}</span>
      </div>

      <h2>{module.name}</h2>
      <p>{module.description}</p>

      {hasCount ? (
        <div className="module-card__footer" aria-label={`${count} registros`}>
          <strong>{isLoading ? '-' : count}</strong>
          <span>registros</span>
        </div>
      ) : null}
    </button>
  );
}
