import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

import {
  groupTrayEntriesByBucket,
  trayEntryFromApi,
  type FieldSheetTrayEntry,
} from './field-sheets-tray';

function entry(bucket: FieldSheetTrayEntry['bucket'], id: number): FieldSheetTrayEntry {
  return {
    workOrderId: 10,
    workOrderFolio: 6400,
    equipmentId: id,
    instrument: 'Manómetro',
    certificateFolio: null,
    documentaryClient: 'Cliente documental',
    fieldSheetId: bucket === 'pending' ? null : id + 100,
    fieldSheetStatus: bucket === 'completed' ? 'completed' : bucket === 'in_progress' ? 'draft' : null,
    bucket,
    templateKey: bucket === 'pending' ? null : 'manometro',
    templateName: bucket === 'pending' ? null : 'Hoja de Campo Manómetro',
    progress: { completed: bucket === 'completed' ? 10 : 3, total: 10 },
  };
}

test('groupTrayEntriesByBucket presenta los buckets decididos por backend sin reclasificarlos', () => {
  const buckets = groupTrayEntriesByBucket([
    entry('pending', 1), entry('in_progress', 2), entry('completed', 3),
  ]);
  assert.deepEqual(buckets.pending.map((item) => item.equipmentId), [1]);
  assert.deepEqual(buckets.in_progress.map((item) => item.equipmentId), [2]);
  assert.deepEqual(buckets.completed.map((item) => item.equipmentId), [3]);
});

test('el agregado backend se transforma sin recalcular autoridad ni revisión en Mobile', () => {
  const mapped = trayEntryFromApi({
    work_order_id: 10, work_order_folio: 6400, work_order_status: 'in_progress',
    equipment_id: 7, instrument: 'Manómetro', brand: 'MYC', model: 'M-1',
    service_type: 'accredited', certificate_folio: 'MYCA-09-26-4700',
    documentary_client_display: 'Cliente documental', field_sheet_id: 9,
    field_sheet_status: 'in_progress', template_key: 'manometro',
    template_name: 'Hoja de Campo Manómetro', revision_number: 2, is_current: true,
    progress_completed: 3, progress_required: 10, bucket: 'in_progress',
  });
  assert.equal(mapped.workOrderId, 10);
  assert.equal(mapped.fieldSheetId, 9);
  assert.equal(mapped.documentaryClient, 'Cliente documental');
  assert.equal(mapped.bucket, 'in_progress');
  assert.deepEqual(mapped.progress, { completed: 3, total: 10 });
});

test('la pantalla consume una sola API agregada, sin fan-out por OT o FieldSheet', () => {
  const source = readFileSync('app/(technician)/field-sheets.tsx', 'utf8');
  assert.match(source, /\/mobile\/v1\/technician\/lab-field-sheets\?offset=0&limit=100/);
  assert.doesNotMatch(source, /Promise\.all/);
  assert.doesNotMatch(source, /lab-work-orders\/\$\{/);
  assert.match(source, /workOrderId: String\(entry\.workOrderId\)/);
});
