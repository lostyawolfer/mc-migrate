.phony: test

POETRY = poetry run
TEST = pytest -v

test:
	$(POETRY) $(TEST)

cover:
	$(POETRY) $(TEST) --cov --cov-report=lcov --cov-report=html