import { useEffect, useState } from "react";

import {
  getListing,
  getListings,
  getSeller,
  type HomepageData,
  type ListingBrowseData,
  type ListingCardData,
  type ListingDetailData,
  type PaginationData,
  type SellerProfileData,
} from "./api/client";

type Labels = HomepageData["labels"];

function formatSellerPrice(price: string, currency: string, locale: string) {
  const isUsd = currency === "USD";
  const formatted = new Intl.NumberFormat(locale, {
    minimumFractionDigits: isUsd ? 2 : 0,
    maximumFractionDigits: isUsd ? 2 : 0,
  }).format(Number(price));
  return isUsd ? `$${formatted}` : `${formatted} ${currency}`;
}

function PageMessage({ children, error = false }: { children: string; error?: boolean }) {
  return (
    <p className={error ? "alert alert-danger" : "text-muted py-4"} role={error ? "alert" : undefined}>
      {children}
    </p>
  );
}

function ListingCards({
  listings,
  labels,
}: {
  listings: ListingCardData[];
  labels: Labels;
}) {
  return (
    <div className="row row-cols-1 row-cols-sm-2 row-cols-lg-4 g-4">
      {listings.map((listing) => (
        <div className="col" key={listing.id}>
          <div className="card listing-card h-100">
            <a href={listing.url} className="text-decoration-none text-body">
              {listing.image ? (
                <img
                  src={listing.image}
                  className="card-img-top listing-card-img"
                  alt={listing.name}
                  loading="lazy"
                />
              ) : (
                <div className="listing-card-img listing-card-img-placeholder">{labels.empty_image}</div>
              )}
              <div className="card-body">
                <h2 className="h6 mb-1 text-truncate">{listing.name}</h2>
                <p className="fw-bold text-brand mb-1">{listing.price}</p>
                <p className="small text-muted mb-0">{listing.location}</p>
              </div>
            </a>
            <div className="card-footer bg-white border-0 pt-0">
              <a href={listing.seller.url} className="seller-card-link">
                {listing.seller.image ? (
                  <img src={listing.seller.image} className="seller-avatar-sm" alt="" loading="lazy" />
                ) : (
                  <span className="seller-avatar-sm seller-avatar-fallback" aria-hidden="true">
                    {listing.seller.username.slice(0, 1).toUpperCase()}
                  </span>
                )}
                <span>{listing.seller.name}</span>
              </a>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function Pagination({
  pagination,
  labels,
}: {
  pagination: PaginationData;
  labels: Labels;
}) {
  const query = new URLSearchParams(window.location.search);
  const linkForPage = (page: number) => {
    const params = new URLSearchParams(query);
    params.set("page", String(page));
    return `${window.location.pathname}?${params.toString()}`;
  };

  if (pagination.pages <= 1) return null;
  return (
    <nav className="mt-4" aria-label="Listing pages">
      <ul className="pagination justify-content-center">
        {pagination.has_previous && (
          <li className="page-item">
            <a className="page-link" href={linkForPage(pagination.page - 1)}>
              {labels.previous_page}
            </a>
          </li>
        )}
        <li className="page-item disabled" aria-current="page">
          <span className="page-link">{pagination.page} / {pagination.pages}</span>
        </li>
        {pagination.has_next && (
          <li className="page-item">
            <a className="page-link" href={linkForPage(pagination.page + 1)}>
              {labels.next_page}
            </a>
          </li>
        )}
      </ul>
    </nav>
  );
}

function ListingBrowse({ labels }: { labels: Labels }) {
  const path = window.location.pathname;
  const categoryMatch = path.match(/^\/listings\/category\/([^/]+)\/?$/);
  const categorySlug = categoryMatch ? decodeURIComponent(categoryMatch[1]) : "";
  const params = new URLSearchParams(window.location.search);
  if (categorySlug) params.set("category", categorySlug);

  const [data, setData] = useState<ListingBrowseData | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    getListings(params)
      .then((response) => {
        if (active) setData(response);
      })
      .catch((loadError: unknown) => {
        if (active) {
          setError(loadError instanceof Error ? loadError.message : "Unable to load listings.");
        }
      });
    return () => {
      active = false;
    };
  }, []);

  if (error) return <main className="container py-4"><PageMessage error>{error}</PageMessage></main>;
  if (!data) return <main className="container py-4"><p aria-live="polite">Loading listings…</p></main>;

  return (
    <main className="container py-4">
      <div className="d-flex flex-wrap justify-content-between align-items-baseline gap-2 mb-3">
        <h1 className="h3 mb-0">{data.category?.name || labels.all_listings}</h1>
        <span className="text-muted small">{data.pagination.count}</span>
      </div>

      <form action="/listings/search/" method="get" className="marketplace-filters card card-body mb-4">
        <div className="row g-3 align-items-end">
          <div className="col-12 col-md-6 col-lg-3">
            <label className="form-label" htmlFor="browse-query">{labels.search}</label>
            <input id="browse-query" name="q" className="form-control" defaultValue={data.filters.q} />
          </div>
          <div className="col-12 col-md-6 col-lg-3">
            <label className="form-label" htmlFor="browse-location">{labels.search_placeholder}</label>
            <input
              id="browse-location"
              name="location"
              className="form-control"
              defaultValue={data.filters.location}
            />
          </div>
          <div className="col-12 col-md-6 col-lg-2">
            <label className="form-label" htmlFor="browse-category">{labels.categories}</label>
            <select id="browse-category" name="category" className="form-select" defaultValue={data.category?.slug || ""}>
              <option value="">{labels.all_listings}</option>
              {data.categories.map((category) => (
                <option key={category.id} value={category.slug}>{category.name}</option>
              ))}
            </select>
          </div>
          <div className="col-12 col-md-6 col-lg-2">
            <label className="form-label" htmlFor="browse-condition">{labels.all_conditions}</label>
            <select id="browse-condition" name="condition" className="form-select" defaultValue={data.filters.condition}>
              <option value="">{labels.all_conditions}</option>
              <option value="new">{labels.new_condition}</option>
              <option value="used">{labels.used_condition}</option>
            </select>
          </div>
          <div className="col-12 col-md-6 col-lg-2">
            <label className="form-label" htmlFor="browse-sort">{labels.newest}</label>
            <select id="browse-sort" name="sort" className="form-select" defaultValue={data.filters.sort}>
              <option value="newest">{labels.newest}</option>
              <option value="oldest">{labels.oldest}</option>
              <option value="most_viewed">{labels.most_viewed}</option>
            </select>
          </div>
          <div className="col-12 col-md-6 col-lg-3">
            <label className="form-label" htmlFor="browse-price">{labels.all_prices}</label>
            <select id="browse-price" name="price_sort" className="form-select" defaultValue={data.filters.price_sort}>
              <option value="">{labels.all_prices}</option>
              <option value="asc">{labels.lowest_price}</option>
              <option value="desc">{labels.highest_price}</option>
            </select>
          </div>
          <div className="col-12 col-md-6 col-lg-2">
            <button type="submit" className="btn btn-brand w-100">{labels.search}</button>
          </div>
        </div>
      </form>

      {data.results.length > 0 ? (
        <>
          <ListingCards listings={data.results} labels={labels} />
          <Pagination pagination={data.pagination} labels={labels} />
        </>
      ) : (
        <PageMessage>{labels.no_results}</PageMessage>
      )}
    </main>
  );
}

function ListingDetail({
  labels,
  csrfToken,
  isAuthenticated,
}: {
  labels: Labels;
  csrfToken: string;
  isAuthenticated: boolean;
}) {
  const id = Number(window.location.pathname.match(/^\/listings\/(\d+)\/?$/)?.[1]);
  const [listing, setListing] = useState<ListingDetailData | null>(null);
  const [error, setError] = useState("");
  const [activeImage, setActiveImage] = useState(0);
  const [copiedText, setCopiedText] = useState("");

  useEffect(() => {
    let active = true;
    getListing(id)
      .then((response) => {
        if (active) setListing(response);
      })
      .catch((loadError: unknown) => {
        if (active) {
          setError(loadError instanceof Error ? loadError.message : "Unable to load this listing.");
        }
      });
    return () => {
      active = false;
    };
  }, [id]);

  if (error) return <main className="container py-4"><PageMessage error>{error}</PageMessage></main>;
  if (!listing) return <main className="container py-4"><p aria-live="polite">Loading listing…</p></main>;

  const seller = listing.seller;
  const listingUrl = window.location.href;
  const whatsappUrl = seller.whatsapp_digits
    ? `https://wa.me/${seller.whatsapp_digits}?text=${encodeURIComponent(`Muraho, nabonye icyo ugurisha "${listing.name}" kuri KazeB`)}`
    : "";
  const locale = document.documentElement.lang || "rw";
  const encodedListingUrl = encodeURIComponent(listingUrl);
  const shareText = encodeURIComponent(`Reba icyo ngurisha "${listing.name}" kuri KazeB: ${listingUrl}`);

  async function copyToClipboard(value: string) {
    try {
      await navigator.clipboard.writeText(value);
      setCopiedText(value);
    } catch {
      window.prompt(labels.copy_listing_link, value);
    }
  }

  return (
    <main className="container py-4">
      <div className="listing-top-meta mb-3">
        <span>{new Intl.DateTimeFormat(locale, { dateStyle: "medium" }).format(new Date(listing.created_at))}</span>
        <span className="mx-1">·</span>
        <a href={seller.reviews_url} className="text-decoration-none">
          {seller.rating !== null ? (
            <><span className="text-brand fw-bold">⭐ {seller.rating.toFixed(1)}</span> <span className="text-muted">({seller.review_count})</span></>
          ) : <span className="text-muted">{labels.no_reviews}</span>}
        </a>
        <span className="mx-1">·</span>
        <a href={seller.url} className="seller-detail-link">
          {seller.image ? (
            <img src={seller.image} className="seller-avatar-sm" alt="" />
          ) : (
            <span className="seller-avatar-sm seller-avatar-fallback" aria-hidden="true">{seller.username.slice(0, 1).toUpperCase()}</span>
          )}
          <span>{labels.posted_by} {seller.name}</span>
        </a>
        {seller.is_phone_verified && <span className="badge bg-success-subtle text-success-emphasis ms-1">✅ {labels.phone_verified}</span>}
      </div>

      <div className="row g-4">
        <div className="col-lg-7">
          {listing.images.length ? (
            <div className="listing-gallery">
              <img
                src={listing.images[activeImage]?.url}
                className="listing-photo mb-3"
                alt={listing.name}
              />
              {listing.images.length > 1 && (
                <div className="d-flex flex-wrap gap-2" aria-label={listing.name}>
                  {listing.images.map((image, index) => (
                    <button
                      type="button"
                      key={image.id}
                      className={`listing-thumbnail${index === activeImage ? " is-active" : ""}`}
                      onClick={() => setActiveImage(index)}
                      aria-label={`${listing.name} ${index + 1}`}
                      aria-pressed={index === activeImage}
                    >
                      <img src={image.url} alt="" />
                    </button>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="listing-photo listing-card-img-placeholder mb-3">{labels.empty_image}</div>
          )}
        </div>

        <div className="col-lg-5">
          <a href={listing.category.url} className="badge bg-secondary-subtle text-secondary-emphasis mb-2 text-decoration-none">
            {listing.category.name}
          </a>
          <h1 className="h3">{listing.name}</h1>
          <p className="fs-4 fw-bold text-brand">{listing.price}</p>
          <p className="text-muted mb-1">📍 {listing.location}</p>
          <p className="text-muted mb-3">{listing.condition}</p>
          <p className="listing-description">{listing.description}</p>
          <p className="small text-muted">{labels.listing_views}: {listing.views_count}</p>

          {!listing.is_owner && (
            <form method="post" action={`/listings/${listing.id}/favorite/`} className="mb-3">
              <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken} />
              <input type="hidden" name="next" value={window.location.pathname + window.location.search} />
              <button type="submit" className={`favorite-btn${listing.is_favorited ? " is-favorited" : ""}`}>
                {listing.is_favorited ? "★" : "☆"} {listing.is_favorited ? labels.saved_favorite : labels.save_favorite}
              </button>
            </form>
          )}

          {!listing.is_owner && (
            <a href={`/trust/listing/${listing.id}/report/`} className="report-link d-inline-flex align-items-center gap-1 mb-2">
              ⚠️ {labels.report_listing}
            </a>
          )}

          <hr />
          {listing.is_owner ? (
            <>
              <h2 className="h6">{labels.share_listing}</h2>
              <div className="d-grid gap-2 contact-options">
                <a href={`https://wa.me/?text=${shareText}`} target="_blank" rel="noopener noreferrer" className="btn btn-success">☘ WhatsApp</a>
                <a href={`https://www.facebook.com/sharer/sharer.php?u=${encodedListingUrl}`} target="_blank" rel="noopener noreferrer" className="btn btn-outline-secondary">📘 Facebook</a>
                <a href={`https://t.me/share/url?url=${encodedListingUrl}&text=${encodeURIComponent(`Reba icyo ngurisha "${listing.name}"`)}`} target="_blank" rel="noopener noreferrer" className="btn btn-outline-secondary">✈️ Telegram</a>
                <button type="button" className="btn btn-outline-secondary" onClick={() => void copyToClipboard(listingUrl)}>
                  🔗 {labels.copy_listing_link}{copiedText === listingUrl ? " ✓" : ""}
                </button>
              </div>
              <div className="d-flex gap-2 mt-3">
                <a href={`/listings/${listing.id}/edit/`} className="btn btn-outline-brand flex-fill">{labels.edit_listing}</a>
                <a href={`/listings/${listing.id}/delete/`} className="btn btn-outline-danger flex-fill">{labels.delete_listing}</a>
              </div>
            </>
          ) : (
            <>
              <h2 className="h6">{labels.contact_seller}</h2>
              <div className="d-grid gap-2 contact-options">
                <a
                  href={isAuthenticated
                    ? `/messages/listing/${listing.id}/`
                    : `/accounts/login/?next=${encodeURIComponent(`/messages/listing/${listing.id}/`)}`}
                  className="btn btn-brand"
                >
                  💬 {isAuthenticated ? labels.send_message : labels.login_to_message}
                </a>
                {whatsappUrl && <a href={whatsappUrl} target="_blank" rel="noopener noreferrer" className="btn btn-success">☘ {labels.whatsapp_seller}</a>}
                {seller.phone_number && (
                  <>
                    <a href={`tel:${seller.phone_number}`} className="btn btn-outline-secondary">📞 {labels.call_seller}: {seller.phone_number}</a>
                    <button type="button" className="btn btn-outline-secondary" onClick={() => void copyToClipboard(seller.phone_number)}>
                      📋 {labels.copy_phone}: {seller.phone_number}{copiedText === seller.phone_number ? " ✓" : ""}
                    </button>
                  </>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </main>
  );
}

function SellerProfile({ labels, isAuthenticated }: { labels: Labels; isAuthenticated: boolean }) {
  const match = window.location.pathname.match(/^\/seller\/([^/]+)\/?$/);
  const username = match ? decodeURIComponent(match[1]) : "";
  const page = new URLSearchParams(window.location.search).get("page") || "";
  const [seller, setSeller] = useState<SellerProfileData | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    getSeller(username, page)
      .then((response) => {
        if (active) setSeller(response);
      })
      .catch((loadError: unknown) => {
        if (active) {
          setError(loadError instanceof Error ? loadError.message : "Unable to load this seller.");
        }
      });
    return () => {
      active = false;
    };
  }, [username, page]);

  if (error) return <main className="container py-4"><PageMessage error>{error}</PageMessage></main>;
  if (!seller) return <main className="container py-4"><p aria-live="polite">Loading seller…</p></main>;

  const firstListing = seller.listings[0];
  const whatsappUrl = seller.whatsapp_digits
    ? `https://wa.me/${seller.whatsapp_digits}?text=${encodeURIComponent("Muraho, nabonye urupapuro rwawe kuri KazeB")}`
    : "";
  const locale = document.documentElement.lang || "rw";
  const cards: ListingCardData[] = seller.listings.map((listing) => ({
    id: listing.id,
    name: listing.title,
    url: listing.url,
    image: listing.image,
    price: formatSellerPrice(listing.price, listing.currency, document.documentElement.lang || "rw"),
    location: listing.location,
    seller: {
      username: seller.username,
      name: seller.display_name,
      url: window.location.pathname,
      image: seller.profile_picture,
    },
  }));

  return (
    <main className="container py-4">
      <section className="seller-profile-card mb-4">
        <div className="d-flex flex-column flex-sm-row align-items-center align-items-sm-start gap-3">
          {seller.profile_picture ? (
            <img src={seller.profile_picture} className="seller-avatar-lg" alt="" />
          ) : (
            <span className="seller-avatar-lg seller-avatar-fallback" aria-hidden="true">{seller.username.slice(0, 1).toUpperCase()}</span>
          )}
          <div className="text-center text-sm-start flex-grow-1">
            <h1 className="h3 mb-1">{seller.display_name}</h1>
            <p className="text-muted mb-2">@{seller.username}</p>
            {seller.location && <p className="mb-2">📍 {seller.location}</p>}
            <p className="small text-muted mb-2">
              {labels.joined_kazeb} {new Intl.DateTimeFormat(locale, { dateStyle: "medium" }).format(new Date(seller.date_joined))}
            </p>
            {seller.is_phone_verified && <span className="badge bg-success-subtle text-success-emphasis">✅ {labels.phone_verified}</span>}
          </div>
          <div className="seller-listing-stat">
            <strong>{seller.active_listings_count}</strong>
            <span>{labels.seller_listing_count}</span>
          </div>
        </div>
        <hr />
        <h2 className="h5">{labels.seller_bio}</h2>
        {seller.bio ? <p className="mb-0 seller-bio">{seller.bio}</p> : <p className="text-muted mb-0">{labels.no_seller_bio}</p>}

        {!seller.is_owner && (
          <>
            <hr />
            <h2 className="h5">{labels.contact_seller}</h2>
            <div className="d-flex flex-wrap gap-2">
              {firstListing && (
                <a
                  href={isAuthenticated
                    ? `/messages/listing/${firstListing.id}/`
                    : `/accounts/login/?next=${encodeURIComponent(`/messages/listing/${firstListing.id}/`)}`}
                  className="btn btn-brand"
                >
                  💬 {isAuthenticated ? labels.send_message : labels.login_to_message}
                </a>
              )}
              {whatsappUrl && <a href={whatsappUrl} target="_blank" rel="noopener noreferrer" className="btn btn-success">☘ WhatsApp</a>}
              {seller.phone_number && <a href={`tel:${seller.phone_number}`} className="btn btn-outline-secondary">📞 {labels.call_seller}</a>}
              {!firstListing && !seller.phone_number && !whatsappUrl && <p className="text-muted mb-0">{labels.no_contact_options}</p>}
            </div>
          </>
        )}
      </section>

      <section>
        <div className="d-flex justify-content-between align-items-baseline mb-3">
          <h2 className="h4 mb-0">{labels.seller_listings}</h2>
          <span className="text-muted small">{seller.active_listings_count}</span>
        </div>
        {cards.length ? (
          <>
            <ListingCards listings={cards} labels={labels} />
            <Pagination pagination={seller.pagination} labels={labels} />
          </>
        ) : <PageMessage>{labels.no_seller_listings}</PageMessage>}
      </section>
    </main>
  );
}

export default function Marketplace({
  labels,
  csrfToken,
  isAuthenticated,
}: {
  labels: Labels;
  csrfToken: string;
  isAuthenticated: boolean;
}) {
  const path = window.location.pathname;
  if (path === "/listings/search/" || path.startsWith("/listings/category/")) {
    return <ListingBrowse labels={labels} />;
  }
  if (/^\/listings\/\d+\/?$/.test(path)) {
    return <ListingDetail labels={labels} csrfToken={csrfToken} isAuthenticated={isAuthenticated} />;
  }
  if (/^\/seller\/[^/]+\/?$/.test(path)) {
    return <SellerProfile labels={labels} isAuthenticated={isAuthenticated} />;
  }
  return <main className="container py-4"><PageMessage error>Page not found.</PageMessage></main>;
}
