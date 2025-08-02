server:	Dockerfile shlocker_test_container.py
	docker build -t testser:latest .

runlocal:
	docker run --name testser -p 9999:9999 testser:latest

rundaemon:
	docker run -d --name testser -p 9999:9999 testser:latest
