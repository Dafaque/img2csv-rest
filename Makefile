test:
	curl -F file='@test.pdf' '0.0.0.0:8080/extract/pdf' -vvv
run:
	python main.py
build:
	docker build -t img2csv:local .
docker-run:
	docker run --rm -p 8080:8080 -d img2csv:local