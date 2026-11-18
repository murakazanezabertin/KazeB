import { useEffect, useState } from "react";

import {
  ApiError,
  deleteSellerListing,
  getSellerDashboard,
  updateSellerListingStatus,
  type SellerDashboardData,
} from "./api/client";
import { sellerMessages, type SellerLanguage } from "./sellerMessages";

type Props = {
  language: SellerLanguage;
};

export default function SellerDashboard({ language }: Props) {
  const [dashboard, setDashboard] = useState<SellerDashboardData | null>(null);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [savingStatusIds, setSavingStatusIds] = useState<Set<number>>(() => new Set());
  const [statusErrors, setStatusErrors] = useState<Record<number, string>>({});
  const [deletingListingIds, setDeletingListingIds] = useState<Set<number>>(() => new Set());
  const [deletionErrors, setDeletionErrors] = useState<Record<number, string>>({});

  async function loadDashboard() {
    setError("");
    try {
      const data = await getSellerDashboard();
      setDashboard(data);
      const saved = new URLSearchParams(window.location.search).get("saved");
      if (saved === "created" || saved === "updated") {
        setSuccessMessage(
          saved === "created" ? data.labels.listing_created : data.labels.listing_updated,
        );
        const url = new URL(window.location.href);
        url.searchParams.delete("saved");
        window.history.replaceState({}, "", url);
      }
    } catch (loadError) {
      if (loadError instanceof ApiError && [401, 403].includes(loadError.status)) {
        setError(sellerMessages[language].authRequired);
      } else {
        setError(
          loadError instanceof ApiError
            ? loadError.message
            : sellerMessages[language].dashboardError,
        );
      }
    }
  }

  useEffect(() => {
    void loadDashboard();
  }, []);

  async function toggleListingStatus(listingId: number, isActive: boolean) {
    setSavingStatusIds((current) => new Set(current).add(listingId));
    setStatusErrors((current) => ({ ...current, [listingId]: "" }));
    try {
      const result = await updateSellerListingStatus(listingId, isActive);
      setDashboard((current) => {
        if (!current) return current;
        const existing = current.listings.find((listing) => listing.id === listingId);
        if (!existing) return current;

        const activeDelta = Number(result.is_active) - Number(existing.is_active);
        return {
          ...current,
          statistics: {
            ...current.statistics,
            active_listings: current.statistics.active_listings + activeDelta,
            inactive_listings: current.statistics.inactive_listings - activeDelta,
          },
          listings: current.listings.map((listing) =>
            listing.id === listingId
              ? {
                  ...listing,
                  is_active: result.is_active,
                  status: result.status,
                }
              : listing,
          ),
        };
      });
    } catch (statusError) {
      setStatusErrors((current) => ({
        ...current,
        [listingId]:
          statusError instanceof Error
            ? statusError.message
            : "Unable to update listing status.",
      }));
    } finally {
      setSavingStatusIds((current) => {
        const next = new Set(current);
        next.delete(listingId);
        return next;
      });
    }
  }

  async function deleteListing(listingId: number, listingTitle: string) {
    if (!dashboard) return;
    if (!window.confirm(`${dashboard.labels.confirm_delete_listing}\n\n${listingTitle}`)) {
      return;
    }

    setDeletingListingIds((current) => new Set(current).add(listingId));
    setDeletionErrors((current) => ({ ...current, [listingId]: "" }));
    try {
      const result = await deleteSellerListing(listingId);
      setDashboard((current) =>
        current
          ? {
              ...current,
              statistics: result.statistics,
              listings: current.listings.filter((listing) => listing.id !== listingId),
            }
          : current,
      );
    } catch (deleteError) {
      setDeletionErrors((current) => ({
        ...current,
        [listingId]:
          deleteError instanceof Error
            ? deleteError.message
            : "Unable to delete listing.",
      }));
    } finally {
      setDeletingListingIds((current) => {
        const next = new Set(current);
        next.delete(listingId);
        return next;
      });
    }
  }

  if (error) {
    return (
      <main className="container py-4 py-md-5">
        <div className="alert alert-danger" role="alert">{error}</div>
      </main>
    );
  }

  if (!dashboard) {
    return (
      <main className="container py-4 py-md-5" aria-live="polite">
        {sellerMessages[language].loading}
      </main>
    );
  }

  const labels = dashboard.labels;
  const locale = language === "fr" ? "fr-FR" : language === "en" ? "en-US" : "rw-RW";

  return (
    <main className="container py-4 py-md-5 seller-dashboard">
      {successMessage && (
        <div className="alert alert-success" role="status">
          {successMessage}
        </div>
      )}
      <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-4">
        <div>
          <h1 className="h3 mb-1">{labels.title}</h1>
          <p className="text-muted mb-0">{labels.subtitle}</p>
        </div>
        <a href="/listings/add/" className="btn btn-brand">
          ➕ {labels.add_listing}
        </a>
      </div>

      <div className="row g-3 mb-4 seller-dashboard-stats">
        {[
          [labels.total_listings, dashboard.statistics.total_listings],
          [labels.active_listings, dashboard.statistics.active_listings],
          [labels.inactive_listings, dashboard.statistics.inactive_listings],
          [labels.total_views, dashboard.statistics.total_views],
          [labels.unread_messages, dashboard.statistics.unread_messages],
        ].map(([label, value]) => (
          <div className="col-6 col-md-4 col-lg" key={String(label)}>
            <div className="seller-stat-card">
              <strong>{value}</strong>
              <span>{label}</span>
            </div>
          </div>
        ))}
      </div>

      <section aria-labelledby="seller-listings-title">
        <h2 className="h5 mb-3" id="seller-listings-title">{labels.my_listings}</h2>
        {dashboard.listings.length === 0 ? (
          <p className="text-muted seller-dashboard-empty">
            {labels.no_listings}
            {" "}
            <a href="/listings/add/">{labels.add_listing}</a>.
          </p>
        ) : (
          <div className="seller-listing-list">
            {dashboard.listings.map((listing) => (
              <article className="seller-listing-row" key={listing.id}>
                <a
                  href={listing.is_active ? listing.url : `/listings/${listing.id}/edit/`}
                  className="seller-listing-main text-decoration-none text-body"
                >
                  {listing.cover_image ? (
                    <img src={listing.cover_image} alt={listing.title} />
                  ) : (
                    <span className="seller-listing-image-placeholder" aria-label={labels.empty_image}>
                      🖼
                    </span>
                  )}
                  <span className="seller-listing-copy">
                    <strong>{listing.title}</strong>
                    <span className="seller-listing-price">{listing.display_price}</span>
                    <span className="text-muted small">
                      {listing.category.name} · {listing.location} · {listing.condition_display}
                    </span>
                  </span>
                </a>
                <div className="seller-listing-meta">
                  <a
                    className="btn btn-sm btn-outline-brand"
                    href={`/listings/${listing.id}/edit/`}
                    aria-label={`${labels.edit_listing} ${listing.title}`}
                  >
                    ✏️
                  </a>
                  <span className={`badge ${listing.is_active ? "bg-success" : "bg-secondary"}`}>
                    {listing.is_active ? labels.active : labels.inactive}
                  </span>
                  <button
                    className={`btn btn-sm ${listing.is_active ? "btn-outline-secondary" : "btn-outline-success"}`}
                    type="button"
                    disabled={savingStatusIds.has(listing.id)}
                    aria-label={listing.is_active ? labels.hide_listing : labels.activate_listing}
                    onClick={() => void toggleListingStatus(listing.id, !listing.is_active)}
                  >
                    {savingStatusIds.has(listing.id)
                      ? labels.status_saving
                      : listing.is_active
                        ? labels.hide_listing
                        : labels.activate_listing}
                  </button>
                  {statusErrors[listing.id] && (
                    <span className="small text-danger" role="alert">
                      {statusErrors[listing.id]}
                    </span>
                  )}
                  <button
                    className="btn btn-sm btn-outline-danger"
                    type="button"
                    disabled={deletingListingIds.has(listing.id)}
                    onClick={() => void deleteListing(listing.id, listing.title)}
                  >
                    {deletingListingIds.has(listing.id)
                      ? labels.delete_loading
                      : labels.delete_listing}
                  </button>
                  {deletionErrors[listing.id] && (
                    <span className="small text-danger" role="alert">
                      {deletionErrors[listing.id]}
                    </span>
                  )}
                  <span className="small text-muted">
                    👁 {listing.views_count} {labels.views}
                  </span>
                  <span className="small text-muted">
                    💬 {listing.thread_count} {labels.conversations}
                  </span>
                  <span className="small text-muted">
                    {labels.created}:{" "}
                    {new Intl.DateTimeFormat(locale, {
                      year: "numeric",
                      month: "short",
                      day: "numeric",
                    }).format(new Date(listing.created_at))}
                  </span>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
