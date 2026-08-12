# NSW Planning Compliance Engine - Frontend

A Next.js 14 application providing precision planning compliance analysis with intelligent reasoning for NSW properties.

## Features

- **Precision Setback Calculator**: Centimeter-level accuracy using NSW Planning API geometry + database intelligence
- **Compliance Explanations**: WHY requirements exist using 514 "because" relationships
- **Heritage Intelligence**: Detailed analysis using 788 heritage controls + protection logic
- **Development Pathway Optimizer**: Strategic recommendations using structured pathway criteria
- **Real-time Property Analysis**: NSW Planning API integration with Google Places autocomplete

## Architecture

- **Frontend**: Next.js 14 with TypeScript and Tailwind CSS
- **Backend**: Next.js API Routes with TypeScript
- **Database**: PostgreSQL (Supabase) via `pg`, plus `@supabase/supabase-js` for Supabase-hosted tables
- **External APIs**: NSW Planning API, Google Places API
- **Deployment**: Vercel-ready configuration

## Installation

1. **Clone and navigate to the frontend directory:**
 ```bash
 cd frontend-nextjs
 ```

2. **Install dependencies:**
 ```bash
 npm install
 ```

3. **Set up environment variables:**
 ```bash
 cp .env.local.template .env.local
 # Edit .env.local with your API keys
 ```

4. **Verify database connection:**
 ```bash
 # Set DB_HOST / DB_PORT / DB_NAME / DB_USER / DB_PASSWORD in .env.local
 # to point at the Supabase PostgreSQL instance
 ```

## Development

### Start the development server:
```bash
npm run dev
```

### Run type checking:
```bash
npm run type-check
```

### Run tests:
```bash
npm test
```

### Build for production:
```bash
npm run build
npm start
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_PLACES_API_KEY` | Google Places API key for address autocomplete | Yes |
| `NSW_PLANNING_API_BASE_URL` | NSW Planning API base URL | No (has default) |
| `DB_HOST` / `DATABASE_HOST` | PostgreSQL host | No (defaults to `localhost`) |
| `DB_PORT` / `DATABASE_PORT` | PostgreSQL port | No (defaults to `5432`) |
| `DB_NAME` / `DATABASE_NAME` | PostgreSQL database name | No (defaults to `nsw_planning`) |
| `DB_USER` / `DATABASE_USER` | PostgreSQL user | No (defaults to `postgres`) |
| `DB_PASSWORD` / `DATABASE_PASSWORD` | PostgreSQL password | Yes, in any non-local environment |

## Testing

### API Health Checks:

1. **Database Connection:**
 ```bash
 curl http://localhost:3000/api/setbacks/calculate
 ```

2. **Property Lookup:**
 ```bash
 curl http://localhost:3000/api/property/15%20Norton%20Street%20Leichhardt%20NSW%202040
 ```

### Test Property Analysis:

Use these test addresses for development:
- `15 Norton Street, Leichhardt NSW 2040`
- `123 King Street, Sydney NSW 2000`
- `45 Smith Street, Marrickville NSW 2204`

## Database Integration

The application integrates with the NSW Planning compliance database containing:

- **9,364** regulatory provisions
- **4,526** development controls 
- **2,734** knowledge graph relationships
- **829** quantitative standards
- **788** heritage controls

### Key Database Queries:

```typescript
// Get setback controls for a zone
const setbacks = db.getSetbackControls('R2');

// Get knowledge graph relationships
const explanations = db.getKGRelationships('because', 'height');

// Get heritage protections
const protections = db.getHeritageProtections();
```

## API Endpoints

### Property Analysis
- `GET /api/property/[address]` - Analyze property and get planning data
- Query parameters: `lat`, `lng` (optional coordinates)

### Setback Calculations 
- `POST /api/setbacks/calculate` - Calculate precise setbacks
- `GET /api/setbacks/calculate` - Health check

### Compliance Explanations
- `POST /api/compliance/explain` - Get requirement explanations
- Uses "because" and "protect" relationships from database

### Heritage Analysis
- `POST /api/heritage/analyze` - Analyze heritage constraints
- Leverages 788 heritage controls with protection logic

### Development Pathways
- `POST /api/pathway/optimize` - Optimize development strategy
- Uses structured JSON pathway criteria

## Performance

- **API Response Times**: <2 seconds for setback calculations
- **Database Queries**: <500ms with optimized indexes
- **Frontend Rendering**: <100ms with React optimizations
- **Bundle Size**: <500KB gzipped

## Security

- Input validation with Zod schemas
- Rate limiting middleware
- CORS configuration
- SQL injection prevention
- Environment variable protection

## Deployment

### Vercel (Recommended):

1. **Connect repository to Vercel**

2. **Set environment variables in Vercel dashboard**

3. **Configure build settings:**
 ```json
 {
 "functions": {
 "app/api/**/route.ts": {
 "maxDuration": 30
 }
 }
 }
 ```

4. **Deploy:**
 ```bash
 vercel deploy --prod
 ```

### Manual Deployment:

```bash
npm run build
npm start
```

## Monitoring

- Built-in API response time tracking
- Database query performance monitoring 
- Error logging with structured format
- Health check endpoints for uptime monitoring

## Development Workflow

1. **Feature Development:**
 - Create feature branch
 - Implement with TypeScript
 - Add comprehensive tests
 - Validate with test properties

2. **Database Changes:**
 - Update type definitions
 - Modify database client
 - Test query performance
 - Update API contracts

3. **API Changes:**
 - Update request/response schemas
 - Add input validation
 - Test error handling
 - Update frontend integration

## Architecture Decisions

### Why Next.js 14?
- **Full-stack in one codebase**: API routes + frontend
- **Server-side rendering**: Better SEO and performance
- **TypeScript by default**: Type safety for complex calculations
- **Built-in optimizations**: Code splitting, prefetching, image optimization

### Why PostgreSQL?
- **Single source of truth**: the same Supabase instance the Python pipeline writes to
- **PostGIS**: spatial overlays and lot geometry queries run in the database
- **Concurrent access**: multiple serverless function instances read the same data

### Why Tailwind CSS?
- **Rapid development**: Utility-first approach
- **Consistency**: Design system built-in
- **Performance**: Only used styles included
- **Responsive**: Mobile-first design patterns

## Troubleshooting

### Common Issues:

1. **Database connection refused:**
 - Verify `DB_HOST` / `DB_PORT` / `DB_NAME` / `DB_USER` / `DB_PASSWORD` in `.env.local`
 - Confirm the Supabase instance accepts connections from this host

2. **Google Places not working:**
 - Check `GOOGLE_PLACES_API_KEY` is valid
 - Verify Places API is enabled in Google Console
 - Check browser console for errors

3. **NSW API timeout:**
 - NSW Planning API can be slow (10-30 seconds)
 - Implement retry logic for production use
 - Consider caching successful responses

4. **TypeScript errors:**
 - Run `npm run type-check` to identify issues
 - Ensure all dependencies have type definitions
 - Check @types packages are installed

## Support

For technical issues or questions:
- Check the troubleshooting section above
- Review console logs for error details
- Verify environment variables are correct
- Test with known working addresses

## Next Steps

- [ ] Add caching layer for NSW API responses
- [ ] Implement real-time collaborative features
- [ ] Add report generation and export
- [ ] Enhance mobile responsive design
- [ ] Add comprehensive error monitoring