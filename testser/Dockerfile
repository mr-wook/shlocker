FROM python:3.11-slim

WORKDIR /app
RUN pip install --no-cache-dir uv                           # uv is on PyPI :contentReference[oaicite:0]{index=0}
COPY shlocker_test_container.py .

# RUN uv venv --prompt project-env                             # layer in a venv without clearing /app :contentReference[oaicite:1]{index=1}  
# RUN . .venv/bin/activate
# RUN uv python install 3.13
# RUN uv pip install fastapi uvicorn
RUN pip install --no-cache-dir fastapi uvicorn
# RUN /bin/ls -l

EXPOSE 9999

# CMD ["/bin/sh", "-c", ". .venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 9999"]

CMD [ "python", "shlocker_test_container.py" ]
