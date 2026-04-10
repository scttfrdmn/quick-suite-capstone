.PHONY: audit sast scan-fs security

audit:
	pip-audit .

sast:
	semgrep scan --config=auto --error .

scan-fs:
	trivy fs --severity HIGH,CRITICAL .

security: audit sast scan-fs
