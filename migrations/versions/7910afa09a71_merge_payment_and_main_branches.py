"""merge payment and main branches

Revision ID: 7910afa09a71
Revises: a2f72710c9af, fix_payment_columns
Create Date: 2025-10-23 03:52:56.959255

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel



# revision identifiers, used by Alembic.
revision: str = '7910afa09a71'
down_revision: Union[str, None] = ('a2f72710c9af', 'fix_payment_columns')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
