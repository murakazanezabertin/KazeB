import { useEffect, useState, type ChangeEvent, type FormEvent } from "react";

import {
  ApiError,
  getSellerListingEdit,
  updateSellerListing,
  type SellerListingEditData,
} from "./api/client";
import { sellerMessages, type SellerLanguage } from "./sellerMessages";

export default function SellerListingEdit({
  listingId,
  language,
}: {
  listingId: number;
  language: SellerLanguage;
}) {
  const [data, setData] = useState<SellerListingEditData | null>(null);
  const [removedImages, setRemovedImages] = useState<number[]>([]);
  const [newImages, setNewImages] = useState<File[]>([]);
  const [newPreviews, setNewPreviews] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string[]>>({});
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let active = true;
    void getSellerListingEdit(listingId)
      .then((result) => {
        if (active) setData(result);
      })
      .catch((loadError) => {
        if (active) {
          setError(
            loadError instanceof ApiError && [401, 403].includes(loadError.status)
              ? sellerMessages[language].authRequired
              : loadError instanceof ApiError
                ? loadError.message
                : sellerMessages[language].formLoadError,
          );
        }
      });
    return () => {
      active = false;
    };
  }, [listingId]);

  useEffect(() => {
    const previews = newImages.map((image) => URL.createObjectURL(image));
    setNewPreviews(previews);
    return () => previews.forEach((preview) => URL.revokeObjectURL(preview));
  }, [newImages]);

  function handleNewImages(event: ChangeEvent<HTMLInputElement>) {
    const selectedImages = Array.from(event.target.files || []);
    if (selectedImages.length > 0) {
      setNewImages((current) => [...current, ...selectedImages]);
    }
    event.target.value = "";
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setFieldErrors({});
    setSubmitting(true);
    const body = new FormData(event.currentTarget);
    body.delete("images");
    removedImages.forEach((id) => body.append("remove_images", String(id)));
    newImages.forEach((image) => body.append("images", image));

    try {
      await updateSellerListing(listingId, body);
      window.location.assign("/listings/dashboard/?saved=updated");
    } catch (submitError) {
      if (submitError instanceof ApiError) {
        setFieldErrors(submitError.fieldErrors);
        setError(submitError.message);
      } else {
        setError(sellerMessages[language].updateError);
      }
    } finally {
      setSubmitting(false);
    }
  }

  if (error && !data) {
    return (
      <main className="container py-4 py-md-5">
        <div className="alert alert-danger" role="alert">{error}</div>
      </main>
    );
  }
  if (!data) {
    return (
      <main className="container py-4 py-md-5" aria-live="polite">
        {sellerMessages[language].loading}
      </main>
    );
  }

  const listing = data.listing;
  const labels = data.labels;
  const fieldError = (name: string) =>
    fieldErrors[name]?.map((message, index) => (
      <div className="invalid-feedback d-block" key={`${name}-${index}`}>{message}</div>
    ));

  return (
    <main className="container py-4 py-md-5 seller-listing-create">
      <div className="seller-listing-form-card">
        <h1 className="h3 mb-4">{labels.title}</h1>
        {error && <div className="alert alert-danger" role="alert">{error}</div>}
        <form onSubmit={(event) => void handleSubmit(event)}>
          <div className="mb-3">
            <label className="form-label" htmlFor="category">{labels.category}</label>
            <select className={`form-select${fieldErrors.category ? " is-invalid" : ""}`} id="category" name="category" defaultValue={listing.category} required>
              {data.categories.map((category) => (
                <option key={category.id} value={category.id}>{category.name}</option>
              ))}
            </select>
            {fieldError("category")}
          </div>

          <div className="mb-3">
            <label className="form-label" htmlFor="name">{labels.name}</label>
            <input className={`form-control${fieldErrors.name ? " is-invalid" : ""}`} id="name" name="name" defaultValue={listing.name} required maxLength={150} />
            {fieldError("name")}
          </div>

          <div className="mb-3">
            <label className="form-label" htmlFor="description">{labels.description}</label>
            <textarea className={`form-control${fieldErrors.description ? " is-invalid" : ""}`} id="description" name="description" defaultValue={listing.description} rows={5} required />
            {fieldError("description")}
          </div>

          <div className="mb-3">
            <label className="form-label" htmlFor="condition">{labels.condition}</label>
            <select className={`form-select${fieldErrors.condition ? " is-invalid" : ""}`} id="condition" name="condition" defaultValue={listing.condition} required>
              {data.conditions.map((condition) => (
                <option key={condition.value} value={condition.value}>{condition.label}</option>
              ))}
            </select>
            {fieldError("condition")}
          </div>

          <div className="row g-3">
            <div className="col-md-6">
              <label className="form-label" htmlFor="district">{labels.district}</label>
              <input className={`form-control${fieldErrors.district ? " is-invalid" : ""}`} id="district" name="district" defaultValue={listing.district} required maxLength={100} />
              {fieldError("district")}
            </div>
            <div className="col-md-6">
              <label className="form-label" htmlFor="sector">{labels.sector}</label>
              <input className={`form-control${fieldErrors.sector ? " is-invalid" : ""}`} id="sector" name="sector" defaultValue={listing.sector} required maxLength={100} />
              {fieldError("sector")}
            </div>
          </div>

          <div className="row g-3 mt-1">
            <div className="col-md-8">
              <label className="form-label" htmlFor="price">{labels.price}</label>
              <input className={`form-control${fieldErrors.price ? " is-invalid" : ""}`} id="price" name="price" type="number" min="0" step="0.01" defaultValue={listing.price} required />
              {fieldError("price")}
            </div>
            <div className="col-md-4">
              <label className="form-label" htmlFor="currency">{labels.currency}</label>
              <select className={`form-select${fieldErrors.currency ? " is-invalid" : ""}`} id="currency" name="currency" defaultValue={listing.currency} required>
                {data.currencies.map((currency) => (
                  <option key={currency.value} value={currency.value}>{currency.label}</option>
                ))}
              </select>
              {fieldError("currency")}
            </div>
          </div>

          {listing.images.length > 0 && (
            <div className="mt-4">
              <label className="form-label">{labels.existing_images}</label>
              <div className="seller-image-preview-grid">
                {listing.images.map((image) => (
                  !removedImages.includes(image.id) && (
                    <div className="seller-image-preview" key={image.id}>
                      <img src={image.url} alt="" onError={(e) => { e.currentTarget.style.display = "none"; }} />
                      {image.is_cover && <span className="seller-image-cover">{labels.cover}</span>}
                      <button
                        type="button"
                        onClick={() => setRemovedImages((current) => [...current, image.id])}
                        aria-label={labels.remove_image}
                      >
                        ×
                      </button>
                    </div>
                  )
                ))}
              </div>
            </div>
          )}

          <div className="mt-4">
            <label className="form-label" htmlFor="images">{labels.images}</label>
            {newPreviews.length > 0 && (
              <div className="seller-image-preview-grid mb-3">
                {newPreviews.map((preview, index) => (
                  <div className="seller-image-preview" key={preview}>
                    <img src={preview} alt="" />
                    <button type="button" onClick={() => setNewImages((current) => current.filter((_, i) => i !== index))} aria-label={labels.remove_image}>×</button>
                  </div>
                ))}
              </div>
            )}
            <input className="form-control" id="images" name="images" type="file" accept="image/*" multiple onChange={handleNewImages} />
            <div className="form-text">{labels.image_help}</div>
          </div>

          <div className="d-grid d-sm-flex justify-content-sm-center gap-2 mt-4">
            <button className="btn btn-brand" type="submit" disabled={submitting}>
              {submitting ? labels.loading : labels.submit}
            </button>
            <a className="btn btn-outline-secondary" href="/listings/dashboard/">{labels.cancel}</a>
          </div>
        </form>
      </div>
    </main>
  );
}
