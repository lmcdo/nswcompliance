#!/bin/bash
# Database Integration Template for PRPs
# This template should be used instead of hardcoded mock data

# API Endpoint Template with Database Integration
create_database_api_template() {
    local API_NAME="$1"
    local ENDPOINT_PATH="$2"
    local DATABASE_CLIENT="$3"
    local DATABASE_METHOD="$4"

    cat > "$FRONTEND_DIR/$ENDPOINT_PATH" << 'EOF'
import { NextApiRequest, NextApiResponse } from 'next';
import { ${DATABASE_CLIENT} } from '@/lib/database/${DATABASE_CLIENT}';

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const client = new ${DATABASE_CLIENT}();

    // Extract parameters from request
    const { zone, propertyId, category } = req.query;

    // Call database method with proper parameters
    const result = await client.${DATABASE_METHOD}(zone as string, propertyId as string);

    // Return database results
    res.status(200).json({
      success: true,
      data: result
    });

  } catch (error) {
    console.error('${API_NAME} API error:', error);
    res.status(500).json({
      error: 'Internal server error',
      message: process.env.NODE_ENV === 'development' ? error.message : 'Database query failed'
    });
  }
}
EOF
}

# Component Template with Database Integration
create_database_component_template() {
    local COMPONENT_NAME="$1"
    local API_ENDPOINT="$2"

    cat > "$FRONTEND_DIR/components/$COMPONENT_NAME.tsx" << 'EOF'
import { useState, useEffect } from 'react';

export const ${COMPONENT_NAME} = ({ zone, propertyId }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!zone) return;

    const fetchData = async () => {
      setLoading(true);
      try {
        const response = await fetch(`${API_ENDPOINT}?zone=${zone}&propertyId=${propertyId}`);
        if (!response.ok) throw new Error('Failed to fetch');
        const result = await response.json();
        setData(result.data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [zone, propertyId]);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;
  if (!data) return <div>No data available</div>;

  return (
    <div>
      {/* Render dynamic data from database */}
      {data.map(item => (
        <div key={item.id}>{item.name}</div>
      ))}
    </div>
  );
};
EOF
}

# Verification Rule Template
create_verification_rule() {
    cat >> "$PRP_DIR/verify_ui_migration.py" << 'EOF'

    def check_no_hardcoded_data(self, file_path: str) -> VerificationResult:
        """Check that files don't contain hardcoded mock data"""
        start_time = time.time()
        full_path = self.frontend_path / file_path

        if not full_path.exists():
            return VerificationResult(
                check_name=f"No Hardcoded Data: {file_path}",
                status=VerificationStatus.FAIL,
                message="File does not exist",
                execution_time=time.time() - start_time
            )

        try:
            content = full_path.read_text()

            # Check for hardcoded patterns
            hardcoded_patterns = [
                r'const\s+mock\w+\s*[:=]',
                r'const\s+\w*[Mm]ock\w*\s*[:=]',
                r'const\s+static\w+\s*[:=]',
                r'\[\s*{[^}]*id:\s*["\']',  # Array of objects with id
                r'generateMock\w*\(',
                r'mockData\s*[:=]'
            ]

            found_patterns = []
            for pattern in hardcoded_patterns:
                if re.search(pattern, content):
                    found_patterns.append(pattern)

            if not found_patterns:
                status = VerificationStatus.PASS
                message = "No hardcoded data found"
                fix_suggestion = None
            else:
                status = VerificationStatus.FAIL
                message = f"Found hardcoded data patterns: {', '.join(found_patterns)}"
                fix_suggestion = f"Replace hardcoded data in {file_path} with database API calls"

        except Exception as e:
            status = VerificationStatus.WARNING
            message = f"Could not check for hardcoded data: {str(e)}"
            fix_suggestion = "Check file permissions and encoding"

        return VerificationResult(
            check_name=f"No Hardcoded Data: {file_path}",
            status=status,
            message=message,
            fix_suggestion=fix_suggestion,
            execution_time=time.time() - start_time
        )
EOF
}