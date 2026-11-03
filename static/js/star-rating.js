(function () {
  const picker = document.getElementById("starRatingPicker");
  if (!picker) return;

  const stars = Array.from(picker.querySelectorAll(".star-rating-star"));

  function paint(uptoValue) {
    stars.forEach((star) => {
      const input = star.querySelector("input");
      const value = Number(input.value);
      star.classList.toggle("is-filled", value <= uptoValue);
    });
  }

  function currentValue() {
    const checked = picker.querySelector("input:checked");
    return checked ? Number(checked.value) : 0;
  }

  paint(currentValue());

  stars.forEach((star) => {
    const input = star.querySelector("input");

    star.addEventListener("mouseenter", () => paint(Number(input.value)));
    star.addEventListener("focus", () => paint(Number(input.value)), true);

    star.addEventListener("click", () => {
      input.checked = true;
      paint(Number(input.value));
    });
  });

  picker.addEventListener("mouseleave", () => paint(currentValue()));
})();
