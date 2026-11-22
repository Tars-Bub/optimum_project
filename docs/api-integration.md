# External API integration: Maya Checkout

**What it is.** Maya (maya.ph) is a Philippine payment provider. The app uses **Maya Checkout** so a customer can pay a
finalized sale by card, Maya wallet or QR on Maya's own secure page. The app never sees or stores card details.

**Why it fits the SRS.** Process 3.0 (Process orders and payments) records the money received for an order. Maya adds an
online way to receive it: `Order.amount_paid` is updated only after Maya confirms the payment.

Official docs: https://developers.maya.ph (Maya Checkout, Webhooks, Sandbox credentials and cards).

## Endpoints used

| Purpose | Method and path | Key | Where in the code |
|---|---|---|---|
| Create a checkout | `POST /checkout/v1/checkouts` | Public (`pk-...`) | `payments/maya.py` `create_checkout` |
| Look up a payment by ID | `GET /payments/v1/payments/{id}` | Secret (`sk-...`) | `get_payment` |
| Look up a payment by our reference | `GET /payments/v1/payment-rrns/{rrn}` | Secret | `get_payment_by_rrn` |
| Receive payment events | `POST /payments/maya/webhook/` (our endpoint, called by Maya) | none | `payments/views.py` `maya_webhook` |

Base URL: `https://pg-sandbox.paymaya.com` (sandbox, the default) or `https://pg.paymaya.com` (live).
Authentication is HTTP Basic: the key is the username and the password is empty.

## How a payment flows

1. A finalized sale has a balance. The cashier opens **Reports & Search → Transactions → Pay with Maya** (or the link shown right after finalizing).
2. The app calls **Create Checkout** with the amount, item lines, our `requestReferenceNumber` (for example `SO-0007-3fa9...`) and three return URLs. It stores a `MayaPayment` row with status *pending*.
3. The cashier shows the customer the **QR code or link**. The customer pays on Maya's page.
4. Maya sends the customer back to `/payments/maya/return/<reference>/` and calls our **webhook**.
5. In both cases the app **asks Maya for the real status** with the secret key (`sync_payment`). Only `PAYMENT_SUCCESS` adds the amount to the order. The payment is then *paid*.
6. The staff page refreshes by itself and the order shows **Paid**.

## Status mapping

| Maya status | Our status | Effect on the order |
|---|---|---|
| `PAYMENT_SUCCESS` | Paid | amount added to `amount_paid` (once) |
| `PAYMENT_FAILED`, `AUTH_FAILED` | Failed | none |
| `PAYMENT_EXPIRED` | Expired | none |
| `PAYMENT_CANCELLED` | Cancelled | none |
| `PENDING_PAYMENT`, `FOR_AUTHENTICATION`, `AUTHENTICATING`, `PAYMENT_PROCESSING`, ... | Pending | none (the Maya status is shown) |

## Safety rules built in

- **Keys are never in the code.** They come from `MAYA_PUBLIC_KEY` / `MAYA_SECRET_KEY` (environment or a git-ignored `.env`). `.env` is in `.gitignore` and `.dockerignore`. The secret key is used only on the server.
- **Nothing is trusted from the browser or the webhook body.** The `?result=success` in the return address and the webhook content only tell us *to look*. The status comes from Maya's API, so a forged request cannot mark an order paid.
- **Paid at most once.** The payment row and the order are locked in one transaction, so a double refresh or a duplicate webhook cannot add the money twice.
- **Amount check.** If Maya reports a different amount than we asked for, the payment is not applied and a note is saved.
- **One open checkout per order.** A recent pending checkout for the same amount is reused instead of creating a second one.
- **Errors are handled.** Network failure, a 4xx/5xx from Maya, or missing keys show a clear message and change nothing. A webhook that cannot verify returns 502 so Maya retries.
- **Audit log.** Checkout created, payment received, payment failed and amount mismatch are written to the Audit Log.

## Setup

1. In **Maya Manager (Sandbox)** go to *API Keys* and create a Public and a Secret key.
2. Copy `.env.example` to `.env` and fill in the two keys (or set them as environment variables on the host).
3. Locally, nothing else is needed: the customer is sent back to `http://127.0.0.1:8000`, and the return page verifies the payment.
4. On the cloud host also set `SITE_URL=https://your-site` and register the webhook (Postman request **1.9**, or Maya Manager): event `PAYMENT_SUCCESS`, URL `https://your-site/payments/maya/webhook/`. Maya cannot call `localhost`.
5. For real money only: `MAYA_BASE_URL=https://pg.paymaya.com` with live keys, after Maya approves your account.

### Sandbox test data (from the Maya docs; check the docs if it stops working)
- Card: Visa `4123450131001381`, expiry `12/2030`, CVC `123`, 3DS passkey `mctest1`.
- Maya wallet: `+639900100900`, password `Password@1`, OTP `123456`.

## How it was tested

| Level | Tool | What it covers |
|---|---|---|
| Unit and integration | `python manage.py test payments` | request format and auth header, status mapping, paid-once, amount mismatch, webhook (including forged and duplicate), login rules, pages |
| API response tests | Postman collection `postman/optimum-maya.postman_collection.json` | **Folder 1:** Maya sandbox API (create checkout, wrong key, empty body, retrieve by ID and by reference, status, webhooks). **Folders 2 and 3:** this app's webhook, health check, return page and login-protected pages |
| Command line | `newman run postman/optimum-maya.postman_collection.json -e postman/optimum-maya.postman_environment.json` | same collection, also run in GitHub Actions (`.github/workflows/postman.yml`) |
| Manual | Sandbox checkout in the browser | pay with the test card, see the order turn Paid; cancel; failed card |

### Running the Postman collection
1. Postman → Import → both files in `postman/`.
2. Choose the environment **Optimum - Maya (sandbox)** and fill `maya_public_key` and `maya_secret_key` (current value only; never commit them).
3. Start the app (`python manage.py runserver`) and run the collection. Folder 1 needs the keys; folders 2 and 3 do not.
4. Command line: `npm i -g newman`, then `newman run postman/optimum-maya.postman_collection.json -e postman/optimum-maya.postman_environment.json --env-var maya_public_key=... --env-var maya_secret_key=...`.

## Known limits
- Only full or balance payment of a **finalized** sale; no refunds through Maya (refund in Maya Manager).
- Refunds from the Returns screen are not sent to Maya.
- Webhooks are not signed by us; we rely on re-checking with the API, which is safer.
- Live behaviour of the retrieve endpoints for a not-yet-opened checkout (200 vs 404) should be confirmed in the sandbox; the code treats 404 as "not paid yet".
