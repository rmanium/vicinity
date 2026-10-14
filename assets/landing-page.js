/**
 * "Add all to cart" for the landing page products section.
 *
 * Adds every in-stock product shown in the section in one /cart/add.js call.
 * With the cart drawer enabled it re-renders and opens the drawer, the same
 * way product-form.js does; with the cart page or popup notification it goes
 * to the cart page, because the notification can only show a single item.
 */
if (!customElements.get('landing-add-all')) {
  customElements.define(
    'landing-add-all',
    class LandingAddAll extends HTMLElement {
      connectedCallback() {
        this.button = this.querySelector('button');
        this.errorMessage = this.querySelector('.landing-add-all__error');
        this.button.addEventListener('click', this.onClick.bind(this));
      }

      get items() {
        return (this.dataset.variantIds || '')
          .split(',')
          .filter(Boolean)
          .map((id) => ({ id: Number(id), quantity: 1 }));
      }

      async onClick() {
        const items = this.items;
        if (!items.length || this.button.getAttribute('aria-disabled') === 'true') return;

        this.setLoading(true);
        this.showError(false);

        const cartDrawer = document.querySelector('cart-drawer');
        const body = { items };
        if (cartDrawer) {
          body.sections = cartDrawer.getSectionsToRender().map((section) => section.id);
          body.sections_url = window.location.pathname;
          cartDrawer.setActiveElement(this.button);
        }

        try {
          const response = await fetch(`${window.routes?.cart_add_url || '/cart/add'}.js`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
            body: JSON.stringify(body),
          });
          const data = await response.json();

          if (!response.ok || data.status) {
            this.showError(data.description || data.message || this.dataset.errorMessage);
            return;
          }

          if (typeof publish === 'function' && typeof PUB_SUB_EVENTS !== 'undefined') {
            publish(PUB_SUB_EVENTS.cartUpdate, { source: 'landing-add-all', cartData: data });
          }

          if (!cartDrawer) {
            window.location = window.routes?.cart_url || '/cart';
            return;
          }

          cartDrawer.classList.remove('is-empty');
          cartDrawer.renderContents({ ...data, id: items[0].id });
        } catch (error) {
          console.error(error);
          this.showError(this.dataset.errorMessage);
        } finally {
          this.setLoading(false);
        }
      }

      setLoading(loading) {
        this.button.classList.toggle('loading', loading);
        if (loading) {
          this.button.setAttribute('aria-disabled', 'true');
        } else {
          this.button.removeAttribute('aria-disabled');
        }
        this.button.querySelector('.loading__spinner')?.classList.toggle('hidden', !loading);
      }

      showError(message) {
        if (!this.errorMessage) return;
        this.errorMessage.hidden = !message;
        this.errorMessage.textContent = message || '';
      }
    }
  );
}
