-- Script pour nettoyer la table student_attachments APRÈS que tout fonctionne
-- À exécuter plus tard pour supprimer les colonnes dupliquées

-- ATTENTION: N'exécute ce script QUE quand l'application fonctionne correctement!

-- 1. Vérifier que les deux colonnes ont les mêmes valeurs
SELECT 
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE attachment_type = document_type) as matching,
    COUNT(*) FILTER (WHERE attachment_type != document_type OR attachment_type IS NULL OR document_type IS NULL) as different
FROM student_attachments;

-- 2. Si tout est OK, copier attachment_type vers document_type (ou vice versa)
-- Choisir quelle colonne garder: document_type semble plus standard

-- Option A: Garder document_type, supprimer attachment_type
UPDATE student_attachments
SET document_type = attachment_type
WHERE document_type IS NULL AND attachment_type IS NOT NULL;

ALTER TABLE student_attachments DROP COLUMN IF EXISTS attachment_type;

-- Option B: Garder attachment_type, supprimer document_type
-- UPDATE student_attachments
-- SET attachment_type = document_type
-- WHERE attachment_type IS NULL AND document_type IS NOT NULL;
-- 
-- ALTER TABLE student_attachments DROP COLUMN IF EXISTS document_type;

-- 3. Mettre à jour le modèle Python en conséquence
-- Si tu gardes document_type, supprime attachment_type du modèle
-- Si tu gardes attachment_type, supprime document_type du modèle

-- 4. Vérifier la structure finale
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'student_attachments'
ORDER BY ordinal_position;
