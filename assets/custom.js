/**
 * Include your custom JavaScript here.
 *
 * We also offer some hooks so you can plug your own logic. For instance, if you want to be notified when the variant
 * changes on product page, you can attach a listener to the document:
 *
 * document.addEventListener('variant:changed', function(event) {
 *   var variant = event.detail.variant; // Gives you access to the whole variant details
 * });
 *
 * You can also add a listener whenever a product is added to the cart:
 *
 * document.addEventListener('product:added', function(event) {
 *   var variant = event.detail.variant; // Get the variant that was added
 *   var quantity = event.detail.quantity; // Get the quantity that was added
 * });
 *
 * If you are an app developer and requires the theme to re-render the mini-cart, you can trigger your own event. If
 * you are adding a product, you need to trigger the "product:added" event, and make sure that you pass the quantity
 * that was added so the theme can properly update the quantity:
 *
 * document.documentElement.dispatchEvent(new CustomEvent('product:added', {
 *   bubbles: true,
 *   detail: {
 *     quantity: 1
 *   }
 * }));
 *
 * If you just want to force refresh the mini-cart without adding a specific product, you can trigger the event
 * "cart:refresh" in a similar way (in that case, passing the quantity is not necessary):
 *
 * document.documentElement.dispatchEvent(new CustomEvent('cart:refresh', {
 *   bubbles: true
 * }));
 */

/**
 * when products was added, send some data to GA
 */
document.addEventListener("product:added", function (event) {
  var quantity = event.detail.quantity; // Get the quantity that was added
  ga("send", {
    hitType: "event",
    eventCategory: "product",
    eventAction: "quick add",
    eventValue: quantity,
  });
});

/**
 * handling custom action
 */
$("[data-action-type]").click(function (e) {
  e.preventDefault();
  var type = this.getAttribute("data-action-type");
  switch (type) {
    case "back":
      window.history.back();
      break;
    default:
      void 0;
      break;
  }
});

/**
 * handle chat button
 */
let checkLoadFBChat;
let media = window.matchMedia("(max-width: 641px)");
function handleVisibilityChatButton() {
  // media = window.matchMedia("(max-width: 641px)");
  const target = document.querySelector("#dummy-chat-button-iframe");
  console.log("media", media, target);
  if (target) {
    clearInterval(checkLoadFBChat);
  }
  if (media.matches) {
    // If media query matches
    target.style.display = "none";
  } else {
    target.style.display = "block";
  }
}
checkLoadFBChat = setInterval(handleVisibilityChatButton, 500);

/**
 * custom modal
 */

// media.addEventListener(handleVisibilityChatButton);

const showModal = () => {
  document.querySelector(".cu-modal").setAttribute("aria-hidden", "false");
  media.addEventListener(handleVisibilityChatButton);
};
const hideModal = () => {
  document.querySelector(".cu-modal").setAttribute("aria-hidden", "true");
  // media.removeEventListener(handleVisibilityChatButton);
};

// Open the Modal Window
document.querySelector("[data-popup-type='survey']").onclick = function () {
  showModal();
  ga("send", {
    hitType: "event",
    eventCategory: "feedback",
    eventAction: "open feedback modal",
  });
};
// Close the Modal Window by clicking the X
document.querySelector(".popup__close").onclick = function () {
  hideModal();
};

// Close the Modal Window by clicking outside the box
window.onclick = function (event) {
  if (event.target === document.querySelector(".cu-modal")) {
    hideModal();
  }
};

/**
 * announcement-bar Slider
 */
$(document).ready(function () {
  $(".announcement-slider").slick({
    autoplay: true,
    autoplaySpeed: 7000,
    infinite: true,
    adaptiveHeight: true,
    arrows: false,
    draggable: false,
    swipe: false,
    vertical: true,
  });
});
