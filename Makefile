PY := python3

.PHONY: help test ci clean

help:
	@echo "make test    run the self-check (writes results/local.txt)"
	@echo "make ci      same thing, under the name CI uses (results/ci.txt)"
	@echo "make clean   remove results/ and output/"
	@echo
	@echo "Details:      ./run_test.sh <name> [submission_dir]"
	@echo "Checker src:  source_test/  (copied from UnaryLab/EEL4768_RISC-V_Project)"

test:
	@./run_test.sh local

ci:
	@./run_test.sh ci

clean:
	rm -rf results output
