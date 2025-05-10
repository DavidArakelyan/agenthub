.PHONY: setup-dev start-local build-all test-all lint-all clean

# Development setup
setup-dev:
	python -m pip install --upgrade pip
	python -m pip install -r requirements-dev.txt
	npm install --prefix services/frontend
	docker-compose -f deploy/docker/docker-compose.dev.yml pull

# Local development
start-local:
	docker-compose -f deploy/docker/docker-compose.dev.yml up -d

stop-local:
	docker-compose -f deploy/docker/docker-compose.dev.yml down

# Building
build-all:
	docker-compose -f deploy/docker/docker-compose.dev.yml build

# Testing
test-all:
	python -m pytest services/*/tests
	cd services/frontend && npm test

# Linting
lint-all:
	black services
	flake8 services
	cd services/frontend && npm run lint

# Cleanup
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name "*.egg" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".coverage" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type d -name "dist" -exec rm -rf {} +
	find . -type d -name "build" -exec rm -rf {} +
	find . -type d -name "node_modules" -exec rm -rf {} + 