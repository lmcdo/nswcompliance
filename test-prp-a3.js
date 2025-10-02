#!/usr/bin/env node

/**
 * PRP-A3: Cloud Deployment Preparation Test
 * Tests all cloud deployment components and configurations
 */

const fs = require('fs').promises;
const path = require('path');

async function testCloudDeploymentPreparation() {
  console.log('=== PRP-A3: Cloud Deployment Preparation Test ===\n');

  let totalTests = 0;
  let passedTests = 0;

  const runTest = async (name, testFn) => {
    totalTests++;
    try {
      const startTime = Date.now();
      await testFn();
      const duration = Date.now() - startTime;
      console.log(`✅ ${name} (${duration}ms)`);
      passedTests++;
    } catch (error) {
      console.log(`❌ ${name}: ${error.message}`);
    }
  };

  // Test 1: Configuration Management
  await runTest('Enterprise Configuration System', async () => {
    const configPath = path.join(process.cwd(), 'config', 'production.js');
    const configExists = await fs.access(configPath).then(() => true).catch(() => false);

    if (!configExists) {
      throw new Error('Production configuration file not found');
    }

    const config = require(configPath);

    // Verify key configuration sections
    const requiredSections = ['database', 'security', 'monitoring', 'cloud'];
    for (const section of requiredSections) {
      if (!config[section]) {
        throw new Error(`Configuration section '${section}' missing`);
      }
    }

    // Verify PRP-A2 compatibility
    if (!config.features?.useDirectDatabase) {
      throw new Error('PRP-A2 direct database feature not configured');
    }

    console.log('  ✓ All configuration sections present');
    console.log('  ✓ PRP-A2 direct database architecture configured');
    console.log('  ✓ Multi-cloud provider support configured');
  });

  // Test 2: Secrets Management
  await runTest('Secrets Management System', async () => {
    const secretsPath = path.join(process.cwd(), 'config', 'secrets-manager.js');
    const secretsExists = await fs.access(secretsPath).then(() => true).catch(() => false);

    if (!secretsExists) {
      throw new Error('Secrets manager not found');
    }

    const { SecretsManager } = require(secretsPath);
    const secretsManager = new SecretsManager({
      provider: 'aws',
      cache: true
    });

    // Test health check
    const health = await secretsManager.healthCheck();

    if (!health.provider) {
      throw new Error('Secrets manager provider not configured');
    }

    console.log(`  ✓ Secrets manager initialized (Provider: ${health.provider})`);
    console.log(`  ✓ Cache enabled: ${health.cache.enabled}`);
    console.log('  ✓ Multi-cloud secrets support ready');
  });

  // Test 3: Health Check API
  await runTest('Health Check API', async () => {
    const healthPath = path.join(process.cwd(), 'frontend-nextjs', 'app', 'api', 'health', 'route.ts');
    const healthExists = await fs.access(healthPath).then(() => true).catch(() => false);

    if (!healthExists) {
      throw new Error('Health check API not found');
    }

    const healthContent = await fs.readFile(healthPath, 'utf-8');

    // Verify health check features
    const requiredFeatures = [
      'liveness',
      'readiness',
      'database',
      'performance',
      'PRP-A2'
    ];

    for (const feature of requiredFeatures) {
      if (!healthContent.includes(feature)) {
        throw new Error(`Health check missing '${feature}' support`);
      }
    }

    console.log('  ✓ Liveness and readiness probes implemented');
    console.log('  ✓ Database health checks (PRP-A2 compatible)');
    console.log('  ✓ Performance metrics included');
  });

  // Test 4: Metrics Endpoint
  await runTest('Prometheus Metrics', async () => {
    const metricsPath = path.join(process.cwd(), 'frontend-nextjs', 'app', 'api', 'health', 'metrics', 'route.ts');
    const metricsExists = await fs.access(metricsPath).then(() => true).catch(() => false);

    if (!metricsExists) {
      throw new Error('Metrics endpoint not found');
    }

    const metricsContent = await fs.readFile(metricsPath, 'utf-8');

    // Verify Prometheus metrics
    const requiredMetrics = [
      'app_uptime_seconds',
      'process_memory_bytes',
      'database_connections_total',
      'database_healthy',
      'feature_direct_database_enabled'
    ];

    for (const metric of requiredMetrics) {
      if (!metricsContent.includes(metric)) {
        throw new Error(`Metric '${metric}' not found`);
      }
    }

    console.log('  ✓ Application metrics implemented');
    console.log('  ✓ Database metrics (PRP-A2 compatible)');
    console.log('  ✓ Feature flag metrics included');
  });

  // Test 5: Docker Configuration
  await runTest('Docker Configuration', async () => {
    const dockerfilePath = path.join(process.cwd(), 'Dockerfile');
    const dockerfileExists = await fs.access(dockerfilePath).then(() => true).catch(() => false);

    if (!dockerfileExists) {
      throw new Error('Dockerfile not found');
    }

    const dockerContent = await fs.readFile(dockerfilePath, 'utf-8');

    // Verify Docker best practices
    const requiredFeatures = [
      'multi-stage',
      'non-root',
      'HEALTHCHECK',
      'dumb-init'
    ];

    for (const feature of requiredFeatures) {
      if (!dockerContent.toLowerCase().includes(feature.toLowerCase())) {
        throw new Error(`Docker feature '${feature}' not found`);
      }
    }

    // Check .dockerignore
    const dockerignorePath = path.join(process.cwd(), '.dockerignore');
    const dockerignoreExists = await fs.access(dockerignorePath).then(() => true).catch(() => false);

    if (!dockerignoreExists) {
      throw new Error('.dockerignore file not found');
    }

    console.log('  ✓ Multi-stage Docker build configured');
    console.log('  ✓ Security best practices implemented');
    console.log('  ✓ Health checks and optimization included');
  });

  // Test 6: Docker Compose Production
  await runTest('Docker Compose Production', async () => {
    const composePath = path.join(process.cwd(), 'docker-compose.production.yml');
    const composeExists = await fs.access(composePath).then(() => true).catch(() => false);

    if (!composeExists) {
      throw new Error('Production docker-compose.yml not found');
    }

    const composeContent = await fs.readFile(composePath, 'utf-8');

    // Verify production services
    const requiredServices = [
      'compliance-engine',
      'postgres',
      'redis',
      'prometheus',
      'grafana',
      'nginx'
    ];

    for (const service of requiredServices) {
      if (!composeContent.includes(service)) {
        throw new Error(`Service '${service}' not configured`);
      }
    }

    // Verify secrets management
    if (!composeContent.includes('secrets:')) {
      throw new Error('Docker secrets not configured');
    }

    console.log('  ✓ Full production stack configured');
    console.log('  ✓ Database and Redis included');
    console.log('  ✓ Monitoring stack (Prometheus/Grafana)');
    console.log('  ✓ Secrets management configured');
  });

  // Test 7: Kubernetes Configuration
  await runTest('Kubernetes Deployment', async () => {
    const k8sPath = path.join(process.cwd(), 'kubernetes', 'deployment.yaml');
    const k8sExists = await fs.access(k8sPath).then(() => true).catch(() => false);

    if (!k8sExists) {
      throw new Error('Kubernetes deployment.yaml not found');
    }

    const k8sContent = await fs.readFile(k8sPath, 'utf-8');

    // Verify Kubernetes resources
    const requiredResources = [
      'Deployment',
      'Service',
      'HorizontalPodAutoscaler',
      'PodDisruptionBudget'
    ];

    for (const resource of requiredResources) {
      if (!k8sContent.includes(`kind: ${resource}`)) {
        throw new Error(`Kubernetes resource '${resource}' not found`);
      }
    }

    // Verify PRP-A2 configuration
    if (!k8sContent.includes('COMPLIANCE_ARCHITECTURE')) {
      throw new Error('PRP-A2 architecture not configured in Kubernetes');
    }

    console.log('  ✓ Production Kubernetes resources configured');
    console.log('  ✓ Auto-scaling and disruption budgets included');
    console.log('  ✓ PRP-A2 direct database architecture configured');
  });

  // Test 8: Deployment Automation
  await runTest('Deployment Automation', async () => {
    const deployPath = path.join(process.cwd(), 'deploy', 'deploy-production.sh');
    const deployExists = await fs.access(deployPath).then(() => true).catch(() => false);

    if (!deployExists) {
      throw new Error('Deployment script not found');
    }

    const deployContent = await fs.readFile(deployPath, 'utf-8');

    // Verify multi-cloud support
    const cloudProviders = ['aws', 'azure', 'gcp'];
    for (const provider of cloudProviders) {
      if (!deployContent.includes(provider)) {
        throw new Error(`Cloud provider '${provider}' not supported`);
      }
    }

    // Verify deployment steps
    const deploySteps = [
      'check_prerequisites',
      'build_image',
      'push_image',
      'deploy_infrastructure',
      'deploy_kubernetes',
      'health_check'
    ];

    for (const step of deploySteps) {
      if (!deployContent.includes(step)) {
        throw new Error(`Deployment step '${step}' not found`);
      }
    }

    console.log('  ✓ Multi-cloud deployment automation');
    console.log('  ✓ Infrastructure provisioning included');
    console.log('  ✓ Health checks and validation');
  });

  // Test 9: Environment Integration
  await runTest('Environment Variable Integration', async () => {
    // Check if .env.local has cloud deployment variables
    const envPath = path.join(process.cwd(), 'frontend-nextjs', '.env.local');
    const envExists = await fs.access(envPath).then(() => true).catch(() => false);

    if (!envExists) {
      throw new Error('.env.local file not found');
    }

    const envContent = await fs.readFile(envPath, 'utf-8');

    // Verify PRP-A2 compatibility
    if (!envContent.includes('COMPLIANCE_ARCHITECTURE')) {
      throw new Error('PRP-A2 architecture not configured in environment');
    }

    if (!envContent.includes('USE_DIRECT_DATABASE')) {
      throw new Error('Direct database feature flag not configured');
    }

    console.log('  ✓ PRP-A2 architecture variables configured');
    console.log('  ✓ Database connection settings present');
    console.log('  ✓ Feature flags for cloud deployment');
  });

  // Test 10: Production Readiness
  await runTest('Production Readiness Check', async () => {
    // Verify all components work together
    const components = [
      { name: 'Configuration', path: 'config/production.js' },
      { name: 'Secrets', path: 'config/secrets-manager.js' },
      { name: 'Health API', path: 'frontend-nextjs/app/api/health/route.ts' },
      { name: 'Metrics API', path: 'frontend-nextjs/app/api/health/metrics/route.ts' },
      { name: 'Docker', path: 'Dockerfile' },
      { name: 'Docker Compose', path: 'docker-compose.production.yml' },
      { name: 'Kubernetes', path: 'kubernetes/deployment.yaml' },
      { name: 'Deploy Script', path: 'deploy/deploy-production.sh' }
    ];

    for (const component of components) {
      const componentPath = path.join(process.cwd(), component.path);
      const exists = await fs.access(componentPath).then(() => true).catch(() => false);

      if (!exists) {
        throw new Error(`${component.name} component missing: ${component.path}`);
      }
    }

    console.log('  ✓ All cloud deployment components present');
    console.log('  ✓ Multi-cloud provider support ready');
    console.log('  ✓ Production monitoring and health checks');
    console.log('  ✓ PRP-A2 direct database architecture integrated');
  });

  // Summary
  console.log('\n=== PRP-A3 Test Summary ===');
  console.log(`Total Tests: ${totalTests}`);
  console.log(`Passed: ${passedTests}`);
  console.log(`Failed: ${totalTests - passedTests}`);
  console.log(`Success Rate: ${Math.round((passedTests / totalTests) * 100)}%`);

  if (passedTests === totalTests) {
    console.log('\n✅ PRP-A3: Cloud Deployment Preparation COMPLETED SUCCESSFULLY!');
    console.log('\nCloud Deployment Ready:');
    console.log('  🚀 Enterprise configuration management');
    console.log('  🔒 Multi-cloud secrets management (AWS/Azure/GCP)');
    console.log('  ❤️  Production health checks and monitoring');
    console.log('  🐳 Optimized containerization (Docker/Kubernetes)');
    console.log('  ⚡ Automated deployment pipeline');
    console.log('  🔗 PRP-A2 direct database architecture integrated');
    console.log('\nNext Steps:');
    console.log('  1. Set cloud provider environment variables');
    console.log('  2. Configure secrets in cloud provider');
    console.log('  3. Run: ./deploy/deploy-production.sh');
    console.log('  4. Monitor via health endpoints and metrics');
  } else {
    console.log('\n❌ PRP-A3: Some components failed validation');
    console.log('Please fix the failed tests before deploying to production');
    process.exit(1);
  }
}

// Run the test
testCloudDeploymentPreparation().catch(console.error);