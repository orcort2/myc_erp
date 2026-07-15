import unittest

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.core.db import Base
from app.models.audit_log import AuditLog
from app.models.client import Client, ClientCertificateProfile, ClientContact
from app.models.quotation import Quotation
from app.services.clients import (
    delete_client_permanently,
    get_client_delete_eligibility,
    restore_client,
)


class ClientDeletionTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def make_client(self, name="Cliente de prueba"):
        client = Client(client_type="persona_moral", legal_name=name, commercial_name=name)
        self.db.add(client)
        self.db.commit()
        return client

    def test_client_without_history_can_be_deleted_permanently(self):
        client = self.make_client()
        result = delete_client_permanently(self.db, client.id)
        self.assertEqual(result.status, "deleted")
        self.assertEqual(result.delete_mode, "hard")
        self.assertIsNone(self.db.get(Client, client.id))

    def test_client_with_auxiliaries_deletes_them_and_preserves_audit(self):
        client = self.make_client()
        self.db.add_all([
            ClientContact(client_id=client.id, name="Contacto"),
            ClientCertificateProfile(client_id=client.id, label="Fiscal", company="MYC", address="Av. 1"),
        ])
        self.db.commit()
        result = delete_client_permanently(self.db, client.id)
        self.assertEqual(result.status, "deleted")
        self.assertEqual(self.db.query(ClientContact).filter_by(client_id=client.id).count(), 0)
        self.assertEqual(self.db.query(ClientCertificateProfile).filter_by(client_id=client.id).count(), 0)
        self.assertEqual(self.db.query(AuditLog).filter_by(action="client_hard_deleted", entity_id=client.id).count(), 1)

    def test_client_with_quotation_is_archived_and_reports_dependencies(self):
        client = self.make_client()
        self.db.add(Quotation(folio="COT-DELETE-001", client_id=client.id))
        self.db.commit()
        eligibility = get_client_delete_eligibility(self.db, client.id)
        self.assertFalse(eligibility.eligible_for_hard_delete)
        self.assertEqual(eligibility.blocking_dependencies["quotations"], 1)
        result = delete_client_permanently(self.db, client.id)
        self.assertEqual(result.status, "archived")
        self.assertFalse(self.db.get(Client, client.id).is_active)
        self.assertEqual(result.blocking_dependencies["quotations"], 1)

    def test_restore_preserves_id_and_blocks_an_occupied_exclusive_rfc(self):
        archived = self.make_client("Archivado")
        archived.rfc = "ABC010101ABC"
        archived.is_active = False
        self.db.commit()
        restored = restore_client(self.db, archived.id)
        self.assertTrue(restored.is_active)
        self.assertEqual(restored.id, archived.id)
        self.assertEqual(self.db.query(AuditLog).filter_by(action="client_restored", entity_id=archived.id).count(), 1)

        archived.is_active = False
        self.db.add(Client(client_type="persona_moral", legal_name="Activo", commercial_name="Activo", rfc="ABC010101ABC"))
        self.db.commit()
        with self.assertRaises(HTTPException) as error:
            restore_client(self.db, archived.id)
        self.assertEqual(error.exception.status_code, 409)
