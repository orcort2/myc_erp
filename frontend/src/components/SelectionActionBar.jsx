import React from "react";
function SelectionActionBar({ selectedCount = 0, onClear, actions = [] }) {
  if (!selectedCount) {
    return null;
  }

  return (
    <div className="selection-action-bar">
      <div className="selection-action-bar__info">
        <strong>
          {selectedCount} {selectedCount === 1 ? 'seleccionado' : 'seleccionados'}
        </strong>

        <button className="ghost-button" type="button" onClick={onClear}>
          Limpiar
        </button>
      </div>

      <div className="selection-action-bar__actions">
        {actions.map((action) => (
          <button
            key={action.label}
            type="button"
            className={action.variant === 'danger' ? 'table-button table-button--danger' : 'table-button'}
            disabled={Boolean(action.disabled)}
            onClick={action.onClick}
          >
            {action.label}
          </button>
        ))}
      </div>
    </div>
  );
}

export default SelectionActionBar;