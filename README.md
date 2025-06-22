# FastAPI Tailwind Demo App

A FastAPI application that serves a Tailwind CSS styled HTML page with dynamic content.

## Features

- Modern UI with Tailwind CSS
- Real-time time display
- Container ID display
- Customizable message
- Health check endpoint
- Time endpoint
- Docker-ready for deployment

## Environment Variables

The application supports the following environment variables:

- `BACKGROUND_COLOR`: Background color of the page (default: "white")
- `CUSTOM_MESSAGE`: Custom message to display (default: "SWFT Demo")

## Running Locally

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
uvicorn app.main:app --reload
```

The application will be available at `http://localhost:8080`

## Running with Docker

1. Build the Docker image:
```bash
docker build -t swft-demo .
```

2. Run the container:
```bash
docker run -p 8080:8080 -e BACKGROUND_COLOR=blue -e CUSTOM_MESSAGE="My Custom Message" swft-demo
```

## Endpoints

- `GET /`: Main page with dynamic content
- `GET /health`: Health check endpoint
- `GET /time`: Current server time

## Deployment

This application is ready to be deployed to:
- Kubernetes
- Azure App Service
- Any container-compatible environment

## License

MIT License