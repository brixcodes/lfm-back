-- Script pour corriger toutes les colonnes de student_attachments
-- Exécute ces commandes une par une

-- 1. Vérifier la structure actuelle
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'student_attachments'
ORDER BY ordinal_position;

-- 2. Copier student_application_id vers application_id (si nécessaire)
UPDATE student_attachments
SET application_id = student_application_id
WHERE application_id IS NULL AND student_application_id IS NOT NULL;

-- 3. Copier attachment_type vers document_type (si nécessaire)
UPDATE student_attachments
SET document_type = attachment_type
WHERE document_type IS NULL AND attachment_type IS NOT NULL;

-- 4. Supprimer la contrainte FK sur student_application_id
ALTER TABLE student_attachments 
DROP CONSTRAINT IF EXISTS student_attachments_student_application_id_fkey;

-- 5. Supprimer la colonne student_application_id
ALTER TABLE student_attachments 
DROP COLUMN IF EXISTS student_application_id;

-- 6. Supprimer la colonne attachment_type
ALTER TABLE student_attachments 
DROP COLUMN IF EXISTS attachment_type;

-- 7. S'assurer que application_id est NOT NULL
ALTER TABLE student_attachments 
ALTER COLUMN application_id SET NOT NULL;

-- 8. S'assurer que document_type est NOT NULL
ALTER TABLE student_attachments 
ALTER COLUMN document_type SET NOT NULL;

-- 9. Ajouter la contrainte FK sur application_id
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

-- 10. Vérifier la structure finale
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'student_attachments'
ORDER BY ordinal_position;

-- 11. Vérifier les données
SELECT COUNT(*) as total FROM student_attachments;
SELECT application_id, document_type, COUNT(*) 
FROM student_attachments 
GROUP BY application_id, document_type;
