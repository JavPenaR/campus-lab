FROM python:3.12-slim
WORKDIR /app
COPY app.py ./
COPY static ./static
RUN mkdir -p /app/data && chown -R 10001:10001 /app
USER 10001
ENV PYTHONUNBUFFERED=1 DATA_DIR=/app/data HOST=0.0.0.0
EXPOSE 8080
CMD ["python", "app.py"]
