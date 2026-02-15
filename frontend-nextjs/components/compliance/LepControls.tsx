import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { LandUseZoningCard } from './LandUseZoningCard';
import { LocalProvisionsCard } from './LocalProvisionsCard';
import { HeritageProvisionsCard } from './HeritageProvisionsCard';
import { NotApplicableCard } from './NotApplicableCard';
import { PlanningConstraints, PlanningLayer } from '@/lib/nsw-planning-portal';
import { AuthorityColors } from '@/lib/design-tokens';

interface LepControlsProps {
  propertyData?: any; // Keep for now - full PropertyData type would require extensive refactoring
  planningLayers: PlanningLayer[];
  constraints: PlanningConstraints;
  formerCouncil?: string;
}

export function LepControls({
  planningLayers,
  constraints,
  formerCouncil
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
      <Card className="border-blue-200 bg-blue-50/30">
        <CardHeader>
          <CardTitle className="text-lg text-blue-900">
            Local Environmental Plan
          </CardTitle>
          <Badge className="bg-blue-100 text-blue-800 mt-2">
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
      {constraints?.localProvisions && constraints.localProvisions.length > 0 ? (
        <LocalProvisionsCard
          localProvisions={constraints.localProvisions}
        />
      ) : (
        <NotApplicableCard
          title="Additional Local Provisions"
          reason="No site-specific local provisions (LEP Part 6) or key site controls apply to this address."
          color="blue"
        />
      )}

      {/* Heritage Provisions Card */}
      {constraints?.heritage ? (
        <HeritageProvisionsCard
          heritage={constraints.heritage}
          heritageType={constraints.heritageType}
          heritageItemName={constraints.heritageItemName}
          heritageItemNumber={constraints.heritageItemNumber}
          heritageLegislativeClause={constraints.heritageLegislativeClause}
          heritageSignificance={constraints.heritageSignificance}
          heritageLegislationUrl={constraints.heritageLegislationUrl}
          formerCouncil={formerCouncil}
        />
      ) : (
        <NotApplicableCard
          title="Heritage Conservation"
          reason="This property is not in a Heritage Conservation Area and is not listed as a heritage item."
          color="blue"
        />
      )}
    </div>
  );
}
