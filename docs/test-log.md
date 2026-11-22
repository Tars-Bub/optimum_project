# Test log

| Date | Area | What was tested | Result | Bug / fix |
|---|---|---|---|---|
| 2026-11-22 | Payments (automated) | `python manage.py test payments`: request format and keys, status mapping, paid once, amount mismatch, webhook (forged, duplicate, bad input), login rules, pages | Pass (39 tests) | One test expected the wrong thing: an in-progress Maya status is shown but must not pay the order. Test corrected. |
| 2026-11-22 | App API (Postman/Newman) | Folders 2 and 3 of `postman/optimum-maya.postman_collection.json` against the local app: health, webhook, return page, login protection, login | Pass (11 requests, 18 assertions) | Postman dropped trailing slashes so Django answered 301/500: URLs are now plain strings. Login got 403: the CSRF token is now read from the login page. |
| 2026-11-22 | Maya API (Postman/Newman) against a stand-in server | Folder 1: create checkout, wrong key, empty body, retrieve by ID/reference/status, webhooks | Pass (16 assertions) on a local stand-in built from the Maya docs, **not** on Maya itself | none |
| 2026-11-22 | End to end (stand-in Maya, real HTTP) | Create checkout, still pending, Maya says paid, webhook, duplicate webhook | Pass: order Paid once | none |
|  | Maya API (Postman) against the real sandbox | Folder 1 with your sandbox keys | To do | |
|  | Manual sandbox checkout | Pay with the test card; cancel; failed card; confirm the order turns Paid | To do | |
