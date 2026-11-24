(() => {
  const links = document.querySelectorAll('.member-index a');

  function markLocation() {
    const section = document.querySelector(':target')?.closest('.member-direction');
    for (const link of links) {
      if (section && link.hash === '#' + section.id) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    }
  }

  window.addEventListener('hashchange', markLocation);
  window.addEventListener('pageshow', markLocation);
  markLocation();
})();
