// === Movers Transport System JS ===

// Fade-in hero text animation
document.addEventListener("DOMContentLoaded", () => {
  const hero = document.querySelector(".hero h1");
  if (hero) {
    hero.style.opacity = 0;
    hero.style.transform = "translateY(20px)";
    setTimeout(() => {
      hero.style.transition = "all 0.8s ease";
      hero.style.opacity = 1;
      hero.style.transform = "translateY(0)";
    }, 300);
  }

  console.log("🚚 Movers Transport System loaded successfully!");
});

