from unittest import TestCase
from unittest.mock import MagicMock

from app.services.invoices import list_invoices


class InvoiceListingTests(TestCase):
    def test_service_order_filter_is_optional_and_scoped(self):
        db = MagicMock()
        db.scalars.return_value.all.return_value = []

        list_invoices(db, service_order_id=17)

        query = db.scalars.call_args.args[0]
        compiled = str(query.compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("invoices.service_order_id = 17", compiled)

    def test_unfiltered_listing_preserves_the_global_workbench_query(self):
        db = MagicMock()
        db.scalars.return_value.all.return_value = []

        list_invoices(db)

        query = db.scalars.call_args.args[0]
        compiled = str(query.compile(compile_kwargs={"literal_binds": True}))
        self.assertNotIn("invoices.service_order_id =", compiled)
