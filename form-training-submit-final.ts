// ✅ SOLUTION FINALE pour la méthode submit() dans form-training.ts
// Remplace la partie next: (response) => { ... } par ceci :

next: (response) => {
  console.log('Candidature soumise avec succès:', response);
  this.isSubmitting = false;
  
  // ✅ Structure de réponse du backend :
  // { success: true, message: "...", data: { application_number: "...", id: 123, ... } }
  
  const applicationNumber = response?.data?.application_number || response?.data?.id?.toString() || '';
  const applicationId = response?.data?.id || '';
  
  // Log pour debug
  console.log('Response data:', response?.data);
  console.log('Application number:', applicationNumber);
  
  // ✅ Redirection vers la page de succès
  this.router.navigate(['/recrutements-success'], {
    queryParams: {
      applicationNumber: applicationNumber,
      applicationId: applicationId,
      email: payload.email,
      trainingTitle: this.selectedSession?.training?.title || '',
      status: response?.data?.status || 'RECEIVED'
    }
  });
},

// ✅ MÉTHODE SUBMIT COMPLÈTE CORRIGÉE :

submit(): void {
  if (this.form.valid && this.selectedSession) {
    this.isSubmitting = true;
    this.submitError = null;

    // Construire les attachments
    const attachments = Object.keys(this.uploadedFiles).map((key) => {
      const file = this.uploadedFiles[key];
      return {
        type: key,        // exemple: 'BANK_TRANSFER_RECEIPT'
        url: file.url,    // L'URL du fichier
        name: file.name   // Le nom du fichier
      };
    });

    const payload: StudentApplicationCreateInput = {
      email: this.form.value.email,
      target_session_id: this.form.value.target_session_id,
      first_name: this.form.value.first_name,
      last_name: this.form.value.last_name,
      phone_number: this.form.value.phone_number,
      civility: this.form.value.civility,
      country_code: 'SN', // Sénégal par défaut
      city: this.form.value.city,
      address: this.form.value.address,
      date_of_birth: this.form.value.date_of_birth,
      payment_method: this.form.value.payment_method || this.paymentMethod,
      attachments: attachments
    };

    // Appel au service pour soumettre la candidature
    this.trainingService.submitApplication(payload).subscribe({
      next: (response) => {
        console.log('Candidature soumise avec succès:', response);
        this.isSubmitting = false;
        
        // ✅ Gestion sécurisée de la réponse
        const applicationNumber = response?.data?.application_number || response?.data?.id?.toString() || '';
        const applicationId = response?.data?.id || '';
        
        // Log pour debug
        console.log('Response data:', response?.data);
        console.log('Application number:', applicationNumber);
        
        // ✅ Redirection vers la page de succès
        this.router.navigate(['/recrutements-success'], {
          queryParams: {
            applicationNumber: applicationNumber,
            applicationId: applicationId,
            email: payload.email,
            trainingTitle: this.selectedSession?.training?.title || '',
            status: response?.data?.status || 'RECEIVED'
          }
        });
      },
      error: (error) => {
        console.error('Erreur lors de la soumission:', error);
        this.isSubmitting = false;
        
        // Gestion des erreurs spécifiques
        if (error.error?.error_code === 'STUDENT_ATTACHMENT_REQUIRED') {
          this.submitError = 'Le reçu de virement bancaire est obligatoire pour ce mode de paiement.';
        } else if (error.error?.message) {
          this.submitError = error.error.message;
        } else {
          this.submitError = 'Une erreur est survenue lors de la soumission. Veuillez réessayer.';
        }
      }
    });
  } else {
    // Marquer tous les champs comme touchés pour afficher les erreurs
    Object.keys(this.form.controls).forEach(key => {
      this.form.get(key)?.markAsTouched();
    });
    
    if (!this.selectedSession) {
      this.submitError = 'Veuillez sélectionner une session de formation.';
    }
  }
}