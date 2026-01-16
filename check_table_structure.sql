-- Script pour vérifier la structure complète de la table student_attachments

SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'student_attachments'
ORDER BY ordinal_position;
