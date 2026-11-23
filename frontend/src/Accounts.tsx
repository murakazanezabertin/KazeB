import { useEffect, useState, type FormEvent, type ReactNode } from "react";

import {
  ApiError,
  getAccount,
  getAuthUi,
  getFavorites,
  submitForm,
  toggleFavorite,
  type AccountData,
  type AuthUiData,
  type FavoriteData,
  type HomepageData,
} from "./api/client";

type CommonLabels = HomepageData["labels"];
type Copy = AuthUiData["labels"];

function AccountCard({ children }: { children: ReactNode }) {
  return (
    <main className="container py-4 py-md-5 account-page">
      <div className="account-page-card">{children}</div>
    </main>
  );
}

function FormErrors({ error, field }: { error: unknown; field?: string }) {
  if (!(error instanceof ApiError)) return null;
  const messages = field ? error.fieldErrors[field] : undefined;
  if (!messages?.length) return null;
  return (
    <div className="invalid-feedback d-block">
      {messages.map((message, index) => <div key={`${message}-${index}`}>{message}</div>)}
    </div>
  );
}

function ApiErrorMessage({ error }: { error: unknown }) {
  if (!(error instanceof Error)) return null;
  const globalErrors = error instanceof ApiError ? error.fieldErrors.__all__ : undefined;
  return (
    <div className="alert alert-danger" role="alert">
      <div>{error.message}</div>
      {globalErrors?.map((message, index) => <div key={`${message}-${index}`}>{message}</div>)}
    </div>
  );
}

function TextField({
  name,
  label,
  defaultValue,
  type = "text",
  required = false,
  error,
  accept,
  maxLength,
  autoComplete,
  inputMode,
  pattern,
}: {
  name: string;
  label: string;
  defaultValue?: string;
  type?: string;
  required?: boolean;
  error?: unknown;
  accept?: string;
  maxLength?: number;
  autoComplete?: string;
  inputMode?: "text" | "search" | "none" | "email" | "tel" | "url" | "numeric" | "decimal";
  pattern?: string;
}) {
  return (
    <div className="mb-3">
      <label className="form-label" htmlFor={name}>{label}</label>
      <input
        className={`form-control${error instanceof ApiError && error.fieldErrors[name] ? " is-invalid" : ""}`}
        id={name}
        name={name}
        type={type}
        defaultValue={defaultValue}
        required={required}
        accept={accept}
        maxLength={maxLength}
        autoComplete={autoComplete}
        inputMode={inputMode}
        pattern={pattern}
      />
      <FormErrors error={error} field={name} />
    </div>
  );
}

function TextAreaField({
  name,
  label,
  defaultValue,
  required = false,
  error,
  maxLength,
}: {
  name: string;
  label: string;
  defaultValue?: string;
  required?: boolean;
  error?: unknown;
  maxLength?: number;
}) {
  return (
    <div className="mb-3">
      <label className="form-label" htmlFor={name}>{label}</label>
      <textarea
        className={`form-control${error instanceof ApiError && error.fieldErrors[name] ? " is-invalid" : ""}`}
        id={name}
        name={name}
        defaultValue={defaultValue}
        required={required}
        maxLength={maxLength}
        rows={4}
      />
      <FormErrors error={error} field={name} />
    </div>
  );
}

function CheckField({
  name,
  label,
  checked = false,
  error,
  children,
}: {
  name: string;
  label: string;
  checked?: boolean;
  error?: unknown;
  children?: ReactNode;
}) {
  return (
    <div className="mb-3">
      <div className="form-check">
        <input
          className={`form-check-input${error instanceof ApiError && error.fieldErrors[name] ? " is-invalid" : ""}`}
          id={name}
          name={name}
          type="checkbox"
          defaultChecked={checked}
          value="true"
        />
        <label className="form-check-label" htmlFor={name}>{label}</label>
        {children}
      </div>
      <FormErrors error={error} field={name} />
    </div>
  );
}

function AuthFrame({
  title,
  children,
  footer,
}: {
  title: string;
  children: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <AccountCard>
      <h1 className="h3 mb-4">{title}</h1>
      {children}
      {footer && <div className="account-form-footer">{footer}</div>}
    </AccountCard>
  );
}

function RegisterPage({ copy, ui }: { copy: Copy; ui: AuthUiData }) {
  const [error, setError] = useState<unknown>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      await submitForm("/api/auth/register/", new FormData(event.currentTarget));
      window.location.assign("/accounts/verify/code/");
    } catch (submitError) {
      setError(submitError);
    }
  }

  return (
    <AuthFrame title={copy.register} footer={<a href="/accounts/login/">{copy.login}</a>}>
      <ApiErrorMessage error={error} />
      <form onSubmit={(event) => void submit(event)} encType="multipart/form-data">
        <TextField name="username" label={ui.register_fields.username || copy.username} required autoComplete="username" error={error} />
        <TextField name="email" label={ui.register_fields.email || copy.email} type="email" required autoComplete="email" error={error} />
        <TextField name="phone_number" label={ui.register_fields.phone_number || copy.phone_number} type="tel" required autoComplete="tel" error={error} />
        <TextField name="whatsapp_number" label={ui.register_fields.whatsapp_number || copy.whatsapp_number} type="tel" required error={error} />
        <TextField name="profile_picture" label={ui.register_fields.profile_picture || copy.profile_picture} type="file" accept="image/*" error={error} />
        <TextField name="password1" label={ui.register_fields.password1 || copy.password} type="password" required autoComplete="new-password" error={error} />
        <TextField name="password2" label={ui.register_fields.password2 || copy.password_confirmation} type="password" required autoComplete="new-password" error={error} />
        <CheckField name="agree_to_terms" label={copy.terms_acceptance} error={error}>
          <span className="d-block ms-4 small">
            <a href={ui.terms_url}>{copy.terms}</a> · <a href={ui.privacy_url}>{copy.privacy}</a>
          </span>
        </CheckField>
        <button className="btn btn-brand w-100" type="submit">{copy.register}</button>
      </form>
    </AuthFrame>
  );
}

function LoginPage({ copy }: { copy: Copy }) {
  const [error, setError] = useState<unknown>(null);
  const [submitting, setSubmitting] = useState(false);
  const next = new URLSearchParams(window.location.search).get("next") || "/";

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    const body = new FormData(event.currentTarget);
    body.set("next", next);
    try {
      const result = await submitForm<{ redirect_to: string }>("/api/auth/login/", body);
      window.location.assign(result.redirect_to);
    } catch (submitError) {
      setError(submitError);
      setSubmitting(false);
    }
  }

  return (
    <AuthFrame
      title={copy.login}
      footer={<><a href="/accounts/register/">{copy.register}</a><span> · </span><a href="/accounts/password_reset/">{copy.forgot_password}</a></>}
    >
      <ApiErrorMessage error={error} />
      <form onSubmit={(event) => void submit(event)}>
        <TextField name="username" label={copy.username} required autoComplete="username" error={error} />
        <TextField name="password" label={copy.password} type="password" required autoComplete="current-password" error={error} />
        <button className="btn btn-brand w-100" type="submit" disabled={submitting}>
          {copy.login}
        </button>
      </form>
      {error instanceof ApiError && error.fieldErrors.__all__?.length > 0 && (
        <div className="account-form-footer">
          <a href="/accounts/verify/resend/">{copy.resend_verification}</a>
        </div>
      )}
    </AuthFrame>
  );
}

function ResendVerificationPage({ copy }: { copy: Copy }) {
  const [error, setError] = useState<unknown>(null);
  const [message, setMessage] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      const response = await submitForm<{ detail: string }>(
        "/api/auth/verify/resend/",
        new FormData(event.currentTarget),
      );
      setMessage(copy.verification_generic || response.detail);
    } catch (submitError) {
      setError(submitError);
    }
  }

  return (
    <AuthFrame title={copy.resend_verification} footer={<a href="/accounts/login/">{copy.login}</a>}>
      {message && <div className="alert alert-success" role="status">{message}</div>}
      <ApiErrorMessage error={error} />
      <form onSubmit={(event) => void submit(event)}>
        <TextField name="email" label={copy.email} type="email" required autoComplete="email" error={error} />
        <button className="btn btn-brand w-100" type="submit">{copy.resend}</button>
      </form>
    </AuthFrame>
  );
}

function VerifyCodePage({ copy }: { copy: Copy }) {
  const [error, setError] = useState<unknown>(null);
  const [message, setMessage] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      const response = await submitForm<{ detail: string; account?: any; redirect_to?: string }>(
        "/api/auth/verify/code/",
        new FormData(event.currentTarget),
      );
      if (response.redirect_to) {
        window.location.assign(response.redirect_to);
        return;
      }
      setMessage(response.detail);
    } catch (submitError) {
      setError(submitError);
    }
  }

  return (
    <AuthFrame title={copy.verify_status || "Emeza imeli"} footer={<a href="/accounts/verify/resend/">{copy.resend_verification}</a>}>
      {message && <div className="alert alert-success" role="status">{message}</div>}
      <ApiErrorMessage error={error} />
      <form onSubmit={(event) => void submit(event)}>
        <TextField
          name="code"
          label={copy.verify_status || "Kode ya 6 inyuguti"}
          type="text"
          required
          autoComplete="one-time-code"
          inputMode="numeric"
          pattern="[0-9]*"
          maxLength={6}
          error={error}
        />
        <button className="btn btn-brand w-100" type="submit">{copy.verify_status || "Emeza"}</button>
      </form>
      <p className="mt-3 text-center small">
        <a href="/accounts/verify/resend/">{copy.resend_verification}</a>
      </p>
      <p className="mt-3 text-center small">
        <a href="/accounts/login/">{copy.login}</a>
      </p>
    </AuthFrame>
  );
}

function PasswordResetRequestPage({ copy }: { copy: Copy }) {
  const [error, setError] = useState<unknown>(null);
  const [message, setMessage] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      const response = await submitForm<{ detail: string }>(
        "/api/auth/password-reset/",
        new FormData(event.currentTarget),
      );
      setMessage(response.detail);
    } catch (submitError) {
      setError(submitError);
    }
  }

  return (
    <AuthFrame title={copy.forgot_password} footer={<a href="/accounts/login/">{copy.login}</a>}>
      {message && <div className="alert alert-success" role="status">{message}</div>}
      <ApiErrorMessage error={error} />
      <form onSubmit={(event) => void submit(event)}>
        <TextField name="email" label={copy.email} type="email" required autoComplete="email" error={error} />
        <button className="btn btn-brand w-100" type="submit">{copy.send_reset_link}</button>
      </form>
    </AuthFrame>
  );
}

function PasswordResetConfirmPage({ copy }: { copy: Copy }) {
  const [error, setError] = useState<unknown>(null);
  const [complete, setComplete] = useState(false);
  const [, uidb64 = "", token = ""] = window.location.pathname.match(
    /^\/accounts\/reset\/([^/]+)\/([^/]+)\/?$/,
  ) || [];

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      await submitForm(
        `/api/auth/password-reset/${encodeURIComponent(uidb64)}/${encodeURIComponent(token)}/`,
        new FormData(event.currentTarget),
      );
      setComplete(true);
    } catch (submitError) {
      setError(submitError);
    }
  }

  return (
    <AuthFrame title={copy.reset_password} footer={<a href="/accounts/login/">{copy.login}</a>}>
      {complete ? (
        <div className="alert alert-success" role="status">{copy.password_reset_complete}</div>
      ) : (
        <>
          <ApiErrorMessage error={error} />
          <form onSubmit={(event) => void submit(event)}>
            <TextField name="new_password1" label={copy.new_password} type="password" required autoComplete="new-password" error={error} />
            <TextField name="new_password2" label={copy.password_confirmation} type="password" required autoComplete="new-password" error={error} />
            <button className="btn btn-brand w-100" type="submit">{copy.reset_password}</button>
          </form>
        </>
      )}
    </AuthFrame>
  );
}

function AccountOverview({
  copy,
  account,
}: {
  copy: Copy;
  account: AccountData;
}) {
  return (
    <AuthFrame title={copy.account_details}>
      <div className="account-profile-header">
        {account.profile_picture ? (
          <img src={account.profile_picture} className="account-avatar" alt=""
            onError={(e) => {
              e.currentTarget.style.display = "none";
              const fallback = e.currentTarget.nextElementSibling;
              if (fallback) {
                (fallback as HTMLElement).style.display = "inline-flex";
              }
            }}
          />
        ) : null}
        <span className="account-avatar account-avatar-fallback" style={{ display: account.profile_picture ? "none" : "inline-flex" }}>{account.username.slice(0, 1).toUpperCase()}</span>
        <div>
          <h2 className="h5 mb-1">{[account.first_name, account.last_name].filter(Boolean).join(" ") || account.username}</h2>
          <p className="text-muted mb-0">@{account.username}</p>
        </div>
      </div>
      <dl className="account-detail-list">
        <dt>{copy.email}</dt><dd>{account.email}</dd>
        <dt>{copy.verify_status}</dt><dd>{account.email_verified ? copy.verified : copy.not_verified}</dd>
        <dt>{copy.phone_number}</dt><dd>{account.phone_number}</dd>
        <dt>{copy.whatsapp_number}</dt><dd>{account.whatsapp_number}</dd>
        <dt>{copy.location}</dt><dd>{account.location || "—"}</dd>
        <dt>{copy.bio}</dt><dd>{account.bio || "—"}</dd>
      </dl>
      <div className="d-flex flex-wrap gap-2">
        <a className="btn btn-brand" href="/accounts/edit/">{copy.save_changes}</a>
        <a className="btn btn-outline-brand" href="/listings/favorites/">{copy.listing_saved}</a>
        <a className="btn btn-outline-danger" href="/accounts/delete/">{copy.delete_account}</a>
      </div>
    </AuthFrame>
  );
}

function AccountPage({
  copy,
  ui,
  mode,
}: {
  copy: Copy;
  ui: AuthUiData;
  mode: "profile" | "edit" | "delete";
}) {
  const [account, setAccount] = useState<AccountData | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [message, setMessage] = useState("");
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    let active = true;
    getAccount()
      .then(({ account: current }) => {
        if (active) setAccount(current);
      })
      .catch((loadError: unknown) => {
        if (active) setError(loadError);
      });
    return () => {
      active = false;
    };
  }, []);

  async function update(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage("");
    try {
      const response = await submitForm<{
        detail: string;
        email_verification_required?: boolean;
      }>("/api/account/edit/", new FormData(event.currentTarget));
      if (response.email_verification_required) {
        window.location.assign("/accounts/verify/sent/");
        return;
      }
      setMessage(response.detail);
      const { account: updated } = await getAccount();
      setAccount(updated);
    } catch (submitError) {
      setError(submitError);
    }
  }

  async function removeAccount(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setDeleting(true);
    try {
      await submitForm("/api/account/delete/", new FormData(event.currentTarget));
      window.location.assign("/");
    } catch (submitError) {
      setError(submitError);
      setDeleting(false);
    }
  }

  if (error instanceof ApiError && error.status === 401) {
    return (
      <AuthFrame title={copy.account}>
        <ApiErrorMessage error={error} />
        <a className="btn btn-brand" href={`/accounts/login/?next=${encodeURIComponent(window.location.pathname)}`}>{copy.login}</a>
      </AuthFrame>
    );
  }
  if (error && !account) return <AuthFrame title={copy.account}><ApiErrorMessage error={error} /></AuthFrame>;
  if (!account) return <AccountCard><p aria-live="polite">{copy.loading}</p></AccountCard>;

  if (mode === "profile") return <AccountOverview copy={copy} account={account} />;

  if (mode === "delete") {
    return (
      <AuthFrame title={copy.delete_account} footer={<a href="/accounts/profile/">{copy.cancel}</a>}>
        <p>{copy.confirm_delete}</p>
        <ApiErrorMessage error={error} />
        <form onSubmit={(event) => void removeAccount(event)}>
          <TextField name="password" label={copy.current_password} type="password" required autoComplete="current-password" error={error} />
          <button className="btn btn-danger w-100" type="submit" disabled={deleting}>{copy.delete_account}</button>
        </form>
      </AuthFrame>
    );
  }

  return (
    <AuthFrame title={copy.account} footer={<a href="/accounts/profile/">{copy.cancel}</a>}>
      {message && <div className="alert alert-success" role="status">{message}</div>}
      <ApiErrorMessage error={error} />
      <form onSubmit={(event) => void update(event)} encType="multipart/form-data">
        <TextField name="first_name" label={ui.account_fields.first_name || copy.first_name} defaultValue={account.first_name} error={error} />
        <TextField name="last_name" label={ui.account_fields.last_name || copy.last_name} defaultValue={account.last_name} error={error} />
        <TextField name="email" label={ui.account_fields.email || copy.email} type="email" defaultValue={account.email} required autoComplete="email" error={error} />
        <TextField name="profile_picture" label={ui.account_fields.profile_picture || copy.profile_picture} type="file" accept="image/*" error={error} />
        <TextField name="location" label={ui.account_fields.location || copy.location} defaultValue={account.location} error={error} />
        <TextAreaField name="bio" label={ui.account_fields.bio || copy.bio} defaultValue={account.bio} maxLength={500} error={error} />
        <TextField name="phone_number" label={ui.account_fields.phone_number || copy.phone_number} type="tel" defaultValue={account.phone_number} required autoComplete="tel" error={error} />
        <TextField name="whatsapp_number" label={ui.account_fields.whatsapp_number || copy.whatsapp_number} type="tel" defaultValue={account.whatsapp_number} required error={error} />
        <button className="btn btn-brand w-100" type="submit">{copy.save_changes}</button>
      </form>
    </AuthFrame>
  );
}

function FavoritesPage({ copy, common }: { copy: Copy; common: CommonLabels }) {
  const [favorites, setFavorites] = useState<FavoriteData[] | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [pending, setPending] = useState<number[]>([]);
  const [pagination, setPagination] = useState<{ page: number; pages: number; has_next: boolean; has_previous: boolean } | null>(null);
  const page = new URLSearchParams(window.location.search).get("page") || "";

  async function load() {
    try {
      const response = await getFavorites(page);
      setFavorites(response.results);
      setPagination(response.pagination);
    } catch (loadError) {
      setError(loadError);
    }
  }

  useEffect(() => {
    void load();
  }, [page]);

  async function remove(listingId: number) {
    const previous = favorites;
    setFavorites((current) => current?.filter((item) => item.listing.id !== listingId) ?? null);
    setPending((current) => [...current, listingId]);
    setError(null);
    try {
      await toggleFavorite(listingId);
    } catch (toggleError) {
      setFavorites(previous);
      setError(toggleError);
    } finally {
      setPending((current) => current.filter((id) => id !== listingId));
    }
  }

  if (error instanceof ApiError && error.status === 401) {
    return (
      <AuthFrame title={copy.listing_saved}>
        <ApiErrorMessage error={error} />
        <a className="btn btn-brand" href={`/accounts/login/?next=${encodeURIComponent(window.location.pathname)}`}>{common.login}</a>
      </AuthFrame>
    );
  }
  if (error && favorites === null) return <AuthFrame title={copy.listing_saved}><ApiErrorMessage error={error} /></AuthFrame>;
  if (favorites === null) return <AccountCard><p aria-live="polite">{common.loading}</p></AccountCard>;

  return (
    <AccountCard>
      <h1 className="h3 mb-4">{copy.listing_saved}</h1>
      <ApiErrorMessage error={error} />
      {favorites.length ? (
        <>
          <div className="row row-cols-1 row-cols-sm-2 row-cols-lg-4 g-4">
            {favorites.map(({ listing, is_active }) => (
              <div className="col" key={listing.id}>
                <article className="card listing-card h-100">
                  {is_active ? (
                    <a href={listing.url} className="text-decoration-none text-body">
                      <FavoriteImage image={listing.image} title={listing.name} emptyLabel={common.empty_image} />
                      <div className="card-body">
                        <h2 className="h6 mb-1">{listing.name}</h2>
                        <p className="fw-bold text-brand mb-1">{listing.price}</p>
                        <p className="small text-muted mb-0">{listing.location}</p>
                      </div>
                    </a>
                  ) : (
                    <div>
                      <FavoriteImage image={listing.image} title={listing.name} emptyLabel={common.empty_image} />
                      <div className="card-body">
                        <h2 className="h6 mb-1">{listing.name}</h2>
                        <p className="small text-muted mb-0">{copy.unavailable}</p>
                      </div>
                    </div>
                  )}
                  <div className="card-footer bg-white border-0 pt-0">
                    <button
                      className="btn btn-sm btn-outline-secondary"
                      type="button"
                      disabled={pending.includes(listing.id)}
                      onClick={() => void remove(listing.id)}
                    >
                      {copy.remove_favorite}
                    </button>
                  </div>
                </article>
              </div>
            ))}
          </div>
          {pagination && pagination.pages > 1 && (
            <nav className="mt-4" aria-label={common.favorites}>
              <ul className="pagination justify-content-center">
                {pagination.has_previous && <li className="page-item"><a className="page-link" href={`?page=${pagination.page - 1}`}>{common.previous_page}</a></li>}
                <li className="page-item disabled"><span className="page-link">{pagination.page} / {pagination.pages}</span></li>
                {pagination.has_next && <li className="page-item"><a className="page-link" href={`?page=${pagination.page + 1}`}>{common.next_page}</a></li>}
              </ul>
            </nav>
          )}
        </>
      ) : (
        <p className="text-muted">{copy.no_favorites}</p>
      )}
    </AccountCard>
  );
}

function FavoriteImage({
  image,
  title,
  emptyLabel,
}: {
  image: string | null;
  title: string;
  emptyLabel: string;
}) {
  return image ? (
    <img src={image} className="card-img-top listing-card-img" alt={title} loading="lazy"
      onError={(e) => {
        e.currentTarget.style.display = "none";
        const placeholder = e.currentTarget.parentNode?.querySelector(".listing-card-img-placeholder");
        if (placeholder) {
          (placeholder as HTMLElement).style.display = "flex";
        }
      }}
    />
  ) : (
    <div className="listing-card-img listing-card-img-placeholder">{emptyLabel}</div>
  );
}

export default function AccountPages({
  pathname,
  common,
}: {
  pathname: string;
  common: CommonLabels;
}) {
  const [ui, setUi] = useState<AuthUiData | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    let active = true;
    getAuthUi()
      .then((response) => {
        if (active) setUi(response);
      })
      .catch((loadError: unknown) => {
        if (active) setError(loadError);
      });
    return () => {
      active = false;
    };
  }, []);

  if (error) return <main className="container py-4"><ApiErrorMessage error={error} /></main>;
  if (!ui) return <AccountCard><p aria-live="polite">{common.loading}</p></AccountCard>;

  if (pathname === "/accounts/register/") return <RegisterPage copy={ui.labels} ui={ui} />;
  if (pathname === "/accounts/login/") return <LoginPage copy={ui.labels} />;
  if (pathname === "/accounts/verify/sent/") {
    return (
      <AuthFrame title={ui.labels.verify_status} footer={<a href="/accounts/verify/resend/">{ui.labels.resend_verification}</a>}>
        <div className="alert alert-success" role="status">{ui.labels.verification_sent}</div>
      </AuthFrame>
    );
  }
  if (pathname === "/accounts/verify/code/") return <VerifyCodePage copy={ui.labels} />;
  if (pathname === "/accounts/verify/resend/") return <ResendVerificationPage copy={ui.labels} />;
  if (pathname === "/accounts/password_reset/") return <PasswordResetRequestPage copy={ui.labels} />;
  if (/^\/accounts\/reset\/[^/]+\/[^/]+\/?$/.test(pathname)) {
    return <PasswordResetConfirmPage copy={ui.labels} />;
  }
  if (pathname === "/accounts/reset/done/" || pathname === "/accounts/password_reset/done/") {
    return <AuthFrame title={ui.labels.reset_password}><div className="alert alert-success">{ui.labels.password_reset_complete}</div></AuthFrame>;
  }
  if (pathname === "/accounts/profile/") return <AccountPage copy={ui.labels} ui={ui} mode="profile" />;
  if (pathname === "/accounts/edit/") return <AccountPage copy={ui.labels} ui={ui} mode="edit" />;
  if (pathname === "/accounts/delete/") return <AccountPage copy={ui.labels} ui={ui} mode="delete" />;
  if (pathname === "/listings/favorites/") return <FavoritesPage copy={ui.labels} common={common} />;
  return <AccountCard><ApiErrorMessage error={new Error(common.page_not_found)} /></AccountCard>;
}
