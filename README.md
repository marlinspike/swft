# FastAPI Tailwind Demo App

A FastAPI application that serves a Tailwind CSS styled HTML page with dynamic content. The application is designed with security in mind and includes container image signing and vulnerability scanning.

## Features

- Modern UI with Tailwind CSS
- Real-time time display
- Container ID display
- Customizable message
- Health check endpoint
- Time endpoint
- Docker-ready for deployment
- Container image signing with Cosign
- SBOM generation with Syft
- CVE scanning with Trivy

## Security Features

The application includes several security features:

- **Image Signing**: All container images are signed using Cosign
- **SBOM Generation**: Software Bill of Materials (SBOM) is generated using Syft
- **Vulnerability Scanning**: Container images are scanned for vulnerabilities using Trivy
- **Deployment Security**: Deployment is gated on successful signature verification

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
python app/main.py
```

The application will be available at `http://localhost:80`

## Security Setup

### Cosign Key Generation

To enable image signing in the GitHub workflow, you need to generate a Cosign key pair and add it as a GitHub secret:

1. Generate the key pair:
```bash
# Install Cosign if not already installed
curl -sfL https://raw.githubusercontent.com/sigstore/cosign/main/scripts/get-cosign.sh | sh

# Generate key pair
cosign generate-key-pair

# Enter a password for the private key when prompted
```

2. Convert the private key to base64:
```bash
base64 -i cosign.key | tr -d '\n' > cosign.key.b64
```

3. Add the following secrets to your GitHub repository:
   - `COSIGN_PRIVATE_KEY`: The contents of `cosign.key.b64`
   - `COSIGN_PASSWORD`: The password you used when generating the key pair

## Running with Docker

1. Build the Docker image:
```bash
docker build -t swft-demo .
```

2. Run the container:
```bash
docker run -p 80:80 -e BACKGROUND_COLOR=blue -e CUSTOM_MESSAGE="My Custom Message" swft-demo
```

## Endpoints

- `GET /`: Main page with dynamic content
- `GET /health`: Health check endpoint
- `GET /time`: Current server time

## Deployment

This application is deployed to Azure Container Instance using GitHub Actions. The deployment workflow includes:

1. Building and pushing the Docker image
2. Generating SBOM with Syft
3. Scanning for vulnerabilities with Trivy
4. Signing the image with Cosign
5. Verifying the image signature
6. Deploying to Azure Container Instance

## License

MIT License

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