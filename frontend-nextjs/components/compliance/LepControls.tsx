import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { LandUseZoningCard } from './LandUseZoningCard';

import { LocalProvisionsCard } from './LocalProvisionsCard';
import { HeritageProvisionsCard } from './HeritageProvisionsCard';
import { PlanningConstraints, PlanningLayer } from '@/lib/nsw-planning-portal';

interface LepControlsProps {
  propertyData?: any; // Keep for now - full PropertyData type would require extensive refactoring
  planningLayers: PlanningLayer[];
  constraints: PlanningConstraints;
}

export function LepControls({
  planningLayers,
  constraints
}: LepControlsProps) {
  const lepName = constraints?.lga 
    ? `${constraints.lga} Local Environmental Plan 2022` 
    : 'Local Environmental Plan';

  // Extract layer metadata for child cards
  const landZoningLayer = planningLayers?.find(
    (layer) => layer.layerName === 'Land Zoning Map'
  );
  const zoneResult = landZoningLayer?.results?.[0];

  return (
    <div className="space-y-6">
      <Card className="border-amber-200 bg-amber-50/30">
        <CardHeader>
          <CardTitle className="text-lg text-amber-900">
            Local Environmental Plan
          </CardTitle>
          <Badge className="bg-amber-100 text-amber-800 mt-2">
            {lepName}
          </Badge>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            The LEP sets the framework for how land can be used and developed in the {constraints?.lga || 'local'} area.
          </p>
        </CardContent>
      </Card>

      {/* Land Use Zoning Card */}
      {constraints?.zone && (
        <LandUseZoningCard
          zone={constraints.zone}
          zoneDescription={constraints.zoneDescription}
          lga={constraints.lga}
          legislationUrl={zoneResult?.['legislationUrl']}
          epiName={zoneResult?.['EPI Name']}
          amendment={zoneResult?.['Amendment']}
          legislativeClause={zoneResult?.['Legislative Clause']}
        />
      )}

      {/* Local Provisions Card */}
      {constraints?.localProvisions && constraints.localProvisions.length > 0 && (
        <LocalProvisionsCard
          localProvisions={constraints.localProvisions}
        />
      )}

      {/* Heritage Provisions Card */}
      {constraints?.heritage && (
        <HeritageProvisionsCard
          heritage={constraints.heritage}
          heritageType={constraints.heritageType}
          heritageItemName={constraints.heritageItemName}
          heritageItemNumber={constraints.heritageItemNumber}
          heritageLegislativeClause={constraints.heritageLegislativeClause}
          heritageSignificance={constraints.heritageSignificance}
          heritageLegislationUrl={constraints.heritageLegislationUrl}
        />
      )}
    </div>
  );
}
