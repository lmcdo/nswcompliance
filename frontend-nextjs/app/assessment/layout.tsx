import 'maplibre-gl/dist/maplibre-gl.css';
// ^ must be imported in a server component to avoid dynamic chunk 404 (see AerialTile.tsx)
import React from 'react';

export default function AssessmentLayout({
 children,
}: {
 children: React.ReactNode;
}) {
 return (
 <div className="assessment-layout">
 {children}
 </div>
 );
}
