import { useEffect, useState, type FormEvent } from "react";

import {
  getCsrfToken,
  getFavorites,
  getHomepage,
  submitForm,
  toggleFavorite,
  type HomepageData,
} from "./api/client";
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

const footerLinks = [
  { key: "about", href: "/about/" },
  { key: "faq", href: "/faq/" },
  { key: "safety", href: "/anti-scam/" },
  { key: "terms", href: "/terms/" },
  { key: "privacy", href: "/privacy/" },
] as const;

const footerSocialLinks = [
  {
    href: "https://www.tiktok.com/@kazeb57?_r=1&_t=ZS-99CeOPSb12T",
    label: "TikTok",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
        <path d="M16.6 5.82c-.9-.88-1.46-2.06-1.6-3.32h-3.06v13.44c0 1.63-1.32 2.95-2.95 2.95a2.95 2.95 0 0 1 0-5.9c.28 0 .55.04.8.12V9.98a6.08 6.08 0 0 0-.8-.05A6.08 6.08 0 1 0 15.03 16V9.4a9.14 9.14 0 0 0 5.35 1.72V8.06a5.98 5.98 0 0 1-3.78-2.24z" />
      </svg>
    ),
  },
  {
    href: "https://www.instagram.com/kazeb.rw?igsi=MWxiODNidWpjeWljeQ==",
    label: "Instagram",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
        <rect x="3" y="3" width="18" height="18" rx="5" />
        <circle cx="12" cy="12" r="4" />
        <circle cx="17.2" cy="6.8" r="1.1" fill="currentColor" stroke="none" />
      </svg>
    ),
  },
  {
    href: "https://www.facebook.com/share/1EUuLs9Mha/",
    label: "Facebook",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
        <path d="M22 12.06C22 6.5 17.52 2 12 2S2 6.5 2 12.06c0 5 3.66 9.15 8.44 9.94v-7.03H7.9v-2.9h2.54V9.85c0-2.5 1.49-3.89 3.77-3.89 1.09 0 2.24.2 2.24.2v2.46h-1.26c-1.24 0-1.63.77-1.63 1.56v1.88h2.78l-.44 2.9h-2.34V22c4.78-.79 8.44-4.94 8.44-9.94z" />
      </svg>
    ),
  },
  {
    href: "https://youtube.com/@kazebrwanda?si=woGH50aq8c8CkiEk",
    label: "YouTube",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
        <path d="M23 12s0-3.5-.45-5.15a2.87 2.87 0 0 0-2-2C18.9 4.4 12 4.4 12 4.4s-6.9 0-8.55.45a2.87 2.87 0 0 0-2 2C1 8.5 1 12 1 12s0 3.5.45 5.15a2.87 2.87 0 0 0 2 2c1.65.45 8.55.45 8.55.45s6.9 0 8.55-.45a2.87 2.87 0 0 0 2-2C23 15.5 23 12 23 12z" />
        <path d="M9.75 15.5V8.5L15.5 12l-5.75 3.5z" fill="white" stroke="none" />
      </svg>
    ),
  },
  {
    href: "https://whatsapp.com/channel/0029VbDSEdp7tkjFMCr2Jm34",
    label: "WhatsApp",
    icon: <img src="/static/images/icons/whatsapp.svg" alt="" width="20" height="20" />,
  },
  {
    href: "https://x.com/KazeBrwanda",
    label: "X",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
        <path d="M18.9 3H22l-7.6 8.68L23.3 21h-6.7l-5.2-6.6L5.4 21H2.3l8.1-9.27L1.4 3h6.9l4.7 6.02L18.9 3zm-1.2 16h1.8L7.4 5H5.5l12.2 14z" />
      </svg>
    ),
  },
] as const;

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
  const [favoriteIds, setFavoriteIds] = useState<Set<number>>(() => new Set());
  const [favoriteLoadStatus, setFavoriteLoadStatus] = useState<"loading" | "ready" | "error">("loading");
  const [pendingFavoriteIds, setPendingFavoriteIds] = useState<Set<number>>(() => new Set());
  const [favoriteError, setFavoriteError] = useState("");

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
        for (let page = 2; page <= firstPage.pagination.pages; page += 1) {
          pages.push(await getFavorites(String(page)));
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
    try {
      const token = csrfToken || (await getCsrfToken());
      const formData = new FormData(form);
      formData.set("csrfmiddlewaretoken", token);
      const returnTo = window.location.pathname + window.location.search + window.location.hash;
      formData.set("next", window.location.pathname + window.location.search);
      const body = new URLSearchParams();
      formData.forEach((value, key) => body.set(key, String(value)));
      const response = await fetch("/i18n/setlang/", {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
          "X-CSRFToken": token,
        },
        credentials: "same-origin",
        body,
      });
      if (!response.ok) {
        throw new Error(`Language change failed (${response.status}).`);
      }
      window.location.assign(returnTo);
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

  const { labels, user } = homepage;
  const isHomepage = pathname === "/";
  const isDashboard = pathname === "/listings/dashboard/";

  return (
    <>
      <header className="mobile-header d-lg-none">
        <a className="mobile-logo" href="/">
          <span className="kazeb-logo-black">Kaze</span>
          <span className="kazeb-logo-orange">B</span>
        </a>
        <div className="mobile-header-actions">
          <a className="mobile-icon" href="/accounts/profile/" aria-label="Profile">
            👤
          </a>
          <form action="/i18n/setlang/" method="post" className="mobile-lang" onSubmit={(event) => void handleLanguageChange(event)}>
            <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken} />
            <input type="hidden" name="next" value={window.location.pathname + window.location.search} />
            <select name="language" defaultValue={homepage.language} aria-label={labels.change_language}>
              <option value="rw">RW</option>
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
            <a className="btn btn-brand w-100" href="/accounts/login/" onClick={() => setDrawerOpen(false)}>Injira</a>
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
                  🏠 {labels.home}
                </a>
              </li>
              <li className="nav-item">
                <a className="nav-link" href="/listings/add/" title={labels.add_listing}>
                  ➕ {labels.add_listing}
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
                      👤 {labels.my_account}
                    </a>
                  </li>
                  <li className="nav-item">
                    <a
                      className="nav-link position-relative"
                      href="/messages/"
                      title={labels.messages}
                    >
                      💬 {labels.messages}
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
                  <select
                    name="language"
                    className="form-select form-select-sm"
                    defaultValue={homepage.language}
                    title={labels.change_language}
                    aria-label={labels.change_language}
                    onChange={(event) => event.currentTarget.form?.requestSubmit()}
                  >
                    <option value="rw">Kinyarwanda</option>
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
                          />
                        ) : (
                          <div className="listing-card-img listing-card-img-placeholder">
                            {labels.empty_image}
                          </div>
                        )}
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
                          />
                        ) : (
                          <span
                            className="seller-avatar-sm seller-avatar-fallback"
                            aria-hidden="true"
                          >
                            {listing.seller.username.slice(0, 1).toUpperCase()}
                          </span>
                        )}
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
        <div className="footer-highlight homepage-footer-band">
          <div className="container homepage-footer-inner">
            <div className="homepage-footer-top">
              <div className="homepage-footer-brand">
                <a href="/" className="homepage-footer-logo" aria-label="KazeB">
                  <span className="kazeb-logo-black">Kaze</span>
                  <span className="kazeb-logo-orange">B</span>
                </a>
                <p className="homepage-footer-tagline">{labels.brand_tagline}</p>
              </div>
              <div className="homepage-footer-follow">
                <h2 className="homepage-footer-follow-title">{labels.follow}</h2>
                <div className="homepage-footer-socials">
                  {footerSocialLinks.map((social) => (
                    <a
                      key={social.label}
                      href={social.href}
                      className="footer-social-icon"
                      target="_blank"
                      rel="noopener noreferrer"
                      aria-label={social.label}
                      title={social.label}
                    >
                      {social.icon}
                    </a>
                  ))}
                </div>
              </div>
            </div>

            <div className="homepage-footer-card">
              <div className="homepage-footer-columns">
                <div className="homepage-footer-column">
                  <h2 className="h6 text-uppercase mb-3">{labels.about}</h2>
                  <ul className="list-unstyled footer-links">
                    {footerLinks.map((link) => (
                      <li key={link.key}>
                        <a href={link.href}>{labels[link.key]}</a>
                      </li>
                    ))}
                  </ul>
                </div>
                <div className="homepage-footer-column">
                  <h2 className="h6 text-uppercase mb-3">{labels.contact}</h2>
                  <ul className="list-unstyled footer-links">
                    <li>
                      <a href="/contact/">{labels.contact}</a>
                    </li>
                  </ul>
                </div>
                <div className="homepage-footer-column">
                  <h2 className="h6 text-uppercase mb-3">{labels.my_account}</h2>
                  <ul className="list-unstyled footer-links">
                    {user.is_authenticated ? (
                      <li>
                        <a href="/listings/dashboard/">{labels.my_account}</a>
                      </li>
                    ) : (
                      <>
                        <li>
                          <a href="/accounts/login/">{labels.login}</a>
                        </li>
                        <li>
                          <a href="/accounts/register/">{labels.register}</a>
                        </li>
                      </>
                    )}
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div className="text-center text-muted py-3 border-top">
          <small>
            © {new Date().getFullYear()} KazeB — {labels.footer_tagline}
          </small>
        </div>
      </footer>
      <nav className="mobile-bottom-nav d-lg-none" aria-label="Bottom navigation">
        <a href="/" className={pathname === "/" ? "active" : ""}>
          <span>H</span>
          <small>Ahabanza</small>
        </a>
        <a href="/listings/" className={pathname.startsWith("/listings") ? "active" : ""}>
          <span>P</span>
          <small>Ibicuruzwa</small>
        </a>
        <a href="/listings/add/" className={pathname === "/listings/add/" ? "active" : ""}>
          <span>+</span>
          <small>Ongeraho</small>
        </a>
        <a href="/messages/" className={pathname.startsWith("/messages") ? "active" : ""}>
          <span>M</span>
          <small>Ubutumwa</small>
        </a>
        <a href="/accounts/profile/" className={pathname === "/accounts/profile/" ? "active" : ""}>
          <span>U</span>
          <small>Konti</small>
        </a>
      </nav>
    </>
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
