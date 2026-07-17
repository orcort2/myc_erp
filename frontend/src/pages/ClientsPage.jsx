import { Building2, Download, FileSpreadsheet, Paperclip, Upload } from 'lucide-react';
import React, { useEffect, useMemo, useRef, useState } from 'react';

import ConfirmDialog from '../components/ConfirmDialog.jsx';
import SelectionActionBar from '../components/SelectionActionBar.jsx';
import SatCatalogField from '../components/invoice-workbench/SatCatalogField.jsx';
import { emptyClientForm } from '../constants/forms.js';
import { clientModalTabs, clientTemplateColumns } from '../constants/templates.js';
import {
  confirmClientImport,
  createClient,
  createClientCertificateProfile,
  createQuotation,
  deleteClient,
  deleteClientCertificateProfile,
  exportClients,
  getClientDeleteEligibility,
  listClients,
  listSatCatalogs,
  previewClientImport,
  previewClientTaxConstancy,
  restoreClient,
  updateClient,
  updateClientCertificateProfile,
  uploadClientTaxConstancy
} from '../services/api.js';
import useConfirmDialog from '../utils/useConfirmDialog.js';
import { downloadCsv } from '../utils/csv.js';
import {
  getClientContact,
  getFirstValidationTab,
  toClientCreatePayload,
  toClientPayload,
  validateClientForm
} from '../utils/clients.js';

function triggerBlobDownload(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

function normalizeImportRows(rows) {
  return Array.isArray(rows) ? rows : [];
}

function getClientTypeLabel(clientType) {
  return clientType === 'persona_fisica' ? 'Persona Física' : 'Persona Moral';
}

function getClientDisplayName(client) {
  return client.commercial_name || client.legal_name;
}

function getMissingClientFields(client) {
  const missing = [];
  if (!client.rfc) missing.push('RFC');
  if (!client.commercial_name) missing.push('Nombre comercial');
  if (!client.postal_code) missing.push('Código postal');
  if (!client.tax_regime) missing.push('Régimen fiscal');
  if (!client.tax_constancy_filename) missing.push('Constancia de situación fiscal');
  if (client.client_type === 'persona_fisica') {
    if (!client.curp) missing.push('CURP');
    if (!client.first_name || !client.first_last_name) missing.push('Nombre completo');
  } else if (!client.legal_name) {
    missing.push('Razón social');
  }
  return missing;
}

function ClientsPage() {
  const [clients, setClients] = useState([]);
  const [satCatalogs, setSatCatalogs] = useState([]);
  const [selectedClientIds, setSelectedClientIds] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('active');
  const [currentPage, setCurrentPage] = useState(1);
  const [form, setForm] = useState(emptyClientForm);
  const [editingClientId, setEditingClientId] = useState(null);
  const [pendingTaxConstancyFile, setPendingTaxConstancyFile] = useState(null);
  const [storedTaxConstancyName, setStoredTaxConstancyName] = useState('');
  const [taxConstancyMessage, setTaxConstancyMessage] = useState('');
  const [taxRegimeOptions, setTaxRegimeOptions] = useState([]);
  const [isClientModalOpen, setIsClientModalOpen] = useState(false);
  const [isClientImportOpen, setIsClientImportOpen] = useState(false);
  const [clientImportFileName, setClientImportFileName] = useState('');
  const [clientImportPreview, setClientImportPreview] = useState(null);
  const [clientImportSummary, setClientImportSummary] = useState(null);
  const [clientImportMessage, setClientImportMessage] = useState('');
  const [clientModalTab, setClientModalTab] = useState('general');
  const [certificateProfiles, setCertificateProfiles] = useState([]);
  const [editingCertificateProfileId, setEditingCertificateProfileId] = useState(null);
  const [certificateProfileForm, setCertificateProfileForm] = useState({
    label: '', company: '', address: '', attention: '', isDefault: false
  });
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [validationErrors, setValidationErrors] = useState({});
  const { confirmDialog, openConfirm, closeConfirm, handleConfirm } = useConfirmDialog();

  const importInputRef = useRef(null);
  const taxConstancyInputRef = useRef(null);
  const selectAllRef = useRef(null);

  async function loadClients() {
    setError('');
    setIsLoading(true);
    try {
      const items = await listClients({ includeInactive: true });
      setClients(Array.isArray(items) ? items : []);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadClients();
    listSatCatalogs().then((items) => setSatCatalogs(Array.isArray(items) ? items : [])).catch(() => setSatCatalogs([]));
  }, []);

  const satCatalogByCode = useMemo(
    () => new Map(satCatalogs.map((catalog) => [catalog.code, catalog])),
    [satCatalogs]
  );

  const visibleClients = useMemo(() => {
    const term = searchTerm.trim().toLowerCase();
    return clients.filter((client) => {
      const matchesStatus =
        statusFilter === 'all' ? true : statusFilter === 'inactive' ? !client.is_active : client.is_active;
      if (!matchesStatus) {
        return false;
      }
      if (!term) {
        return true;
      }
      const contact = getClientContact(client);
      return [
        client.commercial_name,
        client.legal_name,
        client.rfc,
        client.curp,
        client.email,
        client.phone,
        contact?.name,
        contact?.email
      ]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(term));
    });
  }, [clients, searchTerm, statusFilter]);

  const clientsPerPage = 50;
  const totalClientPages = Math.max(1, Math.ceil(visibleClients.length / clientsPerPage));
  const normalizedCurrentPage = Math.min(currentPage, totalClientPages);
  const pageStartIndex = (normalizedCurrentPage - 1) * clientsPerPage;
  const pageEndIndex = pageStartIndex + clientsPerPage;

  const paginatedClients = useMemo(
    () => visibleClients.slice(pageStartIndex, pageEndIndex),
    [visibleClients, pageStartIndex, pageEndIndex]
  );

  const visibleClientIds = useMemo(() => paginatedClients.map((client) => client.id), [paginatedClients]);
  const selectedClients = useMemo(
    () => clients.filter((client) => selectedClientIds.includes(client.id)),
    [clients, selectedClientIds]
  );
  const selectedClient = selectedClients.length === 1 ? selectedClients[0] : null;
  const allVisibleSelected = visibleClientIds.length > 0 && visibleClientIds.every((id) => selectedClientIds.includes(id));
  const someVisibleSelected = visibleClientIds.some((id) => selectedClientIds.includes(id));
  const allFilteredClientsSelected =
    visibleClients.length > 0 && visibleClients.every((client) => selectedClientIds.includes(client.id));
  const canSelectAllFilteredClients =
    allVisibleSelected && visibleClients.length > visibleClientIds.length && !allFilteredClientsSelected;

  const paginationStart = visibleClients.length ? pageStartIndex + 1 : 0;
  const paginationEnd = Math.min(pageEndIndex, visibleClients.length);
  const paginationLabel = visibleClients.length
    ? `Mostrando ${paginationStart}-${paginationEnd} de ${visibleClients.length} clientes`
    : 'Sin clientes para mostrar';

  const pageNumbers = useMemo(() => {
    const pages = [];
    const start = Math.max(1, normalizedCurrentPage - 2);
    const end = Math.min(totalClientPages, normalizedCurrentPage + 2);

    for (let page = start; page <= end; page += 1) {
      pages.push(page);
    }

    return pages;
  }, [normalizedCurrentPage, totalClientPages]);

  useEffect(() => {
    if (selectAllRef.current) {
      selectAllRef.current.indeterminate = !allVisibleSelected && someVisibleSelected;
    }
  }, [allVisibleSelected, someVisibleSelected]);

  useEffect(() => {
    setCurrentPage(1);
    setSelectedClientIds([]);
  }, [searchTerm, statusFilter]);

  useEffect(() => {
    if (currentPage > totalClientPages) {
      setCurrentPage(totalClientPages);
    }
  }, [currentPage, totalClientPages]);

  function goToClientPage(page) {
    const nextPage = Math.min(Math.max(page, 1), totalClientPages);
    setCurrentPage(nextPage);
  }

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
    setPendingTaxConstancyFile(null);
    setStoredTaxConstancyName('');
    setTaxConstancyMessage('');
    setTaxRegimeOptions([]);
    setIsClientModalOpen(false);
    setClientModalTab('general');
    setValidationErrors({});
    setCertificateProfiles([]);
    setEditingCertificateProfileId(null);
    setNotice('');
    setError('');
  }

  function closeClientImportModal() {
    setIsClientImportOpen(false);
    setClientImportFileName('');
    setClientImportPreview(null);
    setClientImportSummary(null);
    setClientImportMessage('');
    setError('');
  }

  function openNewClientModal() {
    setForm(emptyClientForm);
    setEditingClientId(null);
    setPendingTaxConstancyFile(null);
    setStoredTaxConstancyName('');
    setTaxConstancyMessage('');
    setTaxRegimeOptions([]);
    setNotice('');
    setError('');
    setValidationErrors({});
    setClientModalTab('general');
    setCertificateProfiles([]);
    setEditingCertificateProfileId(null);
    setIsClientModalOpen(true);
  }

  function loadClientIntoForm(client, { keepTab = true } = {}) {
    const contact = getClientContact(client);

    setEditingClientId(client.id);
    setNotice('');
    setError('');
    setValidationErrors({});

    if (!keepTab) {
      setClientModalTab('general');
    }

    setPendingTaxConstancyFile(null);
    setStoredTaxConstancyName(client.tax_constancy_filename || '');
    setTaxConstancyMessage('');
    setTaxRegimeOptions([]);
    setIsClientModalOpen(true);
    setCertificateProfiles((client.certificate_profiles ?? []).filter((profile) => profile.is_active !== false));
    setEditingCertificateProfileId(null);

    setForm({
      clientType: client.client_type ?? 'persona_moral',
      legalName: client.legal_name ?? '',
      commercialName: client.commercial_name ?? client.legal_name ?? '',
      rfc: client.rfc ?? '',
      curp: client.curp ?? '',
      firstName: client.first_name ?? '',
      firstLastName: client.first_last_name ?? '',
      secondLastName: client.second_last_name ?? '',
      contactName: contact?.name ?? '',
      phone: client.phone ?? contact?.phone ?? '',
      email: client.email ?? contact?.email ?? '',
      status: client.is_active ? 'Activo' : 'Inactivo',
      streetType: client.street_type ?? '',
      street: client.street ?? '',
      exteriorNumber: client.exterior_number ?? '',
      interiorNumber: client.interior_number ?? '',
      neighborhood: client.neighborhood ?? '',
      locality: client.locality ?? '',
      municipality: client.municipality ?? client.city ?? '',
      city: client.city ?? '',
      addressState: client.state ?? '',
      postalCode: client.postal_code ?? '',
      country: client.country ?? 'Mexico',
      fiscalLegalName: client.legal_name ?? '',
      fiscalRfc: client.rfc ?? '',
      fiscalPostalCode: client.fiscal_postal_code ?? '',
      taxRegime: client.tax_regime ?? '',
      cfdiUse: client.cfdi_use ?? '',
      fiscalCountryCode: client.fiscal_country_code ?? 'MEX'
    });
  }

  function resetCertificateProfileForm() {
    setEditingCertificateProfileId(null);
    setCertificateProfileForm({ label: '', company: '', address: '', attention: '', isDefault: false });
  }

  function editCertificateProfile(profile) {
    setEditingCertificateProfileId(profile.id);
    setCertificateProfileForm({
      label: profile.label ?? '',
      company: profile.company ?? '',
      address: profile.address ?? '',
      attention: profile.attention ?? '',
      isDefault: Boolean(profile.is_default),
    });
  }

  async function saveCertificateProfile() {
    if (!editingClientId) return;
    const payload = {
      label: certificateProfileForm.label.trim(),
      company: certificateProfileForm.company.trim(),
      address: certificateProfileForm.address.trim(),
      attention: certificateProfileForm.attention.trim() || null,
      is_default: Boolean(certificateProfileForm.isDefault),
    };
    if (!payload.label || !payload.company || !payload.address) {
      setError('Captura nombre, empresa y domicilio del dato para certificado.');
      return;
    }
    setIsSaving(true);
    setError('');
    try {
      const saved = editingCertificateProfileId
        ? await updateClientCertificateProfile(editingClientId, editingCertificateProfileId, payload)
        : await createClientCertificateProfile(editingClientId, payload);
      setCertificateProfiles((current) => {
        const normalized = saved.is_default
          ? current.map((profile) => ({ ...profile, is_default: false }))
          : current;
        return normalized.some((profile) => profile.id === saved.id)
          ? normalized.map((profile) => (profile.id === saved.id ? saved : profile))
          : [...normalized, saved];
      });
      setClients((current) => current.map((client) => client.id === editingClientId
        ? { ...client, certificate_profiles: (() => {
          const profiles = saved.is_default
            ? (client.certificate_profiles ?? []).map((profile) => ({ ...profile, is_default: false }))
            : (client.certificate_profiles ?? []);
          return profiles.some((profile) => profile.id === saved.id)
            ? profiles.map((profile) => (profile.id === saved.id ? saved : profile))
            : [...profiles, saved];
        })() }
        : client));
      resetCertificateProfileForm();
      setNotice('Dato para certificado guardado');
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  async function removeCertificateProfile(profile) {
    if (!editingClientId) return;
    setIsSaving(true);
    setError('');
    try {
      await deleteClientCertificateProfile(editingClientId, profile.id);
      setCertificateProfiles((current) => current.filter((item) => item.id !== profile.id));
      setClients((current) => current.map((client) => client.id === editingClientId
        ? { ...client, certificate_profiles: (client.certificate_profiles ?? []).filter((item) => item.id !== profile.id) }
        : client));
      if (editingCertificateProfileId === profile.id) resetCertificateProfileForm();
      setNotice('Dato para certificado eliminado');
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  function startEdit(client) {
    loadClientIntoForm(client, { keepTab: false });
  }

  async function saveCurrentClient() {
    setError('');
    setNotice('');

    const nextValidationErrors = validateClientForm(form);

    if (Object.keys(nextValidationErrors).length) {
      setValidationErrors(nextValidationErrors);
      setClientModalTab(getFirstValidationTab(nextValidationErrors));
      return null;
    }

    setIsSaving(true);

    try {
      const payload = editingClientId ? toClientPayload(form) : toClientCreatePayload(form);

      let savedClient = editingClientId
        ? await updateClient(editingClientId, payload)
        : await createClient(payload);

      if (pendingTaxConstancyFile) {
        savedClient = await uploadClientTaxConstancy(savedClient.id, pendingTaxConstancyFile);
      }

      setClients((current) => {
        const exists = current.some((client) => client.id === savedClient.id);

        if (!exists) {
          return [savedClient, ...current];
        }

        return current.map((client) => (client.id === savedClient.id ? savedClient : client));
      });

      setEditingClientId(savedClient.id);
      setPendingTaxConstancyFile(null);
      setStoredTaxConstancyName(savedClient.tax_constancy_filename || storedTaxConstancyName || '');
      setTaxConstancyMessage('');
      setNotice('Guardado automáticamente');

      return savedClient;
    } catch (requestError) {
      setError(requestError.message);
      return null;
    } finally {
      setIsSaving(false);
    }
  }

  async function navigateClient(direction) {
    if (!editingClientId || !visibleClients.length || isSaving) return;

    const currentIndex = visibleClients.findIndex((client) => client.id === editingClientId);

    if (currentIndex === -1) return;

    const savedClient = await saveCurrentClient();

    if (!savedClient) return;

    const nextIndex =
      direction === 'next'
        ? (currentIndex + 1) % visibleClients.length
        : (currentIndex - 1 + visibleClients.length) % visibleClients.length;

    const nextClient = visibleClients[nextIndex];

    if (nextClient) {
      loadClientIntoForm(nextClient, { keepTab: true });
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();

    const savedClient = await saveCurrentClient();

    if (!savedClient) return;

    setNotice(editingClientId ? 'Cliente actualizado' : 'Cliente creado');
    resetForm();
    await loadClients();
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
    let eligibility;
    try {
      eligibility = await getClientDeleteEligibility(client.id);
    } catch (requestError) {
      setError(requestError.message);
      return;
    }
    const blockers = Object.entries(eligibility.blocking_dependencies ?? {})
      .filter(([, count]) => count)
      .map(([name, count]) => `${name}: ${count}`)
      .join(', ');
    const hardDelete = eligibility.eligible_for_hard_delete;
    openConfirm({
      title: hardDelete ? 'Eliminar definitivamente' : 'Archivar cliente',
      message: hardDelete
        ? `Este cliente no tiene historial y se eliminará definitivamente.`
        : `Este cliente tiene historial y será archivado. Dependencias: ${blockers}.`,
      confirmText: hardDelete ? 'Eliminar definitivamente' : 'Archivar cliente',
      variant: 'danger',
      onConfirm: async () => {
        setError('');
        setNotice('');
        setIsSaving(true);
        try {
          const result = await deleteClient(client.id);
          if (editingClientId === client.id) resetForm();
          setNotice(result?.message ?? (hardDelete ? 'Cliente eliminado definitivamente' : 'Cliente archivado'));
          await loadClients();
        } catch (requestError) {
          setError(requestError.message);
        } finally {
          setIsSaving(false);
        }
      }
    });
  }

  async function handleRestoreClient(client) {
    openConfirm({
      title: 'Restaurar cliente',
      message: `El cliente ${client.legal_name ?? client.commercial_name} volverá a estar activo.`,
      confirmText: 'Restaurar cliente',
      onConfirm: async () => {
        setError('');
        setNotice('');
        setIsSaving(true);
        try {
          await restoreClient(client.id);
          setNotice('Cliente restaurado');
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
      current.includes(clientId) ? current.filter((id) => id !== clientId) : [...current, clientId]
    );
  }

  function toggleSelectAllVisible() {
    setSelectedClientIds((current) => {
      if (allVisibleSelected) {
        return current.filter((id) => !visibleClientIds.includes(id));
      }
      const next = new Set(current);
      visibleClientIds.forEach((id) => next.add(id));
      return Array.from(next);
    });
  }

  function selectAllFilteredClients() {
    setSelectedClientIds(visibleClients.map((client) => client.id));
    setNotice(`${visibleClients.length} clientes seleccionados para exportar.`);
  }

  function clearClientSelection() {
    setSelectedClientIds([]);
  }

  async function handleBulkDeleteClients() {
    if (!selectedClients.length) return;
    openConfirm({
      title: 'Archivar clientes',
      message: `Se archivarán ${selectedClients.length} clientes visibles seleccionados.`,
      confirmText: 'Archivar seleccionados',
      variant: 'danger',
      onConfirm: async () => {
        setError('');
        setNotice('');
        setIsSaving(true);
        try {
          for (const client of selectedClients) {
            await deleteClient(client.id);
          }
          clearClientSelection();
          setNotice(`${selectedClients.length} clientes archivados`);
          await loadClients();
        } catch (requestError) {
          setError(requestError.message);
        } finally {
          setIsSaving(false);
        }
      }
    });
  }

  function buildClientExportRows(items) {
    return items.map((client) => {
      const contact = getClientContact(client);
      return {
        tipo_cliente: client.client_type === 'persona_fisica' ? 'Persona Física' : 'Persona Moral',
        nombre_comercial: client.commercial_name ?? '',
        razon_social: client.legal_name ?? '',
        curp: client.curp ?? '',
        nombres: client.first_name ?? '',
        primer_apellido: client.first_last_name ?? '',
        segundo_apellido: client.second_last_name ?? '',
        rfc: client.rfc ?? '',
        contacto: contact?.name ?? '',
        telefono: client.phone ?? contact?.phone ?? '',
        correo: client.email ?? contact?.email ?? '',
        pais: client.country ?? '',
        tipo_vialidad: client.street_type ?? '',
        calle: client.street ?? '',
        numero_exterior: client.exterior_number ?? '',
        numero_interior: client.interior_number ?? '',
        colonia: client.neighborhood ?? '',
        localidad: client.locality ?? '',
        municipio: client.municipality ?? client.city ?? '',
        municipio_ciudad: client.city ?? '',
        estado: client.state ?? '',
        codigo_postal: client.postal_code ?? '',
        regimen_fiscal: client.tax_regime ?? '',
        uso_cfdi: client.cfdi_use ?? '',
        estado_cliente: client.is_active ? 'Activo' : 'Inactivo'
      };
    });
  }

  function downloadClientTemplate() {
    downloadCsv('plantilla_clientes_myc.csv', clientTemplateColumns, [
      {
        tipo_cliente: 'Persona Moral',
        nombre_comercial: 'Cliente Demo',
        razon_social: 'Cliente Demo SA de CV',
        curp: '',
        nombres: '',
        primer_apellido: '',
        segundo_apellido: '',
        rfc: 'CDE010101AB1',
        contacto: 'Contacto Compras',
        telefono: '5555555555',
        correo: 'compras@cliente.com',
        pais: 'Mexico',
        tipo_vialidad: 'Calle',
        calle: 'Calle ejemplo',
        numero_exterior: '100',
        numero_interior: '',
        colonia: 'Centro',
        localidad: 'Centro',
        municipio: 'Ciudad de Mexico',
        municipio_ciudad: 'Ciudad de Mexico',
        estado: 'CDMX',
        codigo_postal: '01000',
        regimen_fiscal: '601',
        uso_cfdi: 'G03',
        estado_cliente: 'Activo'
      }
    ]);
  }

  async function handleExportClients() {
    try {
      const result = await exportClients({
        search: searchTerm.trim(),
        status: statusFilter
      });
      triggerBlobDownload(result.blob, result.filename || 'clientes_myc_export.xlsx');
      setNotice(`Exportación lista: ${visibleClients.length} clientes visibles.`);
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  function exportSelectedClients() {
    downloadCsv('clientes_myc_seleccionados.csv', clientTemplateColumns, buildClientExportRows(selectedClients));
  }

  async function handleClientImportFile(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    setClientImportFileName(file.name);
    setClientImportMessage('');
    setClientImportSummary(null);
    setClientImportPreview(null);
    setIsSaving(true);
    try {
      const preview = await previewClientImport(file);
      setClientImportPreview(preview);
      setClientImportMessage(
        `Archivo validado. Importables: ${preview.valid_count ?? 0} (${preview.warning_count ?? 0} con advertencias). Duplicados: ${preview.duplicate_count ?? 0}. Errores: ${preview.error_count ?? 0}.`
      );
    } catch (requestError) {
      setClientImportPreview(null);
      setClientImportMessage('');
      setError(requestError.message);
    } finally {
      setIsSaving(false);
      event.target.value = '';
    }
  }

  async function handleTaxConstancyFile(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    setPendingTaxConstancyFile(file);
    setStoredTaxConstancyName(file.name);
    setTaxConstancyMessage('Analizando constancia fiscal...');
    setTaxRegimeOptions([]);
    setIsSaving(true);
    try {
      const preview = await previewClientTaxConstancy(file);
      if (preview.extracted_client_type) {
        updateForm('clientType', preview.extracted_client_type);
      }
      if (preview.extracted_legal_name) {
        updateForm('fiscalLegalName', preview.extracted_legal_name);
        updateForm('legalName', preview.extracted_legal_name);
      }
      if (preview.extracted_commercial_name) {
        updateForm('commercialName', preview.extracted_commercial_name);
      }
      if (preview.extracted_rfc) {
        updateForm('fiscalRfc', preview.extracted_rfc);
        updateForm('rfc', preview.extracted_rfc);
      }
      if (preview.extracted_curp) {
        updateForm('curp', preview.extracted_curp);
      }
      if (preview.extracted_first_name) {
        updateForm('firstName', preview.extracted_first_name);
      }
      if (preview.extracted_first_last_name) {
        updateForm('firstLastName', preview.extracted_first_last_name);
      }
      if (preview.extracted_second_last_name) {
        updateForm('secondLastName', preview.extracted_second_last_name);
      }
      if (preview.extracted_fiscal_postal_code) {
        updateForm('fiscalPostalCode', preview.extracted_fiscal_postal_code);
        updateForm('postalCode', preview.extracted_fiscal_postal_code);
      }
      if (preview.extracted_street_type) {
        updateForm('streetType', preview.extracted_street_type);
      }
      if (preview.extracted_street) {
        updateForm('street', preview.extracted_street);
      }
      if (preview.extracted_exterior_number) {
        updateForm('exteriorNumber', preview.extracted_exterior_number);
      }
      if (preview.extracted_interior_number) {
        updateForm('interiorNumber', preview.extracted_interior_number);
      }
      if (preview.extracted_neighborhood) {
        updateForm('neighborhood', preview.extracted_neighborhood);
      }
      if (preview.extracted_locality) {
        updateForm('locality', preview.extracted_locality);
      }
      if (preview.extracted_municipality) {
        updateForm('municipality', preview.extracted_municipality);
        updateForm('city', preview.extracted_municipality);
      }
      if (preview.extracted_state) {
        updateForm('addressState', preview.extracted_state);
      }
      if (preview.extracted_tax_regime) {
        updateForm('taxRegime', preview.extracted_tax_regime);
      }
      setTaxRegimeOptions(Array.isArray(preview.extracted_tax_regimes) ? preview.extracted_tax_regimes : []);
      setTaxConstancyMessage(preview.message);
    } catch (requestError) {
      setTaxConstancyMessage(requestError.message);
    } finally {
      setIsSaving(false);
      event.target.value = '';
    }
  }

  function discardPendingTaxConstancy() {
    setPendingTaxConstancyFile(null);
    setStoredTaxConstancyName('');
    setTaxConstancyMessage('');
    setTaxRegimeOptions([]);
    if (taxConstancyInputRef.current) {
      taxConstancyInputRef.current.value = '';
    }
  }

  async function confirmImportAction() {
    const rows = normalizeImportRows(clientImportPreview?.rows).map((row) => row.raw);
    if (!rows.length) return;
    setIsSaving(true);
    setError('');
    setNotice('');
    try {
      const result = await confirmClientImport(rows);
      setClientImportSummary(result);
      setClientImportMessage(
        `Importación finalizada: ${result.imported_count} importados (${result.imported_with_warnings_count ?? 0} con advertencias), ${result.duplicate_count} duplicados y ${result.error_count} errores.`
      );
      await loadClients();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  const modalTitle = editingClientId ? 'Editar cliente' : 'Nuevo cliente';

  const currentClientIndex = editingClientId
    ? visibleClients.findIndex((client) => client.id === editingClientId)
    : -1;

  const modalNavigatorLabel =
    editingClientId && currentClientIndex >= 0
      ? `${currentClientIndex + 1} de ${visibleClients.length}`
      : '';

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
            <h2>{isLoading ? 'Cargando...' : paginationLabel}</h2>
          </div>
          <div className="toolbar-actions">
            <button className="table-button" onClick={() => setIsClientImportOpen(true)} type="button">
              <Upload size={16} />
              Importar clientes
            </button>
            <button className="table-button" onClick={handleExportClients} type="button">
              <Download size={16} />
              Exportar Excel
            </button>
            <button className="table-button" onClick={downloadClientTemplate} type="button">
              <FileSpreadsheet size={16} />
              Descargar plantilla
            </button>
            <button className="primary-button" onClick={openNewClientModal} type="button">
              Nuevo cliente
            </button>
          </div>
        </div>

        <div className="catalog-filters clients-filters">
          <label>
            Buscar
            <input
              onChange={(event) => setSearchTerm(event.target.value)}
              placeholder="Cliente, RFC, contacto o correo"
              type="search"
              value={searchTerm}
            />
          </label>
          <label>
            Estado
            <select onChange={(event) => setStatusFilter(event.target.value)} value={statusFilter}>
              <option value="active">Activos</option>
              <option value="inactive">Inactivos</option>
              <option value="all">Todos</option>
            </select>
          </label>
        </div>

        <SelectionActionBar
          selectedCount={selectedClients.length}
          onClear={clearClientSelection}
          actions={[
            ...(canSelectAllFilteredClients
              ? [
                  {
                    label: `Seleccionar todos (${visibleClients.length})`,
                    onClick: selectAllFilteredClients
                  }
                ]
              : []),
            ...(selectedClient
              ? [
                  { label: 'Editar', onClick: () => startEdit(selectedClient) },
                  ...(selectedClient.is_active
                    ? [
                        { label: 'Cotización', onClick: () => handleCreateQuotation(selectedClient) },
                        { label: 'Archivar', variant: 'danger', onClick: () => handleDeactivateClient(selectedClient) }
                      ]
                    : [{ label: 'Restaurar', onClick: () => handleRestoreClient(selectedClient) }])
                ]
              : []),
            ...(selectedClients.length > 1
              ? [
                  { label: 'Exportar seleccionados', onClick: exportSelectedClients },
                  { label: 'Eliminar', variant: 'danger', onClick: handleBulkDeleteClients }
                ]
              : [])
          ]}
        />

        <div className="clients-table clients-table--clickable" aria-busy={isLoading}>
          <div className="clients-table__head">
            <span>
              <input
                aria-label="Seleccionar todos los clientes visibles"
                checked={allVisibleSelected}
                className="row-selector"
                onChange={toggleSelectAllVisible}
                ref={selectAllRef}
                type="checkbox"
              />
            </span>
            <span>Cliente</span>
            <span>RFC</span>
            <span>Contacto</span>
            <span>Teléfono</span>
            <span>Correo</span>
            <span>Estado</span>
          </div>

          {isLoading ? (
            <div className="clients-empty">Cargando clientes...</div>
          ) : paginatedClients.length ? (
            paginatedClients.map((client) => {
              const contact = getClientContact(client);
              const isSelected = selectedClientIds.includes(client.id);
              const missingFields = getMissingClientFields(client);

              return (
                <div
                  className={isSelected ? 'clients-table__row clients-table__row--clickable table-row--selected' : 'clients-table__row clients-table__row--clickable'}
                  key={client.id}
                  onClick={() => startEdit(client)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                      event.preventDefault();
                      startEdit(client);
                    }
                  }}
                  role="button"
                  tabIndex={0}
                >
                  <span
                    onClick={(event) => event.stopPropagation()}
                    onKeyDown={(event) => event.stopPropagation()}
                  >
                    <input
                      checked={isSelected}
                      className="row-selector"
                      onChange={() => toggleClientSelection(client.id)}
                      type="checkbox"
                    />
                  </span>
                  <span>
                    {getClientDisplayName(client)}
                    <small className="client-row-meta">{getClientTypeLabel(client.client_type)}</small>
                    {missingFields.length ? (
                      <small className="client-row-alert" title={`Información pendiente: ${missingFields.join(', ')}`}>
                        Información pendiente
                      </small>
                    ) : null}
                  </span>
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
            <div className="clients-empty">No hay clientes para los filtros aplicados.</div>
          )}
        </div>

        {visibleClients.length > clientsPerPage ? (
          <div className="clients-pagination" aria-label="Paginación de clientes">
            <span>{paginationLabel}</span>
            <div className="clients-pagination__controls">
              <button
                className="table-button"
                disabled={normalizedCurrentPage === 1}
                onClick={() => goToClientPage(1)}
                type="button"
              >
                «
              </button>
              <button
                className="table-button"
                disabled={normalizedCurrentPage === 1}
                onClick={() => goToClientPage(normalizedCurrentPage - 1)}
                type="button"
              >
                ‹
              </button>
              {pageNumbers[0] > 1 ? <small>...</small> : null}
              {pageNumbers.map((page) => (
                <button
                  className={page === normalizedCurrentPage ? 'table-button table-button--primary' : 'table-button'}
                  key={page}
                  onClick={() => goToClientPage(page)}
                  type="button"
                >
                  {page}
                </button>
              ))}
              {pageNumbers[pageNumbers.length - 1] < totalClientPages ? <small>...</small> : null}
              <button
                className="table-button"
                disabled={normalizedCurrentPage === totalClientPages}
                onClick={() => goToClientPage(normalizedCurrentPage + 1)}
                type="button"
              >
                ›
              </button>
              <button
                className="table-button"
                disabled={normalizedCurrentPage === totalClientPages}
                onClick={() => goToClientPage(totalClientPages)}
                type="button"
              >
                »
              </button>
            </div>
          </div>
        ) : null}
      </section>

      {isClientModalOpen ? (
        <div className="modal-backdrop" role="presentation">
          <section className="client-modal" aria-modal="true" role="dialog">
            <div className="client-modal-header">
              <div>
                <p>Clientes</p>
                <h2>{modalTitle}</h2>
                {notice && isClientModalOpen ? <span>{notice}</span> : null}
              </div>

              <div className="client-modal-navigator">
                {editingClientId ? (
                  <>
                    <button
                      aria-label="Cliente anterior"
                      disabled={isSaving || visibleClients.length <= 1}
                      onClick={() => navigateClient('previous')}
                      type="button"
                    >
                      ◀
                    </button>

                    <strong>{modalNavigatorLabel}</strong>

                    <button
                      aria-label="Cliente siguiente"
                      disabled={isSaving || visibleClients.length <= 1}
                      onClick={() => navigateClient('next')}
                      type="button"
                    >
                      ▶
                    </button>
                  </>
                ) : null}

                <button aria-label="Cerrar modal" disabled={isSaving} onClick={resetForm} type="button">
                  ✕
                </button>
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
                    Tipo de cliente
                    <select
                      aria-invalid={Boolean(validationErrors.clientType)}
                      onChange={(event) => updateForm('clientType', event.target.value)}
                      value={form.clientType}
                    >
                      <option value="persona_moral">Persona Moral</option>
                      <option value="persona_fisica">Persona Física</option>
                    </select>
                    {validationErrors.clientType ? <span className="field-error">{validationErrors.clientType}</span> : null}
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

                  {form.clientType === 'persona_fisica' ? (
                    <>
                      <label>
                        CURP
                        <input maxLength={18} onChange={(event) => updateForm('curp', event.target.value.toUpperCase())} type="text" value={form.curp} />
                      </label>
                      <label>
                        Nombre(s)
                        <input
                          aria-invalid={Boolean(validationErrors.firstName)}
                          onChange={(event) => updateForm('firstName', event.target.value)}
                          type="text"
                          value={form.firstName}
                        />
                        {validationErrors.firstName ? <span className="field-error">{validationErrors.firstName}</span> : null}
                      </label>
                      <label>
                        Primer apellido
                        <input
                          aria-invalid={Boolean(validationErrors.firstLastName)}
                          onChange={(event) => updateForm('firstLastName', event.target.value)}
                          type="text"
                          value={form.firstLastName}
                        />
                        {validationErrors.firstLastName ? <span className="field-error">{validationErrors.firstLastName}</span> : null}
                      </label>
                      <label>
                        Segundo apellido
                        <input onChange={(event) => updateForm('secondLastName', event.target.value)} type="text" value={form.secondLastName} />
                      </label>
                    </>
                  ) : (
                    <label>
                      Razón social
                      <input
                        aria-invalid={Boolean(validationErrors.legalName)}
                        onChange={(event) => updateForm('legalName', event.target.value)}
                        type="text"
                        value={form.legalName}
                      />
                      {validationErrors.legalName ? <span className="field-error">{validationErrors.legalName}</span> : null}
                    </label>
                  )}

                  <label>
                    Nombre comercial
                    <input
                      aria-invalid={Boolean(validationErrors.commercialName)}
                      onChange={(event) => updateForm('commercialName', event.target.value)}
                      type="text"
                      value={form.commercialName}
                    />
                    {validationErrors.commercialName ? <span className="field-error">{validationErrors.commercialName}</span> : null}
                  </label>

                  <label>
                    Contacto
                    <input onChange={(event) => updateForm('contactName', event.target.value)} type="text" value={form.contactName} />
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
                    Código postal
                    <input
                      aria-invalid={Boolean(validationErrors.postalCode)}
                      inputMode="numeric"
                      onChange={(event) => updateForm('postalCode', event.target.value.replace(/\D/g, ''))}
                      type="text"
                      value={form.postalCode}
                    />
                    {validationErrors.postalCode ? <span className="field-error">{validationErrors.postalCode}</span> : null}
                  </label>
                  <label>
                    Tipo de vialidad
                    <input onChange={(event) => updateForm('streetType', event.target.value)} type="text" value={form.streetType} />
                  </label>
                  <label>
                    Calle
                    <input onChange={(event) => updateForm('street', event.target.value)} type="text" value={form.street} />
                  </label>
                  <label>
                    Número exterior
                    <input onChange={(event) => updateForm('exteriorNumber', event.target.value)} type="text" value={form.exteriorNumber} />
                  </label>
                  <label>
                    Número interior
                    <input onChange={(event) => updateForm('interiorNumber', event.target.value)} type="text" value={form.interiorNumber} />
                  </label>
                  <label>
                    Colonia
                    <input onChange={(event) => updateForm('neighborhood', event.target.value)} type="text" value={form.neighborhood} />
                  </label>
                  <label>
                    Localidad
                    <input onChange={(event) => updateForm('locality', event.target.value)} type="text" value={form.locality} />
                  </label>
                  <label>
                    Municipio
                    <input onChange={(event) => updateForm('municipality', event.target.value)} type="text" value={form.municipality} />
                  </label>
                  <label>
                    Municipio / Ciudad
                    <input onChange={(event) => updateForm('city', event.target.value)} type="text" value={form.city} />
                  </label>
                  <label>
                    Estado
                    <input onChange={(event) => updateForm('addressState', event.target.value)} type="text" value={form.addressState} />
                  </label>
                  <label>
                    País
                    <input onChange={(event) => updateForm('country', event.target.value)} type="text" value={form.country} />
                  </label>
                </>
              ) : null}

              {clientModalTab === 'fiscal' ? (
                <div className="client-fiscal-layout">
                  <div className="client-fiscal-fields">
                  {form.clientType === 'persona_moral' ? (
                    <label>
                      Razón social
                      <input onChange={(event) => updateForm('fiscalLegalName', event.target.value)} type="text" value={form.fiscalLegalName} />
                    </label>
                  ) : null}
                  <label>
                    RFC fiscal
                    <input
                      maxLength={13}
                      onChange={(event) => updateForm('fiscalRfc', event.target.value.toUpperCase())}
                      type="text"
                      value={form.fiscalRfc}
                    />
                  </label>
                  <SatCatalogField catalog={satCatalogByCode.get('postal_codes')} catalogCode="postal_codes" label="Código postal fiscal" onChange={(value) => updateForm('fiscalPostalCode', value.code)} value={form.fiscalPostalCode ? { code: form.fiscalPostalCode } : null} />
                  <SatCatalogField catalog={satCatalogByCode.get('fiscal_regimes')} catalogCode="fiscal_regimes" label="Régimen fiscal" onChange={(value) => updateForm('taxRegime', value.code)} showAllOnOpen value={form.taxRegime ? { code: form.taxRegime } : null} />
                  <SatCatalogField catalog={satCatalogByCode.get('cfdi_uses')} catalogCode="cfdi_uses" label="Uso CFDI predeterminado" onChange={(value) => updateForm('cfdiUse', value.code)} showAllOnOpen value={form.cfdiUse ? { code: form.cfdiUse } : null} />
                  <SatCatalogField catalog={satCatalogByCode.get('countries')} catalogCode="countries" label="País fiscal" onChange={(value) => updateForm('fiscalCountryCode', value.code)} value={form.fiscalCountryCode ? { code: form.fiscalCountryCode } : null} />

                  {taxConstancyMessage ? <div className="client-fiscal-note">{taxConstancyMessage}</div> : null}
                  </div>

                  <input
                    accept=".pdf,.png,.jpg,.jpeg"
                    hidden
                    onChange={handleTaxConstancyFile}
                    ref={taxConstancyInputRef}
                    type="file"
                  />

                  <aside className="client-fiscal-support">
                    <div className="client-form__visual-actions">
                    <button
                      className="table-button"
                      disabled={isSaving}
                      onClick={() => taxConstancyInputRef.current?.click()}
                      type="button"
                    >
                      <Paperclip size={16} />
                      Subir constancia de situación fiscal
                    </button>
                    <div className="client-file-indicator">
                      <strong>{pendingTaxConstancyFile?.name || storedTaxConstancyName || 'Sin archivo cargado'}</strong>
                      <span>{editingClientId ? 'Se guardará al confirmar cambios.' : 'Se cargará al crear el cliente.'}</span>
                    </div>
                    {(pendingTaxConstancyFile || storedTaxConstancyName) ? (
                      <button className="icon-text-button" disabled={isSaving} onClick={discardPendingTaxConstancy} type="button">
                        Descartar archivo
                      </button>
                    ) : null}
                    </div>
                  </aside>
                </div>
              ) : null}

              {clientModalTab === 'certificate-data' ? (
                <section className="client-certificate-profiles">
                  {!editingClientId ? (
                    <div className="form-notice">Guarda primero el cliente para poder registrar datos reutilizables de certificados.</div>
                  ) : (
                    <>
                      <div className="client-certificate-profiles__intro">
                        <div><h3>Datos para certificados</h3><p>Empresas, domicilios y personas de atención que pueden diferir de los datos de facturación.</p></div>
                        <button className="table-button" onClick={resetCertificateProfileForm} type="button">Agregar datos</button>
                      </div>
                      {certificateProfiles.length ? (
                        <div className="client-certificate-profile-list">
                          {certificateProfiles.map((profile) => (
                            <article className={editingCertificateProfileId === profile.id ? 'client-certificate-profile is-active' : 'client-certificate-profile'} key={profile.id}>
                              <div><strong>{profile.label}</strong>{profile.is_default ? <span>Predeterminado</span> : null}<p>{profile.company}</p><small>{profile.address}</small>{profile.attention ? <small>Atención: {profile.attention}</small> : null}</div>
                              <div><button className="icon-text-button" onClick={() => editCertificateProfile(profile)} type="button">Editar</button><button className="icon-text-button danger-text" onClick={() => removeCertificateProfile(profile)} type="button">Eliminar</button></div>
                            </article>
                          ))}
                        </div>
                      ) : <div className="clients-empty">Aún no hay datos adicionales para certificados.</div>}
                      <div className="client-certificate-profile-editor">
                        <label>Nombre para identificarlo<input onChange={(event) => setCertificateProfileForm((current) => ({ ...current, label: event.target.value }))} placeholder="Ej. Planta Guadalajara" type="text" value={certificateProfileForm.label} /></label>
                        <label>Empresa<input onChange={(event) => setCertificateProfileForm((current) => ({ ...current, company: event.target.value }))} type="text" value={certificateProfileForm.company} /></label>
                        <label>Atención<input onChange={(event) => setCertificateProfileForm((current) => ({ ...current, attention: event.target.value }))} type="text" value={certificateProfileForm.attention} /></label>
                        <label className="form-field--wide">Domicilio<textarea onChange={(event) => setCertificateProfileForm((current) => ({ ...current, address: event.target.value }))} rows={3} value={certificateProfileForm.address} /></label>
                        <label className="field-sheet-inline-check form-field--wide"><input checked={certificateProfileForm.isDefault} onChange={(event) => setCertificateProfileForm((current) => ({ ...current, isDefault: event.target.checked }))} type="checkbox" /><span><strong>Usar como opción predeterminada</strong></span></label>
                        <div className="client-certificate-profile-editor__actions form-field--wide"><button className="icon-text-button" onClick={resetCertificateProfileForm} type="button">Limpiar</button><button className="primary-button" disabled={isSaving} onClick={saveCertificateProfile} type="button">{editingCertificateProfileId ? 'Actualizar datos' : 'Guardar datos'}</button></div>
                      </div>
                    </>
                  )}
                </section>
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
                    <p>Zona de eliminación</p>
                    <span>Esta acción eliminará el cliente. No se eliminará físicamente y el backend validará dependencias activas.</span>
                  </div>
                  <div className="toolbar-actions">
                    <button
                      className="table-button table-button--danger"
                      disabled={isSaving}
                      onClick={() =>
                        handleDeactivateClient({
                          id: editingClientId,
                          legal_name: form.fiscalLegalName || form.legalName || form.commercialName
                        })
                      }
                      type="button"
                    >
                      Eliminar cliente
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

            <div className="import-upload-zone import-upload-zone--clients">
              <div className="import-upload-zone__control">
                <span>Archivo CSV o XLSX</span>
                <input
                  accept=".xlsx,.xls,.csv,.tsv"
                  hidden
                  onChange={handleClientImportFile}
                  ref={importInputRef}
                  type="file"
                />
                <button className="table-button table-button--file" disabled={isSaving} onClick={() => importInputRef.current?.click()} type="button">
                  <Upload size={16} />
                  Seleccionar archivo
                </button>
              </div>
              <div>
                <strong>{clientImportFileName || 'Sin archivo seleccionado'}</strong>
                <span>Formato esperado: plantilla MYC con encabezados en snake_case.</span>
              </div>
            </div>

            {clientImportMessage ? <div className="client-fiscal-note">{clientImportMessage}</div> : null}

            {clientImportSummary ? (
              <div className="client-fiscal-note">
                Resumen final: {clientImportSummary.imported_count} importados en total ({clientImportSummary.imported_with_warnings_count ?? 0} con advertencias),
                {` ${clientImportSummary.duplicate_count} duplicados y ${clientImportSummary.error_count} errores.`}
              </div>
            ) : null}

            {clientImportSummary?.warnings?.length ? (
              <section className="import-preview-section">
                <h3>Importados con advertencias</h3>
                <div className="import-preview-list">
                  {clientImportSummary.warnings.slice(0, 20).map((item, index) => (
                    <article className="import-row import-row--warning" key={`${index}-${item.message}`}>
                      <strong>{item.name || 'Cliente importado'}</strong>
                      <small>{item.message}</small>
                    </article>
                  ))}
                </div>
              </section>
            ) : null}

            {clientImportSummary?.errors?.length ? (
              <section className="import-preview-section">
                <h3>Errores</h3>
                <div className="import-preview-list">
                  {clientImportSummary.errors.slice(0, 5).map((item, index) => (
                    <article className="import-row import-row--error" key={`${index}-${item.message}`}>
                      <strong>{item.row?.nombre_comercial || item.row?.razon_social || 'Registro con error'}</strong>
                      <small>{item.message}</small>
                    </article>
                  ))}
                </div>
              </section>
            ) : null}

            <div className="client-form__actions client-form__actions--modal">
              <button className="table-button" onClick={downloadClientTemplate} type="button">
                <FileSpreadsheet size={16} />
                Descargar plantilla
              </button>
              <button className="icon-text-button" onClick={closeClientImportModal} type="button">
                Cancelar
              </button>
              <button
                className="primary-button"
                disabled={isSaving || !clientImportPreview?.rows.length}
                onClick={confirmImportAction}
                type="button"
              >
                {isSaving ? 'Importando...' : 'Importar'}
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
