"""initialize 2026 institutional sequence floors

Revision ID: b03b4c5d6e7f
Revises: af2a3b4c5d6e
Create Date: 2026-07-30 00:25:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "b03b4c5d6e7f"
down_revision: Union[str, None] = "af2a3b4c5d6e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO institutional_folio_sequences
            (document_type, prefix, year, next_value, created_at, updated_at)
        SELECT
            'certificate',
            prefix,
            2026,
            GREATEST(
                8000,
                COALESCE(
                    (
                        SELECT MAX(RIGHT(certificates.folio, 4)::integer) + 1
                        FROM certificates
                        WHERE certificates.folio ~ ('^' || prefix || '26[0-1][0-9][0-9]{4}$')
                    ),
                    8000
                )
            ),
            NOW(),
            NOW()
        FROM (VALUES ('MYCA'), ('MYCT')) AS prefixes(prefix)
        ON CONFLICT (document_type, prefix, year)
        DO UPDATE SET
            next_value = GREATEST(
                institutional_folio_sequences.next_value,
                EXCLUDED.next_value,
                8000
            ),
            updated_at = NOW()
        """
    )
    op.execute(
        """
        INSERT INTO institutional_folio_sequences
            (document_type, prefix, year, next_value, created_at, updated_at)
        VALUES (
            'work_order',
            'OT',
            2026,
            GREATEST(
                7000,
                COALESCE((SELECT MAX(work_order_number) + 1 FROM service_orders), 7000),
                COALESCE((SELECT MAX(work_order_number) + 1 FROM service_work_orders), 7000)
            ),
            NOW(),
            NOW()
        )
        ON CONFLICT (document_type, prefix, year)
        DO UPDATE SET
            next_value = GREATEST(
                institutional_folio_sequences.next_value,
                EXCLUDED.next_value,
                7000
            ),
            updated_at = NOW()
        """
    )


def downgrade() -> None:
    # Sólo se retiran filas que nunca reservaron un consecutivo. Una secuencia
    # consumida no se reduce ni elimina para impedir reutilización de folios.
    op.execute(
        """
        DELETE FROM institutional_folio_sequences
        WHERE year = 2026
          AND (
            (document_type = 'certificate' AND prefix IN ('MYCA', 'MYCT') AND next_value = 8000)
            OR
            (document_type = 'work_order' AND prefix = 'OT' AND next_value = 7000)
          )
        """
    )
