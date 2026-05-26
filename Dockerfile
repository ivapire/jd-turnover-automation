FROM python:3.12-slim

WORKDIR /app
COPY . .
RUN pip install -e .
CMD cd src && uvicorn jd_turnover.main:app --host 0.0.0.0 --port ${PORT:-8000}
