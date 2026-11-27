import { useEffect, useState, type FormEvent } from "react";

import {
  getCsrfToken,
  getFavorites,
  getHomepage,
  submitForm,
  toggleFavorite,
  type HomepageData,
} from "./api/client";
import { LanguageProvider, useLanguage } from "./LanguageContext";
import AdminDashboard from "./AdminDashboard";
import AccountPages from "./Accounts";
import Marketplace from "./Marketplace";
import SellerDashboard from "./SellerDashboard";
import SellerListingCreate from "./SellerListingCreate";
import SellerListingEdit from "./SellerListingEdit";

const heroSlides = [
  { src: "car.png", alt: "Car" },
  { src: "house.png", alt: "House" },
  { src: "smartphone.png", alt: "Smartphone" },
  { src: "motorcycle.png", alt: "Motorcycle" },
  { src: "laptop.png", alt: "Laptop" },
  { src: "sofa.png", alt: "Sofa" },
  { src: "shoes.png", alt: "Shoes" },
  { src: "clothes.png", alt: "Clothes" },
];

function SearchForm({
  search,
  placeholder,
  className,
}: {
  search: string;
  placeholder: string;
  className: string;
}) {
  return (
    <form action="/listings/search/" method="get" className={className}>
      <div className="input-group">
        <span className="input-group-text bg-white border-end-0" aria-hidden="true">
          🔍
        </span>
        <input
          type="search"
          name="q"
          className="form-control border-start-0"
          placeholder={placeholder}
        />
        <button type="submit" className="btn btn-brand">
          {search}
        </button>
      </div>
    </form>
  );
}

function App() {
  const pathname = window.location.pathname;
  const [homepage, setHomepage] = useState<HomepageData | null>(null);
  const [csrfToken, setCsrfToken] = useState("");
  const [error, setError] = useState("");
  const [activeSlide, setActiveSlide] = useState(0);
  const [menuOpen, setMenuOpen] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [footerExpanded, setFooterExpanded] = useState<Set<string>>(new Set());
  const [favoriteIds, setFavoriteIds] = useState<Set<number>>(() => new Set());
  const [favoriteLoadStatus, setFavoriteLoadStatus] = useState<"loading" | "ready" | "error">("loading");
  const [pendingFavoriteIds, setPendingFavoriteIds] = useState<Set<number>>(() => new Set());
  const [favoriteError, setFavoriteError] = useState("");

  const { language, labels, setLanguage } = useLanguage();

  async function loadHomepage() {
    setError("");
    try {
      const [data, token] = await Promise.all([getHomepage(), getCsrfToken()]);
      setHomepage(data);
      setCsrfToken(token);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load KazeB.");
    }
  }

  useEffect(() => {
    if (pathname === "/admin-dashboard/") return;
    void loadHomepage();
  }, []);

  useEffect(() => {
    if (!homepage) return;
    const timer = window.setInterval(
      () => setActiveSlide((current) => (current + 1) % heroSlides.length),
      3000,
    );
    return () => window.clearInterval(timer);
  }, [homepage]);

  useEffect(() => {
    if (!homepage) return;

    let cancelled = false;
    setFavoriteError("");
    setFavoriteIds(new Set());
    if (!homepage.user.is_authenticated || homepage.recent_listings.length === 0) {
      setFavoriteLoadStatus("ready");
      return () => {
        cancelled = true;
      };
    }

    setFavoriteLoadStatus("loading");
    async function loadFavoriteIds() {
      try {
        const firstPage = await getFavorites();
        const pages = [firstPage];
        const totalPages = firstPage.pagination.pages;
        if (totalPages > 1) {
          const remaining = Array.from({ length: totalPages - 1 }, (_, i) => i + 2);
          const concurrency = 3;
          for (let i = 0; i < remaining.length; i += concurrency) {
            const chunk = remaining.slice(i, i + concurrency);
            const results = await Promise.all(chunk.map((page) => getFavorites(String(page))));
            pages.push(...results);
            if (cancelled) return;
          }
        }
        const ids = new Set(
          pages.flatMap((page) => page.results.map(({ listing }) => listing.id)),
        );
        if (!cancelled) {
          setFavoriteIds(ids);
          setFavoriteLoadStatus("ready");
        }
      } catch (loadError) {
        if (!cancelled) {
          setFavoriteError(
            loadError instanceof Error ? loadError.message : "Unable to load favourites.",
          );
          setFavoriteLoadStatus("error");
        }
      }
    }
    void loadFavoriteIds();

    return () => {
      cancelled = true;
    };
  }, [homepage]);

  useEffect(() => {
    if (homepage) {
      document.documentElement.lang = homepage.language;
    }
  }, [homepage]);

  async function handleLanguageChange(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const select = form.elements.namedItem("language") as HTMLSelectElement | null;
    if (!select) return;
    try {
      await setLanguage(select.value as HomepageData["language"]);
    } catch (languageError) {
      setError(languageError instanceof Error ? languageError.message : "Language change failed.");
    }
  }

  async function handleLogout() {
    setError("");
    try {
      await submitForm("/api/auth/logout/", new URLSearchParams());
      window.location.assign("/");
    } catch (logoutError) {
      setError(logoutError instanceof Error ? logoutError.message : "Logout failed.");
    }
  }

  async function handleHomepageFavoriteToggle(listingId: number) {
    if (!homepage?.user.is_authenticated) {
      window.location.assign(
        `/accounts/login/?next=${encodeURIComponent(window.location.pathname + window.location.search)}`,
      );
      return;
    }

    const wasFavorited = favoriteIds.has(listingId);
    setFavoriteError("");
    setFavoriteIds((current) => {
      const next = new Set(current);
      if (wasFavorited) next.delete(listingId);
      else next.add(listingId);
      return next;
    });
    setPendingFavoriteIds((current) => new Set(current).add(listingId));

    try {
      const response = await toggleFavorite(listingId);
      setFavoriteIds((current) => {
        const next = new Set(current);
        if (response.is_favorited) next.add(listingId);
        else next.delete(listingId);
        return next;
      });
    } catch (toggleError) {
      setFavoriteIds((current) => {
        const next = new Set(current);
        if (wasFavorited) next.add(listingId);
        else next.delete(listingId);
        return next;
      });
      setFavoriteError(
        toggleError instanceof Error
          ? toggleError.message
          : "Unable to update favourites.",
      );
    } finally {
      setPendingFavoriteIds((current) => {
        const next = new Set(current);
        next.delete(listingId);
        return next;
      });
    }
  }

  if (pathname === "/admin-dashboard/") {
    return <AdminDashboard />;
  }

  if (error) {
    return (
      <main className="container py-5" role="alert">
        <p>{error}</p>
        <button className="btn btn-brand" onClick={() => void loadHomepage()} type="button">
          Retry
        </button>
      </main>
    );
  }

  if (!homepage) {
    return (
      <main className="container py-5" aria-live="polite">
        Loading KazeB…
      </main>
    );
  }

  const { user } = homepage;
  const isHomepage = pathname === "/";
  const isDashboard = pathname === "/listings/dashboard/";

  return (
    <LanguageProvider initialLanguage={homepage.language} initialLabels={homepage.labels}>
      <>
      <header className="mobile-header d-lg-none">
        <a className="mobile-logo" href="/">
          <span className="kazeb-logo-black">Kaze</span>
          <span className="kazeb-logo-orange">B</span>
        </a>
        <div className="mobile-header-actions">
          <a className="mobile-icon" href="/accounts/profile/" aria-label="Profile">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="black" strokeWidth="2" aria-hidden="true"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 4-6 8-6s8 2 8 6"/></svg>
            {user.is_authenticated && <span className="mobile-account-dot" aria-label="Signed in" />}
          </a>
          <form action="/i18n/setlang/" method="post" className="mobile-lang" onSubmit={(event) => void handleLanguageChange(event)}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="black" strokeWidth="2" aria-hidden="true"><circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15 15 0 0 1 0 20M12 2a15 15 0 0 0 0 20"/></svg>
            <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken} />
            <input type="hidden" name="next" value={window.location.pathname + window.location.search} />
            <select name="language" value={language} aria-label={labels.change_language} className="language-select" onChange={(event) => { event.preventDefault(); void setLanguage(event.currentTarget.value as HomepageData["language"]); }}>
              <option value="rw">Kinya</option>
              <option value="en">EN</option>
              <option value="fr">FR</option>
            </select>
          </form>
          <button className="mobile-hamburger" type="button" aria-label="Open menu" onClick={() => setDrawerOpen(true)}>
            ☰
          </button>
        </div>
      </header>
      {drawerOpen && (
        <div className="mobile-drawer-overlay" onClick={() => setDrawerOpen(false)} />
      )}
      <aside className={`mobile-drawer ${drawerOpen ? "open" : ""}`} aria-hidden={!drawerOpen}>
        <div className="mobile-drawer-header">
          <span className="kazeb-logo-black">Kaze</span>
          <span className="kazeb-logo-orange">B</span>
          <button className="mobile-drawer-close" type="button" aria-label="Close menu" onClick={() => setDrawerOpen(false)}>
            ✕
          </button>
        </div>
        <nav className="mobile-drawer-nav">
          <a href="/" onClick={() => setDrawerOpen(false)}>Ahabanza</a>
          <a href="/accounts/profile/" onClick={() => setDrawerOpen(false)}>Konti yanjye</a>
          <a href="/about/" onClick={() => setDrawerOpen(false)}>Uko bikora</a>
          <a href="/faq/" onClick={() => setDrawerOpen(false)}>Ibibazo bikunze kubazwa</a>
          <a href="/terms/" onClick={() => setDrawerOpen(false)}>Ibanza n'Amabwiriza</a>
        </nav>
        {!user.is_authenticated && (
          <div className="mobile-drawer-footer">
            <a className="btn btn-white-orange w-100" href="/accounts/login/" onClick={() => setDrawerOpen(false)}>Injira</a>
          </div>
        )}
      </aside>
      <nav
        className={`navbar navbar-expand-lg navbar-light bg-white border-bottom sticky-top${
          isHomepage || isDashboard ? " homepage-navbar" : ""
        }`}
      >
        <div className="container flex-wrap">
          <a className="navbar-brand fw-bold" href="/">
            <span className="kazeb-logo-black">Kaze</span>
            <span className="kazeb-logo-orange">B</span>
          </a>

          {!isHomepage && (
            <SearchForm
              search={labels.search}
              placeholder={labels.search_placeholder}
              className="nav-search-box order-lg-0 flex-grow-1 mx-lg-3 my-2 my-lg-0"
            />
          )}

          <button
            className="navbar-toggler order-lg-1"
            type="button"
            aria-controls="navMain"
            aria-expanded={menuOpen}
            aria-label="Toggle navigation"
            onClick={() => setMenuOpen((open) => !open)}
          >
            <span className="navbar-toggler-icon" />
          </button>

          <div className={`collapse navbar-collapse order-lg-2${menuOpen ? " show" : ""}`} id="navMain">
            <ul className="navbar-nav me-auto mb-2 mb-lg-0 nav-icons">
              <li className="nav-item">
                <a
                  className={`nav-link${isHomepage ? " is-active" : ""}`}
                  href="/"
                  title={labels.home}
                >
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6"><path d="M3 10l9-7 9 7v11a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/></svg> {labels.home}
                </a>
              </li>
              <li className="nav-item">
                <a className="nav-link" href="/listings/add/" title={labels.add_listing}>
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6"><rect x="3" y="3" width="20" height="20" rx="4"/><path d="M12 8v8M8 12h8"/></svg> {labels.add_listing}
                </a>
              </li>
              {user.is_authenticated && (
                <>
                  <li className="nav-item">
                    <a
                      className={`nav-link${isDashboard ? " is-active" : ""}`}
                      href="/listings/dashboard/"
                      title={labels.my_account}
                    >
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 4-6 8-6s8 2 8 6"/></svg> {labels.my_account}
                    </a>
                  </li>
                  <li className="nav-item">
                    <a
                      className="nav-link position-relative"
                      href="/messages/"
                      title={labels.messages}
                    >
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg> {labels.messages}
                      {user.unread_message_count > 0 && (
                        <span className="unread-badge">{user.unread_message_count}</span>
                      )}
                    </a>
                  </li>
                </>
              )}
            </ul>

            <ul className="navbar-nav align-items-lg-center gap-lg-2">
              <li className="nav-item">
                <form
                  action="/i18n/setlang/"
                  method="post"
                  className="d-flex align-items-center"
                  onSubmit={(event) => void handleLanguageChange(event)}
                >
                  <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken} />
                  <input
                    type="hidden"
                    name="next"
                    value={window.location.pathname + window.location.search}
                  />
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true" className="language-globe"><circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15 15 0 0 1 0 20M12 2a15 15 0 0 0 0 20"/></svg>
                  <select
                    name="language"
                    className="form-select form-select-sm language-select"
                    value={language}
                    title={labels.change_language}
                    aria-label={labels.change_language}
                    onChange={(event) => { event.preventDefault(); void setLanguage(event.currentTarget.value as HomepageData["language"]); }}
                  >
                    <option value="rw">Kinya</option>
                    <option value="en">English</option>
                    <option value="fr">Français</option>
                  </select>
                </form>
              </li>
              {user.is_authenticated ? (
                <>
                  <li className="nav-item">
                    <a
                      className={`nav-link${pathname === "/accounts/profile/" ? " is-active" : ""}`}
                      href="/accounts/profile/"
                    >
                      {labels.account}
                    </a>
                  </li>
                  <li className="nav-item">
                    <a className="nav-link" href="/listings/favorites/">{labels.favorites}</a>
                  </li>
                  <li className="nav-item">
                    <button className="btn btn-sm btn-outline-brand" type="button" onClick={() => void handleLogout()}>
                      {labels.sign_out}
                    </button>
                  </li>
                </>
              ) : (
                <>
                  <li className="nav-item">
                    <a className="btn btn-sm btn-outline-brand" href="/accounts/login/">
                      {labels.login}
                    </a>
                  </li>
                  <li className="nav-item">
                    <a className="btn btn-sm btn-brand" href="/accounts/register/">
                      {labels.register}
                    </a>
                  </li>
                </>
              )}
            </ul>
          </div>
        </div>
      </nav>

      {isHomepage ? (
      <main className="container-fluid pt-4 pb-4 kazeb-homepage-content">
        <h1 className="kazeb-welcome-title">
          {labels.welcome_prefix} <span className="kazeb-logo-black">Kaze</span>
          <span className="kazeb-logo-orange">B</span>!
        </h1>
        <p className="kazeb-welcome-tagline">Ikiraro gihuza abaguzi n'abagurisha</p>
        <div className="homepage-search">
          <SearchForm
            search={labels.search}
            placeholder={labels.search_placeholder}
            className="nav-search-box homepage-search-form"
          />
        </div>
        <section className="kazeb-hero mb-5" aria-label="KazeB promotion">
          <div className="kazeb-hero-inner">
            <div className="kazeb-hero-content">
              <h2 className="kazeb-hero-title">
                {labels.hero_title_line_1}
                <br />
                {labels.hero_title_line_2}
                <br />
                {labels.hero_title_line_3}
                <br />
                {labels.hero_title_line_4}
                <br />
                {labels.hero_title_line_5}
              </h2>
              <div className="kazeb-hero-actions">
                <a href="/listings/add/" className="btn btn-brand kazeb-hero-primary">
                  {labels.hero_buyer_cta}
                </a>
                <a href="#categories" className="btn btn-outline-brand kazeb-hero-secondary">
                  {labels.hero_seller_cta}
                </a>
              </div>
            </div>

            <div className="kazeb-hero-visual">
              <div className="kazeb-hero-slides">
                {heroSlides.map((slide, index) => (
                  <div
                    className={`kazeb-hero-slide${index === activeSlide ? " is-active" : ""}`}
                    key={slide.src}
                    aria-hidden={index !== activeSlide}
                  >
                    <img
                      src={`/static/images/hero/${slide.src}`}
                      alt={slide.alt}
                      loading={index === 0 ? "eager" : "lazy"}
                    />
                  </div>
                ))}
              </div>
            </div>

            <div className="kazeb-hero-dots" role="tablist" aria-label="KazeB promotions">
              {heroSlides.map((slide, index) => (
                <button
                  type="button"
                  className={`kazeb-hero-dot${index === activeSlide ? " is-active" : ""}`}
                  key={slide.src}
                  aria-label={slide.alt}
                  aria-selected={index === activeSlide}
                  role="tab"
                  onClick={() => setActiveSlide(index)}
                />
              ))}
            </div>
          </div>
        </section>

        <section
          id="categories"
          className={`homepage-category-section${
            homepage.recent_listings.length > 0 ? " mb-5" : ""
          }`}
        >
          <h2 className="find-by-category">{labels.categories}</h2>
          {homepage.categories.length > 0 ? (
            <div className="homepage-category-grid">
              {homepage.categories.map((category) => (
                <div className="homepage-category-item" key={category.id}>
                  <a href={category.url} className="category-card text-decoration-none">
                    <div className="category-icon">
                      {category.icon ? (
                        <img src={category.icon} alt={category.name} loading="lazy" />
                      ) : (
                        <span className="category-icon-fallback">
                          {category.name.slice(0, 1)}
                        </span>
                      )}
                    </div>
                    <div className="category-name">{category.name}</div>
                  </a>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-muted mt-3">{labels.empty_categories}</p>
          )}
        </section>

        {homepage.recent_listings.length > 0 && (
          <section aria-labelledby="recent-listings-title">
            <h2 className="h4 mb-3" id="recent-listings-title">
              {labels.recent_listings}
            </h2>
            <div className="homepage-product-grid">
              {homepage.recent_listings.map((listing) => (
                <div className="homepage-product-item" key={listing.id}>
                  <article className="card listing-card homepage-product-card h-100">
                    <div className="homepage-product-image-wrap">
                      <a
                        href={listing.url}
                        className="homepage-product-image-link"
                        aria-label={listing.name}
                      >
                        {listing.image ? (
                          <img
                            src={listing.image}
                            className="card-img-top listing-card-img"
                            alt={listing.name}
                            loading="lazy"
                            onError={(e) => {
                              e.currentTarget.style.display = "none";
                              const placeholder = e.currentTarget.parentNode?.querySelector(".listing-card-img-placeholder");
                              if (placeholder) {
                                (placeholder as HTMLElement).style.display = "flex";
                              }
                            }}
                          />
                        ) : null}
                        <div className="listing-card-img listing-card-img-placeholder" style={{ display: listing.image ? "none" : "flex" }}>
                          {labels.empty_image}
                        </div>
                      </a>
                      <button
                        type="button"
                        className={`homepage-favorite-btn${favoriteIds.has(listing.id) ? " is-favorited" : ""}`}
                        aria-label={
                          favoriteIds.has(listing.id)
                            ? labels.saved_favorite
                            : labels.save_favorite
                        }
                        aria-pressed={favoriteIds.has(listing.id)}
                        disabled={
                          (user.is_authenticated && favoriteLoadStatus !== "ready") ||
                          pendingFavoriteIds.has(listing.id)
                        }
                        onClick={() => void handleHomepageFavoriteToggle(listing.id)}
                      >
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                          <path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8l1.1 1.1L12 21l7.8-7.5 1.1-1.1a5.5 5.5 0 0 0-.1-7.8Z" />
                        </svg>
                      </button>
                    </div>
                    <a
                      href={listing.url}
                      className="homepage-product-details-link text-decoration-none text-body"
                    >
                      <div className="card-body">
                        <h3 className="h6 mb-1 text-truncate">{listing.name}</h3>
                        <p className="fw-bold text-brand mb-1">{listing.price}</p>
                        <p className="homepage-product-location small text-muted mb-0">
                          <svg viewBox="0 0 24 24" aria-hidden="true">
                            <path d="M20 10c0 5-8 12-8 12S4 15 4 10a8 8 0 1 1 16 0Z" />
                            <circle cx="12" cy="10" r="2.5" />
                          </svg>
                          <span>{listing.location}</span>
                        </p>
                      </div>
                    </a>
                    <div className="card-footer bg-white border-0 pt-0">
                      <a href={listing.seller.url} className="seller-card-link">
                        {listing.seller.image ? (
                          <img
                            src={listing.seller.image}
                            className="seller-avatar-sm"
                            alt=""
                            loading="lazy"
                            onError={(e) => {
                              e.currentTarget.style.display = "none";
                              const fallback = e.currentTarget.nextElementSibling;
                              if (fallback) {
                                (fallback as HTMLElement).style.display = "inline-flex";
                              }
                            }}
                          />
                        ) : null}
                        <span className="seller-avatar-sm seller-avatar-fallback" style={{ display: listing.seller.image ? "none" : "inline-flex" }} aria-hidden="true">
                          {listing.seller.username.slice(0, 1).toUpperCase()}
                        </span>
                        <span>{listing.seller.name}</span>
                      </a>
                    </div>
                  </article>
                </div>
              ))}
            </div>
            {favoriteError && (
              <p className="alert alert-danger mt-3 mb-0" role="alert">
                {favoriteError}
              </p>
            )}
          </section>
        )}
      </main>
      ) : isAccountPage(pathname) ? (
        <AccountPages pathname={pathname} common={labels} />
      ) : isDashboard ? (
        <SellerDashboard language={homepage.language} />
      ) : pathname === "/listings/add/" ? (
        <SellerListingCreate language={homepage.language} />
      ) : /^\/listings\/\d+\/edit\/?$/.test(pathname) ? (
        <SellerListingEdit
          listingId={Number(pathname.match(/^\/listings\/(\d+)\/edit\/?$/)?.[1])}
          language={homepage.language}
        />
      ) : (
        <Marketplace
          labels={labels}
          isAuthenticated={user.is_authenticated}
        />
      )}

      <footer className="homepage-footer">
        <div className="footer-brand">
          <div className="container">
            <a href="/" className="footer-logo d-flex align-items-center gap-2 text-decoration-none">
              <span className="kazeb-logo-black fw-bold">Kaze</span>
              <span className="kazeb-logo-orange fw-bold">B</span>
            </a>
            <p className="footer-description">{labels.footer_description}</p>
            <div className="footer-socials">
              <a
                href="https://www.tiktok.com/@kazeb57?_r=1&_t=ZS-99CeOPSb12T"
                className="footer-social-icon"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="TikTok"
                title="TikTok"
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                  <path d="M16.6 5.82c-.9-.88-1.46-2.06-1.6-3.32h-3.06v13.44c0 1.63-1.32 2.95-2.95 2.95a2.95 2.95 0 0 1 0-5.9c.28 0 .55.04.8.12V9.98a6.08 6.08 0 0 0-.8-.05A6.08 6.08 0 1 0 15.03 16V9.4a9.14 9.14 0 0 0 5.35 1.72V8.06a5.98 5.98 0 0 1-3.78-2.24z" />
                </svg>
              </a>
              <a
                href="https://www.instagram.com/kazeb.rw?igsi=MWxiODNidWpjeWljeQ=="
                className="footer-social-icon"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="Instagram"
                title="Instagram"
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
                  <rect x="3" y="3" width="18" height="18" rx="5" />
                  <circle cx="12" cy="12" r="4" />
                  <circle cx="17.2" cy="6.8" r="1.1" fill="currentColor" stroke="none" />
                </svg>
              </a>
              <a
                href="https://www.facebook.com/share/1EUuLs9Mha/"
                className="footer-social-icon"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="Facebook"
                title="Facebook"
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                  <path d="M22 12.06C22 6.5 17.52 2 12 2S2 6.5 2 12.06c0 5 3.66 9.15 8.44 9.94v-7.03H7.9v-2.9h2.54V9.85c0-2.5 1.49-3.89 3.77-3.89 1.09 0 2.24.2 2.24.2v2.46h-1.26c-1.24 0-1.63.77-1.63 1.56v1.88h2.78l-.44 2.9h-2.34V22c4.78-.79 8.44-4.94 8.44-9.94z" />
                </svg>
              </a>
              <a
                href="https://youtube.com/@kazebrwanda?si=woGH50aq8c8CkiEk"
                className="footer-social-icon"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="YouTube"
                title="YouTube"
              >
<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                  <path d="M23 12c0-3.53-.47-6.88-1.31-10.09C20.47 3.82 18.26 2 12 2S3.53 3.82 2.31 7.03C1.53 10.24 1 13.59 1 17c0 3.41.53 6.76 1.31 9.97C3.53 20.18 5.74 22 12 22s8.47-1.82 9.69-4.03C22.47 13.76 23 10.41 23 17z" />
                  <path d="M10 15.5l5.5-3.5v-6L10 15.5z" fill="currentColor" stroke="none" />
                </svg>
              </a>
              <a
                href="https://whatsapp.com/channel/0029VbDSEdp7tkjFMCr2Jm34"
                className="footer-social-icon"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="WhatsApp"
                title="WhatsApp"
              >
                <img src="/static/images/icons/whatsapp.svg" alt="" width="20" height="20" />
              </a>
              <a
                href="https://x.com/KazeBrwanda"
                className="footer-social-icon"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="X"
                title="X"
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                  <path d="M18.9 3H22l-7.6 8.68L23.3 21h-6.7l-5.2-6.6L5.4 21H2.3l8.1-9.27L1.4 3h6.9l4.7 6.02L18.9 3zm-1.2 16h1.8L7.4 5H5.5l12.2 14z" />
                </svg>
              </a>
            </div>
          </div>
        </div>

        <div className="footer-sections">
          <div className="container homepage-footer-inner">
            <div className="homepage-footer-columns">
              <div className="homepage-footer-column footer-accordion">
                <button
                  className="footer-accordion-header"
                  type="button"
                  aria-expanded={footerExpanded.has("explore")}
                  aria-controls="footer-explore"
                  onClick={() => {
                    const next = new Set(footerExpanded);
                    if (next.has("explore")) next.delete("explore");
                    else next.add("explore");
                    setFooterExpanded(next);
                  }}
                >
                  {labels.explore}
                  <svg className="footer-chevron" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                    <polyline points="6 9 12 15 18 9" />
                  </svg>
                </button>
                <div
                  className={`footer-accordion-content${footerExpanded.has("explore") ? " open" : ""}`}
                  id="footer-explore"
                >
                  <ul className="list-unstyled footer-links">
                    <li><a href="/listings/">{labels.browse_listings}</a></li>
                    <li><a href="/faq/">{labels.faq}</a></li>
                    <li><a href="/anti-scam/">{labels.safety}</a></li>
                  </ul>
                </div>
              </div>

              <div className="homepage-footer-column footer-accordion">
                <button
                  className="footer-accordion-header"
                  type="button"
                  aria-expanded={footerExpanded.has("kazeb")}
                  aria-controls="footer-kazeb"
                  onClick={() => {
                    const next = new Set(footerExpanded);
                    if (next.has("kazeb")) next.delete("kazeb");
                    else next.add("kazeb");
                    setFooterExpanded(next);
                  }}
                >
                  {labels.my_kazeb}
                  <svg className="footer-chevron" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                    <polyline points="6 9 12 15 18 9" />
                  </svg>
                </button>
                <div
                  className={`footer-accordion-content${footerExpanded.has("kazeb") ? " open" : ""}`}
                  id="footer-kazeb"
                >
                  <ul className="list-unstyled footer-links">
                    <li><a href="/accounts/login/">{labels.login}</a></li>
                    <li><a href="/accounts/register/">{labels.register}</a></li>
                    <li><a href="/listings/favorites/">{labels.favorites}</a></li>
                    <li><a href="/listings/add/">{labels.add_listing}</a></li>
                    {user.is_authenticated && (
                      <li><a href="/listings/dashboard/">{labels.my_account}</a></li>
                    )}
                  </ul>
                </div>
              </div>

              <div className="homepage-footer-column footer-accordion">
                <button
                  className="footer-accordion-header"
                  type="button"
                  aria-expanded={footerExpanded.has("about")}
                  aria-controls="footer-about"
                  onClick={() => {
                    const next = new Set(footerExpanded);
                    if (next.has("about")) next.delete("about");
                    else next.add("about");
                    setFooterExpanded(next);
                  }}
                >
                  {labels.about_support}
                  <svg className="footer-chevron" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                    <polyline points="6 9 12 15 18 9" />
                  </svg>
                </button>
                <div
                  className={`footer-accordion-content${footerExpanded.has("about") ? " open" : ""}`}
                  id="footer-about"
                >
                  <ul className="list-unstyled footer-links">
                    <li><a href="/about/">{labels.about}</a></li>
                    <li><a href="/contact/">{labels.contact}</a></li>
                    <li><a href="/terms/">{labels.terms}</a></li>
                    <li><a href="/privacy/">{labels.privacy}</a></li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="footer-bottom">
          <div className="container">
            <div className="footer-bottom-content">
              <span className="footer-copyright">
                © {new Date().getFullYear()} KazeB. All rights reserved.
              </span>
              <div className="footer-bottom-links">
                <a href="/terms/">{labels.terms}</a>
                <span className="footer-separator">·</span>
                <a href="/privacy/">{labels.privacy}</a>
              </div>
              <span className="footer-copyright">
                © {new Date().getFullYear()} KazeB. {labels.footer_copyright}
              </span>
            </div>
          </div>
        </div>
      </footer>
      <nav className="mobile-bottom-nav d-lg-none" aria-label="Bottom navigation">
        <a href="/" className={pathname === "/" ? "active" : ""}>
          <span><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6"><path d="M3 10l9-7 9 7v11a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/></svg></span>
          <small>Ahabanza</small>
        </a>
        <a href="/listings/" className={pathname.startsWith("/listings") ? "active" : ""}>
          <span><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg></span>
          <small>Ibicuruzwa</small>
        </a>
        <a href="/listings/add/" className={pathname === "/listings/add/" ? "active" : ""}>
          <span><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6"><rect x="3" y="3" width="20" height="20" rx="4"/><path d="M12 8v8M8 12h8"/></svg></span>
          <small>Ongeraho</small>
        </a>
        <a href="/messages/" className={pathname.startsWith("/messages") ? "active" : ""}>
          <span><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg></span>
          <small>Ubutumwa</small>
        </a>
        <a href="/accounts/profile/" className={pathname === "/accounts/profile/" ? "active" : ""}>
          <span><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 4-6 8-6s8 2 8 6"/></svg></span>
          <small>Konti</small>
        </a>
      </nav>
    </>
    </LanguageProvider>
  );
}

function isAccountPage(pathname: string) {
  return (
    pathname === "/accounts/register/" ||
    pathname === "/accounts/login/" ||
    pathname === "/accounts/edit/" ||
    pathname === "/accounts/delete/" ||
    pathname === "/accounts/profile/" ||
    pathname === "/accounts/verify/sent/" ||
    pathname === "/accounts/verify/resend/" ||
    pathname === "/accounts/password_reset/" ||
    pathname === "/accounts/password_reset/done/" ||
    pathname === "/accounts/reset/done/" ||
    /^\/accounts\/reset\/[^/]+\/[^/]+\/?$/.test(pathname) ||
    pathname === "/listings/favorites/"
  );
}

export default App;

