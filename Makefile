RARS_VERSION := v1.6
RARS_URL     := https://github.com/TheThirdOne/rars/releases/download/v1.6/rars1_6.jar
PY           := python3
REQUIRED_CUSTOM_TESTS ?= 3

.PHONY: help test retest ci dist clean clean-golden

help:
	@echo "make rars.jar   download the reference assembler ($(RARS_VERSION))"
	@echo "make test       diff our assembler against RARS on every .s"
	@echo "make retest     same, but regenerate the cached RARS output first"
	@echo "make ci         exactly what the pipeline runs, locally"
	@echo "make clean      remove rars.jar, golden/ and dist/"
	@echo
	@echo "One test:       $(PY) tools/difftest.py -k custom_2"
	@echo "Root only:      $(PY) tools/difftest.py ."

rars.jar:
	curl -fsSL -o $@ $(RARS_URL)

test: rars.jar
	@$(PY) tools/difftest.py

retest: rars.jar
	@$(PY) tools/difftest.py --update-golden

ci: rars.jar
	@$(PY) tools/difftest.py \
		--update-golden \
		--require-custom $(REQUIRED_CUSTOM_TESTS) \
		--summary-md summary.md \
		--junit junit.xml

clean-golden:
	rm -rf golden

clean: clean-golden
	rm -f rars.jar summary.md junit.xml
	rm -rf dist
