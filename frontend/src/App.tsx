import { useEffect, useState, type FormEvent } from "react";

import {
  getCsrfToken,
  getHomepage,
  submitForm,
  type HomepageData,
} from "./api/client";
import AccountPages from "./Accounts";
import Marketplace from "./Marketplace";

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

function App() {
  const [homepage, setHomepage] = useState<HomepageData | null>(null);
  const [csrfToken, setCsrfToken] = useState("");
  const [error, setError] = useState("");
  const [activeSlide, setActiveSlide] = useState(0);
  const [menuOpen, setMenuOpen] = useState(false);

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
      window.location.assign("/");
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

  return (
    <>
      <nav className="navbar navbar-expand-lg navbar-light bg-white border-bottom sticky-top">
        <div className="container flex-wrap">
          <a className="navbar-brand fw-bold" href="/">
            <span className="kazeb-logo-black">Kaze</span>
            <span className="kazeb-logo-orange">B</span>
          </a>

          <form action="/listings/search/" method="get" className="nav-search-box order-lg-0 flex-grow-1 mx-lg-3 my-2 my-lg-0">
            <div className="input-group">
              <span className="input-group-text bg-white border-end-0" aria-hidden="true">
                🔍
              </span>
              <input
                type="search"
                name="q"
                className="form-control border-start-0"
                placeholder={labels.search_placeholder}
              />
              <button type="submit" className="btn btn-brand">
                {labels.search}
              </button>
            </div>
          </form>

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
                <a className="nav-link" href="/" title={labels.home}>
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
                    <a className="nav-link" href="/listings/dashboard/" title={labels.my_account}>
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
                  <input type="hidden" name="next" value="/" />
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
                    <a className="nav-link" href="/accounts/profile/">{labels.account}</a>
                  </li>
                  <li className="nav-item">
                    <a className="nav-link" href="/listings/favorites/">{labels.favorites}</a>
                  </li>
                  <li className="nav-item">
                    <a className="nav-link" href="/listings/dashboard/">{labels.my_account}</a>
                  </li>
                  <li className="nav-item">
                    <button className="btn btn-sm btn-outline-secondary" type="button" onClick={() => void handleLogout()}>
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

      {window.location.pathname === "/" ? (
      <main className="container py-4">
        <h1 className="kazeb-welcome-title">Murakaza neza kuri KazeB!</h1>
        <section className="kazeb-hero mb-5" aria-label="KazeB promotion">
          <div className="kazeb-hero-inner">
            <div className="kazeb-hero-content">
              <h2 className="kazeb-hero-title">
                Bona umuguzi
                <br />
                cyangwa
                <br />
                umugurisha
                <br />
                vuba kandi
                <br />
                byoroshye.
              </h2>
              <div className="kazeb-hero-actions">
                <a href="/listings/add/" className="btn btn-brand kazeb-hero-primary">
                  Shaka umuguzi nonaha
                </a>
                <a href="#categories" className="btn btn-outline-brand kazeb-hero-secondary">
                  Shaka umugurisha nonaha
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

        <section id="categories" className="mb-5">
          <h2 className="find-by-category">{labels.categories}</h2>
          {homepage.categories.length > 0 ? (
            <div className="row row-cols-2 row-cols-md-3 row-cols-lg-6 g-4 mt-2">
              {homepage.categories.map((category) => (
                <div className="col" key={category.id}>
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
            <div className="row row-cols-1 row-cols-sm-2 row-cols-lg-4 g-4">
              {homepage.recent_listings.map((listing) => (
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
                        <div className="listing-card-img listing-card-img-placeholder">
                          {labels.empty_image}
                        </div>
                      )}
                      <div className="card-body">
                        <h3 className="h6 mb-1 text-truncate">{listing.name}</h3>
                        <p className="fw-bold text-brand mb-1">{listing.price}</p>
                        <p className="small text-muted mb-0">{listing.location}</p>
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
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}
      </main>
      ) : isAccountPage(window.location.pathname) ? (
        <AccountPages pathname={window.location.pathname} common={labels} />
      ) : (
        <Marketplace
          labels={labels}
          isAuthenticated={user.is_authenticated}
        />
      )}

      <footer className="mt-5">
        <div className="footer-highlight py-5">
          <div className="container">
            <div className="row gy-4">
              <div className="col-6 col-md-3">
                <h2 className="h6 text-uppercase mb-3">{labels.about}</h2>
                <ul className="list-unstyled footer-links">
                  {footerLinks.map((link) => (
                    <li key={link.key}>
                      <a href={link.href}>{labels[link.key]}</a>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="col-6 col-md-3">
                <h2 className="h6 text-uppercase mb-3">{labels.contact}</h2>
                <ul className="list-unstyled footer-links">
                  <li>
                    <a href="/contact/">{labels.contact}</a>
                  </li>
                </ul>
              </div>
              <div className="col-6 col-md-3">
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
              <div className="col-6 col-md-3">
                <h2 className="h6 text-uppercase mb-3">{labels.follow}</h2>
                <div className="d-flex flex-wrap gap-2">
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
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                      <path d="M23 12s0-3.5-.45-5.15a2.87 2.87 0 0 0-2-2C18.9 4.4 12 4.4 12 4.4s-6.9 0-8.55.45a2.87 2.87 0 0 0-2 2C1 8.5 1 12 1 12s0 3.5.45 5.15a2.87 2.87 0 0 0 2 2c1.65.45 8.55.45 8.55.45s6.9 0 8.55-.45a2.87 2.87 0 0 0 2-2C23 15.5 23 12 23 12z" />
                      <path d="M9.75 15.5V8.5L15.5 12l-5.75 3.5z" fill="white" stroke="none" />
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
          </div>
        </div>
        <div className="text-center text-muted py-3 border-top">
          <small>
            © {new Date().getFullYear()} KazeB — {labels.footer_tagline}
          </small>
        </div>
      </footer>
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
