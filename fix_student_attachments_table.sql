-- Script SQL pour corriger la table student_attachments
-- La table a deux colonnes: student_application_id ET application_id
-- Il faut supprimer student_application_id et garder application_id

-- 1. Vérifier la structure actuelle de la table
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'student_attachments'
ORDER BY ordinal_position;

-- 2. Copier les données de student_application_id vers application_id (si nécessaire)
-- Seulement si application_id est NULL et student_application_id a des valeurs
UPDATE student_attachments
SET application_id = student_application_id
WHERE application_id IS NULL AND student_application_id IS NOT NULL;

-- 3. Vérifier qu'il n'y a plus de NULL dans application_id
SELECT COUNT(*) as null_count
FROM student_attachments
WHERE application_id IS NULL;

-- 4. Supprimer la contrainte de clé étrangère sur student_application_id (si elle existe)
-- D'abord, trouver le nom de la contrainte
SELECT constraint_name
FROM information_schema.table_constraints
WHERE table_name = 'student_attachments'
  AND constraint_type = 'FOREIGN KEY';

-- Supprimer la contrainte (remplace le nom si différent)
ALTER TABLE student_attachments 
DROP CONSTRAINT IF EXISTS student_attachments_student_application_id_fkey;

-- 5. Supprimer la colonne student_application_id
ALTER TABLE student_attachments 
DROP COLUMN IF EXISTS student_application_id;

-- 6. S'assurer que application_id est NOT NULL
ALTER TABLE student_attachments 
ALTER COLUMN application_id SET NOT NULL;

-- 7. Ajouter la contrainte de clé étrangère sur application_id (si elle n'existe pas)
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

-- 8. Vérifier la structure finale
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'student_attachments'
ORDER BY ordinal_position;

-- 9. Vérifier les contraintes finales
SELECT
    tc.constraint_name,
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_name = 'student_attachments';

-- 10. Vérifier que les données sont intactes
SELECT COUNT(*) as total_attachments FROM student_attachments;
SELECT application_id, COUNT(*) as count 
FROM student_attachments 
GROUP BY application_id 
ORDER BY application_id;
