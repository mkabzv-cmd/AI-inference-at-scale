.PHONY: preflight build render deploy wait test observe break cleanup

preflight:
	@./scripts/check-prerequisites.sh

build:
	@./scripts/build-push-image.sh

render:
	@./scripts/render.sh

deploy:
	@./scripts/deploy.sh

wait:
	@./scripts/wait-ready.sh

test:
	@./scripts/test-api.sh

observe:
	@./scripts/observe.sh

break:
	@./scripts/failure-drill.sh

cleanup:
	@./scripts/cleanup.sh
