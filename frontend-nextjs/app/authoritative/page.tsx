'use client';

import React, { useState } from 'react';
import AuthoritativeComplianceDisplay from '@/components/compliance/AuthoritativeComplianceDisplay';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

export default function AuthoritativePage() {
  const [zoneCode, setZoneCode] = useState('R2');
  const [developmentType, setDevelopmentType] = useState('dwelling_house');
  const [address, setAddress] = useState('15 Norton St Leichhardt');
  const [propertyId, setPropertyId] = useState<number | null>(null);
  const [showResults, setShowResults] = useState(false);

  const handleAnalyze = () => {
    setShowResults(true);
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="text-center mb-8">
        <h1 className="text-4xl font-bold text-gray-900 mb-2">
          PRP-8B Authoritative Compliance System
        </h1>
        <p className="text-xl text-gray-600">
          5-Tier Hierarchy Resolution with SEPP → LEP → DCP Authority Precedence
        </p>
      </div>

      {/* Input Form */}
      <Card>
        <CardHeader>
          <CardTitle>Property Analysis Input</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <Label htmlFor="zoneCode">Zone Code</Label>
              <Select value={zoneCode} onValueChange={setZoneCode}>
                <SelectTrigger>
                  <SelectValue placeholder="Select zone" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="R1">R1 - General Residential</SelectItem>
                  <SelectItem value="R2">R2 - Low Density Residential</SelectItem>
                  <SelectItem value="R3">R3 - Medium Density Residential</SelectItem>
                  <SelectItem value="R4">R4 - High Density Residential</SelectItem>
                  <SelectItem value="B1">B1 - Neighbourhood Centre</SelectItem>
                  <SelectItem value="B2">B2 - Local Centre</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label htmlFor="developmentType">Development Type</Label>
              <Select value={developmentType} onValueChange={setDevelopmentType}>
                <SelectTrigger>
                  <SelectValue placeholder="Select development type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="dwelling_house">Single Dwelling House</SelectItem>
                  <SelectItem value="dual_occupancy">Dual Occupancy</SelectItem>
                  <SelectItem value="multi_dwelling_housing">Multi Dwelling Housing</SelectItem>
                  <SelectItem value="residential_flat_buildings">Residential Flat Buildings</SelectItem>
                  <SelectItem value="attached_dwelling">Attached Dwelling</SelectItem>
                  <SelectItem value="secondary_dwelling">Secondary Dwelling</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label htmlFor="address">Property Address</Label>
              <Input
                id="address"
                type="text"
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                placeholder="e.g. 15 Norton St Leichhardt"
              />
            </div>
          </div>

          <div className="mt-6 flex justify-center">
            <Button onClick={handleAnalyze} className="px-8 py-2">
              Analyze Authoritative Compliance
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Results */}
      {showResults && (
        <AuthoritativeComplianceDisplay
          zoneCode={zoneCode}
          developmentType={developmentType}
          address={address}
          propertyId={propertyId}
          onDataLoaded={(data) => {
            console.log('Authoritative compliance data loaded:', data);
          }}
        />
      )}

      {/* Feature Documentation */}
      <Card>
        <CardHeader>
          <CardTitle>PRP-8B Implementation Features</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h3 className="text-lg font-semibold mb-3">Authority Hierarchy</h3>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 bg-green-500 rounded"></div>
                  <span>Tier 1: SEPP/LEP Fully Authoritative</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 bg-blue-500 rounded"></div>
                  <span>Tier 2: DCP High Authority</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 bg-orange-500 rounded"></div>
                  <span>Tier 3: Moderate Authority</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 bg-yellow-500 rounded"></div>
                  <span>Tier 4: Framework Guidance</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 bg-red-500 rounded"></div>
                  <span>Tier 5: Specialist Required</span>
                </div>
              </div>
            </div>

            <div>
              <h3 className="text-lg font-semibold mb-3">System Capabilities</h3>
              <ul className="space-y-1 text-sm text-gray-600">
                <li>• SEPP > LEP > DCP precedence resolution</li>
                <li>• Primary authority identification by context</li>
                <li>• Confidence scoring and complexity assessment</li>
                <li>• Legal disclaimer generation by tier</li>
                <li>• Response caching for performance</li>
                <li>• Full text provision display</li>
                <li>• Authority override tracking</li>
                <li>• Professional guidance referrals</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}