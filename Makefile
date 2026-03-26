.PHONY: setup run test clean build help

.DEFAULT_GOAL := help

ifeq ($(OS),Windows_NT)
    MVNW = mvnw.cmd
else
    MVNW = ./mvnw
endif

# Alvo padrão
help:
	@echo "Alvos disponíveis:"
	@echo "  make setup   — verifica pré-requisitos e copia .env.example"
	@echo "  make run     — sobe os containers em background e aguarda o health check"
	@echo "  make test    — executa testes unitários"
	@echo "  make build   — compila o JAR sem Docker"
	@echo "  make clean   — para containers e remove volumes"

setup:
	@echo "→ Verificando pré-requisitos..."
	@command -v java   >/dev/null 2>&1 || (echo "ERRO: Java 21+ não encontrado" && exit 1)
	@command -v docker >/dev/null 2>&1 || (echo "ERRO: Docker não encontrado" && exit 1)
	@command -v mvn    >/dev/null 2>&1 || $(MVNW) --version >/dev/null 2>&1 || (echo "ERRO: Maven não encontrado" && exit 1)
	@[ -f .env ] || (cp .env.example .env && echo "→ .env criado a partir de .env.example")
	@echo "✓ Setup concluído. Execute 'make run' para subir o serviço."

run: setup
	docker compose up -d --build --wait
	@echo "✓ Serviço disponível em http://localhost:8080"
	@echo "✓ Swagger UI: http://localhost:8080/swagger-ui.html"

test:
	$(MVNW) test -Dspring.profiles.active=test


build:
	$(MVNW) package -DskipTests

clean:
	docker compose down -v
	$(MVNW) clean
