export interface DevelopmentType {
 id: string;
 code: string;
 name: string;
 description: string;
 category: 'residential' | 'commercial' | 'industrial' | 'mixed';
 complianceRequirements: string[];
 applicableZones: string[];
 minimumLotSize?: number;
 maximumHeight?: number;
 isEnabled: boolean;
}

export interface DevelopmentSelectorProps {
 selectedDevelopment?: DevelopmentType;
 onDevelopmentChange: (development: DevelopmentType | null) => void;
 propertyId?: string;
 zoning?: string;
 lotSize?: number;
 disabled?: boolean;
 variant?: 'default' | 'compact' | 'detailed';
 showDescription?: boolean;
 filterByZoning?: boolean;
}

export interface ValidationResult {
 isValid: boolean;
 warnings: string[];
 errors: string[];
}
