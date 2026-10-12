/**
 * Vicinity Mart — desktop mega menu opens on hover.
 *
 * In header-mega-menu.liquid a top-level item with children is a link to its
 * own page plus a caret <summary> that toggles the menu. On devices that can
 * hover, pointing at the item opens its menu and leaving it closes it after a
 * short delay, long enough to cross the gap down into the panel. Touch and
 * keyboard users open the menu with the caret, as before.
 *
 * Opening and closing go through the <details> element and Trade's
 * <header-menu> (details-disclosure.js), so its animation and sticky-header
 * handling still run.
 */
(() => {
  const canHover = window.matchMedia('(hover: hover) and (pointer: fine)');
  const CLOSE_DELAY = 200;

  const closeOthers = (current) => {
    document.querySelectorAll('.header__menu-parent header-menu').forEach((menu) => {
      if (menu !== current && menu.mainDetailsToggle?.open) menu.close();
    });
  };

  const setUp = (item) => {
    if (item.dataset.hoverMenu) return;
    item.dataset.hoverMenu = 'ready';

    const menu = item.querySelector('header-menu');
    const details = item.querySelector('details');
    const summary = details?.querySelector('summary');
    if (!menu || !details || !summary) return;

    let closeTimer;

    item.addEventListener('mouseenter', () => {
      if (!canHover.matches) return;
      clearTimeout(closeTimer);
      if (details.open) return;
      closeOthers(menu);
      details.dataset.openedBy = 'hover';
      details.open = true;
      summary.setAttribute('aria-expanded', 'true');
    });

    item.addEventListener('mouseleave', () => {
      if (!canHover.matches || !details.open) return;
      clearTimeout(closeTimer);
      closeTimer = setTimeout(() => {
        delete details.dataset.openedBy;
        menu.close();
      }, CLOSE_DELAY);
    });

    // A mouse user who hovered the item and then clicks the caret expects the
    // menu to stay open, not to toggle shut under the pointer. global.js has
    // already flipped aria-expanded for the toggle we are cancelling.
    summary.addEventListener('click', (event) => {
      if (details.dataset.openedBy !== 'hover') return;
      event.preventDefault();
      delete details.dataset.openedBy;
      summary.setAttribute('aria-expanded', 'true');
    });
  };

  const init = () => document.querySelectorAll('.header__menu-parent').forEach(setUp);

  init();
  // The theme editor re-renders the header section when its settings change.
  document.addEventListener('shopify:section:load', init);
})();
