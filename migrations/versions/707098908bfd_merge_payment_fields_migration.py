"""merge payment fields migration

Revision ID: 707098908bfd
Revises: 2454ebe4a24e, add_payment_fields_to_student_applications
Create Date: 2025-10-22 12:08:25.256147

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel



# revision identifiers, used by Alembic.
revision: str = '707098908bfd'
down_revision: Union[str, None] = ('2454ebe4a24e', 'add_payment_fields')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
