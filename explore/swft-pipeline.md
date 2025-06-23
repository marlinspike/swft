
### High Level Ovrerview of DoD AI Apps and MSFT Plugins

```mermaid
graph TD
  A[GitHub CI CD Pipeline] --> B[Build Secure Container]
  B --> C[Generate SBOM and CVEs]
  C --> D[Sign and Upload to Azure Storage]
  D --> E[Submit to DoD SWFT REST API]
  E --> F[Rapid Authorization]

  subgraph Data Lakehouse
    G[Azure Blob Storage]
    H[Azure Databases]
    I[Azure Synapse]
    J[Microsoft Purview]
  end

  G --> K[Unified DoD Data Lakehouse]
  H --> K
  I --> K
  J --> K

  subgraph AI Canvases
    L[Ask Sage]
    M[ChatGPT Gov]
    N[Microsoft Copilot]
    O[Palantir AIP]
    P[NIPR GPT]
  end

  subgraph AI Agents
    Q[Mission Risk Agent]
    R[SBOM Analyzer Agent]
    S[Compliance Insight Agent]
    T[Threat Synthesizer Agent]
  end

  L --> Q
  M --> R
  N --> S
  O --> T
  P --> Q

  Q --> K
  R --> K
  S --> K
  T --> K

  subgraph ISD Agent Factory
    U[Define Mission Logic]
    V[Build Agent or MCP Server]
    W[Deploy to Canvas or Marketplace]
  end

  U --> V --> W
  W --> Q
  W --> R
  W --> S
  W --> T


```

### Mermaid Diagram
```mermaid
graph TD
  A[GitHub CI CD Pipeline] --> B[Generate SBOM and CVE Lists]
  B --> C[Sign Artifacts with Cosign]
  C --> D[Upload to Azure Storage]
  D --> E[Analyze with Azure Function App AI]
  E --> F[Package and Prepare Artifacts]
  F --> G[Submit to DoD REST API]
  G --> H[Rapid Authorization by DoD AO]

  subgraph AI Canvases
    AC[Ask Sage]
    AG[ChatGPT Gov]
    AP[Palantir AIP]
    AM[Microsoft Copilot]
    AN[NIPR GPT]
  end

  subgraph AI Agents
    AA[SWFT Explainer Agent]
    AB[SBOM Inspector Agent]
    AD[Mission Risk Synthesizer]
  end

  AC --> AA
  AG --> AB
  AP --> AD
  AM --> AA
  AN --> AD

  AA --> E
  AB --> L
  AD --> L

  subgraph Continuous Monitoring
    I[Microsoft Defender for Cloud]
    J[Microsoft Sentinel]
  end

  I --> K[Real-time Threat Detection]
  J --> K
  K --> L[Dynamic Risk Scoring]
  L --> H

  subgraph Compliance Enforcement
    M[Azure Policy]
    N[Ratify for Runtime Verification]
  end

  M --> O[Policy Enforcement]
  N --> O
  O --> P[Secure Runtime]
  P --> H

  subgraph Deployment Strategy
    Q[Container Deployments via AKS]
    R[Limited VM Deployments]
  end

  Q --> S[Use of Azure Marketplace Images]
  R --> S
  S --> T[Deploy in Azure Kubernetes Service]
  T --> K

  subgraph Data Sources
    U[SBOMs, CVEs]
    V[DoD Mission Impact Data]
    W[Threat Intel Feeds]
    X[Compliance Databases]
  end

  U --> E
  V --> L
  W --> L
  X --> O

```

## SWFT Pipeline Diagram

```mermaid
graph TD
  start[Start Triggered by push to main or manual dispatch]

  start --> install_trivy[Install Trivy]
  install_trivy --> install_cosign[Install Cosign]
  install_cosign --> checkout[Checkout source code]
  checkout --> azure_login[Azure Login]
  azure_login --> buildx[Set up Docker Buildx]
  buildx --> acr_login[Login to ACR]
  acr_login --> decode_cosign_priv[Decode Cosign private key]
  decode_cosign_priv --> decode_cosign_pub1[Decode Cosign public key]
  decode_cosign_pub1 --> docker_build[Build and push Docker image]
  docker_build --> cosign_sign[Sign image with Cosign]
  cosign_sign --> generate_sbom[Generate SBOM using Syft]
  generate_sbom --> trivy_scan[Run CVE scan with Trivy]
  trivy_scan --> analysis_complete[SBOM and Trivy ready]

  subgraph Azure Storage
    upload_sbom_azure[Upload SBOM to Azure Blob]
    upload_trivy_azure[Upload Trivy report to Azure Blob]
    upload_artifacts_azure[Upload build artifacts to Azure Blob]
  end

  analysis_complete --> upload_sbom_azure
  analysis_complete --> upload_trivy_azure
  upload_sbom_azure --> swft_stub
  upload_trivy_azure --> swft_stub

  subgraph DoD SWFT
    swft_stub[Stub Upload SBOM and Trivy to DoD SWFT API]
  end

  swft_stub --> artifact_check[Check for local artifacts]
  artifact_check --> upload_artifacts_azure

  upload_artifacts_azure --> decode_cosign_pub2[Decode Cosign public key]
  decode_cosign_pub2 --> cosign_verify[Verify container signature]
  cosign_verify --> proceed_deploy[Proceed to ACI deployment]

  subgraph Azure Container Instance
    proceed_deploy --> deploy_check[Check if container exists]
    deploy_check --> delete_container[Delete container if exists]
    delete_container --> wait_delete[Wait for deletion]
    wait_delete --> create_container[Create container instance with public IP]
    deploy_check --> create_container
    create_container --> get_ip[Fetch public IP]
  end

  get_ip --> workflow_complete[Workflow complete]

```


## SWFT App

First we need to create the Azure resources

```bash
# Login to Azure
az login

# Create resource group
az group create --name demo-swft-cicd --location eastus

# Create an Azure Container Registry (ACR)
az acr create --resource-group demo-swft-cicd --name swftacr$RANDOM --sku Basic

# Create a Storage Account for SBOMs
az storage account create --name swftsbomstore$RANDOM --resource-group demo-swft-cicd --location eastus --sku Standard_LRS

# (Optional) Create a blob container for SBOMs
az storage container create --account-name <storage_account_name> --name sboms

# Create a Service Principal for GitHub Actions
az ad sp create-for-rbac --name "swft-cicd-sp" --role contributor \
  --scopes /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/demo-swft-cicd \
  --sdk-auth


```

#### Github Secrets
```markdown
| Secret Name             | How to Create/Get                                            |
| ----------------------- | ------------------------------------------------------------ |
| AZURE\_CLIENT\_ID       | From your Azure Service Principal                            |
| AZURE\_TENANT\_ID       | From your Azure Active Directory                             |
| AZURE\_SUBSCRIPTION\_ID | From your Azure Portal                                       |
| AZURE\_CLIENT\_SECRET   | From your Azure Service Principal                            |
| ACR\_LOGIN\_SERVER      | From `az acr show ... --query loginServer`                   |
| ACR\_USERNAME           | From `az acr credential show ... --query username`           |
| ACR\_PASSWORD           | From `az acr credential show ... --query passwords[0].value` |
| AZURE\_STORAGE\_ACCOUNT | Your storage account name                                    |
| AZURE\_STORAGE\_KEY     | From `az storage account keys list ...`                      |


```

#### Integrated Security Best Practices

- Base Images: Use FIPS-compatible images (e.g., Chainguard Wolfi).

- SBOM Format: Use SPDX or CycloneDX.

- Policy as Code: Enforce compliance using Azure Policy and OPA/Gatekeeper with Ratify.

- Runtime Controls: Reject unsigned or policy-violating containers during AKS admission.



### SWFT CICD Pipeline
Overview of Pipeline Phases

```markdown
| **Phase**             | **Description**                                     | **Tools/Integrations**                                     | **SWFT RFI Mapping** |
| --------------------- | --------------------------------------------------- | ---------------------------------------------------------- | -------------------- |
| 1. Checkout           | Pull latest code from GitHub repo                   | `actions/checkout@v3`                                      | -                    |
| 2. Build Container    | Build container image using hardened base           | `docker build`, Wolfi/Chainguard, Azure Marketplace images | Tools Q1, Q2         |
| 3. Generate SBOM      | Output full SBOM with license and component details | `anchore/sbom-action`, `cyclonedx-github-action`           | Tools Q3             |
| 4. CVE Scan           | Scan for known vulnerabilities                      | `aquasecurity/trivy-action`, or `github/codeql-action`     | AI Q1, Tools Q4      |
| 5. Sign Image         | Sign container image and SBOM                       | `sigstore/cosign-installer`, `cosign sign`                 | External Q5          |
| 6. Push to Registry   | Push to ACR (Azure Container Registry)              | `docker push`, `az acr login`                              | -                    |
| 7. Upload SBOM        | Upload SBOM to Azure Storage for pipeline tracking  | `azure/CLI`, `az storage blob upload`                      | Tools Q5, Q6         |
| 8. Submit to SWFT API | Submit artifact metadata for SWFT risk decision     | Azure Function or REST Client                              | AI Q1, Q3            |
| 9. Deployment         | Deploy to AKS with runtime policy enforcement       | GitHub Deployments + Ratify + Gatekeeper                   | Tools Q4, AI Q4      |
| 10. Monitoring        | Continuously monitor deployed containers            | Microsoft Defender for Cloud, Microsoft Sentinel           | AI Q1, Q2            |
| 11. Rescan            | Periodic rescan of registry images                  | `schedule:` + Azure Defender or Trivy in cron              | Tools Q4             |
| 12. Artifact Logs     | Upload logs for audit                               | `actions/upload-artifact@v3`                               | External Q5          |
```



#### Workflow Steps

```github-workflow
name: SWFT Container CI/CD

on:
  push:
    branches: [ main ]
  workflow_dispatch:

permissions:
  contents: read
  id-token: write

env:
  ACR_LOGIN_SERVER:    ${{ secrets.ACR_LOGIN_SERVER }}
  ACR_USERNAME:        ${{ secrets.ACR_USERNAME }}
  ACR_PASSWORD:        ${{ secrets.ACR_PASSWORD }}
  IMAGE_NAME:          fastapi-demo
  IMAGE_TAG:           ${{ github.sha }}
  AZURE_RESOURCE_GROUP: demo-swft-cicd
  AZURE_CONTAINER_NAME: swft-fastapi
  AZURE_STORAGE_ACCOUNT: ${{ secrets.AZURE_STORAGE_ACCOUNT }}
  AZURE_STORAGE_KEY:     ${{ secrets.AZURE_STORAGE_KEY }}

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest

    steps:
      - name: Install Trivy
        uses: aquasecurity/setup-trivy@v0.2.1

      - name: Checkout source
        uses: actions/checkout@v3

      - name: Azure Login
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to ACR
        run: |
          echo "$ACR_PASSWORD" \
            | docker login "$ACR_LOGIN_SERVER" \
                          -u "$ACR_USERNAME" \
                          --password-stdin

      - name: Build Docker image
        run: |
          docker buildx build \
            -t "$ACR_LOGIN_SERVER/$IMAGE_NAME:$IMAGE_TAG" \
            --push \
            .

      - name: Generate SBOM (Syft)
        uses: anchore/sbom-action@v0.20.1
        with:
          image:        ${{ env.ACR_LOGIN_SERVER }}/${{ env.IMAGE_NAME }}:${{ env.IMAGE_TAG }}
          format:       cyclonedx-json
          output-file:  sbom.cyclonedx.json
          upload-artifact: false

      - name: CVE Scan and save report (Trivy)
        run: |
          trivy image \
            --format json \
            --output trivy-report.json \
            --severity HIGH,CRITICAL \
            --ignore-unfixed \
            "$ACR_LOGIN_SERVER/$IMAGE_NAME:$IMAGE_TAG"


      - name: Upload SBOM to Azure Storage
        env:
          AZURE_STORAGE_ACCOUNT: ${{ secrets.AZURE_STORAGE_ACCOUNT }}
          AZURE_STORAGE_KEY: ${{ secrets.AZURE_STORAGE_KEY }}
          IMAGE_NAME: ${{ env.IMAGE_NAME }}
          IMAGE_TAG: ${{ env.IMAGE_TAG }}
        run: |
          az storage blob upload \
            --auth-mode key \
            --account-name "$AZURE_STORAGE_ACCOUNT" \
            --account-key  "$AZURE_STORAGE_KEY" \
            --container-name sboms \
            --file           sbom.cyclonedx.json \
            --name           "${IMAGE_NAME}-${IMAGE_TAG}-sbom.json" \
            --overwrite


      - name: Upload Trivy report to Azure Storage
        env:
          AZURE_STORAGE_ACCOUNT: ${{ secrets.AZURE_STORAGE_ACCOUNT }}
          AZURE_STORAGE_KEY: ${{ secrets.AZURE_STORAGE_KEY }}
          IMAGE_NAME: ${{ env.IMAGE_NAME }}
          IMAGE_TAG: ${{ env.IMAGE_TAG }}
        run: |
          az storage blob upload \
            --auth-mode key \
            --account-name "$AZURE_STORAGE_ACCOUNT" \
            --account-key  "$AZURE_STORAGE_KEY" \
            --container-name scans \
            --file           trivy-report.json \
            --name           "${IMAGE_NAME}-${IMAGE_TAG}-trivy.json" \
            --overwrite


      - name: Upload SBOM to DoD SWFT REST API (stubbed)
        run: |
          echo "🟡 STUB: Would POST SBOM to DoD SWFT API"
          echo "Endpoint: https://api.swft.dod.mil/v1/sboms"
          echo "Auth: Bearer ${{ secrets.DO_D_SWFT_API_TOKEN }}"
          echo "Payload: ${{ env.IMAGE_NAME }}-${{ env.IMAGE_TAG }}"


      - name: Upload all artifacts to Azure Blob Storage
        uses: azure/CLI@v2
        env:
          AZURE_STORAGE_ACCOUNT: ${{ secrets.AZURE_STORAGE_ACCOUNT }}
          AZURE_STORAGE_KEY: ${{ secrets.AZURE_STORAGE_KEY }}
          IMAGE_TAG: ${{ env.IMAGE_TAG }}
        with:
          inlineScript: |
            az storage container create \
              --account-name "$AZURE_STORAGE_ACCOUNT" \
              --account-key  "$AZURE_STORAGE_KEY" \
              --name         artifacts \
              --public-access off

            if compgen -G "./artifacts/*" > /dev/null; then
              for file in ./artifacts/*; do
                filename=$(basename "$file")
                echo "Uploading $filename..."
                az storage blob upload \
                  --account-name   "$AZURE_STORAGE_ACCOUNT" \
                  --account-key    "$AZURE_STORAGE_KEY" \
                  --container-name artifacts \
                  --file           "$file" \
                  --name           "${IMAGE_TAG}-${filename}"
              done
            else
              echo "No files found in ./artifacts/ — skipping upload."
            fi

      - name: Deploy to Azure Container Instance
        shell: bash
        env:
          AZURE_RESOURCE_GROUP: ${{ secrets.AZURE_RESOURCE_GROUP }}
          AZURE_CONTAINER_NAME: ${{ env.AZURE_CONTAINER_NAME }}
          ACR_LOGIN_SERVER:     ${{ env.ACR_LOGIN_SERVER }}
          ACR_USERNAME:         ${{ secrets.ACR_USERNAME }}
          ACR_PASSWORD:         ${{ secrets.ACR_PASSWORD }}
          IMAGE_NAME:           ${{ env.IMAGE_NAME }}
          IMAGE_TAG:            ${{ env.IMAGE_TAG }}
        run: |
          echo "Checking if container instance exists..."
          if az container show \
              --resource-group "$AZURE_RESOURCE_GROUP" \
              --name "$AZURE_CONTAINER_NAME" \
              --only-show-errors \
              --output none 2>/dev/null; then
            echo "Container exists. Deleting and recreating..."
            az container delete \
              --resource-group "$AZURE_RESOURCE_GROUP" \
              --name "$AZURE_CONTAINER_NAME" \
              --yes

            echo "Waiting for container deletion..."
            for i in {1..30}; do
              if ! az container show --resource-group "$AZURE_RESOURCE_GROUP" --name "$AZURE_CONTAINER_NAME" &>/dev/null; then
                echo "✅ Container deleted."
                break
              fi
              echo "... Still deleting... retry $i"
              sleep 5
            done
          else
            echo "Container does not exist. Creating..."
          fi

          echo "Creating container instance..."
          az container create \
            --resource-group "$AZURE_RESOURCE_GROUP" \
            --name "$AZURE_CONTAINER_NAME" \
            --image "$ACR_LOGIN_SERVER/$IMAGE_NAME:$IMAGE_TAG" \
            --registry-login-server "$ACR_LOGIN_SERVER" \
            --registry-username     "$ACR_USERNAME" \
            --registry-password     "$ACR_PASSWORD" \
            --cpu 1 --memory 1 \
            --os-type Linux \
            --ports 80 \
            --ip-address Public

          echo "Fetching container public IP..."
          PUBLIC_IP=$(az container show \
            --resource-group "$AZURE_RESOURCE_GROUP" \
            --name "$AZURE_CONTAINER_NAME" \
            --query "ipAddress.ip" -o tsv)

          echo "✅ Container is deployed and accessible at: http://$PUBLIC_IP"

```


<!-- @import "[TOC]" {cmd="toc" depthFrom=1 depthTo=6 orderedList=false} -->
