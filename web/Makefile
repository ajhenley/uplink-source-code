.PHONY: run run-backend run-frontend test migrate install clean build-frontend build

# Install all dependencies
install:
	cd backend && pip install -e ".[dev]"
	cd frontend && npm install

# Run both backend and frontend (use two terminals or background one)
run: run-backend

run-backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

run-frontend:
	cd frontend && npm run dev

# Run backend tests
test:
	cd backend && python -m pytest -v

# Create a new Alembic migration
migrate:
	cd backend && alembic revision --autogenerate -m "$(msg)"

# Apply migrations
migrate-up:
	cd backend && alembic upgrade head

# Build frontend for production
build-frontend:
	cd frontend && npm run build

# Full production build (frontend + backend serves it)
build: build-frontend

# Clean generated files
clean:
	rm -f backend/uplink.db
	rm -rf backend/__pycache__ backend/app/__pycache__
	rm -rf frontend/dist frontend/node_modules/.vite
