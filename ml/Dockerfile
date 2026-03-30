FROM python:3.10
WORKDIR /app
RUN pip install pandas scikit-learn psycopg2-binary matplotlib
COPY model.py .
COPY evaluate_models.py .
CMD ["python", "-u", "model.py"]
