BUILD_NAME?=interview_assistant
SVC_TAG?=latest

LANGUAGE = python
PWD = $(shell pwd)


local:
	$(MAKE) build
	$(MAKE) run


sh:
	$(MAKE) run cmd="/bin/bash"


lint:
	$(MAKE) run cmd="python -m flake8 . --count"

typecheck:
	$(MAKE) run cmd="mypy -p src"

black:
	$(MAKE) run cmd="python -m black -l 120 ./src"


build:
	# Build the base dependencies image
	docker build --rm \
		-f Dockerfile \
		-t $(BUILD_NAME):$(SVC_TAG) \
		.

run:
	$(MAKE) stop
	docker run \
		-it --rm \
		-p 8080:8080 \
		-v $(PWD)/:/app \
		-e PYTHONPATH="/app/src:$(PYTHONPATH)" \
		--name $(BUILD_NAME) \
		$(BUILD_NAME):$(SVC_TAG) \
		$(cmd)

stop:
	docker stop $(BUILD_NAME) || true && docker rm $(BUILD_NAME) || true


clean:
	docker rmi $(BUILD_NAME)