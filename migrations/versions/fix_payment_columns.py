"""fix payment columns

Revision ID: fix_payment_columns
Revises: 707098908bfd
Create Date: 2025-01-22 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fix_payment_columns'
down_revision = '707098908bfd'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Vérifier si les colonnes existent déjà et les ajouter si nécessaire
    connection = op.get_bind()
    
    # Vérifier l'existence des colonnes
    result = connection.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'student_applications' 
        AND column_name IN ('payment_method', 'civility', 'city', 'address', 'date_of_birth');
    """))
    
    existing_columns = [row[0] for row in result.fetchall()]
    print(f"Colonnes existantes: {existing_columns}")
    
    # Ajouter les colonnes manquantes
    columns_to_add = {
        'payment_method': 'VARCHAR(20)',
        'civility': 'VARCHAR(10)', 
        'city': 'VARCHAR(100)',
        'address': 'VARCHAR(255)',
        'date_of_birth': 'VARCHAR(20)'
    }
    
    for column_name, column_type in columns_to_add.items():
        if column_name not in existing_columns:
            print(f"Ajout de la colonne {column_name}...")
            op.execute(f"ALTER TABLE student_applications ADD COLUMN {column_name} {column_type};")
            print(f"Colonne {column_name} ajoutée avec succès")
        else:
            print(f"Colonne {column_name} existe déjà")


def downgrade() -> None:
    # Supprimer les colonnes ajoutées
    columns_to_remove = ['date_of_birth', 'address', 'city', 'civility', 'payment_method']
    
    for column_name in columns_to_remove:
        try:
            op.execute(f"ALTER TABLE student_applications DROP COLUMN IF EXISTS {column_name};")
            print(f"Colonne {column_name} supprimée")
        except Exception as e:
            print(f"Erreur lors de la suppression de {column_name}: {e}")
