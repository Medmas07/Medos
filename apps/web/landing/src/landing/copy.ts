/**
 * Every visible string of the MedOS landing page. The statements describe the
 * product vision (docs/product/FEDERATED_HEALTHCARE_ECOSYSTEM.md); they make no
 * security or clinical-validation claim, and the demo uses fictional data only.
 */
export const copy = {
  brand: 'MedOS',
  nav: {
    how: 'Fonctionnement',
    ecosystem: 'Écosystème',
    trust: 'Confiance',
    hospitals: 'Établissements',
    signIn: 'Se connecter',
    cta: "Télécharger l'instance",
    skip: 'Aller au contenu',
  },
  loader: 'Connexion des établissements',
  hero: {
    title: 'La santé, fédérée.',
    body: 'Chaque hôpital garde ses données. MedOS relie hôpitaux, patients, cliniciens et chercheurs sous une gouvernance éthique explicite, sans base clinique centrale.',
    primary: "Télécharger l'instance pour hôpitaux",
    secondary: 'Voir le fonctionnement',
  },
  gather: {
    title: 'Vos données restent chez vous.',
    body: "Le nœud hospitalier MedOS s'installe dans votre établissement. Un adaptateur DMI local traduit votre système existant en FHIR : les données cliniques sources ne quittent pas votre contrôle.",
    chips: ['DMI / SIH existant', 'Adaptateur DMI local', 'Représentation FHIR', 'Hospital Node'],
  },
  share: {
    title: 'Chaque échange, autorisé.',
    body: "Synchronisation entre hôpitaux, accès patient, projet de recherche : l'Autorité de gouvernance décide de la portée, de la finalité et de la durée. Chaque accès est tracé.",
    chips: ['Portée et finalité explicites', 'Durée limitée', "Journal d'audit"],
  },
  /** Labels of the six nodes linked by threads in the 3D scene; the first one lights up. */
  sceneNodes: ['Gouvernance', 'Hôpital A', 'Hôpital B', 'Patients', 'Cliniciens', 'Recherche'],
  features: {
    title: 'Un écosystème, cinq acteurs.',
    nodes: {
      title: 'Un nœud par hôpital',
      body: 'Votre Hospital Node conserve les données sources. Le réseau échange des vues autorisées, jamais votre base.',
    },
    governance: {
      title: 'Gouvernance éthique',
      body: "Une autorité indépendante approuve adhésions, synchronisations et recherches. MedOS n'approuve jamais ses propres demandes.",
      chips: ['Portée', 'Finalité', 'Durée', 'Audit'],
    },
    research: {
      title: 'Recherche compute-to-data',
      body: "Les algorithmes approuvés viennent aux données ; seuls des résultats contrôlés en sortent.",
    },
    ai: {
      title: 'Une IA qui assiste',
      body: 'Extraction, alertes et revue documentaire restent indicatives : un humain responsable valide toujours.',
    },
    apps: {
      title: 'Patients et cliniciens',
      body: "Le patient gère les accès à son historique ; le clinicien consulte un contexte autorisé, depuis son mobile.",
    },
  },
  trust: {
    title: 'Confiance par conception.',
    body: "Des principes d'architecture, pas des options.",
    items: [
      {
        title: 'Données locales',
        body: 'Les données cliniques sources restent dans chaque Hospital Node. Aucun service central ne se connecte à un DMI.',
      },
      {
        title: 'Autorisation explicite',
        body: 'Portée, finalité, durée et consentement sont décidés par la Gouvernance, accès par accès.',
      },
      {
        title: 'Des preuves, pas des dossiers',
        body: "Le registre d'audit ne garde que des preuves minimales : identifiants, horodatages, empreintes. Jamais de données médicales.",
      },
    ],
  },
  hospitals: {
    title: 'Rejoignez le réseau MedOS.',
    body: "Remplissez les formulaires d'adhésion en ligne. Après l'approbation de l'Autorité de gouvernance, suivez le guide de configuration et téléchargez votre instance.",
    steps: [
      { title: "Formulaires d'adhésion", body: 'Inscription, profil, documents, accords, questionnaires technique et DMI.' },
      { title: 'Validation par la Gouvernance', body: 'Contrôles automatiques, revue humaine, puis décision de l’Autorité.' },
      { title: 'Configuration et téléchargement', body: "Guide de configuration du nœud, puis téléchargement de l'instance." },
    ],
    cta: "Télécharger l'instance pour hôpitaux",
  },
  footer: {
    tagline: 'Les données de santé, fédérées et gouvernées.',
    product: 'Produit',
    hospitals: 'Établissements',
    rights: 'MedOS · Démonstration Hackcure : données fictives, services simulés.',
  },
  fallback: 'Illustration de dossiers hospitaliers réunis dans un nœud local, relié au réseau fédéré',
} as const
