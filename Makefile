.PHONY: install test test-all dev site
install:
	pip install -r requirements.txt
test:
	python -m pytest -m "not integration and not network"
test-all:
	python -m pytest -m "not network"
dev:
	python site/build.py && (cd site/dist && python -m http.server 8080 &) && python -m uvicorn app.main:app --reload --port 8000
site:
	python site/build.py
