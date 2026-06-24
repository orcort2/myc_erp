import { Building2, Download, Upload } from 'lucide-react';
import React, { useEffect, useState } from 'react';

import ConfirmDialog from '../components/ConfirmDialog.jsx';
import SelectionActionBar from '../components/SelectionActionBar.jsx';
import { emptyClientForm } from '../constants/forms.js';
import { clientModalTabs, clientTemplateColumns } from '../constants/templates.js';
import { createClient, createQuotation, deleteClient, listClients, updateClient } from '../services/api.js';
import useConfirmDialog from '../utils/useConfirmDialog.js';
import { downloadCsv, parseDelimitedText } from '../utils/csv.js';
import {
  buildClientImportPreview,
  getClientContact,
  getFirstValidationTab,
  getRowValue,
  toClientCreatePayload,
  toClientPayload,
  validateClientForm
} from '../utils/clients.js';

function ClientsPage() {
  const [clients, setClients] = useState([]);
  const [selectedClientIds, setSelectedClientIds] = useState([]);
  const [form, setForm] = useState(emptyClientForm);
  const [editingClientId, setEditingClientId] = useState(null);
  const [isClientModalOpen, setIsClientModalOpen] = useState(false);
  const [isClientImportOpen, setIsClientImportOpen] = useState(false);
  const [clientImportFileName, setClientImportFileName] = useState('');
  const [clientImportColumns, setClientImportColumns] = useState([]);
  const [clientImportPreview, setClientImportPreview] = useState(null);
  const [clientImportMessage, setClientImportMessage] = useState('');
  const [clientModalTab, setClientModalTab] = useState('general');
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [validationErrors, setValidationErrors] = useState({});
  const { confirmDialog, openConfirm, closeConfirm, handleConfirm } = useConfirmDialog();

  async function loadClients() {
    setError('');
    setIsLoading(true);
    try {
      const items = await listClients();
      setClients(Array.isArray(items) ? items : []);
      setSelectedClientIds([]);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadClients();
  }, []);

  function updateForm(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
    setValidationErrors((current) => {
      if (!current[field]) return current;
      const next = { ...current };
      delete next[field];
      return next;
    });
  }

  function resetForm() {
    setForm(emptyClientForm);
    setEditingClientId(null);
    setIsClientModalOpen(false);
    setClientModalTab('general');
    setValidationErrors({});
    setNotice('');
    setError('');
  }

  function closeClientImportModal() {
    setIsClientImportOpen(false);
    setClientImportFileName('');
    setClientImportColumns([]);
    setClientImportPreview(null);
    setClientImportMessage('');
    setError('');
  }

  function openNewClientModal() {
    setForm(emptyClientForm);
    setEditingClientId(null);
    setNotice('');
    setError('');
    setValidationErrors({});
    setClientModalTab('general');
    setIsClientModalOpen(true);
  }

  function startEdit(client) {
    const contact = getClientContact(client);
    setEditingClientId(client.id);
    setNotice('');
    setError('');
    setValidationErrors({});
    setClientModalTab('general');
    setIsClientModalOpen(true);
    setForm({
      commercialName: client.commercial_name ?? client.legal_name ?? '',
      rfc: client.rfc ?? '',
      contactName: contact?.name ?? '',
      phone: client.phone ?? contact?.phone ?? '',
      email: client.email ?? contact?.email ?? '',
      status: client.is_active ? 'Activo' : 'Inactivo',
      street: '',
      exteriorNumber: '',
      interiorNumber: '',
      neighborhood: '',
      city: '',
      addressState: '',
      postalCode: '',
      country: 'Mexico',
      fiscalLegalName: client.legal_name ?? '',
      fiscalRfc: client.rfc ?? '',
      fiscalPostalCode: '',
      taxRegime: client.tax_regime ?? '',
      cfdiUse: ''
    });
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    setNotice('');

    const nextValidationErrors = validateClientForm(form);
    if (Object.keys(nextValidationErrors).length) {
      setValidationErrors(nextValidationErrors);
      setClientModalTab(getFirstValidationTab(nextValidationErrors));
      return;
    }

    setIsSaving(true);

    try {
      if (editingClientId) {
        await updateClient(editingClientId, toClientPayload(form));
        setNotice('Cliente actualizado');
      } else {
        await createClient(toClientCreatePayload(form));
        setNotice('Cliente creado');
      }

      resetForm();
      await loadClients();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  async function handleCreateQuotation(client) {
    openConfirm({
      title: 'Crear cotización',
      message: `Se creará una nueva cotización para ${client.legal_name ?? client.commercial_name}.`,
      confirmText: 'Crear cotización',
      onConfirm: async () => {
        setError('');
        setNotice('');
        try {
          const quotation = await createQuotation({
            client_id: client.id,
            items: [],
            notes: `Cotización creada desde cliente ${client.legal_name ?? client.commercial_name}`
          });
          setNotice(`Cotización ${quotation.folio} creada para ${client.legal_name ?? client.commercial_name}`);
        } catch (requestError) {
          setError(requestError.message);
        }
      }
    });
  }

  async function handleDeactivateClient(client) {
    openConfirm({
      title: 'Dar de baja cliente',
      message: `Esta acción dará de baja el cliente ${client.legal_name ?? client.commercial_name}.\nNo se eliminará físicamente el registro.`,
      confirmText: 'Dar de baja cliente',
      variant: 'danger',
      onConfirm: async () => {
        setError('');
        setNotice('');
        setIsSaving(true);
        try {
          await deleteClient(client.id);
          if (editingClientId === client.id) resetForm();
          setNotice('Cliente dado de baja');
          await loadClients();
        } catch (requestError) {
          setError(requestError.message);
        } finally {
          setIsSaving(false);
        }
      }
    });
  }

  function toggleClientSelection(clientId) {
    setSelectedClientIds((current) =>
      current.includes(clientId)
        ? current.filter((id) => id !== clientId)
        : [...current, clientId]
    );
  }

  function clearClientSelection() {
    setSelectedClientIds([]);
  }

  const selectedClients = clients.filter((client) => selectedClientIds.includes(client.id));
  const selectedClient = selectedClients.length === 1 ? selectedClients[0] : null;

  function buildClientExportRows(items) {
    return items.map((client) => {
      const contact = getClientContact(client);
      return {
        'Nombre comercial': client.commercial_name ?? '',
        'Razon social': client.legal_name ?? '',
        RFC: client.rfc ?? '',
        'Contacto principal': contact?.name ?? '',
        Correo: client.email ?? contact?.email ?? '',
        Telefono: client.phone ?? contact?.phone ?? '',
        Pais: '',
        Calle: '',
        'Numero exterior': '',
        'Numero interior': '',
        Colonia: '',
        'Municipio / Ciudad': '',
        Estado: '',
        'Codigo postal': '',
        'Regimen fiscal': client.tax_regime ?? '',
        'Uso CFDI': '',
        'Estado del cliente': client.is_active ? 'Activo' : 'Inactivo'
      };
    });
  }

  function downloadClientTemplate() {
    downloadCsv('plantilla_clientes_myc.csv', clientTemplateColumns, [
      {
        'Nombre comercial': 'Cliente Demo',
        'Razon social': 'Cliente Demo SA de CV',
        RFC: 'CDE010101AB1',
        'Contacto principal': 'Contacto Compras',
        Correo: 'compras@cliente.com',
        Telefono: '5555555555',
        Pais: 'Mexico',
        Calle: 'Calle ejemplo',
        'Numero exterior': '100',
        'Numero interior': '',
        Colonia: 'Centro',
        'Municipio / Ciudad': 'Ciudad de Mexico',
        Estado: 'CDMX',
        'Codigo postal': '01000',
        'Regimen fiscal': '601',
        'Uso CFDI': 'G03',
        'Estado del cliente': 'Activo'
      }
    ]);
  }

  function exportClients() {
    downloadCsv('clientes_myc_export.csv', clientTemplateColumns, buildClientExportRows(clients));
  }

  function exportSelectedClients() {
    downloadCsv('clientes_myc_seleccionados.csv', clientTemplateColumns, buildClientExportRows(selectedClients));
  }

  function downloadClientImportErrors() {
    if (!clientImportPreview?.errors.length) return;

    const rows = clientImportPreview.errors.map((row) => ({
      ...row.raw,
      Errores: row.errors.join(' | ')
    }));

    downloadCsv('clientes_myc_errores.csv', [...clientImportColumns, 'Errores'], rows);
  }

  function handleClientImportFile(event) {
    const file = event.target.files?.[0];
    if (!file) return;

    setClientImportFileName(file.name);
    setClientImportMessage('');

    if (/\.(xlsx|xls)$/i.test(file.name)) {
      setClientImportColumns(clientTemplateColumns);
      setClientImportPreview(buildClientImportPreview([], clients));
      setClientImportMessage(
        'Archivo Excel recibido. La lectura real de XLSX se conectará cuando el backend o parser dedicado esté listo; por ahora usa CSV exportado desde Excel para vista previa.'
      );
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      const { columns, rows } = parseDelimitedText(String(reader.result ?? ''));
      setClientImportColumns(columns);
      setClientImportPreview(buildClientImportPreview(rows, clients));
    };
    reader.readAsText(file);
  }

  async function confirmClientImport() {
    const validRows = clientImportPreview?.valid ?? [];
    if (!validRows.length) return;

    setIsSaving(true);
    setError('');
    setClientImportMessage('');

    try {
      let imported = 0;
      const failed = [];

      for (const row of validRows) {
        const raw = row.raw;
        const commercialName = getRowValue(raw, ['Nombre comercial', 'nombre', 'Cliente']);
        const legalName = getRowValue(raw, ['Razon social', 'Razón social']);
        const contactName = getRowValue(raw, ['Contacto principal', 'Contacto']);
        const email = getRowValue(raw, ['Correo', 'Email']);
        const phone = getRowValue(raw, ['Telefono', 'Teléfono']);

        try {
          await createClient({
            commercial_name: commercialName.trim(),
            legal_name: legalName.trim() || commercialName.trim(),
            rfc: getRowValue(raw, ['RFC']).trim().toUpperCase() || null,
            email: email.trim() || null,
            phone: phone.trim() || null,
            tax_regime: getRowValue(raw, ['Regimen fiscal', 'Régimen fiscal']).trim() || null,
            contacts: contactName.trim()
              ? [
                  {
                    name: contactName.trim(),
                    email: email.trim() || null,
                    phone: phone.trim() || null,
                    position: null
                  }
                ]
              : []
          });
          imported += 1;
        } catch (requestError) {
          failed.push({ ...raw, Errores: requestError.message });
        }
      }

      if (failed.length) {
        downloadCsv('clientes_myc_importacion_fallida.csv', [...clientImportColumns, 'Errores'], failed);
      }

      setClientImportMessage(
        `Importación finalizada: ${imported} clientes creados${failed.length ? `, ${failed.length} con error` : ''}.`
      );

      await loadClients();
    } finally {
      setIsSaving(false);
    }
  }

  const modalTitle = editingClientId ? 'Editar cliente' : 'Nuevo cliente';

  return (
    <section className="module-workspace clients-workspace">
      <div className="module-workspace__hero clients-hero">
        <span className="module-workspace__icon">
          <Building2 size={28} />
        </span>
        <div>
          <p>Módulo MYC SYSTEM</p>
          <h1>Clientes</h1>
          <span>Base operativa para cotizaciones, órdenes de servicio y certificados.</span>
        </div>
      </div>

      {error && !isClientModalOpen ? <div className="form-error dashboard-error">{error}</div> : null}
      {notice ? <div className="form-notice dashboard-error">{notice}</div> : null}

      <section className="clients-list-panel">
        <div className="section-heading">
          <div>
            <p>Listado de clientes</p>
            <h2>{isLoading ? 'Cargando...' : `${clients.length} clientes`}</h2>
          </div>
          <div className="toolbar-actions">
            <button className="table-button" onClick={() => setIsClientImportOpen(true)} type="button">
              <Upload size={16} />
              Importar Excel
            </button>
            <button className="table-button" onClick={exportClients} type="button">
              <Download size={16} />
              Exportar Excel
            </button>
            <button className="table-button" onClick={downloadClientTemplate} type="button">
              <Download size={16} />
              Descargar plantilla
            </button>
            <button className="primary-button" onClick={openNewClientModal} type="button">
              Nuevo cliente
            </button>
          </div>
        </div>

        <SelectionActionBar
          selectedCount={selectedClientIds.length}
          onClear={clearClientSelection}
          actions={[
            ...(selectedClient
              ? [
                  { label: 'Editar', onClick: () => startEdit(selectedClient) },
                  { label: 'Cotización', onClick: () => handleCreateQuotation(selectedClient) },
                  {
                    label: 'Dar de baja',
                    variant: 'danger',
                    onClick: () => handleDeactivateClient(selectedClient)
                  }
                ]
              : []),
            ...(selectedClientIds.length > 1
              ? [{ label: 'Exportar seleccionados', onClick: exportSelectedClients }]
              : [])
          ]}
        />

        <div className="clients-table" aria-busy={isLoading}>
          <div className="clients-table__head">
            <span></span>
            <span>Cliente</span>
            <span>RFC</span>
            <span>Contacto</span>
            <span>Teléfono</span>
            <span>Correo</span>
            <span>Estado</span>
          </div>

          {isLoading ? (
            <div className="clients-empty">Cargando clientes...</div>
          ) : clients.length ? (
            clients.map((client) => {
              const contact = getClientContact(client);
              const isSelected = selectedClientIds.includes(client.id);

              return (
                <div
                  className={isSelected ? 'clients-table__row table-row--selected' : 'clients-table__row'}
                  key={client.id}
                >
                  <span>
                    <input
                      checked={isSelected}
                      className="row-selector"
                      onChange={() => toggleClientSelection(client.id)}
                      type="checkbox"
                    />
                  </span>
                  <span>{client.commercial_name || client.legal_name}</span>
                  <span>{client.rfc || '-'}</span>
                  <span>{contact?.name || '-'}</span>
                  <span>{client.phone || contact?.phone || '-'}</span>
                  <span>{client.email || contact?.email || '-'}</span>
                  <span>
                    <mark className={client.is_active ? 'status-pill' : 'status-pill status-pill--muted'}>
                      {client.is_active ? 'Activo' : 'Inactivo'}
                    </mark>
                  </span>
                </div>
              );
            })
          ) : (
            <div className="clients-empty">Todavía no hay clientes registrados.</div>
          )}
        </div>
      </section>

      {isClientModalOpen ? (
        <div className="modal-backdrop" role="presentation">
          <section className="client-modal" aria-modal="true" role="dialog">
            <div className="section-heading">
              <div>
                <p>Clientes</p>
                <h2>{modalTitle}</h2>
              </div>
            </div>

            {error ? <div className="form-error dashboard-error">{error}</div> : null}
            {Object.keys(validationErrors).length ? (
              <div className="form-error dashboard-error">Revisa los campos marcados antes de guardar.</div>
            ) : null}

            <div className="client-modal-tabs" role="tablist" aria-label="Secciones del cliente">
              {clientModalTabs.map((tab) => (
                <button
                  aria-selected={clientModalTab === tab.key}
                  className={clientModalTab === tab.key ? 'client-modal-tab is-active' : 'client-modal-tab'}
                  disabled={isSaving}
                  key={tab.key}
                  onClick={() => setClientModalTab(tab.key)}
                  type="button"
                >
                  {tab.label}
                </button>
              ))}
            </div>

            <form className="client-form client-form--modal" noValidate onSubmit={handleSubmit}>
              {clientModalTab === 'general' ? (
                <>
                  <label>
                    Nombre comercial
                    <input
                      aria-invalid={Boolean(validationErrors.commercialName)}
                      onChange={(event) => updateForm('commercialName', event.target.value)}
                      required
                      type="text"
                      value={form.commercialName}
                    />
                    {validationErrors.commercialName ? (
                      <span className="field-error">{validationErrors.commercialName}</span>
                    ) : null}
                  </label>

                  <label>
                    RFC
                    <input
                      aria-invalid={Boolean(validationErrors.rfc)}
                      maxLength={13}
                      onChange={(event) => updateForm('rfc', event.target.value.toUpperCase())}
                      required
                      type="text"
                      value={form.rfc}
                    />
                    {validationErrors.rfc ? <span className="field-error">{validationErrors.rfc}</span> : null}
                  </label>

                  <label>
                    Contacto
                    <input
                      disabled={Boolean(editingClientId)}
                      onChange={(event) => updateForm('contactName', event.target.value)}
                      type="text"
                      value={form.contactName}
                    />
                  </label>

                  <label>
                    Teléfono
                    <input onChange={(event) => updateForm('phone', event.target.value)} type="tel" value={form.phone} />
                  </label>

                  <label>
                    Correo
                    <input
                      aria-invalid={Boolean(validationErrors.email)}
                      onChange={(event) => updateForm('email', event.target.value)}
                      type="email"
                      value={form.email}
                    />
                    {validationErrors.email ? <span className="field-error">{validationErrors.email}</span> : null}
                  </label>

                  <label>
                    Estado
                    <select disabled onChange={(event) => updateForm('status', event.target.value)} value={form.status}>
                      <option>Activo</option>
                      <option>Inactivo</option>
                    </select>
                  </label>
                </>
              ) : null}

              {clientModalTab === 'address' ? (
                <>
                  <label>
                    Calle
                    <input onChange={(event) => updateForm('street', event.target.value)} type="text" value={form.street} />
                  </label>
                  <label>
                    Número exterior
                    <input
                      onChange={(event) => updateForm('exteriorNumber', event.target.value)}
                      type="text"
                      value={form.exteriorNumber}
                    />
                  </label>
                  <label>
                    Número interior
                    <input
                      onChange={(event) => updateForm('interiorNumber', event.target.value)}
                      type="text"
                      value={form.interiorNumber}
                    />
                  </label>
                  <label>
                    Colonia
                    <input
                      onChange={(event) => updateForm('neighborhood', event.target.value)}
                      type="text"
                      value={form.neighborhood}
                    />
                  </label>
                  <label>
                    Municipio / Ciudad
                    <input onChange={(event) => updateForm('city', event.target.value)} type="text" value={form.city} />
                  </label>
                  <label>
                    Estado
                    <input
                      onChange={(event) => updateForm('addressState', event.target.value)}
                      type="text"
                      value={form.addressState}
                    />
                  </label>
                  <label>
                    Código postal
                    <input
                      aria-invalid={Boolean(validationErrors.postalCode)}
                      inputMode="numeric"
                      onChange={(event) => updateForm('postalCode', event.target.value.replace(/\D/g, ''))}
                      type="text"
                      value={form.postalCode}
                    />
                    {validationErrors.postalCode ? (
                      <span className="field-error">{validationErrors.postalCode}</span>
                    ) : null}
                  </label>
                  <label>
                    País
                    <input onChange={(event) => updateForm('country', event.target.value)} type="text" value={form.country} />
                  </label>
                </>
              ) : null}

              {clientModalTab === 'fiscal' ? (
                <>
                  <label>
                    Razón social
                    <input
                      onChange={(event) => updateForm('fiscalLegalName', event.target.value)}
                      type="text"
                      value={form.fiscalLegalName}
                    />
                  </label>
                  <label>
                    RFC fiscal
                    <input
                      maxLength={13}
                      onChange={(event) => updateForm('fiscalRfc', event.target.value.toUpperCase())}
                      type="text"
                      value={form.fiscalRfc}
                    />
                  </label>
                  <label>
                    Código postal fiscal
                    <input
                      aria-invalid={Boolean(validationErrors.fiscalPostalCode)}
                      inputMode="numeric"
                      onChange={(event) => updateForm('fiscalPostalCode', event.target.value.replace(/\D/g, ''))}
                      type="text"
                      value={form.fiscalPostalCode}
                    />
                    {validationErrors.fiscalPostalCode ? (
                      <span className="field-error">{validationErrors.fiscalPostalCode}</span>
                    ) : null}
                  </label>
                  <label>
                    Régimen fiscal
                    <input
                      onChange={(event) => updateForm('taxRegime', event.target.value)}
                      type="text"
                      value={form.taxRegime}
                    />
                  </label>
                  <label>
                    Uso CFDI
                    <input onChange={(event) => updateForm('cfdiUse', event.target.value)} type="text" value={form.cfdiUse} />
                  </label>

                  <div className="client-form__visual-actions">
                    <button className="table-button" disabled={isSaving} type="button">
                      Subir constancia fiscal
                    </button>
                    <button className="table-button table-button--primary" disabled={isSaving} type="button">
                      Capturar manualmente
                    </button>
                  </div>

                  <div className="client-fiscal-note">Los datos fiscales completos se conectarán al módulo de facturación.</div>
                </>
              ) : null}

              <div className="client-form__actions client-form__actions--modal">
                <button className="icon-text-button" disabled={isSaving} onClick={resetForm} type="button">
                  Cancelar
                </button>
                <button className="primary-button" disabled={isSaving} type="submit">
                  {isSaving ? 'Guardando...' : editingClientId ? 'Guardar cambios' : 'Guardar cliente'}
                </button>
              </div>

              {editingClientId ? (
                <section className="danger-zone">
                  <div className="danger-zone__copy">
                    <p>Zona de baja</p>
                    <span>
                      Esta acción dará de baja el cliente. No se eliminará físicamente y el backend validará dependencias
                      activas.
                    </span>
                  </div>
                  <div className="toolbar-actions">
                    <button
                      className="table-button table-button--danger"
                      disabled={isSaving}
                      onClick={() =>
                        handleDeactivateClient({
                          id: editingClientId,
                          legal_name: form.fiscalLegalName || form.commercialName
                        })
                      }
                      type="button"
                    >
                      Dar de baja cliente
                    </button>
                  </div>
                </section>
              ) : null}
            </form>
          </section>
        </div>
      ) : null}

      {isClientImportOpen ? (
        <div className="modal-backdrop" role="presentation">
          <section className="client-modal import-modal" aria-modal="true" role="dialog">
            <div className="section-heading">
              <div>
                <p>Clientes</p>
                <h2>Importar clientes</h2>
              </div>
              <button className="icon-text-button" onClick={closeClientImportModal} type="button">
                Cerrar
              </button>
            </div>

            <div className="import-upload-zone">
              <label>
                Archivo Excel o CSV
                <input accept=".xlsx,.xls,.csv,.tsv" onChange={handleClientImportFile} type="file" />
              </label>
              <div>
                <strong>{clientImportFileName || 'Sin archivo seleccionado'}</strong>
                <span>La importación no se ejecuta automáticamente. Primero se revisa la vista previa.</span>
              </div>
            </div>

            {clientImportMessage ? <div className="client-fiscal-note">{clientImportMessage}</div> : null}

            <div className="import-template-grid">
              <article>
                <span>Columnas detectadas</span>
                <strong>{clientImportColumns.length}</strong>
              </article>
              <article>
                <span>Registros válidos</span>
                <strong>{clientImportPreview?.valid.length ?? 0}</strong>
              </article>
              <article>
                <span>Posibles duplicados</span>
                <strong>{clientImportPreview?.duplicates.length ?? 0}</strong>
              </article>
              <article>
                <span>Con errores</span>
                <strong>{clientImportPreview?.errors.length ?? 0}</strong>
              </article>
            </div>

            <section className="import-preview-section">
              <h3>Columnas esperadas / detectadas</h3>
              <div className="import-chip-list">
                {(clientImportColumns.length ? clientImportColumns : clientTemplateColumns).map((column) => (
                  <span key={column}>{column}</span>
                ))}
              </div>
            </section>

            <section className="import-preview-section">
              <h3>Vista previa</h3>
              <div className="import-preview-list">
                {clientImportPreview?.rows.length ? (
                  clientImportPreview.rows.slice(0, 8).map((row) => (
                    <article className={`import-row import-row--${row.status}`} key={row.id}>
                      <strong>{row.name}</strong>
                      <span>
                        {row.rfc} · {row.email}
                      </span>
                      <small>
                        {row.status === 'valid'
                          ? 'Válido'
                          : row.status === 'duplicate'
                            ? `Duplicado posible: ${row.duplicates.join(', ')}`
                            : row.errors.join(', ')}
                      </small>
                    </article>
                  ))
                ) : (
                  <div className="clients-empty">Sube un CSV exportado desde Excel para ver registros en esta versión.</div>
                )}
              </div>
            </section>

            <div className="client-form__actions client-form__actions--modal">
              <button className="table-button" disabled={!clientImportPreview?.errors.length} onClick={downloadClientImportErrors} type="button">
                Descargar errores
              </button>
              <button className="icon-text-button" onClick={closeClientImportModal} type="button">
                Cancelar
              </button>
              <button className="primary-button" disabled={!clientImportPreview?.valid.length} onClick={confirmClientImport} type="button">
                Confirmar importación
              </button>
            </div>
          </section>
        </div>
      ) : null}

      <ConfirmDialog
        cancelText={confirmDialog?.cancelText}
        confirmText={confirmDialog?.confirmText}
        isLoading={Boolean(confirmDialog?.isConfirming)}
        isOpen={Boolean(confirmDialog)}
        message={confirmDialog?.message}
        onClose={closeConfirm}
        onConfirm={handleConfirm}
        title={confirmDialog?.title}
        variant={confirmDialog?.variant}
      />
    </section>
  );
}

export default ClientsPage;