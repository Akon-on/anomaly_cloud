FROM python:3.10
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY visualize.py .
COPY metrics.py .
COPY batch_report.py .
COPY generate_threshold_comparison.py .
COPY gen_threshold_compare.py .
CMD ["python", "metrics.py"]
