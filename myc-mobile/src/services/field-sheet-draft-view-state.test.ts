import assert from 'node:assert/strict';
import test from 'node:test';

import {
  captureIsAlwaysReadOnly,
  initialViewMode,
  isFieldSheetEditable,
  viewModeAfterDraftSaved,
  viewModeAfterEditRequested,
} from './field-sheet-draft-view-state';

test('una hoja recién abierta/creada empieza en modo edición', () => {
  assert.equal(initialViewMode(), 'edit');
});

test('guardar borrador con éxito pasa a modo consulta (sólo lectura)', () => {
  assert.equal(viewModeAfterDraftSaved(), 'view');
});

test('"Editar" vuelve a habilitar los inputs', () => {
  assert.equal(viewModeAfterEditRequested(), 'edit');
});

test('completed siempre es de sólo lectura, sin importar el modo local', () => {
  assert.equal(captureIsAlwaysReadOnly('completed'), true);
  assert.equal(captureIsAlwaysReadOnly('draft'), false);
  assert.equal(captureIsAlwaysReadOnly('in_progress'), false);
});

test('isFieldSheetEditable combina status backend + modo local, backend manda', () => {
  assert.equal(isFieldSheetEditable('draft', 'edit'), true);
  assert.equal(isFieldSheetEditable('draft', 'view'), false);
  // completed nunca es editable aunque el modo local siga en "edit" (p.ej.
  // el usuario tocó "Editar" justo antes de que otro flujo completara la hoja).
  assert.equal(isFieldSheetEditable('completed', 'edit'), false);
});
