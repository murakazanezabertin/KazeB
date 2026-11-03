(function () {
  const pickerInput = document.getElementById("photoPickerInput");
  const formInput = document.getElementById("id_images");
  const addBtn = document.getElementById("addPhotosBtn");
  const grid = document.getElementById("photoPreviewGrid");

  if (!pickerInput || !formInput || !addBtn || !grid) return;

  // Holds every photo the seller has picked so far, across as many
  // "Add photos" clicks as they want -- a plain <input multiple>
  // resets its selection every time the dialog reopens, so we keep
  // our own running list and rebuild the real form input from it.
  let selectedFiles = [];

  addBtn.addEventListener("click", () => pickerInput.click());

  pickerInput.addEventListener("change", () => {
    selectedFiles = selectedFiles.concat(Array.from(pickerInput.files));
    pickerInput.value = "";
    render();
  });

  // Event delegation: one listener on the grid itself, rather than a
  // fresh listener bound to every remove button on every render. This
  // is what was breaking the "remove a picked photo" button -- once a
  // tile was removed and the grid re-rendered, a per-button listener
  // could end up unbound/mismatched. Delegating to the grid means
  // there is exactly one listener, ever, and it always targets
  // whatever is currently in the DOM.
  grid.addEventListener("click", (event) => {
    const removeBtn = event.target.closest(".photo-picker-remove");
    if (removeBtn) {
      event.preventDefault();
      event.stopPropagation();
      const index = Number(removeBtn.dataset.index);
      if (!Number.isNaN(index)) {
        selectedFiles.splice(index, 1);
        render();
      }
      return;
    }

    const addTile = event.target.closest(".photo-picker-add-tile");
    if (addTile) {
      pickerInput.click();
    }
  });

  function render() {
    grid.innerHTML = "";

    selectedFiles.forEach((file, index) => {
      const tile = document.createElement("div");
      tile.className = "photo-picker-tile";

      const img = document.createElement("img");
      img.src = URL.createObjectURL(file);
      img.onload = () => URL.revokeObjectURL(img.src);
      tile.appendChild(img);

      if (index === 0) {
        const badge = document.createElement("span");
        badge.className = "photo-picker-cover-badge";
        badge.textContent = "★";
        tile.appendChild(badge);
      }

      const removeBtn = document.createElement("button");
      removeBtn.type = "button";
      removeBtn.className = "photo-picker-remove";
      removeBtn.textContent = "×";
      removeBtn.dataset.index = String(index);
      tile.appendChild(removeBtn);

      grid.appendChild(tile);
    });

    const addTile = document.createElement("div");
    addTile.className = "photo-picker-add-tile";
    addTile.textContent = "➕";
    grid.appendChild(addTile);

    // Rebuild the actual <input name="images"> the form submits, since
    // File inputs can't have their .files set directly.
    const dataTransfer = new DataTransfer();
    selectedFiles.forEach((file) => dataTransfer.items.add(file));
    formInput.files = dataTransfer.files;
  }

  render();

  // --- Existing photos (edit page): click a tile to mark it for
  // removal (a checkbox per photo, submitted as "remove_images").
  // Driven explicitly in JS rather than relying only on the label's
  // implicit click-toggles-checkbox behaviour, which is what made
  // this unreliable before -- this version always works the same
  // way no matter what was clicked inside the tile.
  const existingGrid = document.getElementById("existingPhotoGrid");
  if (existingGrid) {
    existingGrid.addEventListener("click", (event) => {
      const tile = event.target.closest(".existing-photo-tile");
      if (!tile) return;

      const checkbox = tile.querySelector(".existing-photo-remove");
      if (!checkbox) return;

      checkbox.checked = !checkbox.checked;
      tile.classList.toggle("marked-for-removal", checkbox.checked);
    });
  }
})();
