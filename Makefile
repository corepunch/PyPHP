PYTHON       ?= $(shell command -v python3 || command -v python)
TEST_DIR     := tests
EXAMPLES_DIR := examples

.PHONY: test examples

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

examples:
	@echo "=== C Header (examples/c_header/header.php) ==="
	@$(PYTHON) -m pyphp $(EXAMPLES_DIR)/c_header/header.php $(EXAMPLES_DIR)/c_header/model.xml
	@echo ""
	@echo "=== HTML Report (examples/html/report.php) ==="
	@$(PYTHON) -m pyphp $(EXAMPLES_DIR)/html/report.php
	@echo ""
	@echo "=== API Docs (examples/docs/api.php) ==="
	@$(PYTHON) -m pyphp $(EXAMPLES_DIR)/docs/api.php
	@echo ""
	@echo "=== Book Catalog / SimpleXML (examples/simplexml/catalog.php) ==="
	@$(PYTHON) -m pyphp $(EXAMPLES_DIR)/simplexml/catalog.php
	@echo ""
	@echo "=== CLI options / getopt (examples/getopt/greet.php) ==="
	@$(PYTHON) -m pyphp $(EXAMPLES_DIR)/getopt/greet.php --user=World --greeting=Hello