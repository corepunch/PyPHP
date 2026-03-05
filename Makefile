PYTHON ?= python3
TEST_DIR := tests

.PHONY: test

test:
	@fail=0; \
	for php_file in $$(find $(TEST_DIR) -name '*.php' | sort); do \
		if $(PYTHON) -m pyphp "$$php_file" > /dev/null 2>&1; then \
			echo "PASS: $$php_file"; \
		else \
			echo "FAIL: $$php_file"; \
			$(PYTHON) -m pyphp "$$php_file"; \
			fail=1; \
		fi; \
	done; \
	exit $$fail
