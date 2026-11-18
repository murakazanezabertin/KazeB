export type SellerLanguage = "rw" | "en" | "fr";

export const sellerMessages: Record<
  SellerLanguage,
  {
    loading: string;
    dashboardError: string;
    formLoadError: string;
    authRequired: string;
    createError: string;
    updateError: string;
  }
> = {
  rw: {
    loading: "Birimo gutegurwa...",
    dashboardError: "Ntibashoboye gutegura konti y'ibicuruzwa.",
    formLoadError: "Ntibashoboye gutegura ifishi y'igicuruzwa.",
    authRequired: "Injira kugira ngo ucunge ibicuruzwa byawe.",
    createError: "Kohereza igicuruzwa ntibyakunze.",
    updateError: "Kubika impinduka ntibyakunze.",
  },
  en: {
    loading: "Loading...",
    dashboardError: "Unable to load the seller dashboard.",
    formLoadError: "Unable to load the listing form.",
    authRequired: "Sign in to manage your listings.",
    createError: "Unable to create the listing.",
    updateError: "Unable to save the listing changes.",
  },
  fr: {
    loading: "Chargement...",
    dashboardError: "Impossible de charger le tableau de bord vendeur.",
    formLoadError: "Impossible de charger le formulaire d'annonce.",
    authRequired: "Connectez-vous pour gérer vos annonces.",
    createError: "Impossible de créer l'annonce.",
    updateError: "Impossible d'enregistrer les modifications de l'annonce.",
  },
};
