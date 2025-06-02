.PHONY: setup-dev setup-prod start-local stop-local start-prod stop-prod build-all build-prod test-all lint-all clean quick-start

# Quick start - setup and run in one command
quick-start:
	@echo "🚀 Setting up and starting AgentHub..."
	@if [ -z "$$OPENAI_API_KEY" ]; then \
		echo "⚠️  No OPENAI_API_KEY environment variable found"; \
		read -p "Enter your OpenAI API key: " api_key; \
		export OPENAI_API_KEY=$$api_key; \
		./setup.sh quick $$api_key && make start-local; \
	else \
		echo "✅ Using OPENAI_API_KEY from environment"; \
		./setup.sh quick $$OPENAI_API_KEY && make start-local; \
	fi
	@echo "✅ AgentHub is now running at http://localhost:3000"

# Development setup
setup-dev:
	python -m pip install --upgrade pip
	python -m pip install -r requirements-dev.txt
	npm install --prefix services/frontend
	docker-compose -f deploy/docker/docker-compose.dev.yml pull

# Production setup
setup-prod:
	./setup.sh production

# Local development
start-local:
	docker-compose -f deploy/docker/docker-compose.dev.yml up -d

stop-local:
	docker-compose -f deploy/docker/docker-compose.dev.yml down

# Production deployment
start-prod:
	docker-compose -f deploy/docker/docker-compose.prod.yml up -d

stop-prod:
	docker-compose -f deploy/docker/docker-compose.prod.yml down

# Building
build-all:
	docker-compose -f deploy/docker/docker-compose.dev.yml build

build-prod:
	docker-compose -f deploy/docker/docker-compose.prod.yml build

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