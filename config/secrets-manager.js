/**
 * PRP-A3: Enterprise Secrets Management
 * Multi-cloud secrets integration with fallback hierarchy
 *
 * Supports AWS Secrets Manager, Azure Key Vault, GCP Secret Manager
 */

const crypto = require('crypto');

class SecretsManager {
  constructor(options = {}) {
    this.provider = options.provider || process.env.CLOUD_PROVIDER || 'aws';
    this.region = options.region || process.env.AWS_REGION || 'ap-southeast-2';
    this.cache = new Map();
    this.cacheEnabled = options.cache !== false;
    this.cacheTTL = options.cacheTTL || 300000; // 5 minutes

    console.log(`[PRP-A3] Secrets Manager initialized - Provider: ${this.provider}`);
  }

  /**
   * Get secret with multi-cloud fallback
   */
  async getSecret(secretName, options = {}) {
    const cacheKey = `${this.provider}:${secretName}`;

    // Check cache first
    if (this.cacheEnabled && this.cache.has(cacheKey)) {
      const cached = this.cache.get(cacheKey);
      if (Date.now() - cached.timestamp < this.cacheTTL) {
        console.log(`[PRP-A3] Secret cache hit: ${secretName}`);
        return cached.value;
      }
      this.cache.delete(cacheKey);
    }

    try {
      let secret;

      switch (this.provider) {
        case 'aws':
          secret = await this.getAWSSecret(secretName, options);
          break;
        case 'azure':
          secret = await this.getAzureSecret(secretName, options);
          break;
        case 'gcp':
          secret = await this.getGCPSecret(secretName, options);
          break;
        default:
          // Fallback to environment variables
          secret = this.getEnvironmentSecret(secretName, options);
      }

      // Cache the secret
      if (this.cacheEnabled && secret) {
        this.cache.set(cacheKey, {
          value: secret,
          timestamp: Date.now()
        });
      }

      return secret;

    } catch (error) {
      console.warn(`[PRP-A3] Failed to get secret from ${this.provider}: ${error.message}`);

      // Fallback to environment variables
      console.log(`[PRP-A3] Falling back to environment variables for: ${secretName}`);
      return this.getEnvironmentSecret(secretName, options);
    }
  }

  /**
   * AWS Secrets Manager integration
   */
  async getAWSSecret(secretName, options = {}) {
    try {
      // AWS SDK v3
      const { SecretsManagerClient, GetSecretValueCommand } = require('@aws-sdk/client-secrets-manager');

      const client = new SecretsManagerClient({
        region: this.region,
        credentials: {
          accessKeyId: process.env.AWS_ACCESS_KEY_ID,
          secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY
        }
      });

      const command = new GetSecretValueCommand({
        SecretId: secretName,
        VersionStage: options.version || 'AWSCURRENT'
      });

      const response = await client.send(command);

      if (response.SecretString) {
        try {
          // Try to parse as JSON first
          const parsed = JSON.parse(response.SecretString);
          return options.key ? parsed[options.key] : parsed;
        } catch {
          // Return as string if not JSON
          return response.SecretString;
        }
      }

      throw new Error('Secret value not found');

    } catch (error) {
      if (error.name === 'ResourceNotFoundException') {
        throw new Error(`Secret not found: ${secretName}`);
      }
      throw error;
    }
  }

  /**
   * Azure Key Vault integration
   */
  async getAzureSecret(secretName, options = {}) {
    try {
      const { SecretClient } = require('@azure/keyvault-secrets');
      const { DefaultAzureCredential } = require('@azure/identity');

      const vaultUrl = process.env.AZURE_KEY_VAULT_URL ||
                      `https://${process.env.AZURE_KEY_VAULT_NAME}.vault.azure.net/`;

      const credential = new DefaultAzureCredential();
      const client = new SecretClient(vaultUrl, credential);

      const secret = await client.getSecret(secretName, {
        version: options.version
      });

      if (secret.value) {
        try {
          // Try to parse as JSON
          const parsed = JSON.parse(secret.value);
          return options.key ? parsed[options.key] : parsed;
        } catch {
          // Return as string if not JSON
          return secret.value;
        }
      }

      throw new Error('Secret value not found');

    } catch (error) {
      if (error.statusCode === 404) {
        throw new Error(`Secret not found: ${secretName}`);
      }
      throw error;
    }
  }

  /**
   * Google Cloud Secret Manager integration
   */
  async getGCPSecret(secretName, options = {}) {
    try {
      const { SecretManagerServiceClient } = require('@google-cloud/secret-manager');

      const client = new SecretManagerServiceClient({
        projectId: process.env.GOOGLE_CLOUD_PROJECT_ID,
        keyFilename: process.env.GOOGLE_CLOUD_KEY_FILE
      });

      const projectId = process.env.GOOGLE_CLOUD_PROJECT_ID;
      const version = options.version || 'latest';
      const name = `projects/${projectId}/secrets/${secretName}/versions/${version}`;

      const [response] = await client.accessSecretVersion({ name });
      const secretValue = response.payload.data.toString();

      if (secretValue) {
        try {
          // Try to parse as JSON
          const parsed = JSON.parse(secretValue);
          return options.key ? parsed[options.key] : parsed;
        } catch {
          // Return as string if not JSON
          return secretValue;
        }
      }

      throw new Error('Secret value not found');

    } catch (error) {
      if (error.code === 5) { // NOT_FOUND
        throw new Error(`Secret not found: ${secretName}`);
      }
      throw error;
    }
  }

  /**
   * Environment variable fallback
   */
  getEnvironmentSecret(secretName, options = {}) {
    // Try multiple environment variable formats
    const envFormats = [
      secretName,
      secretName.toUpperCase(),
      secretName.toUpperCase().replace(/-/g, '_'),
      secretName.toUpperCase().replace(/\./g, '_')
    ];

    for (const envName of envFormats) {
      const value = process.env[envName];
      if (value) {
        console.log(`[PRP-A3] Using environment variable: ${envName}`);

        try {
          // Try to parse as JSON
          const parsed = JSON.parse(value);
          return options.key ? parsed[options.key] : parsed;
        } catch {
          // Return as string if not JSON
          return value;
        }
      }
    }

    if (options.required !== false) {
      throw new Error(`Secret not found in any provider or environment: ${secretName}`);
    }

    return options.default || null;
  }

  /**
   * Database credentials with automatic rotation support
   */
  async getDatabaseCredentials() {
    try {
      // Try to get from secrets manager first
      const dbSecrets = await this.getSecret('database-credentials', {
        required: false
      });

      if (dbSecrets) {
        return {
          host: dbSecrets.host || process.env.DB_HOST,
          port: dbSecrets.port || process.env.DB_PORT,
          database: dbSecrets.database || process.env.DB_NAME,
          username: dbSecrets.username || process.env.DB_USER,
          password: dbSecrets.password || process.env.DB_PASSWORD,
          ssl: dbSecrets.ssl || (process.env.NODE_ENV === 'production')
        };
      }

      // Fallback to environment variables
      return {
        host: process.env.DB_HOST || 'localhost',
        port: parseInt(process.env.DB_PORT || '5432'),
        database: process.env.DB_NAME || 'nsw_planning',
        username: process.env.DB_USER || 'postgres',
        password: process.env.DB_PASSWORD || '',
        ssl: process.env.NODE_ENV === 'production'
      };

    } catch (error) {
      console.error('[PRP-A3] Failed to get database credentials:', error.message);
      throw new Error('Database credentials not available');
    }
  }

  /**
   * API keys with rotation support
   */
  async getAPIKeys() {
    const keys = {};

    // Get all API keys in parallel
    const secretPromises = [
      this.getSecret('google-maps-api-key', { required: false }),
      this.getSecret('openai-api-key', { required: false }),
      this.getSecret('deepseek-api-key', { required: false }),
      this.getSecret('gemini-api-key', { required: false }),
      this.getSecret('nsw-planning-api-key', { required: false })
    ];

    try {
      const [googleMaps, openai, deepseek, gemini, nswPlanning] = await Promise.all(secretPromises);

      keys.googleMaps = googleMaps || process.env.GOOGLE_MAPS_API_KEY;
      keys.googlePlaces = googleMaps || process.env.GOOGLE_PLACES_API_KEY;
      keys.openai = openai || process.env.OPENAI_API_KEY;
      keys.deepseek = deepseek || process.env.DEEPSEEK_API_KEY;
      keys.gemini = gemini || process.env.GEMINI_API_KEY;
      keys.nswPlanning = nswPlanning || process.env.NSW_PLANNING_API_KEY;

      return keys;

    } catch (error) {
      console.warn('[PRP-A3] Some API keys failed to load:', error.message);

      // Return environment fallbacks
      return {
        googleMaps: process.env.GOOGLE_MAPS_API_KEY,
        googlePlaces: process.env.GOOGLE_PLACES_API_KEY,
        openai: process.env.OPENAI_API_KEY,
        deepseek: process.env.DEEPSEEK_API_KEY,
        gemini: process.env.GEMINI_API_KEY,
        nswPlanning: process.env.NSW_PLANNING_API_KEY
      };
    }
  }

  /**
   * JWT secrets with automatic rotation
   */
  async getJWTSecrets() {
    try {
      const jwtSecrets = await this.getSecret('jwt-secrets', { required: false });

      if (jwtSecrets) {
        return {
          secret: jwtSecrets.secret,
          refreshSecret: jwtSecrets.refreshSecret,
          algorithm: jwtSecrets.algorithm || 'HS256',
          expiresIn: jwtSecrets.expiresIn || '24h',
          refreshExpiresIn: jwtSecrets.refreshExpiresIn || '7d'
        };
      }

      // Generate secure fallback if not in secrets manager
      const secret = process.env.JWT_SECRET || this.generateSecureKey();
      const refreshSecret = process.env.JWT_REFRESH_SECRET || this.generateSecureKey();

      return {
        secret,
        refreshSecret,
        algorithm: process.env.JWT_ALGORITHM || 'HS256',
        expiresIn: process.env.JWT_EXPIRES_IN || '24h',
        refreshExpiresIn: process.env.JWT_REFRESH_EXPIRES_IN || '7d'
      };

    } catch (error) {
      console.error('[PRP-A3] Failed to get JWT secrets:', error.message);
      throw new Error('JWT secrets not available');
    }
  }

  /**
   * Generate secure random key
   */
  generateSecureKey(length = 64) {
    return crypto.randomBytes(length).toString('hex');
  }

  /**
   * Clear secrets cache
   */
  clearCache() {
    this.cache.clear();
    console.log('[PRP-A3] Secrets cache cleared');
  }

  /**
   * Health check for secrets providers
   */
  async healthCheck() {
    const checks = {
      provider: this.provider,
      cache: {
        enabled: this.cacheEnabled,
        size: this.cache.size
      },
      connectivity: {}
    };

    // Test connectivity to secrets provider
    try {
      switch (this.provider) {
        case 'aws':
          await this.testAWSConnectivity();
          checks.connectivity.aws = { status: 'healthy' };
          break;
        case 'azure':
          await this.testAzureConnectivity();
          checks.connectivity.azure = { status: 'healthy' };
          break;
        case 'gcp':
          await this.testGCPConnectivity();
          checks.connectivity.gcp = { status: 'healthy' };
          break;
      }
    } catch (error) {
      checks.connectivity[this.provider] = {
        status: 'error',
        error: error.message
      };
    }

    // Test environment fallback
    checks.environment = {
      available: !!process.env.DB_PASSWORD || !!process.env.DATABASE_PASSWORD
    };

    return checks;
  }

  async testAWSConnectivity() {
    const { SecretsManagerClient, ListSecretsCommand } = require('@aws-sdk/client-secrets-manager');

    const client = new SecretsManagerClient({
      region: this.region,
      credentials: {
        accessKeyId: process.env.AWS_ACCESS_KEY_ID,
        secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY
      }
    });

    await client.send(new ListSecretsCommand({ MaxResults: 1 }));
  }

  async testAzureConnectivity() {
    const { SecretClient } = require('@azure/keyvault-secrets');
    const { DefaultAzureCredential } = require('@azure/identity');

    const vaultUrl = process.env.AZURE_KEY_VAULT_URL ||
                    `https://${process.env.AZURE_KEY_VAULT_NAME}.vault.azure.net/`;

    const credential = new DefaultAzureCredential();
    const client = new SecretClient(vaultUrl, credential);

    // Try to list secrets (will fail if no access, but that's expected)
    try {
      const iterator = client.listPropertiesOfSecrets();
      await iterator.next();
    } catch (error) {
      // Expected if no list permissions, but client is connected
      if (error.statusCode !== 403) {
        throw error;
      }
    }
  }

  async testGCPConnectivity() {
    const { SecretManagerServiceClient } = require('@google-cloud/secret-manager');

    const client = new SecretManagerServiceClient({
      projectId: process.env.GOOGLE_CLOUD_PROJECT_ID,
      keyFilename: process.env.GOOGLE_CLOUD_KEY_FILE
    });

    const projectId = process.env.GOOGLE_CLOUD_PROJECT_ID;
    await client.listSecrets({
      parent: `projects/${projectId}`,
      pageSize: 1
    });
  }
}

module.exports = { SecretsManager };