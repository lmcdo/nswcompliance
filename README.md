# NSW Planning Compliance Engine

An engineering codebase for processing NSW planning and regulatory information into structured, source-linked data and application responses.

This repository contains substantial development work across regulatory document processing, deterministic controls, AI-assisted extraction, geospatial analysis, APIs, database migrations, and automated QA. It is not a legal-advice system and does not establish that a development is compliant.

## Features

### Enhanced Semantic Processing
- **Dual Semantic Pipeline**: Combines LangExtract + AutoSchemaKG for complex rule understanding
- **Conditional Logic Support**: Handles rules like "0.9m minimum OR 0.5 times building height, whichever is greater"
- **Source Text Grounding**: Carries source and page context into selected extracted results
- **Three-Tier Classification**: Mandatory, Recommended, and Informational rule enforcement levels

### API Integration
- **Enhanced Compliance API**: `/api/compliance/check` with semantic rule processing
- **Setbacks API**: `/api/compliance/setbacks` with fallback mechanisms
- **Property Data API**: NSW Planning Portal integration for official constraints
- **Performance Caching**: Intelligent caching for repeated queries

### Frontend Interface
- **Above-the-fold Design**: Compact, professional interface
- **Source Citation Display**: Shows regulatory text with highlighting
- **Processing Method Indicators**: Visual badges for Semantic/Manual/Fallback
- **Confidence and review states**: Selected surfaces distinguish automated results from review-required states
- **Responsive Design**: Works on mobile, tablet, and desktop

## Architecture

```
compliance-engine/
├── app/
│ ├── api/compliance/ # Enhanced APIs with semantic processing
│ ├── property/enhanced/ # Advanced frontend with source citations
│ └── globals.css # Enhanced styling
├── lib/
│ ├── enhanced-compliance-engine.ts # Core semantic compliance logic
│ ├── semantic-compliance-bridge.ts # Bridge between semantic and API layers
│ ├── enhanced-setback-processor.ts # Semantic rule processor
│ └── property-data.ts # NSW Planning Portal integration
├── examples/regulatory-engine/
│ ├── dual_semantic_processor.py # Main semantic processing engine
│ ├── langextract_config.py # LangExtract configuration
│ └── compare_extraction_methods.py # Regex vs Semantic comparison
└── public/regulatory-data/ # Processed DCP data and caches
```

## Quick Start

### Development Setup

```bash
# Clone the repository
git clone https://github.com/lmcdo/nswcompliance.git
cd nswcompliance

# Install Node.js dependencies
npm install

# Set up Python virtual environment
python -m venv venv_linux
source venv_linux/bin/activate # Linux/Mac
# or venv_linux\Scripts\activate # Windows

# Install Python dependencies
pip install -r requirements.txt

# Set up environment variables from a reviewed placeholder template
cp .env.example .env.local
# Add credentials only to the local file; never commit it

# Start the development server
npm run dev
```

### Database Configuration

**PostgreSQL Connection Parameters:**
- Host: `localhost`
- Port: `5432` (standard PostgreSQL port)
- Database: `nsw_planning`
- User: `postgres`
- Password: `postgres`

Test your database connection:
```bash
python db_config.py
```

### Usage

1. **Standard Compliance Check**: Visit `/property` for basic compliance checking
2. **Enhanced Compliance Check**: Visit `/property/enhanced` for semantic processing with source citations

### API Endpoints

```bash
# Get enhanced setback rules
curl "http://localhost:3000/api/compliance/setbacks?address=123%20Main%20St%20Ashfield%202131&semantic=true"

# Check development compliance
curl -X POST "http://localhost:3000/api/compliance/check" \
 -H "Content-Type: application/json" \
 -d '{
 "propertyData": {...},
 "proposal": {...},
 "formerCouncilArea": "Ashfield",
 "useSemanticRules": true
 }'
```

## Technical Details

### Semantic Processing Pipeline

1. **LangExtract**: Precise source text grounding with regulatory citations
2. **AutoSchemaKG**: Knowledge graph construction for complex relationships
3. **Three-Tier Classification**: Automatic enforcement level detection
4. **Bridge Layer**: Converts semantic outputs to compliance rule format

### Supported Areas

- **Ashfield**: Former Ashfield Council area
- **Leichhardt**: Former Leichhardt Council area 
- **Marrickville**: Former Marrickville Council area

### Rule Types

- **LEP Rules**: Height and FSR from NSW Planning Portal (HIGH confidence)
- **DCP Setbacks**: Semantic extraction from council documents (MEDIUM confidence)
- **Complex Conditions**: Conditional logic like "minimum OR calculated, whichever is greater"

## Limitations

- Regulatory content changes and must be checked against current authoritative sources.
- Extracted or classified content can be incomplete or wrong.
- External planning, property, spatial, and document sources vary in availability and quality.
- The software does not replace advice from a qualified planning, legal, building, surveying, or other relevant professional.
- Performance, accuracy, coverage, customer, and production-deployment claims are intentionally not stated without reproducible evidence.

## Testing

```bash
# Run Python tests
pytest examples/regulatory-engine/

# Run comparison analysis
python examples/regulatory-engine/compare_extraction_methods.py

# Test API endpoints
npm run test # (if test suite exists)
```

## Deployment

The system is designed for production deployment with:

- **Caching Strategy**: Pre-processed rules cached in `public/regulatory-data/`
- **Fallback Mechanisms**: Graceful degradation from semantic to basic processing
- **Error Handling**: Comprehensive error catching with user-friendly messages
- **Performance Monitoring**: Processing time tracking and confidence scoring

## Documentation

- **Integration Plan**: See `AUTOSCHEMAKG_INTEGRATION_PLAN.md`
- **API Documentation**: Swagger/OpenAPI specs available at `/api/docs`
- **Processing Comparison**: See `public/regulatory-data/extraction_method_comparison.json`

## Contributing

This project uses Context Engineering principles with Claude Code:

1. Review `CLAUDE.md` for development guidelines
2. Add examples to `examples/` folder for new patterns
3. Follow the three-tier rule classification system
4. Ensure all regulatory extractions include source grounding

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and feature requests:
- GitHub Issues: https://github.com/lmcdo/nswcompliance/issues
- Documentation: See `/docs` folder for detailed guides

---

This repository is being prepared for public release. See [SECURITY.md](SECURITY.md) for the current publication boundary.
