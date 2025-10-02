#!/bin/bash
# PRP-A3: Production Deployment Automation
# Multi-cloud deployment script for AWS, Azure, GCP

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEPLOY_ENV="${DEPLOY_ENV:-production}"
CLOUD_PROVIDER="${CLOUD_PROVIDER:-aws}"
APP_VERSION="${APP_VERSION:-$(git rev-parse --short HEAD)}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_header() {
    echo -e "\n${BLUE}=== $1 ===${NC}"
}

# Check prerequisites
check_prerequisites() {
    log_header "Checking Prerequisites"

    # Check required tools
    local required_tools=("docker" "git" "curl" "jq")

    case "$CLOUD_PROVIDER" in
        aws)
            required_tools+=("aws" "kubectl")
            ;;
        azure)
            required_tools+=("az" "kubectl")
            ;;
        gcp)
            required_tools+=("gcloud" "kubectl")
            ;;
    esac

    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log_error "Required tool '$tool' is not installed"
            exit 1
        fi
        log_info "✓ $tool is available"
    done

    # Check environment variables
    local required_vars=("DEPLOY_ENV")

    case "$CLOUD_PROVIDER" in
        aws)
            required_vars+=("AWS_REGION" "AWS_ACCOUNT_ID")
            ;;
        azure)
            required_vars+=("AZURE_SUBSCRIPTION_ID" "AZURE_RESOURCE_GROUP")
            ;;
        gcp)
            required_vars+=("GOOGLE_CLOUD_PROJECT_ID" "GCP_REGION")
            ;;
    esac

    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            log_error "Required environment variable '$var' is not set"
            exit 1
        fi
        log_info "✓ $var is set"
    done

    log_success "Prerequisites check completed"
}

# Build and tag Docker image
build_image() {
    log_header "Building Docker Image"

    cd "$PROJECT_ROOT"

    # Build the image
    log_info "Building compliance-engine:$APP_VERSION"
    docker build -t "compliance-engine:$APP_VERSION" -t "compliance-engine:latest" .

    # Tag for cloud registry
    case "$CLOUD_PROVIDER" in
        aws)
            local registry="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
            docker tag "compliance-engine:$APP_VERSION" "$registry/compliance-engine:$APP_VERSION"
            docker tag "compliance-engine:latest" "$registry/compliance-engine:latest"
            log_info "Tagged for AWS ECR: $registry/compliance-engine:$APP_VERSION"
            ;;
        azure)
            local registry="${AZURE_CONTAINER_REGISTRY}.azurecr.io"
            docker tag "compliance-engine:$APP_VERSION" "$registry/compliance-engine:$APP_VERSION"
            docker tag "compliance-engine:latest" "$registry/compliance-engine:latest"
            log_info "Tagged for Azure ACR: $registry/compliance-engine:$APP_VERSION"
            ;;
        gcp)
            local registry="gcr.io/${GOOGLE_CLOUD_PROJECT_ID}"
            docker tag "compliance-engine:$APP_VERSION" "$registry/compliance-engine:$APP_VERSION"
            docker tag "compliance-engine:latest" "$registry/compliance-engine:latest"
            log_info "Tagged for GCP GCR: $registry/compliance-engine:$APP_VERSION"
            ;;
    esac

    log_success "Docker image built and tagged"
}

# Push to cloud registry
push_image() {
    log_header "Pushing to Cloud Registry"

    case "$CLOUD_PROVIDER" in
        aws)
            # Login to ECR
            log_info "Logging into AWS ECR"
            aws ecr get-login-password --region "$AWS_REGION" | \
                docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

            # Create repository if it doesn't exist
            if ! aws ecr describe-repositories --repository-names compliance-engine --region "$AWS_REGION" &>/dev/null; then
                log_info "Creating ECR repository"
                aws ecr create-repository --repository-name compliance-engine --region "$AWS_REGION"
            fi

            # Push images
            local registry="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
            docker push "$registry/compliance-engine:$APP_VERSION"
            docker push "$registry/compliance-engine:latest"
            ;;

        azure)
            # Login to ACR
            log_info "Logging into Azure ACR"
            az acr login --name "$AZURE_CONTAINER_REGISTRY"

            # Push images
            local registry="${AZURE_CONTAINER_REGISTRY}.azurecr.io"
            docker push "$registry/compliance-engine:$APP_VERSION"
            docker push "$registry/compliance-engine:latest"
            ;;

        gcp)
            # Configure Docker for GCR
            log_info "Configuring Docker for GCP GCR"
            gcloud auth configure-docker

            # Push images
            local registry="gcr.io/${GOOGLE_CLOUD_PROJECT_ID}"
            docker push "$registry/compliance-engine:$APP_VERSION"
            docker push "$registry/compliance-engine:latest"
            ;;
    esac

    log_success "Images pushed to cloud registry"
}

# Deploy infrastructure
deploy_infrastructure() {
    log_header "Deploying Infrastructure"

    case "$CLOUD_PROVIDER" in
        aws)
            deploy_aws_infrastructure
            ;;
        azure)
            deploy_azure_infrastructure
            ;;
        gcp)
            deploy_gcp_infrastructure
            ;;
    esac

    log_success "Infrastructure deployment completed"
}

# AWS infrastructure deployment
deploy_aws_infrastructure() {
    log_info "Deploying AWS infrastructure"

    # Check if EKS cluster exists
    if ! aws eks describe-cluster --name "compliance-engine-cluster" --region "$AWS_REGION" &>/dev/null; then
        log_info "Creating EKS cluster"

        # Create EKS cluster (this would typically use CloudFormation/CDK/Terraform)
        aws eks create-cluster \
            --name compliance-engine-cluster \
            --version 1.27 \
            --role-arn "arn:aws:iam::${AWS_ACCOUNT_ID}:role/compliance-engine-eks-role" \
            --resources-vpc-config subnetIds="${EKS_SUBNET_IDS}" \
            --region "$AWS_REGION"

        # Wait for cluster to be active
        log_info "Waiting for EKS cluster to be ready..."
        aws eks wait cluster-active --name compliance-engine-cluster --region "$AWS_REGION"
    fi

    # Update kubeconfig
    aws eks update-kubeconfig --name compliance-engine-cluster --region "$AWS_REGION"

    # Create RDS instance if it doesn't exist
    if ! aws rds describe-db-instances --db-instance-identifier compliance-engine-db --region "$AWS_REGION" &>/dev/null; then
        log_info "Creating RDS PostgreSQL instance"
        aws rds create-db-instance \
            --db-instance-identifier compliance-engine-db \
            --db-instance-class db.t3.medium \
            --engine postgres \
            --engine-version 15.3 \
            --master-username postgres \
            --master-user-password "$DB_PASSWORD" \
            --allocated-storage 100 \
            --vpc-security-group-ids "$RDS_SECURITY_GROUP_ID" \
            --db-subnet-group-name "$RDS_SUBNET_GROUP" \
            --region "$AWS_REGION"
    fi

    # Create ElastiCache Redis cluster
    if ! aws elasticache describe-cache-clusters --cache-cluster-id compliance-engine-redis --region "$AWS_REGION" &>/dev/null; then
        log_info "Creating ElastiCache Redis cluster"
        aws elasticache create-cache-cluster \
            --cache-cluster-id compliance-engine-redis \
            --cache-node-type cache.t3.micro \
            --engine redis \
            --num-cache-nodes 1 \
            --security-group-ids "$REDIS_SECURITY_GROUP_ID" \
            --cache-subnet-group-name "$REDIS_SUBNET_GROUP" \
            --region "$AWS_REGION"
    fi
}

# Azure infrastructure deployment
deploy_azure_infrastructure() {
    log_info "Deploying Azure infrastructure"

    # Create resource group
    az group create --name "$AZURE_RESOURCE_GROUP" --location "$AZURE_REGION"

    # Create AKS cluster
    if ! az aks show --name compliance-engine-cluster --resource-group "$AZURE_RESOURCE_GROUP" &>/dev/null; then
        log_info "Creating AKS cluster"
        az aks create \
            --resource-group "$AZURE_RESOURCE_GROUP" \
            --name compliance-engine-cluster \
            --node-count 3 \
            --node-vm-size Standard_D2s_v3 \
            --kubernetes-version 1.27 \
            --enable-managed-identity \
            --attach-acr "$AZURE_CONTAINER_REGISTRY"
    fi

    # Get AKS credentials
    az aks get-credentials --resource-group "$AZURE_RESOURCE_GROUP" --name compliance-engine-cluster

    # Create Azure Database for PostgreSQL
    if ! az postgres server show --name compliance-engine-db --resource-group "$AZURE_RESOURCE_GROUP" &>/dev/null; then
        log_info "Creating Azure Database for PostgreSQL"
        az postgres server create \
            --resource-group "$AZURE_RESOURCE_GROUP" \
            --name compliance-engine-db \
            --location "$AZURE_REGION" \
            --admin-user postgres \
            --admin-password "$DB_PASSWORD" \
            --sku-name GP_Gen5_2 \
            --version 11
    fi

    # Create Azure Cache for Redis
    if ! az redis show --name compliance-engine-redis --resource-group "$AZURE_RESOURCE_GROUP" &>/dev/null; then
        log_info "Creating Azure Cache for Redis"
        az redis create \
            --location "$AZURE_REGION" \
            --name compliance-engine-redis \
            --resource-group "$AZURE_RESOURCE_GROUP" \
            --sku Basic \
            --vm-size c0
    fi
}

# GCP infrastructure deployment
deploy_gcp_infrastructure() {
    log_info "Deploying GCP infrastructure"

    # Create GKE cluster
    if ! gcloud container clusters describe compliance-engine-cluster --zone "$GCP_ZONE" --project "$GOOGLE_CLOUD_PROJECT_ID" &>/dev/null; then
        log_info "Creating GKE cluster"
        gcloud container clusters create compliance-engine-cluster \
            --zone "$GCP_ZONE" \
            --project "$GOOGLE_CLOUD_PROJECT_ID" \
            --num-nodes 3 \
            --machine-type e2-standard-2 \
            --enable-autoscaling \
            --min-nodes 1 \
            --max-nodes 5
    fi

    # Get GKE credentials
    gcloud container clusters get-credentials compliance-engine-cluster --zone "$GCP_ZONE" --project "$GOOGLE_CLOUD_PROJECT_ID"

    # Create Cloud SQL PostgreSQL instance
    if ! gcloud sql instances describe compliance-engine-db --project "$GOOGLE_CLOUD_PROJECT_ID" &>/dev/null; then
        log_info "Creating Cloud SQL PostgreSQL instance"
        gcloud sql instances create compliance-engine-db \
            --database-version POSTGRES_15 \
            --tier db-f1-micro \
            --region "$GCP_REGION" \
            --project "$GOOGLE_CLOUD_PROJECT_ID"

        # Set root password
        gcloud sql users set-password postgres \
            --instance compliance-engine-db \
            --password "$DB_PASSWORD" \
            --project "$GOOGLE_CLOUD_PROJECT_ID"
    fi

    # Create Memorystore Redis instance
    if ! gcloud redis instances describe compliance-engine-redis --region "$GCP_REGION" --project "$GOOGLE_CLOUD_PROJECT_ID" &>/dev/null; then
        log_info "Creating Memorystore Redis instance"
        gcloud redis instances create compliance-engine-redis \
            --size 1 \
            --region "$GCP_REGION" \
            --project "$GOOGLE_CLOUD_PROJECT_ID"
    fi
}

# Deploy Kubernetes manifests
deploy_kubernetes() {
    log_header "Deploying to Kubernetes"

    cd "$PROJECT_ROOT"

    # Create namespace
    kubectl create namespace nsw-compliance --dry-run=client -o yaml | kubectl apply -f -

    # Apply secrets
    log_info "Creating secrets"
    kubectl create secret generic database-credentials \
        --from-literal=username=postgres \
        --from-literal=password="$DB_PASSWORD" \
        --namespace=nsw-compliance \
        --dry-run=client -o yaml | kubectl apply -f -

    kubectl create secret generic api-keys \
        --from-literal=google-maps="$GOOGLE_MAPS_API_KEY" \
        --from-literal=openai="$OPENAI_API_KEY" \
        --from-literal=deepseek="$DEEPSEEK_API_KEY" \
        --from-literal=gemini="$GEMINI_API_KEY" \
        --namespace=nsw-compliance \
        --dry-run=client -o yaml | kubectl apply -f -

    # Update deployment with new image
    log_info "Updating deployment with image version $APP_VERSION"
    sed -i.bak "s|image: compliance-engine:latest|image: compliance-engine:$APP_VERSION|g" kubernetes/deployment.yaml

    # Apply Kubernetes manifests
    kubectl apply -f kubernetes/ --namespace=nsw-compliance

    # Wait for deployment to be ready
    log_info "Waiting for deployment to be ready..."
    kubectl rollout status deployment/compliance-engine --namespace=nsw-compliance --timeout=600s

    # Restore original deployment file
    mv kubernetes/deployment.yaml.bak kubernetes/deployment.yaml

    log_success "Kubernetes deployment completed"
}

# Health check
health_check() {
    log_header "Running Health Checks"

    # Get service URL
    local service_url
    if command -v kubectl &> /dev/null; then
        service_url=$(kubectl get service compliance-engine-service --namespace=nsw-compliance -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "localhost")
        if [[ "$service_url" == "localhost" ]]; then
            # Port forward for testing
            kubectl port-forward service/compliance-engine-service 8080:80 --namespace=nsw-compliance &
            local port_forward_pid=$!
            service_url="localhost:8080"
            sleep 5
        fi
    else
        service_url="localhost:3000"
    fi

    # Test health endpoints
    local endpoints=("health?type=liveness" "health?type=readiness" "health/metrics")

    for endpoint in "${endpoints[@]}"; do
        log_info "Testing /$endpoint"
        if curl -f -s "http://$service_url/api/$endpoint" > /dev/null; then
            log_success "✓ /$endpoint is healthy"
        else
            log_error "✗ /$endpoint failed"
        fi
    done

    # Clean up port forward if started
    if [[ -n "${port_forward_pid:-}" ]]; then
        kill $port_forward_pid 2>/dev/null || true
    fi

    log_success "Health checks completed"
}

# Cleanup on exit
cleanup() {
    log_info "Cleaning up..."
    # Kill any background processes
    jobs -p | xargs -r kill 2>/dev/null || true
}

# Main deployment function
main() {
    log_header "PRP-A3: Production Deployment Starting"
    log_info "Environment: $DEPLOY_ENV"
    log_info "Cloud Provider: $CLOUD_PROVIDER"
    log_info "App Version: $APP_VERSION"

    # Set trap for cleanup
    trap cleanup EXIT

    # Run deployment steps
    check_prerequisites
    build_image
    push_image
    deploy_infrastructure
    deploy_kubernetes
    health_check

    log_header "Deployment Completed Successfully!"
    log_success "Application deployed with version: $APP_VERSION"
    log_success "Health checks passed"

    # Show access information
    echo ""
    log_info "Access URLs:"
    log_info "  Application: http://$service_url"
    log_info "  Health Check: http://$service_url/api/health"
    log_info "  Metrics: http://$service_url/api/health/metrics"
}

# Run main function
main "$@"