function copyPhone(button) {
  const value = button.getAttribute("data-phone");
  const original = button.innerHTML;

  const done = () => {
    button.innerHTML = "✅ Byakoporowe";
    setTimeout(() => { button.innerHTML = original; }, 2000);
  };

  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(value).then(done).catch(() => fallbackCopy(value, done));
  } else {
    fallbackCopy(value, done);
  }
}

function fallbackCopy(text, onDone) {
  const temp = document.createElement("textarea");
  temp.value = text;
  temp.style.position = "fixed";
  temp.style.opacity = "0";
  document.body.appendChild(temp);
  temp.select();
  try {
    document.execCommand("copy");
  } finally {
    document.body.removeChild(temp);
    onDone();
  }
}

document.addEventListener("DOMContentLoaded", function () {
  const carousel = document.querySelector("[data-kazeb-carousel]");
  const hero = document.querySelector(".kazeb-hero");
  const slides = carousel ? carousel.querySelectorAll(".kazeb-hero-slide") : [];
  const dots = hero ? hero.querySelectorAll(".kazeb-hero-dot") : [];

  if (!slides.length) {
    return;
  }

  let currentSlide = 0;
  let carouselTimer = null;

  slides.forEach((slide, index) => {
    if (slide.classList.contains("is-active")) {
      currentSlide = index;
    }
  });

  function showSlide(index) {
    currentSlide = (index + slides.length) % slides.length;

    slides.forEach((slide, slideIndex) => {
      const wasActive = slide.classList.contains("is-active");
      slide.classList.remove("is-active", "is-leaving");

      if (slideIndex === currentSlide) {
        slide.classList.add("is-active");
      } else if (wasActive) {
        slide.classList.add("is-leaving");
      }
    });

    dots.forEach((dot, dotIndex) => {
      const isActive = dotIndex === currentSlide;
      dot.classList.toggle("is-active", isActive);
      dot.setAttribute("aria-selected", isActive ? "true" : "false");

      if (isActive) {
        dot.setAttribute("aria-current", "true");
      } else {
        dot.removeAttribute("aria-current");
      }
    });
  }

  function stopCarousel() {
    if (carouselTimer !== null) {
      clearInterval(carouselTimer);
      carouselTimer = null;
    }
  }

  function startCarousel() {
    stopCarousel();
    carouselTimer = setInterval(() => showSlide(currentSlide + 1), 3000);
  }

  dots.forEach((dot, index) => {
    dot.addEventListener("click", function () {
      showSlide(index);
      startCarousel();
    });
  });

  if (hero) {
    hero.addEventListener("mouseenter", stopCarousel);
    hero.addEventListener("mouseleave", startCarousel);
  }

  document.addEventListener("visibilitychange", function () {
    if (document.hidden) {
      stopCarousel();
    } else {
      startCarousel();
    }
  });

  showSlide(currentSlide);
  startCarousel();
});
