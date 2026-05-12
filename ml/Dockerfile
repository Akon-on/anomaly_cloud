FROM python:3.10
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY feature_engineering.py .
COPY model.py .
COPY evaluate_models.py .
COPY test_feature_engineering.py .
COPY test_evaluator.py .
COPY drift.py .
COPY test_drift.py .
COPY test_realtime_model.py .
CMD ["python", "-u", "model.py"]
