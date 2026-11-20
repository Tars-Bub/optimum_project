# Contributing

## Areas and owners
Replace the names with your group's members. Each owner reviews changes to their own area.

| Area | Folders | Owner |
|---|---|---|
| Lead, setup and deployment | `config/`, `core/`, `Dockerfile`, `.github/`, `requirements.txt` | _name_ |
| UI/UX | `templates/`, `static/` | _name_ |
| Accounts, products and stock | `accounts/`, `catalog/`, `stock/` | _name_ |
| Sales and documents | `sales/`, `documents/` | _name_ |
| Reports, tests and docs | `reports/`, `docs/`, tests | _name_ |

## Workflow
1. `main` is protected: changes arrive only through a pull request with at least one review.
2. Create a branch from the latest `main`: `git checkout main && git pull && git checkout -b <type>/<short-name>`.
3. Branch types: `feat/`, `fix/`, `test/`, `docs/`, `chore/`.
4. Commit messages say what you actually changed, for example `fix(stock): block negative adjustment counts`.
5. Run `python manage.py test` before opening the pull request. CI runs it again.
6. In the pull request, describe what changed and how you checked it.

## Tracking
Keep tasks on the Scrum board (Trello or Jira) and put the card name in the pull request,
so the board and the commits match.
