FROM python:3.10
WORKDIR /app
RUN pip install pandas matplotlib psycopg2-binary
COPY visualize.py .
COPY metrics.py .
CMD ["python", "metrics.py"]
