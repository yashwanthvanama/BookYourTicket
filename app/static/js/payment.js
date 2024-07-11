const stripe = Stripe('pk_test_51OCcWxF26FYMfquJMNRCiEbVlGeR2TVCpdv972arJY323BErl0Jc2Nf9xQZj0tIBnDgOgLYvYcbRWHNgajXxbSTH00zR6Y3ajN');

const items = [{ id: "xl-tshirt" }];

let elements;
var show_modal = true;

initialize();
checkStatus();

document.getElementById('Signup').onclick = routetToLogin;
document.getElementById('apply').onclick = applyPromotion;
document.getElementById('email').onchange = UpdateEmail;
document.getElementById('number').onchange = UpdatePhone;

document
  .querySelector("#payment-form")
  .addEventListener("submit", handleSubmit);

// Fetches a payment intent and captures the client secret
async function initialize() {
  const response = await fetch("/create-payment-intent", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ items }),
  });
  const { clientSecret } = await response.json();

  const appearance = {
    theme: 'stripe',
  };
  elements = stripe.elements({ appearance, clientSecret });

  const paymentElementOptions = {
        layout: {
            type: 'accordion',
            defaultCollapsed: false,
            radios: true,
            spacedAccordionItems: false
        }
    };

  const paymentElement = elements.create("payment", paymentElementOptions);
  paymentElement.mount("#payment-element");
  if(current_username != '') {
    const promotionLink = document.querySelector("#promotion-link");
    promotionLink.classList.remove("d-none");
    show_modal = false;
  }
}

async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    const email_value = document.getElementById('email').value;
    console.log(email_value);
    if(email_value == '') {
      showMessage("Please enter the contact email");
    }
    else {
      if(show_modal == true) {
        $('#modal').modal('show')
      }
      else {
        const { error } = await stripe.confirmPayment({
          elements,
          confirmParams: {
            // Make sure to change this to your payment completion page
            return_url: "http://" + window.location.host+ "/confirmation/" + booking_id,
            receipt_email: email_value,
          },
        });
      
        // This point will only be reached if there is an immediate error when
        // confirming the payment. Otherwise, your customer will be redirected to
        // your `return_url`. For some payment methods like iDEAL, your customer will
        // be redirected to an intermediate site first to authorize the payment, then
        // redirected to the `return_url`.
        if (error.type === "card_error" || error.type === "validation_error") {
          showMessage(error.message);
        } else {
          showMessage("An unexpected error occurred.");
        }
      }
    }
    setLoading(false);
  }

// Fetches the payment intent status after payment submission
async function checkStatus() {
  const clientSecret = new URLSearchParams(window.location.search).get(
    "payment_intent_client_secret"
  );

  if (!clientSecret) {
    return;
  }

  const { paymentIntent } = await stripe.retrievePaymentIntent(clientSecret);

  switch (paymentIntent.status) {
    case "succeeded":
      showMessage("Payment succeeded!");
      break;
    case "processing":
      showMessage("Your payment is processing.");
      break;
    case "requires_payment_method":
      showMessage("Your payment was not successful, please try again.");
      break;
    default:
      showMessage("Something went wrong.");
      break;
  }
}

// ------- UI helpers -------

function showMessage(messageText) {
  const messageContainer = document.querySelector("#payment-message");

  messageContainer.classList.remove("d-none");
  messageContainer.textContent = messageText;

  setTimeout(function () {
    messageContainer.classList.add("d-none");
    messageContainer.textContent = "";
  }, 4000);
}

// Show a spinner on payment submission
function setLoading(isLoading) {
  if (isLoading) {
    // Disable the button and show a spinner
    document.querySelector("#submit").disabled = true;
    document.querySelector("#spinner").classList.remove("d-none");
    document.querySelector("#button-text").classList.add("d-none");
  } else {
    document.querySelector("#submit").disabled = false;
    document.querySelector("#spinner").classList.add("d-none");
    document.querySelector("#button-text").classList.remove("d-none");
  }
}

$('#modal').on('hidden.bs.modal', function (e) {
    // do something...
    show_modal = false;
  })  
  
  function routetToLogin(e) {
    window.location.replace("http://" + window.location.host+"/login")
  }

  function disableCheckboxes(event) {
    if (event.checked) {
      const checkboxes = document.querySelectorAll('.couponCheckbox');
      checkboxes.forEach(checkbox => {
          if (checkbox !== event) {
              checkbox.disabled = true;
          }
      });
  } else {
      // Re-enable all checkboxes when a checkbox is unchecked
      const checkboxes = document.querySelectorAll('.couponCheckbox');
      checkboxes.forEach(checkbox => {
          checkbox.disabled = false;
      });
  }
  }
  
  function applyPromotion() {
    const promotionsContainer = document.querySelector("#promotions-container");
    const promoName = document.querySelector("#promotion-name");
    const promoValue = document.querySelector("#promotion-value");
    const total_amount = document.querySelector("#total_amount");
    const selectedCheckbox = document.querySelector('.couponCheckbox:checked');
    if (selectedCheckbox) {
        const discount = selectedCheckbox.value;
        const couponId = selectedCheckbox.id;
        total = sub_total - ((sub_total*Number(discount))/100) + booking_fee;
        promoName.innerHTML = selectedCheckbox.name;
        promoValue.innerHTML = "-USD. " + ((sub_total*Number(discount))/100).toFixed(2);
        total_amount.innerHTML = "USD. " + total;
        promotionsContainer.classList.remove("d-none");
        fetch('/apply-coupon/'+booking_id+'/'+couponId, {
          method: 'PUT',
      })
      .then(response => response.json())
      .then(data => {
          // Display the result message
          console.log(data.message);
      })
      .catch(error => {
          console.error('Error:', error);
      });
    }
    closeModal()
  }

  function closeModal() {
    $('#modal').modal('hide');
    $('#promotionsModal').modal('hide');
    show_modal = false;
}

function UpdateEmail() {
  const email = document.getElementById('email').value;
  const number = document.getElementById('number').value;
  fetch('/update-contact-email/'+booking_id+'/'+email, {
    method: 'PUT',
})
.then(response => response.json())
.then(data => {
    // Display the result message
    console.log(data.message);
})
.catch(error => {
    console.log('Error:', error);
});
}

function UpdatePhone() {
  const number = document.getElementById('number').value;
  fetch('/update-contact-phone/'+booking_id+'/'+number, {
    method: 'PUT',
})
.then(response => response.json())
.then(data => {
    // Display the result message
    console.log(data.message);
})
.catch(error => {
    console.log('Error:', error);
});
}

function showPromotions() {
  console.log('show promotions');
  $('#promotionsModal').modal('show');
}