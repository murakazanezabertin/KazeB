export interface HomepageData {
  language: "rw" | "en" | "fr";
  labels: {
    home: string;
    add_listing: string;
    search_placeholder: string;
    search: string;
    login: string;
    register: string;
    my_account: string;
    account: string;
    favorites: string;
    messages: string;
    categories: string;
    recent_listings: string;
    about: string;
    faq: string;
    safety: string;
    terms: string;
    privacy: string;
    contact: string;
    follow: string;
    footer_tagline: string;
    change_language: string;
    sign_out: string;
    empty_image: string;
    empty_categories: string;
    all_listings: string;
    all_conditions: string;
    new_condition: string;
    used_condition: string;
    newest: string;
    oldest: string;
    most_viewed: string;
    all_prices: string;
    lowest_price: string;
    highest_price: string;
    previous_page: string;
    next_page: string;
    no_results: string;
    listing_views: string;
    no_reviews: string;
    posted_by: string;
    phone_verified: string;
    save_favorite: string;
    saved_favorite: string;
    report_listing: string;
    contact_seller: string;
    send_message: string;
    login_to_message: string;
    whatsapp_seller: string;
    copy_listing_link: string;
    copy_phone: string;
    call_seller: string;
    joined_kazeb: string;
    seller_listing_count: string;
    seller_bio: string;
    no_seller_bio: string;
    seller_listings: string;
    no_seller_listings: string;
    no_contact_options: string;
    edit_listing: string;
    delete_listing: string;
    share_listing: string;
  };
  user: {
    is_authenticated: boolean;
    unread_message_count: number;
  };
  categories: Array<{
    id: number;
    name: string;
    slug: string;
    url: string;
    icon: string | null;
  }>;
  recent_listings: Array<{
    id: number;
    name: string;
    url: string;
    image: string | null;
    price: string;
    location: string;
    seller: {
      username: string;
      name: string;
      url: string;
      image: string | null;
    };
  }>;
}

export interface ListingCardData {
  id: number;
  name: string;
  url: string;
  image: string | null;
  price: string;
  location: string;
  seller: {
    username: string;
    name: string;
    url: string;
    image: string | null;
  };
}

export interface PaginationData {
  page: number;
  pages: number;
  has_next: boolean;
  has_previous: boolean;
  count?: number;
}

export interface ListingBrowseData {
  category: { id: number; name: string; slug: string; url: string } | null;
  categories: Array<{ id: number; name: string; slug: string; url: string }>;
  results: ListingCardData[];
  pagination: PaginationData;
  filters: {
    q: string;
    location: string;
    condition: string;
    sort: string;
    price_sort: string;
  };
}

export interface ListingDetailData {
  id: number;
  name: string;
  description: string;
  condition: string;
  category: { id: number; name: string; slug: string; url: string };
  price: string;
  location: string;
  created_at: string;
  views_count: number;
  images: Array<{ id: number; url: string }>;
  seller: {
    id: number;
    username: string;
    name: string;
    url: string;
    image: string | null;
    phone_number: string;
    whatsapp_digits: string;
    is_phone_verified: boolean;
    rating: number | null;
    review_count: number;
    reviews_url: string;
  };
  is_owner: boolean;
  is_favorited: boolean;
}

export interface SellerProfileData {
  username: string;
  display_name: string;
  profile_picture: string | null;
  location: string;
  bio: string;
  phone_number: string;
  whatsapp_digits: string;
  date_joined: string;
  is_phone_verified: boolean;
  is_owner: boolean;
  active_listings_count: number;
  listings: Array<{
    id: number;
    title: string;
    image: string | null;
    price: string;
    currency: string;
    location: string;
    url: string;
  }>;
  pagination: PaginationData;
}

export interface AuthUiData {
  labels: Record<string, string>;
  register_fields: Record<string, string>;
  account_fields: Record<string, string>;
  terms_url: string;
  privacy_url: string;
}

export interface AccountData {
  username: string;
  first_name: string;
  last_name: string;
  email: string;
  email_verified: boolean;
  agreed_to_terms: boolean;
  profile_picture: string | null;
  location: string;
  bio: string;
  phone_number: string;
  whatsapp_number: string;
  is_phone_verified: boolean;
  date_joined: string;
}

export interface FavoriteData {
  listing: ListingCardData;
  is_active: boolean;
}

export interface FavoritesResponse {
  results: FavoriteData[];
  pagination: PaginationData;
}

export interface SellerDashboardListing {
  id: number;
  title: string;
  url: string;
  price: string;
  display_price: string;
  currency: string;
  condition: string;
  condition_display: string;
  status: "active" | "inactive";
  is_active: boolean;
  created_at: string;
  views_count: number;
  thread_count: number;
  cover_image: string | null;
  category: { id: number; name: string; slug: string; url: string };
  location: string;
}

export interface SellerDashboardData {
  statistics: {
    total_listings: number;
    active_listings: number;
    inactive_listings: number;
    total_views: number;
    unread_messages: number;
  };
  listings: SellerDashboardListing[];
  labels: Record<string, string>;
}

export interface ListingCreateMetadata {
  categories: Array<{ id: number; name: string; slug: string }>;
  conditions: Array<{ value: string; label: string }>;
  currencies: Array<{ value: string; label: string }>;
  labels: Record<string, string>;
}

export interface ListingCreateResult {
  detail: string;
  listing: { id: number; url: string };
}

export interface SellerListingEditData extends ListingCreateMetadata {
  listing: {
    id: number;
    category: number;
    name: string;
    description: string;
    condition: string;
    district: string;
    sector: string;
    price: string;
    currency: string;
    is_active: boolean;
    images: Array<{ id: number; url: string; is_cover: boolean }>;
  };
}

interface CsrfResponse {
  csrfToken: string;
}

let csrfToken: string | null = null;

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly fieldErrors: Record<string, string[]> = {},
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method || "GET").toUpperCase();
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");

  if (!["GET", "HEAD", "OPTIONS", "TRACE"].includes(method)) {
    headers.set("X-CSRFToken", await getCsrfToken());
  }

  const response = await fetch(path, {
    ...init,
    method,
    headers,
    credentials: "same-origin",
  });

  if (!response.ok) {
    let message = `Django request failed (${response.status}).`;
    let fieldErrors: Record<string, string[]> = {};
    if (response.headers.get("content-type")?.includes("application/json")) {
      try {
        const payload: unknown = await response.json();
        if (payload && typeof payload === "object") {
          const errorPayload = payload as { detail?: unknown; errors?: unknown };
          if (typeof errorPayload.detail === "string") message = errorPayload.detail;
          if (errorPayload.errors && typeof errorPayload.errors === "object") {
            fieldErrors = errorPayload.errors as Record<string, string[]>;
          }
        }
      } catch {
        message = `Django request failed (${response.status}).`;
      }
    }
    throw new ApiError(message, response.status, fieldErrors);
  }
  return response.json() as Promise<T>;
}

export function getHomepage(): Promise<HomepageData> {
  return apiRequest<HomepageData>("/api/home/");
}

export function getListings(query: URLSearchParams): Promise<ListingBrowseData> {
  const suffix = query.toString();
  return apiRequest<ListingBrowseData>(`/api/listings/${suffix ? `?${suffix}` : ""}`);
}

export function getListing(id: number): Promise<ListingDetailData> {
  const pendingRequest = listingDetailRequests.get(id);
  if (pendingRequest) return pendingRequest;

  const request = apiRequest<ListingDetailData>(`/api/listings/${id}/`);
  listingDetailRequests.set(id, request);
  request.then(
    () => listingDetailRequests.delete(id),
    () => listingDetailRequests.delete(id),
  );
  return request;
}

const listingDetailRequests = new Map<number, Promise<ListingDetailData>>();

export function getSeller(username: string, page: string): Promise<SellerProfileData> {
  const query = new URLSearchParams();
  if (page) query.set("page", page);
  const suffix = query.toString();
  return apiRequest<SellerProfileData>(
    `/api/sellers/${encodeURIComponent(username)}/${suffix ? `?${suffix}` : ""}`,
  );
}

export function getAuthUi(): Promise<AuthUiData> {
  return apiRequest<AuthUiData>("/api/auth/ui/");
}

export function getAccount(): Promise<{ account: AccountData }> {
  return apiRequest<{ account: AccountData }>("/api/account/");
}

export function getFavorites(page = ""): Promise<FavoritesResponse> {
  const query = new URLSearchParams();
  if (page) query.set("page", page);
  const suffix = query.toString();
  return apiRequest<FavoritesResponse>(`/api/favorites/${suffix ? `?${suffix}` : ""}`);
}

export function submitForm<T>(path: string, body: FormData | URLSearchParams): Promise<T> {
  return apiRequest<T>(path, { method: "POST", body });
}

export function toggleFavorite(listingId: number): Promise<{ is_favorited: boolean }> {
  return submitForm<{ is_favorited: boolean }>(
    `/api/favorites/${listingId}/toggle/`,
    new URLSearchParams(),
  );
}

export function getSellerDashboard(): Promise<SellerDashboardData> {
  return apiRequest<SellerDashboardData>("/api/seller/dashboard/");
}

export function getListingCreateMetadata(): Promise<ListingCreateMetadata> {
  return apiRequest<ListingCreateMetadata>("/api/seller/listings/");
}

export function createSellerListing(body: FormData): Promise<ListingCreateResult> {
  return apiRequest<ListingCreateResult>("/api/seller/listings/", {
    method: "POST",
    body,
  });
}

export function getSellerListingEdit(id: number): Promise<SellerListingEditData> {
  return apiRequest<SellerListingEditData>(`/api/seller/listings/${id}/`);
}

export function updateSellerListing(id: number, body: FormData): Promise<ListingCreateResult> {
  return apiRequest<ListingCreateResult>(`/api/seller/listings/${id}/`, {
    method: "PATCH",
    body,
  });
}

export function updateSellerListingStatus(
  id: number,
  isActive: boolean,
): Promise<{ is_active: boolean; status: "active" | "inactive"; detail: string }> {
  return apiRequest<{ is_active: boolean; status: "active" | "inactive"; detail: string }>(
    `/api/seller/listings/${id}/status/`,
    {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ is_active: isActive }),
    },
  );
}

export function deleteSellerListing(
  id: number,
): Promise<{ detail: string; listing_id: number; statistics: SellerDashboardData["statistics"] }> {
  return apiRequest<{
    detail: string;
    listing_id: number;
    statistics: SellerDashboardData["statistics"];
  }>(
    `/api/seller/listings/${id}/`,
    { method: "DELETE" },
  );
}

export async function getCsrfToken(): Promise<string> {
  if (!csrfToken) {
    const data = await apiRequest<CsrfResponse>("/api/csrf/");
    csrfToken = data.csrfToken;
  }
  return csrfToken;
}
