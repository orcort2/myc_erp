import { describe, expect, it } from 'vitest';
import { emptyClientForm } from '../constants/forms.js';
import { toClientPayload } from './clients.js';

describe('RFC de clientes', () => {
  it('guarda el RFC editado aunque el valor fiscal anterior sea diferente', () => {
    const form = {
      ...emptyClientForm,
      clientType: 'persona_moral',
      legalName: 'Cliente de prueba',
      rfc: 'ABC010101AAA',
      fiscalRfc: 'XAXX010101000',
    };

    expect(toClientPayload(form, { includeContacts: false }).rfc)
      .toBe('ABC010101AAA');
  });
});
