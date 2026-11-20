import { useEffect, useMemo, useState, type FormEvent } from "react";

import {
  getAdminActivity,
  getAdminOverview,
  getAdminPhones,
  getAdminReports,
  getAdminReviews,
  getAdminUserDetail,
  getAdminUsers,
  getAdminListings,
  moderateAdminListing,
  removeAdminReview,
  updateAdminReport,
  updateAdminUserStatus,
  type AdminAuditEntry,
  type AdminListing,
  type AdminOverviewData,
  type AdminPageData,
  type AdminPhoneVerification,
  type AdminReport,
  type AdminReview,
  type AdminUser,
  type PaginationData,
} from "./api/client";

type Section = "overview" | "users" | "listings" | "reports" | "reviews" | "phones" | "activity";

const sections: Array<{ id: Section; label: string }> = [
  { id: "overview", label: "Overview" },
  { id: "users", label: "User management" },
  { id: "listings", label: "Listings" },
  { id: "reports", label: "Reports" },
  { id: "reviews", label: "Reviews" },
  { id: "phones", label: "Phone verification" },
  { id: "activity", label: "Audit activity" },
];

function displayDate(value: string | null) {
  return value ? new Date(value).toLocaleString() : "Never";
}

function AdminDashboard() {
  const [section, setSection] = useState<Section>("overview");
  const [overview, setOverview] = useState<AdminOverviewData | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [listings, setListings] = useState<AdminListing[]>([]);
  const [reports, setReports] = useState<AdminReport[]>([]);
  const [reviews, setReviews] = useState<AdminReview[]>([]);
  const [phones, setPhones] = useState<AdminPhoneVerification[]>([]);
  const [activities, setActivities] = useState<AdminAuditEntry[]>([]);
  const [pagination, setPagination] = useState<PaginationData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");
  const [filter, setFilter] = useState("");
  const [joinedFrom, setJoinedFrom] = useState("");
  const [joinedTo, setJoinedTo] = useState("");
  const [page, setPage] = useState(1);
  const [reloadKey, setReloadKey] = useState(0);
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);
  const [selectedUser, setSelectedUser] = useState<{
    user: AdminUser;
    statistics: { listings: number; reviews_received: number; reports_received: number };
    listings: AdminListing[];
    reports: AdminReport[];
    activity: Array<{ type: string; title: string; created_at: string }>;
  } | null>(null);
  const [selectedListingId, setSelectedListingId] = useState<number | null>(null);
  const [selectedReportId, setSelectedReportId] = useState<number | null>(null);
  const [reason, setReason] = useState("");
  const [decisionNotes, setDecisionNotes] = useState("");
  const [nextReportStatus, setNextReportStatus] = useState<AdminReport["status"]>("under_review");
  const [actionPending, setActionPending] = useState(false);

  const permissions = overview?.permissions;
  const selectedListing = listings.find((listing) => listing.id === selectedListingId) || null;
  const selectedReport = reports.find((report) => report.id === selectedReportId) || null;

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError("");
      setPagination(null);
      try {
        if (section === "overview") {
          const data = await getAdminOverview();
          if (!cancelled) setOverview(data);
          return;
        }
        const query = { q: appliedSearch, page, page_size: 20 };
        let result: AdminPageData<unknown>;
        if (section === "users") {
          const data = await getAdminUsers({
            ...query,
            verified: filter,
            joined_from: joinedFrom,
            joined_to: joinedTo,
          });
          result = data;
          if (!cancelled) setUsers(data.results);
        } else if (section === "listings") {
          const data = await getAdminListings({ ...query, status: filter });
          result = data;
          if (!cancelled) setListings(data.results);
        } else if (section === "reports") {
          const data = await getAdminReports({ ...query, status: filter });
          result = data;
          if (!cancelled) setReports(data.results);
        } else if (section === "reviews") {
          const data = await getAdminReviews(query);
          result = data;
          if (!cancelled) setReviews(data.results);
        } else if (section === "phones") {
          const data = await getAdminPhones({ ...query, verified: filter });
          result = data;
          if (!cancelled) setPhones(data.results);
        } else {
          const data = await getAdminActivity(query);
          result = data;
          if (!cancelled) setActivities(data.results);
        }
        if (!cancelled) setPagination(result.pagination);
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Unable to load administrator data.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [section, appliedSearch, filter, joinedFrom, joinedTo, page, reloadKey]);

  useEffect(() => {
    let cancelled = false;
    setSelectedUser(null);
    if (selectedUserId === null) return () => { cancelled = true; };
    getAdminUserDetail(selectedUserId).then(
      (data) => {
        if (!cancelled) setSelectedUser(data);
      },
      (detailError: unknown) => {
        if (!cancelled) {
          setError(detailError instanceof Error ? detailError.message : "Unable to load user details.");
        }
      },
    );
    return () => {
      cancelled = true;
    };
  }, [selectedUserId, reloadKey]);

  function chooseSection(next: Section) {
    setSection(next);
    setPage(1);
    setSearch("");
    setAppliedSearch("");
    setFilter("");
    setJoinedFrom("");
    setJoinedTo("");
    setSelectedUserId(null);
    setSelectedListingId(null);
    setSelectedReportId(null);
    setReason("");
    setDecisionNotes("");
  }

  function applySearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPage(1);
    setAppliedSearch(search.trim());
  }

  function refresh() {
    setReloadKey((value) => value + 1);
  }

  async function changeUserStatus(user: AdminUser) {
    setActionPending(true);
    setError("");
    try {
      await updateAdminUserStatus(user.id, !user.is_active, reason.trim());
      setReason("");
      refresh();
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : "Unable to update account status.");
    } finally {
      setActionPending(false);
    }
  }

  async function moderateListing(action: "hide" | "restore" | "remove") {
    if (!selectedListing) return;
    setActionPending(true);
    setError("");
    try {
      await moderateAdminListing(selectedListing.id, action, reason.trim());
      setReason("");
      refresh();
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : "Unable to moderate listing.");
    } finally {
      setActionPending(false);
    }
  }

  async function saveReport() {
    if (!selectedReport) return;
    setActionPending(true);
    setError("");
    try {
      await updateAdminReport(selectedReport.id, nextReportStatus, decisionNotes.trim());
      setDecisionNotes("");
      refresh();
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : "Unable to update report.");
    } finally {
      setActionPending(false);
    }
  }

  async function removeReview(review: AdminReview) {
    const moderationReason = window.prompt("Reason for removing this review:");
    if (moderationReason === null) return;
    setActionPending(true);
    setError("");
    try {
      await removeAdminReview(review.id, moderationReason.trim());
      refresh();
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : "Unable to remove review.");
    } finally {
      setActionPending(false);
    }
  }

  const availableSections = useMemo(
    () => sections.filter(({ id }) => {
      if (id === "overview") return true;
      if (!permissions) return false;
      if (id === "users") return permissions.users;
      if (id === "listings") return permissions.listings;
      if (id === "reports") return permissions.reports;
      if (id === "reviews") return permissions.reviews;
      if (id === "phones") return permissions.phones;
      return permissions.activity;
    }),
    [permissions],
  );

  function renderOverview() {
    if (!overview) return null;
    const { statistics } = overview;
    const cards = [
      { label: "Registered users", value: statistics.users.total, note: `${statistics.users.verified} verified · ${statistics.users.unverified} unverified` },
      { label: "Listings", value: statistics.listings.total, note: `${statistics.listings.active} active · ${statistics.listings.hidden} hidden (${statistics.listings.removed} removed) · ${statistics.listings.inactive} inactive` },
      { label: "Reports", value: statistics.reports.total, note: `${statistics.reports.pending} pending · ${statistics.reports.resolved} resolved · ${statistics.reports.rejected} rejected` },
      { label: "Trust signals", value: statistics.reviews, note: `${statistics.verified_phones} verified phones · ${statistics.unverified_phones} unverified` },
    ];
    const trends = [
      { title: "Registrations", data: overview.registration_trend },
      { title: "Listings created", data: overview.listing_trend },
    ];
    return (
      <>
        <div className="admin-stat-grid">
          {cards.map((card) => (
            <article className="admin-stat-card" key={card.label}>
              <span>{card.label}</span>
              <strong>{card.value.toLocaleString()}</strong>
              <small>{card.note}</small>
            </article>
          ))}
        </div>
        <div className="admin-trend-grid">
          {trends.map(({ title, data }) => {
            const max = Math.max(1, ...data.map((item) => item.total));
            return (
              <section className="admin-panel" key={title}>
                <h2>{title} · last 7 days</h2>
                {data.length ? (
                  <div className="admin-chart" role="img" aria-label={`${title} chart`}>
                    {data.map((item) => (
                      <div className="admin-chart-column" key={item.date} title={`${item.date}: ${item.total}`}>
                        <strong>{item.total}</strong>
                        <span style={{ height: `${Math.max(6, (item.total / max) * 100)}%` }} />
                        <small>{new Date(`${item.date}T00:00:00`).toLocaleDateString(undefined, { weekday: "short" })}</small>
                      </div>
                    ))}
                  </div>
                ) : <p className="admin-empty">No data for this period.</p>}
              </section>
            );
          })}
        </div>
        <div className="admin-overview-columns">
          <section className="admin-panel">
            <h2>Recent registrations</h2>
            {overview.recent_registrations.length ? overview.recent_registrations.map((user) => (
              <div className="admin-activity-row" key={user.id}>
                <span><strong>{user.username}</strong><small>{user.email}</small></span>
                <small>{displayDate(user.date_joined)}</small>
              </div>
            )) : <p className="admin-empty">No registrations yet.</p>}
          </section>
          <section className="admin-panel">
            <h2>Recent listings</h2>
            {overview.recent_listings.length ? overview.recent_listings.map((listing) => (
              <div className="admin-activity-row" key={listing.id}>
                <span><strong>{listing.name}</strong><small>{listing.seller.username} · {listing.price}</small></span>
                <small>{displayDate(listing.created_at)}</small>
              </div>
            )) : <p className="admin-empty">No listings yet.</p>}
          </section>
        </div>
        <section className="admin-panel">
          <h2>Recent platform activity</h2>
          {overview.recent_activity.length ? overview.recent_activity.map((activity, index) => (
            <div className="admin-activity-row" key={`${activity.created_at}-${index}`}>
              <span><strong>{activity.title}</strong><small>{activity.type}</small></span>
              <small>{displayDate(activity.created_at)}</small>
            </div>
          )) : <p className="admin-empty">No activity recorded yet.</p>}
        </section>
      </>
    );
  }

  function renderUsers() {
    return (
      <>
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead><tr><th>User</th><th>Phone</th><th>Joined</th><th>Verification</th><th>Status</th></tr></thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id} className={selectedUserId === user.id ? "is-selected" : ""}>
                  <td><button className="admin-row-link" onClick={() => setSelectedUserId(user.id)} type="button">{user.username}</button><small>{user.email}</small></td>
                  <td>{user.phone_number || "—"}</td>
                  <td>{displayDate(user.date_joined)}</td>
                  <td>{user.email_verified ? "Email verified" : "Email unverified"}<small>{user.is_phone_verified ? "Phone verified" : "Phone unverified"}</small></td>
                  <td><span className={`admin-status ${user.is_active ? "is-active" : "is-muted"}`}>{user.is_active ? "Active" : "Suspended"}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
          {!users.length && !loading && <p className="admin-empty">No users match these filters.</p>}
        </div>
        {selectedUser && (
          <section className="admin-detail-panel">
            <div className="admin-detail-heading"><h2>{selectedUser.user.username}</h2><button type="button" className="admin-close" onClick={() => setSelectedUserId(null)}>Close</button></div>
            <p>{selectedUser.user.email} · {selectedUser.user.phone_number || "No phone number"} · Last login: {displayDate(selectedUser.user.last_login)}</p>
            <p>{selectedUser.statistics.listings} listings · {selectedUser.statistics.reviews_received} reviews · {selectedUser.statistics.reports_received} reports received</p>
            {permissions?.suspend_users && !selectedUser.user.is_staff && (
              <div className="admin-action-row">
                <input className="form-control" value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Reason required" aria-label="Account action reason" />
                <button className="btn btn-outline-danger" disabled={actionPending || !reason.trim()} onClick={() => void changeUserStatus(selectedUser.user)} type="button">
                  {selectedUser.user.is_active ? "Suspend account" : "Reactivate account"}
                </button>
              </div>
            )}
            <h3>User listings</h3>
            {selectedUser.listings.length ? selectedUser.listings.map((listing) => (
              <div className="admin-activity-row" key={listing.id}>
                <span><strong>{listing.name}</strong><small>{listing.moderation_status} · {listing.price}</small></span>
                <small>{displayDate(listing.created_at)}</small>
              </div>
            )) : <p className="admin-empty">This user has no listings.</p>}
            <h3>Reports involving this user</h3>
            {selectedUser.reports.length ? selectedUser.reports.map((report) => (
              <div className="admin-activity-row" key={report.id}>
                <span><strong>Report #{report.id} · {report.status.replace("_", " ")}</strong><small>{report.target?.label || report.reason} · {report.reporter}</small></span>
                <small>{displayDate(report.created_at)}</small>
              </div>
            )) : <p className="admin-empty">No reports involving this user.</p>}
            <h3>Recent user activity</h3>
            {selectedUser.activity.length ? selectedUser.activity.map((activity, index) => (
              <div className="admin-activity-row" key={`${activity.created_at}-${index}`}>
                <span><strong>{activity.title}</strong><small>{activity.type}</small></span>
                <small>{displayDate(activity.created_at)}</small>
              </div>
            )) : <p className="admin-empty">No recent activity found.</p>}
          </section>
        )}
      </>
    );
  }

  function renderListings() {
    return (
      <>
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead><tr><th>Listing</th><th>Seller</th><th>Price</th><th>Status</th><th>Posted</th></tr></thead>
            <tbody>
              {listings.map((listing) => (
                <tr key={listing.id} className={selectedListingId === listing.id ? "is-selected" : ""}>
                  <td><button className="admin-row-link" onClick={() => { setSelectedListingId(listing.id); setReason(""); }} type="button">{listing.name}</button><small>{listing.category}</small></td>
                  <td>{listing.seller.username}<small>{listing.seller.phone_number}</small></td>
                  <td>{listing.price}</td>
                  <td><span className="admin-status">{listing.moderation_status === "visible" ? (listing.is_active ? "Active" : "Inactive") : listing.moderation_status}</span></td>
                  <td>{displayDate(listing.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!listings.length && !loading && <p className="admin-empty">No listings match these filters.</p>}
        </div>
        {selectedListing && (
          <section className="admin-detail-panel">
            <div className="admin-detail-heading"><h2>{selectedListing.name}</h2><button type="button" className="admin-close" onClick={() => setSelectedListingId(null)}>Close</button></div>
            <p>{selectedListing.description}</p>
            <p>Seller: {selectedListing.seller.username} · {selectedListing.seller.email} · {selectedListing.seller.phone_number}</p>
            <p>Current moderation: {selectedListing.moderation_status}. {selectedListing.moderation_reason}</p>
            <label className="form-label" htmlFor="listing-moderation-reason">Moderation reason</label>
            <textarea id="listing-moderation-reason" className="form-control mb-3" value={reason} onChange={(event) => setReason(event.target.value)} rows={2} />
            <div className="admin-action-row">
              {selectedListing.moderation_status !== "hidden" && permissions?.moderate_listings && (
                <button className="btn btn-outline-warning" disabled={actionPending || !reason.trim()} onClick={() => void moderateListing("hide")} type="button">Hide listing</button>
              )}
              {selectedListing.moderation_status !== "visible" && permissions?.moderate_listings && (
                <button className="btn btn-outline-success" disabled={actionPending || !reason.trim()} onClick={() => void moderateListing("restore")} type="button">Restore listing</button>
              )}
              {selectedListing.moderation_status !== "removed" && permissions?.remove_listings && (
                <button className="btn btn-danger" disabled={actionPending || !reason.trim()} onClick={() => void moderateListing("remove")} type="button">Remove from marketplace</button>
              )}
            </div>
          </section>
        )}
      </>
    );
  }

  function renderReports() {
    return (
      <>
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead><tr><th>Report</th><th>Target</th><th>Reason</th><th>Status</th><th>Created</th></tr></thead>
            <tbody>
              {reports.map((report) => (
                <tr key={report.id} className={selectedReportId === report.id ? "is-selected" : ""}>
                  <td><button className="admin-row-link" onClick={() => { setSelectedReportId(report.id); setNextReportStatus(report.status); setDecisionNotes(report.decision_notes); }} type="button">#{report.id} · {report.reporter}</button><small>{report.details}</small></td>
                  <td>{report.target ? `${report.target.type}: ${report.target.label}` : "Unknown"}</td>
                  <td>{report.reason}</td>
                  <td><span className="admin-status">{report.status.replace("_", " ")}</span></td>
                  <td>{displayDate(report.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!reports.length && !loading && <p className="admin-empty">No reports match these filters.</p>}
        </div>
        {selectedReport && (
          <section className="admin-detail-panel">
            <div className="admin-detail-heading"><h2>Report #{selectedReport.id}</h2><button type="button" className="admin-close" onClick={() => setSelectedReportId(null)}>Close</button></div>
            <p>Reporter: {selectedReport.reporter} · Target: {selectedReport.target?.label || "Unknown"}</p>
            <p>{selectedReport.details || "No description was provided."}</p>
            <p>{selectedReport.evidence.length ? selectedReport.evidence.join(", ") : "No evidence was attached."}</p>
            <p>Handled by: {selectedReport.handled_by || "Not assigned"} · {displayDate(selectedReport.handled_at)}</p>
            {permissions?.manage_reports && (
              <div className="admin-report-decision">
                <label className="form-label" htmlFor="report-status">Decision status</label>
                <select id="report-status" className="form-select mb-2" value={nextReportStatus} onChange={(event) => setNextReportStatus(event.target.value as AdminReport["status"])}>
                  <option value="pending">Pending</option>
                  <option value="under_review">Under review</option>
                  <option value="resolved">Resolved</option>
                  <option value="rejected">Rejected</option>
                </select>
                <label className="form-label" htmlFor="report-notes">Decision notes</label>
                <textarea id="report-notes" className="form-control mb-2" value={decisionNotes} onChange={(event) => setDecisionNotes(event.target.value)} rows={3} />
                <button className="btn btn-brand" disabled={actionPending || ((nextReportStatus === "resolved" || nextReportStatus === "rejected") && !decisionNotes.trim())} onClick={() => void saveReport()} type="button">Save decision</button>
              </div>
            )}
          </section>
        )}
      </>
    );
  }

  function renderReviews() {
    return (
      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead><tr><th>Reviewer</th><th>Seller</th><th>Rating</th><th>Review</th><th>Created</th><th /></tr></thead>
          <tbody>
            {reviews.map((review) => (
              <tr key={review.id}>
                <td>{review.reviewer}</td><td>{review.seller}</td><td>{review.rating}/5</td><td>{review.comment || "—"}</td><td>{displayDate(review.created_at)}</td>
                <td>{permissions?.remove_reviews && <button className="btn btn-sm btn-outline-danger" disabled={actionPending} onClick={() => void removeReview(review)} type="button">Remove</button>}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!reviews.length && !loading && <p className="admin-empty">No reviews found.</p>}
      </div>
    );
  }

  function renderPhones() {
    return (
      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead><tr><th>User</th><th>Phone</th><th>Status</th><th>Code attempts</th><th>Last request</th><th>Expires</th></tr></thead>
          <tbody>
            {phones.map((item) => (
              <tr key={`${item.user}-${item.created_at}`}><td>{item.user}</td><td>{item.phone_number}</td><td>{item.is_verified ? "Verified" : "Unverified"}</td><td>{item.attempts}</td><td>{displayDate(item.created_at)}</td><td>{displayDate(item.expires_at)}</td></tr>
            ))}
          </tbody>
        </table>
        {!phones.length && !loading && <p className="admin-empty">No phone verification attempts found.</p>}
      </div>
    );
  }

  function renderActivity() {
    return (
      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead><tr><th>Action</th><th>Target</th><th>Administrator</th><th>Reason</th><th>Time</th></tr></thead>
          <tbody>
            {activities.map((entry) => (
              <tr key={entry.id}><td>{entry.action}</td><td>{entry.target_label}</td><td>{entry.actor || "System"}</td><td>{entry.reason || "—"}</td><td>{displayDate(entry.created_at)}</td></tr>
            ))}
          </tbody>
        </table>
        {!activities.length && !loading && <p className="admin-empty">No administrator actions recorded.</p>}
      </div>
    );
  }

  const title = sections.find((item) => item.id === section)?.label || "Overview";
  const showSearch = section !== "overview";
  const showFilter = section === "users" || section === "listings" || section === "reports" || section === "phones";

  return (
    <main className="admin-dashboard">
      <aside className="admin-sidebar">
        <a href="/" className="admin-brand"><span className="kazeb-logo-black">Kaze</span><span className="kazeb-logo-orange">B</span><small>Administrator</small></a>
        <nav aria-label="Administrator sections">
          {availableSections.map((item) => (
            <button type="button" key={item.id} className={section === item.id ? "is-active" : ""} onClick={() => chooseSection(item.id)}>
              <span aria-hidden="true">{item.id === "overview" ? "▦" : item.id === "users" ? "♙" : item.id === "listings" ? "▤" : item.id === "reports" ? "⚑" : item.id === "reviews" ? "★" : item.id === "phones" ? "☎" : "◷"}</span>
              {item.label}
            </button>
          ))}
        </nav>
        <a className="admin-back-link" href="/">← Back to marketplace</a>
      </aside>
      <section className="admin-main">
        <header className="admin-topbar">
          <div><p>KazeB platform administration</p><h1>{title}</h1></div>
          <a className="btn btn-outline-brand" href="/admin/">Django admin</a>
        </header>
        {showSearch && (
          <form className="admin-toolbar" onSubmit={applySearch}>
            <input className="form-control" type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder={`Search ${section}...`} aria-label={`Search ${section}`} />
            {section === "users" && (
              <>
                <input className="form-control admin-date-filter" type="date" value={joinedFrom} onChange={(event) => { setJoinedFrom(event.target.value); setPage(1); }} aria-label="Registered from" />
                <input className="form-control admin-date-filter" type="date" value={joinedTo} onChange={(event) => { setJoinedTo(event.target.value); setPage(1); }} aria-label="Registered through" />
              </>
            )}
            {showFilter && (
              <select className="form-select" aria-label="Filter results" value={filter} onChange={(event) => { setFilter(event.target.value); setPage(1); }}>
                <option value="">All statuses</option>
                {section === "users" && <><option value="verified">Email verified</option><option value="unverified">Email unverified</option></>}
                {section === "listings" && <><option value="active">Active</option><option value="hidden">Hidden</option><option value="inactive">Inactive</option><option value="removed">Removed</option></>}
                {section === "reports" && <><option value="pending">Pending</option><option value="under_review">Under review</option><option value="resolved">Resolved</option><option value="rejected">Rejected</option></>}
                {section === "phones" && <><option value="verified">Verified</option><option value="unverified">Unverified</option></>}
              </select>
            )}
            <button className="btn btn-brand" type="submit">Search</button>
          </form>
        )}
        {error && <div className="alert alert-danger" role="alert">{error}</div>}
        {loading && <div className="admin-loading" role="status">Loading administrator data…</div>}
        {!loading && !error && (
          <div className="admin-content">
            {section === "overview" && renderOverview()}
            {section === "users" && renderUsers()}
            {section === "listings" && renderListings()}
            {section === "reports" && renderReports()}
            {section === "reviews" && renderReviews()}
            {section === "phones" && renderPhones()}
            {section === "activity" && renderActivity()}
            {pagination && pagination.pages > 1 && (
              <div className="admin-pagination">
                <button className="btn btn-outline-brand" disabled={!pagination.has_previous} onClick={() => setPage((value) => value - 1)} type="button">Previous</button>
                <span>Page {pagination.page} of {pagination.pages} · {pagination.count ?? 0} records</span>
                <button className="btn btn-outline-brand" disabled={!pagination.has_next} onClick={() => setPage((value) => value + 1)} type="button">Next</button>
              </div>
            )}
          </div>
        )}
      </section>
    </main>
  );
}

export default AdminDashboard;
