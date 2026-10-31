.PHONY: test dev site
test:
	python -m pytest -q engine mapping app site
dev:
	python -m uvicorn app.main:app --reload --port 8000
site:
	python site/build.py
