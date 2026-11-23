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
  const account = dashboard.account;
  const locale = language === "fr" ? "fr-FR" : language === "en" ? "en-US" : "rw-RW";
  const avatarInitial = (account.display_name || account.username).slice(0, 1).toUpperCase();

  return (
    <main className="container py-4 py-md-5 seller-dashboard">
      {successMessage && (
        <div className="alert alert-success" role="status">
          {successMessage}
        </div>
      )}

      <header className="seller-dashboard-header mb-4">
        <h1 className="h3 mb-1">{labels.title}</h1>
        <p className="text-muted mb-0">{labels.subtitle}</p>
      </header>

      <section className="account-card seller-profile-card mb-4" aria-label={labels.title}>
        {account.profile_picture ? (
          <img
            src={account.profile_picture}
            alt={account.display_name}
            className="account-avatar"
            onError={(e) => {
              e.currentTarget.style.display = "none";
              const fallback = e.currentTarget.nextElementSibling;
              if (fallback) {
                (fallback as HTMLElement).style.display = "inline-flex";
              }
            }}
          />
        ) : null}
        <span className="account-avatar account-avatar-fallback" style={{ display: account.profile_picture ? "none" : "inline-flex" }} aria-hidden="true">
          {avatarInitial}
        </span>
        <div className="seller-profile-copy">
          <div className="fw-bold seller-profile-name">{account.display_name}</div>
          {account.phone_number && (
            <div className="small text-muted">📞 {account.phone_number}</div>
          )}
          {account.whatsapp_number && (
            <div className="small text-muted">🟢 {account.whatsapp_number}</div>
          )}
          <div className="small mt-1">
            <a href={account.reviews_url} className="seller-reviews-link">
              {labels.my_reviews}
            </a>
          </div>
        </div>
      </section>

      <div className="row g-3 mb-4 seller-dashboard-stats">
        <div className="col-6 col-md">
          <div className="seller-stat-card">
            <strong>{dashboard.statistics.total_listings}</strong>
            <span>{labels.total_listings}</span>
          </div>
        </div>
        <div className="col-6 col-md">
          <div className="seller-stat-card">
            <strong>{dashboard.statistics.total_views}</strong>
            <span>{labels.total_views}</span>
          </div>
        </div>
        <div className="col-6 col-md">
          <div className="seller-stat-card">
            <strong>{dashboard.statistics.unread_messages}</strong>
            <span>{labels.unread_messages}</span>
          </div>
        </div>
        <div className="col-6 col-md">
          <a href="/listings/favorites/" className="seller-stat-card seller-stat-card-action">
            <strong aria-hidden="true">★</strong>
            <span>{labels.favorites}</span>
          </a>
        </div>
        <div className="col-6 col-md">
          <a href="/listings/add/" className="seller-stat-card seller-stat-card-action">
            <strong aria-hidden="true">➕</strong>
            <span>{labels.add_listing}</span>
          </a>
        </div>
      </div>

      <div className="row g-4 seller-dashboard-panels">
        <section className="col-lg-7" aria-labelledby="seller-listings-title">
          <h2 className="h5 mb-3" id="seller-listings-title">
            {labels.my_listings}
          </h2>
          {dashboard.listings.length === 0 ? (
            <p className="text-muted seller-dashboard-empty">
              {labels.no_listings}{" "}
              <a href="/listings/add/">{labels.add_listing}</a>.
            </p>
          ) : (
            <div className="seller-listing-list">
              {dashboard.listings.map((listing) => {
                const moderated = listing.moderation_status !== "visible";
                return (
                  <article className="seller-listing-row" key={listing.id}>
                    <a
                      href={listing.is_active && !moderated ? listing.url : `/listings/${listing.id}/edit/`}
                      className="seller-listing-main text-decoration-none text-body"
                    >
                      {listing.cover_image ? (
                        <img src={listing.cover_image} alt={listing.title} onError={(e) => {
                          e.currentTarget.style.display = "none";
                          const placeholder = e.currentTarget.parentNode?.querySelector(".seller-listing-image-placeholder");
                          if (placeholder) {
                            (placeholder as HTMLElement).style.display = "inline-flex";
                          }
                        }} />
                      ) : null}
                      <span className="seller-listing-image-placeholder" style={{ display: listing.cover_image ? "none" : "inline-flex" }} aria-label={labels.empty_image}>
                        🖼
                      </span>
                      <span className="seller-listing-copy">
                        <strong>{listing.title}</strong>
                        <span className="seller-listing-price">{listing.display_price}</span>
                        <span className="text-muted small">{listing.location}</span>
                        {!listing.is_active && !moderated && (
                          <span className="badge bg-secondary align-self-start">
                            {labels.inactive}
                          </span>
                        )}
                        {moderated && (
                          <>
                            <span className="badge bg-warning text-dark align-self-start">
                              {listing.moderation_status === "hidden"
                                ? labels.moderation_hidden
                                : labels.moderation_removed}
                            </span>
                            {listing.moderation_reason && (
                              <span className="text-muted small">{listing.moderation_reason}</span>
                            )}
                          </>
                        )}
                      </span>
                    </a>
                    <div className="seller-listing-meta">
                      <div className="seller-listing-counts">
                        <span title={labels.views}>👁 {listing.views_count}</span>
                        <span title={labels.conversations}>💬 {listing.thread_count}</span>
                      </div>
                      <div className="seller-listing-actions">
                        <a
                          className="btn btn-sm btn-outline-brand"
                          href={`/listings/${listing.id}/edit/`}
                          aria-label={`${labels.edit_listing} ${listing.title}`}
                          title={labels.edit_listing}
                        >
                          ✏️
                        </a>
                        {!moderated && (
                          <button
                            className={`btn btn-sm ${
                              listing.is_active ? "btn-outline-secondary" : "btn-outline-success"
                            }`}
                            type="button"
                            disabled={savingStatusIds.has(listing.id)}
                            aria-label={
                              listing.is_active ? labels.hide_listing : labels.activate_listing
                            }
                            title={listing.is_active ? labels.hide_listing : labels.activate_listing}
                            onClick={() => void toggleListingStatus(listing.id, !listing.is_active)}
                          >
                            {savingStatusIds.has(listing.id)
                              ? "…"
                              : listing.is_active
                                ? "👁‍🗨"
                                : "👁"}
                          </button>
                        )}
                        <button
                          className="btn btn-sm btn-outline-danger"
                          type="button"
                          disabled={deletingListingIds.has(listing.id)}
                          aria-label={`${labels.delete_listing} ${listing.title}`}
                          title={labels.delete_listing}
                          onClick={() => void deleteListing(listing.id, listing.title)}
                        >
                          {deletingListingIds.has(listing.id) ? "…" : "🗑"}
                        </button>
                      </div>
                      {statusErrors[listing.id] && (
                        <span className="small text-danger" role="alert">
                          {statusErrors[listing.id]}
                        </span>
                      )}
                      {deletionErrors[listing.id] && (
                        <span className="small text-danger" role="alert">
                          {deletionErrors[listing.id]}
                        </span>
                      )}
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </section>

        <section className="col-lg-5" aria-labelledby="seller-messages-title">
          <h2 className="h5 mb-3" id="seller-messages-title">
            {labels.recent_messages}
          </h2>
          {dashboard.recent_messages.length === 0 ? (
            <div className="seller-messages-empty">
              <div className="seller-messages-empty-icon" aria-hidden="true">
                💬
              </div>
              <p className="mb-0">{labels.no_messages}</p>
            </div>
          ) : (
            <div className="seller-message-list">
              {dashboard.recent_messages.map((message) => (
                <a
                  key={message.id}
                  href={message.url}
                  className={`seller-message-row${message.is_read ? "" : " is-unread"}`}
                >
                  <div className="seller-message-top">
                    <strong>{message.sender.username}</strong>
                    <small>
                      {new Intl.DateTimeFormat(locale, {
                        day: "numeric",
                        month: "short",
                        hour: "2-digit",
                        minute: "2-digit",
                      }).format(new Date(message.created_at))}
                    </small>
                  </div>
                  <div className="seller-message-listing text-muted small">
                    {message.listing.name}
                  </div>
                  <div className="seller-message-body">{message.body}</div>
                </a>
              ))}
            </div>
          )}
        </section>
      </div>

      <div className="seller-account-actions">
        <a href="/accounts/edit/" className="account-action-btn account-action-edit">
          ✏️ {labels.edit_account}
        </a>
        <a href="/accounts/delete/" className="account-action-btn account-action-delete">
          🗑 {labels.delete_account}
        </a>
      </div>
    </main>
  );
}
