import React, {
  useEffect,
  useMemo,
  useState,
} from 'react';

import {
  ClipboardCheck,
  PackageCheck,
} from 'lucide-react';

import {
  registerRepairArrival,
} from '../../../services/api.js';


function safeArray(value) {
  return Array.isArray(value)
    ? value
    : [];
}


function safeText(
  value,
  fallback = '-',
) {
  if (
    value === undefined ||
    value === null ||
    value === ''
  ) {
    return fallback;
  }

  return value;
}


function RepairReceptionSection({
  order,
  execution,
  board = null,
  isBusy = false,
  onBusyChange,
  onBoardChange,
  onError,
  onNotice,
}) {
  const [form, setForm] =
    useState({
      equipmentId: '',
      name: '',
      brand: '',
      model: '',
      serialNumber: '',
    });


  const equipmentOptions =
    useMemo(
      () => {
        const possibleSources = [
          board?.equipment,
          board?.available_equipment,
          order?.equipment,
        ];

        const found =
          possibleSources.find(
            (value) =>
              Array.isArray(value),
          );

        return safeArray(found);
      },
      [
        board,
        order,
      ],
    );


  const canRegisterArrival =
    execution?.status ===
    'pending_arrival';


  const equipmentAlreadyLinked =
    Boolean(
      execution?.equipment_id,
    );


  useEffect(() => {
    /*
     * Si cambiamos de expediente,
     * el formulario de recepción
     * no debe conservar datos del
     * equipo anterior.
     */

    setForm({
      equipmentId: '',
      name: '',
      brand: '',
      model: '',
      serialNumber: '',
    });
  }, [execution?.id]);


  function setBusy(value) {
    if (
      typeof onBusyChange ===
      'function'
    ) {
      onBusyChange(value);
    }
  }


  function reportError(message) {
    if (
      typeof onError ===
      'function'
    ) {
      onError(message);
    }
  }


  function reportNotice(message) {
    if (
      typeof onNotice ===
      'function'
    ) {
      onNotice(message);
    }
  }


  function updateBoard(result) {
    if (
      result &&
      typeof onBoardChange ===
      'function'
    ) {
      onBoardChange(result);
    }
  }


  function updateField(
    field,
    value,
  ) {
    setForm(
      (current) => ({
        ...current,
        [field]: value,
      }),
    );
  }


  function handleExistingEquipmentChange(
    value,
  ) {
    updateField(
      'equipmentId',
      value,
    );

    if (!value) {
      return;
    }

    /*
     * Cuando seleccionamos un equipo
     * existente no copiamos sus datos
     * al formulario.
     *
     * El backend seguirá siendo la
     * autoridad de la identidad del
     * equipo vinculado.
     */

    setForm(
      (current) => ({
        ...current,
        equipmentId: value,
        name: '',
        brand: '',
        model: '',
        serialNumber: '',
      }),
    );
  }


  async function handleSubmit(
    event,
  ) {
    event.preventDefault();

    if (
      !order?.id ||
      !execution?.id ||
      isBusy
    ) {
      return;
    }

    const equipmentId =
      form.equipmentId
        ? Number(
            form.equipmentId,
          )
        : null;

    const name =
      form.name.trim();

    const brand =
      form.brand.trim();

    const model =
      form.model.trim();

    const serialNumber =
      form.serialNumber.trim();


    if (
      !equipmentId &&
      !name
    ) {
      reportError(
        'Selecciona un equipo existente o captura el nombre del equipo recibido.',
      );

      return;
    }


    setBusy(true);

    reportError('');
    reportNotice('');


    try {
      const result =
        await registerRepairArrival(
          order.id,
          execution.id,
          {
            equipment_id:
              equipmentId,

            name:
              equipmentId
                ? null
                : name,

            brand:
              equipmentId
                ? null
                : (
                    brand ||
                    null
                  ),

            model:
              equipmentId
                ? null
                : (
                    model ||
                    null
                  ),

            serial_number:
              equipmentId
                ? null
                : (
                    serialNumber ||
                    null
                  ),
          },
        );


      updateBoard(result);


      setForm({
        equipmentId: '',
        name: '',
        brand: '',
        model: '',
        serialNumber: '',
      });


      reportNotice(
        'Equipo recibido y vinculado correctamente al expediente de reparación.',
      );
    } catch (requestError) {
      reportError(
        requestError?.message ||
          'No fue posible registrar la recepción del equipo.',
      );
    } finally {
      setBusy(false);
    }
  }


  /* =======================================================
     RECEPCIÓN YA COMPLETADA
     ======================================================= */

  if (!canRegisterArrival) {
    return (
      <section className="repair-v2-stage">
        <header className="repair-v2-stage__heading">
          <div>
            <h4>
              Recepción del equipo
            </h4>
          </div>


          <span className="repair-v2-stage__state is-done">
            <ClipboardCheck size={15} />

            Registrada
          </span>
        </header>


        <div className="repair-v2-reception-summary">
          <article>
            <span>
              Equipo
            </span>

            <strong>
              {safeText(
                execution?.equipment_name,
                'Equipo recibido',
              )}
            </strong>
          </article>


          <article>
            <span>
              ID de equipo
            </span>

            <strong>
              {safeText(
                execution?.equipment_id,
                'No disponible',
              )}
            </strong>
          </article>


          <article>
            <span>
              Serie
            </span>

            <strong>
              {safeText(
                execution?.serial_number ||
                  execution?.equipment_serial_number,
                'Sin serie registrada',
              )}
            </strong>
          </article>


          <article>
            <span>
              Estado actual
            </span>

            <strong>
              {safeText(
                execution?.status,
              )}
            </strong>
          </article>
        </div>
      </section>
    );
  }


  /* =======================================================
     RECEPCIÓN PENDIENTE
     ======================================================= */

  return (
    <section className="repair-v2-stage">
      <header className="repair-v2-stage__heading">
        <div>
          <h4>
            Recepción del equipo
          </h4>

          <p>
            Confirma qué equipo físico
            ingresó para este servicio de
            reparación.
          </p>
        </div>


        <span className="repair-v2-stage__state is-active">
          <PackageCheck size={15} />

          Pendiente
        </span>
      </header>


      {equipmentAlreadyLinked ? (
        <div className="repair-v2-stage__notice">
          Este expediente ya tiene un
          equipo vinculado, pero permanece
          en estado de recepción pendiente.
          Revisa la consistencia del flujo
          antes de registrar nuevamente el
          arribo.
        </div>
      ) : null}


      <form
        className="repair-v2-form"
        onSubmit={handleSubmit}
      >
        {/* =================================================
            EQUIPO EXISTENTE
            ================================================= */}

        <section className="repair-v2-form__group repair-v2-form__group--full">
          <header>
            <span>
              Equipo existente
            </span>

            <p>
              Si el equipo ya está dado de
              alta en el ERP, selecciónalo
              aquí.
            </p>
          </header>


          <label>
            Equipo registrado

            <select
              disabled={isBusy}
              onChange={(event) =>
                handleExistingEquipmentChange(
                  event.target.value,
                )
              }
              value={
                form.equipmentId
              }
            >
              <option value="">
                Selecciona un equipo
              </option>

              {equipmentOptions.map(
                (equipment) => {
                  const name =
                    equipment?.name ||
                    equipment?.equipment_name ||
                    equipment?.description ||
                    `Equipo #${equipment?.id}`;

                  const serial =
                    equipment?.serial_number ||
                    equipment?.serial ||
                    null;

                  return (
                    <option
                      key={
                        equipment.id
                      }
                      value={
                        equipment.id
                      }
                    >
                      {name}
                      {serial
                        ? ` · Serie ${serial}`
                        : ''}
                    </option>
                  );
                },
              )}
            </select>
          </label>
        </section>


        {/* =================================================
            SEPARADOR
            ================================================= */}

        <div className="repair-v2-form__separator">
          <span>
            o captura el equipo recibido
          </span>
        </div>


        {/* =================================================
            EQUIPO NUEVO / IDENTIDAD DE RECEPCIÓN
            ================================================= */}

        <label className="repair-v2-form__field repair-v2-form__field--wide">
          Nombre del equipo

          <input
            disabled={
              isBusy ||
              Boolean(
                form.equipmentId,
              )
            }
            onChange={(event) =>
              updateField(
                'name',
                event.target.value,
              )
            }
            placeholder="Ej. Multímetro digital"
            type="text"
            value={form.name}
          />
        </label>


        <label className="repair-v2-form__field">
          Marca

          <input
            disabled={
              isBusy ||
              Boolean(
                form.equipmentId,
              )
            }
            onChange={(event) =>
              updateField(
                'brand',
                event.target.value,
              )
            }
            placeholder="Ej. Fluke"
            type="text"
            value={form.brand}
          />
        </label>


        <label className="repair-v2-form__field">
          Modelo

          <input
            disabled={
              isBusy ||
              Boolean(
                form.equipmentId,
              )
            }
            onChange={(event) =>
              updateField(
                'model',
                event.target.value,
              )
            }
            placeholder="Ej. 87V"
            type="text"
            value={form.model}
          />
        </label>


        <label className="repair-v2-form__field repair-v2-form__field--wide">
          Número de serie

          <input
            disabled={
              isBusy ||
              Boolean(
                form.equipmentId,
              )
            }
            onChange={(event) =>
              updateField(
                'serialNumber',
                event.target.value,
              )
            }
            placeholder="Serie física del equipo"
            type="text"
            value={
              form.serialNumber
            }
          />
        </label>


        {/* =================================================
            CONTEXTO
            ================================================= */}

        <div className="repair-v2-reception-context">
          <div>
            <span>
              Expediente
            </span>

            <strong>
              #{safeText(
                execution?.id,
              )}
            </strong>
          </div>


          <div>
            <span>
              Orden de trabajo
            </span>

            <strong>
              {execution?.work_order_number
                ? `OT-${execution.work_order_number}`
                : 'Se generará / vinculará según el flujo operativo'}
            </strong>
          </div>
        </div>


        {/* =================================================
            ACCIONES
            ================================================= */}

        <footer className="repair-v2-form__actions">
          <button
            className="primary-button"
            disabled={
              isBusy
            }
            type="submit"
          >
            <PackageCheck size={16} />

            {isBusy
              ? 'Registrando...'
              : 'Confirmar recepción'}
          </button>
        </footer>
      </form>
    </section>
  );
}


export default RepairReceptionSection;