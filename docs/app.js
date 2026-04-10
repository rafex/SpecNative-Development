const revealTargets = document.querySelectorAll(
  ".section-heading, .card, .mini-card, .diagram-card, .runtime-card, .stack-item, .resource-link, .flow-steps article, .hero-copy, .hero-panel"
);

for (const target of revealTargets) {
  target.classList.add("reveal");
}

const observer = new IntersectionObserver(
  (entries) => {
    for (const entry of entries) {
      if (entry.isIntersecting) {
        entry.target.classList.add("in-view");
        observer.unobserve(entry.target);
      }
    }
  },
  {
    threshold: 0.14,
    rootMargin: "0px 0px -40px 0px",
  }
);

for (const target of revealTargets) {
  observer.observe(target);
}
