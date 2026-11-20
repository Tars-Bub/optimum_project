# What each member builds next

The base only has screens. Each task below turns sample data into real behavior. Each member writes
and tests their own part, and should be able to explain it. Work on a branch, open a pull request,
and describe what you changed in your own words.

Suggested order: the Lead's task first (database and login), then the others in parallel.

## 1. Lead: database, login and deployment (`feat/database-auth`, `chore/ci-deploy`)
- Add a `DATABASES` setting (SQLite first, MySQL later) and the first models for products and categories.
- Real login and logout, protected pages, and Admin / Staff roles.
- Add a Dockerfile and a GitHub Actions workflow that runs `python manage.py test`.
- Deploy a first version to a free cloud host (Form D: hosting verified, DB/storage configured, pipeline mapped).
- Review and merge pull requests.

## 2. UI/UX (`feat/ui-polish`)
- Compare each screen to the Figma and wireframe and fix differences in layout, spacing and labels.
- Add empty states ("No products yet"), error and success messages, and a mobile layout.
- Make the print page for invoices and delivery receipts and fit it to the real pre-printed form.
- Done when every screen matches the Figma and nothing looks broken on a phone-width window.

## 3. Backend A: accounts, products and stock (`feat/accounts`, `feat/catalog-stock`)
- Register Staff Account (stays Pending), Admin approval, edit, deactivate, reset password.
- Categories and products: add, edit, delete, search and filter, with status from the reorder level.
- Stock: incoming, adjust from a physical count, movement history, low-stock alerts.
- Rule: quantity on hand changes only through a recorded stock movement.

## 4. Backend B: sales and documents (`feat/sales`, `feat/documents`)
- Cart, drafts, payments (Paid / Partial / Unpaid) and Finalize Sale, which deducts stock all-or-nothing.
- Returns, exchanges and voids that put stock back.
- Invoice and delivery receipt printing with a required, unique serial number, plus Reprint.
- One external API integration that adds business value (for example SMS for low-stock alerts), required by the Phase 4 rubric.

## 5. Reports and QA (`feat/reports`, `test/*`, `docs/*`)
- Reports: Transactions, Sales (with period filter), Stock, Inventory Summary, Activity, Audit Log (Admin only).
- Tests for each area as it lands, and a bug log in `docs/test-log.md`.
- A Postman collection for the main API calls, and the user manual in `docs/user-manual.md`.
