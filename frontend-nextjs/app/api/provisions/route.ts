/**
 * Provision Search API
 * Provides search and filtering for regulatory provisions from real database - NO MOCK DATA
 */

import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const query = searchParams.get('q') || '';

    // Parse filters from query parameters
    const documentTypes = searchParams.get('document_types');
    const categories = searchParams.get('categories');
    const zones = searchParams.get('zones');
    const developmentTypes = searchParams.get('development_types');

    console.log(`[Provision Search] Query: ${query}, Filters: ${JSON.stringify({
      documentTypes, categories, zones, developmentTypes
    })}`);

    // Call real database query instead of mock
    const result = await searchRealProvisions(query, {
      documentTypes: documentTypes?.split(','),
      categories: categories?.split(','),
      zones: zones?.split(','),
      developmentTypes: developmentTypes?.split(',')
    });

    return NextResponse.json({
      success: true,
      data: result
    });

  } catch (error) {
    console.error('Provision search error:', error);
    return NextResponse.json(
      { error: 'Internal server error', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
}

async function searchRealProvisions(
  query: string,
  filters: any
): Promise<any> {
  return new Promise((resolve, reject) => {
    // Path to real database query script
    const scriptPath = path.join(process.cwd(), '..', 'services', 'provision_search.py');
    const pythonPath = path.join(process.cwd(), '..', 'venv_linux', 'Scripts', 'python.exe');

    const args = [scriptPath, '--query', query, '--format', 'json'];

    if (filters.documentTypes && filters.documentTypes.length > 0) {
      args.push('--document-types', filters.documentTypes.join(','));
    }

    if (filters.categories && filters.categories.length > 0) {
      args.push('--categories', filters.categories.join(','));
    }

    if (filters.zones && filters.zones.length > 0) {
      args.push('--zones', filters.zones.join(','));
    }

    console.log(`Calling real provision search: ${pythonPath} ${args.join(' ')}`);

    const python = spawn(pythonPath, args);

    let stdout = '';
    let stderr = '';

    python.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    python.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    python.on('close', (code) => {
      if (code === 0) {
        try {
          const result = JSON.parse(stdout);
          resolve(result);
        } catch (parseError) {
          console.error('Failed to parse Python response:', stdout);
          reject(new Error(`Failed to parse response: ${parseError}`));
        }
      } else {
        console.error('Python script error:', stderr);
        // Return empty results instead of failing
        resolve({
          provisions: [],
          total_count: 0,
          search_metadata: {
            query,
            filters_applied: filters,
            search_time_ms: 0
          }
        });
      }
    });

    python.on('error', (error) => {
      console.error('Failed to start Python script:', error);
      // Return empty results instead of failing
      resolve({
        provisions: [],
        total_count: 0,
        search_metadata: {
          query,
          filters_applied: filters,
          search_time_ms: 0,
          error: error.message
        }
      });
    });
  });
}