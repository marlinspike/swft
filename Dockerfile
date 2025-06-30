# Stage: Build in wolfi-base
FROM cgr.dev/chainguard/wolfi-base AS builder
ARG version=3.11

WORKDIR /app
RUN apk add python-${version} py${version}-pip && \
    chown -R nonroot:nonroot /app/
USER nonroot

COPY requirements.txt app/ templates/ static/ /app/
RUN pip install --user -r requirements.txt

# Stage: Runtime on Chainguard distroless Python
FROM cgr.dev/chainguard/python:latest

WORKDIR /app
ENV PATH="/home/nonroot/.local/bin:$PATH"

COPY --from=builder /home/nonroot/.local /home/nonroot/.local
COPY app/ templates/ static/ /app/

EXPOSE 80
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]


