-- Script SQL simplifié pour corriger la table student_attachments
-- Exécute ces commandes une par une dans ton client PostgreSQL

-- Étape 1: Copier les données de student_application_id vers application_id
UPDATE student_attachments
SET application_id = student_application_id
WHERE application_id IS NULL AND student_application_id IS NOT NULL;

-- Étape 2: Supprimer la contrainte de clé étrangère sur student_application_id
ALTER TABLE student_attachments 
DROP CONSTRAINT IF EXISTS student_attachments_student_application_id_fkey;

-- Étape 3: Supprimer la colonne student_application_id
ALTER TABLE student_attachments 
DROP COLUMN IF EXISTS student_application_id;

-- Étape 4: S'assurer que application_id est NOT NULL
ALTER TABLE student_attachments 
ALTER COLUMN application_id SET NOT NULL;

-- Étape 5: Ajouter la contrainte de clé étrangère sur application_id
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'student_attachments_application_id_fkey' 
        AND table_name = 'student_attachments'
    ) THEN
        ALTER TABLE student_attachments 
        ADD CONSTRAINT student_attachments_application_id_fkey 
        FOREIGN KEY (application_id) REFERENCES student_applications(id) ON DELETE CASCADE;
    END IF;
END $$;

-- Vérification finale
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'student_attachments'
ORDER BY ordinal_position;
