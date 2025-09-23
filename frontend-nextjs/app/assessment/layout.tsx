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
