.PHONY: list validate test-cpu validate-structure validate-lessons validate-files validate-security

list:
	@./scripts/list-lessons.sh

validate: validate-structure validate-lessons validate-files validate-security

test-cpu:
	@./scripts/run-cpu-fixtures.sh

validate-structure:
	@./scripts/validate-structure.sh

validate-lessons:
	@./scripts/validate-published-lessons.sh

validate-files:
	@./scripts/validate-runnable-files.sh

validate-security:
	@python3 ./scripts/validate-security.py
