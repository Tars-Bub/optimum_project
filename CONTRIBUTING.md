# Contributing

1. `main` is protected: changes arrive only through a pull request with at least one review.
2. Branch from the latest `main`: `git checkout main && git pull && git checkout -b <type>/<short-name>`.
3. Branch types: `feat/`, `fix/`, `test/`, `docs/`, `chore/`.
4. Commit messages say what you actually changed, for example `feat(stock): record incoming deliveries`.
5. Run `python manage.py test` before opening the pull request.
6. In the pull request, say what changed and how you checked it, and name the board card.
