import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  Shield, 
  Building, 
  FileText, 
  AlertTriangle, 
  CheckCircle, 
  Clock,
  ChevronDown,
  ChevronUp
} from 'lucide-react';

// PRP-8B Tier Icons and Colors
const TIER_CONFIG = {
  1: {
    icon: Shield,
    color: 'bg-green-500',
    textColor: 'text-green-700',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200',
    name: 'Fully Authoritative',
    description: 'SEPP/LEP provisions with numeric values'
  },
  2: {
    icon: Building,
    color: 'bg-blue-500', 
    textColor: 'text-blue-700',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    name: 'High Authority',
    description: 'Clear DCP measurements'
  },
  3: {
    icon: FileText,
    color: 'bg-orange-500',
    textColor: 'text-orange-700', 
    bgColor: 'bg-orange-50',
    borderColor: 'border-orange-200',
    name: 'Moderate Authority',
    description: 'Qualitative provisions requiring interpretation'
  },
  4: {
    icon: Clock,
    color: 'bg-yellow-500',
    textColor: 'text-yellow-700',
    bgColor: 'bg-yellow-50', 
    borderColor: 'border-yellow-200',
    name: 'Framework Guidance',
    description: 'General guidance provisions'
  },
  5: {
    icon: AlertTriangle,
    color: 'bg-red-500',
    textColor: 'text-red-700',
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200',
    name: 'Specialist Required',
    description: 'Professional consultation required'
  }
};

interface Provision {
  id: number;
  document_type: string;
  document_name: string;
  clause_reference: string;
  provision_text: string;
  provision_type: string;
  numeric_value?: number;
  unit?: string;
  measurement_context?: string;
  boundary_type?: string;
  confidence_level: number;
  tier_level: number;
  tier_name: string;
  authority_level: number;
}

interface PrimaryAuthority {
  document_type: string;
  document_name: string;
  clause_reference: string; 
  authority_level: number;
  numeric_value?: number;
  unit?: string;
  confidence_level: number;
  tier_level: number;
  overrides_count: number;
}

interface AuthoritativeComplianceData {
  property: {
    property_id: number;
    zone_code: string;
    development_type?: string;
  };
  tier_1_provisions: Provision[];
  tier_2_provisions: Provision[];
  tier_3_provisions: Provision[];
  tier_4_provisions: Provision[];
  tier_5_provisions: Provision[];
  primary_authorities: Record<string, PrimaryAuthority>;
  complexity_assessment: string;
  confidence_level: number;
  legal_disclaimer: string;
  processing_metadata: {
    total_provisions_found: number;
    tier_distribution: Record<string, number>;
    processing_time: string;
    cache_hit: boolean;
  };
}

interface Props {
  zoneCode: string;
  developmentType?: string;
  address?: string;
  propertyId?: number;
  onDataLoaded?: (data: AuthoritativeComplianceData) => void;
}

export default function AuthoritativeComplianceDisplay({ 
  zoneCode, 
  developmentType,
  address,
  propertyId,
  onDataLoaded 
}: Props) {
  const [data, setData] = useState<AuthoritativeComplianceData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedTiers, setExpandedTiers] = useState<Set<number>>(new Set([1, 2]));
  const [expandedProvisions, setExpandedProvisions] = useState<Set<number>>(new Set());

  const lookupPropertyId = async (address: string): Promise<number> => {
    const response = await fetch(`/api/property?address=${encodeURIComponent(address)}`);
    if (!response.ok) {
      throw new Error('Failed to lookup property');
    }
    const data = await response.json();
    return data.propId;
  };

  const fetchComplianceData = async () => {
    setLoading(true);
    setError(null);

    try {
      let resolvedPropertyId = propertyId;
      
      // If we have an address but no property ID, look it up
      if (address && !propertyId) {
        try {
          resolvedPropertyId = await lookupPropertyId(address);
        } catch (lookupError) {
          console.warn('[AuthoritativeCompliance] Property lookup failed, using default ID 1:', lookupError);
          resolvedPropertyId = 1;
        }
      }

      const payload = {
        zone_code: zoneCode,
        property_id: resolvedPropertyId || 1,
        development_type: developmentType
      };

      console.log('[AuthoritativeCompliance] Fetching:', payload);

      const response = await fetch('/api/authoritative/compliance-check', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `API error: ${response.status}`);
      }

      const result = await response.json();
      console.log('[AuthoritativeCompliance] Response:', result);
      
      setData(result);
      onDataLoaded?.(result);

    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(message);
      console.error('[AuthoritativeCompliance] Error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (zoneCode) {
      fetchComplianceData();
    }
  }, [zoneCode, developmentType, address, propertyId]);

  const toggleTier = (tier: number) => {
    const newExpanded = new Set(expandedTiers);
    if (newExpanded.has(tier)) {
      newExpanded.delete(tier);
    } else {
      newExpanded.add(tier);
    }
    setExpandedTiers(newExpanded);
  };

  const toggleProvision = (provisionId: number) => {
    const newExpanded = new Set(expandedProvisions);
    if (newExpanded.has(provisionId)) {
      newExpanded.delete(provisionId);
    } else {
      newExpanded.add(provisionId);
    }
    setExpandedProvisions(newExpanded);
  };

  const getComplexityIcon = (complexity: string) => {
    if (complexity.includes('low')) return <CheckCircle className="w-4 h-4 text-green-500" />;
    if (complexity.includes('high') || complexity.includes('specialist')) return <AlertTriangle className="w-4 h-4 text-red-500" />;
    return <Clock className="w-4 h-4 text-orange-500" />;
  };

  const formatProvisionText = (text: string, maxLength: number = 150) => {
    return text.length > maxLength ? `${text.substring(0, maxLength)}...` : text;
  };

  const renderProvision = (provision: Provision) => {
    const isExpanded = expandedProvisions.has(provision.id);
    const tierConfig = TIER_CONFIG[provision.tier_level as keyof typeof TIER_CONFIG];

    return (
      <div key={provision.id} className={`border rounded-lg p-3 ${tierConfig.borderColor} ${tierConfig.bgColor}`}>
        {/* Provision Header */}
        <div className="flex items-start justify-between mb-2">
          <div className="flex items-start gap-2">
            <Badge variant="secondary" className={`${tierConfig.color} text-white text-xs`}>
              {provision.document_type}
            </Badge>
            <div className="text-sm">
              <span className="font-medium">{provision.clause_reference}</span>
              {provision.numeric_value && (
                <span className="ml-2 font-bold text-lg">
                  {provision.numeric_value}{provision.unit}
                </span>
              )}
            </div>
          </div>
          
          <div className="flex items-center gap-1">
            <span className="text-xs text-gray-500">
              {(provision.confidence_level * 100).toFixed(0)}%
            </span>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => toggleProvision(provision.id)}
              className="p-1 h-auto"
            >
              {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </Button>
          </div>
        </div>

        {/* Provision Content */}
        <div className="text-sm text-gray-700 mb-2">
          {isExpanded ? provision.provision_text : formatProvisionText(provision.provision_text)}
        </div>

        {/* Provision Metadata */}
        {isExpanded && (
          <div className="grid grid-cols-2 gap-2 text-xs text-gray-500 pt-2 border-t border-gray-200">
            <div>Type: {provision.provision_type}</div>
            <div>Context: {provision.measurement_context || 'General'}</div>
            {provision.boundary_type && <div>Boundary: {provision.boundary_type}</div>}
            <div>Authority Level: {provision.authority_level}</div>
          </div>
        )}
      </div>
    );
  };

  const renderTier = (tierLevel: number, provisions: Provision[]) => {
    const tierConfig = TIER_CONFIG[tierLevel as keyof typeof TIER_CONFIG];
    const TierIcon = tierConfig.icon;
    const isExpanded = expandedTiers.has(tierLevel);

    if (provisions.length === 0) return null;

    return (
      <Card key={tierLevel} className={`${tierConfig.borderColor} border-2`}>
        <CardHeader 
          className={`${tierConfig.bgColor} cursor-pointer`}
          onClick={() => toggleTier(tierLevel)}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`p-2 rounded-full ${tierConfig.color}`}>
                <TierIcon className="w-4 h-4 text-white" />
              </div>
              <div>
                <CardTitle className={`text-lg ${tierConfig.textColor}`}>
                  Tier {tierLevel}: {tierConfig.name}
                </CardTitle>
                <p className="text-sm text-gray-600 mt-1">
                  {tierConfig.description} • {provisions.length} provisions
                </p>
              </div>
            </div>
            {isExpanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
          </div>
        </CardHeader>
        
        {isExpanded && (
          <CardContent className="pt-4">
            <div className="space-y-3">
              {provisions.map(renderProvision)}
            </div>
          </CardContent>
        )}
      </Card>
    );
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
            <span className="ml-2">Loading authoritative compliance assessment...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="p-6">
          <Alert>
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              Error loading compliance data: {error}
              <Button 
                onClick={fetchComplianceData}
                variant="outline" 
                size="sm" 
                className="ml-4"
              >
                Retry
              </Button>
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  if (!data) {
    return null;
  }

  const totalProvisions = data.processing_metadata.total_provisions_found;

  return (
    <div className="space-y-6">
      {/* Header Summary */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-blue-500" />
            Authoritative Compliance Assessment
          </CardTitle>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">{totalProvisions}</div>
              <div className="text-sm text-gray-500">Total Provisions</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">{Object.keys(data.primary_authorities).length}</div>
              <div className="text-sm text-gray-500">Primary Controls</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-orange-600">{Math.round(data.confidence_level * 100)}%</div>
              <div className="text-sm text-gray-500">Confidence</div>
            </div>
            <div className="text-center flex items-center justify-center">
              {getComplexityIcon(data.complexity_assessment)}
              <div className="text-sm text-gray-500 ml-1">
                {data.complexity_assessment.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
              </div>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Primary Authorities */}
      {Object.keys(data.primary_authorities).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Primary Authorities</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4">
              {Object.entries(data.primary_authorities).map(([context, authority]) => (
                <div key={context} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div>
                    <div className="font-medium capitalize">{context.replace('_', ' ')}</div>
                    <div className="text-sm text-gray-600">
                      {authority.document_type} - {authority.clause_reference}
                      {authority.overrides_count > 0 && (
                        <span className="ml-2 text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">
                          Overrides {authority.overrides_count}
                        </span>
                      )}
                    </div>
                  </div>
                  {authority.numeric_value && (
                    <div className="text-right">
                      <div className="text-lg font-bold">{authority.numeric_value}{authority.unit}</div>
                      <div className="text-xs text-gray-500">{Math.round(authority.confidence_level * 100)}% confidence</div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Tier-by-Tier Provisions */}
      <div className="space-y-4">
        {renderTier(1, data.tier_1_provisions)}
        {renderTier(2, data.tier_2_provisions)}
        {renderTier(3, data.tier_3_provisions)}
        {renderTier(4, data.tier_4_provisions)}
        {renderTier(5, data.tier_5_provisions)}
      </div>

      {/* Legal Disclaimer */}
      <Alert>
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription className="text-sm">
          <strong>Legal Disclaimer:</strong> {data.legal_disclaimer}
        </AlertDescription>
      </Alert>

      {/* Processing Metadata */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Processing Information</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-gray-500">Cache Hit:</span>
              <span className={`ml-2 ${data.processing_metadata.cache_hit ? 'text-green-600' : 'text-orange-600'}`}>
                {data.processing_metadata.cache_hit ? 'Yes' : 'No'}
              </span>
            </div>
            <div>
              <span className="text-gray-500">Zone:</span>
              <span className="ml-2 font-medium">{data.property.zone_code}</span>
            </div>
            <div>
              <span className="text-gray-500">Dev Type:</span>
              <span className="ml-2">{data.property.development_type || 'General'}</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}