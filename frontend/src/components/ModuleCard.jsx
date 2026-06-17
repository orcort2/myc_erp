export function ModuleCard({ module }) {
  const Icon = module.icon;

  return (
    <article className="module-card" id={module.name}>
      <div className="module-card__header">
        <span className="module-card__icon">
          <Icon size={20} />
        </span>
        <span className="module-card__status">{module.status}</span>
      </div>
      <h2>{module.name}</h2>
      <p>{module.description}</p>
    </article>
  );
}

