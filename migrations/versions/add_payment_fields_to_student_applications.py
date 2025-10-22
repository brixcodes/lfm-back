"""add payment fields to student applications

Revision ID: add_payment_fields_to_student_applications
Revises: 900108de420f_add_payment_id_to_cabinet_applications
Create Date: 2025-01-22 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic...
revision = 'add_payment_fields'
down_revision = '900108de420f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to student_applications table
    op.add_column('student_applications', sa.Column('payment_method', sa.String(length=20), nullable=True))
    op.add_column('student_applications', sa.Column('civility', sa.String(length=10), nullable=True))
    op.add_column('student_applications', sa.Column('city', sa.String(length=100), nullable=True))
    op.add_column('student_applications', sa.Column('address', sa.String(length=255), nullable=True))
    op.add_column('student_applications', sa.Column('date_of_birth', sa.String(length=20), nullable=True))


def downgrade() -> None:
    # Remove the added columns
    op.drop_column('student_applications', 'date_of_birth')
    op.drop_column('student_applications', 'address')
    op.drop_column('student_applications', 'city')
    op.drop_column('student_applications', 'civility')
    op.drop_column('student_applications', 'payment_method')
