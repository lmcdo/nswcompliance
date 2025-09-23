/**
 * Version Management API
 * Provides access to document version information
 */

import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const action = searchParams.get('action');
    const documentType = searchParams.get('documentType');
    const documentIdentifier = searchParams.get('documentIdentifier');
    const targetDate = searchParams.get('targetDate');

    switch (action) {
      case 'current':
        return await getCurrentVersion(documentType!, documentIdentifier!);

      case 'atDate':
        return await getVersionAtDate(documentType!, documentIdentifier!, targetDate!);

      case 'statistics':
        return await getVersionStatistics();

      case 'comparison':
        return await getVersionComparison(documentType!, documentIdentifier!);

      default:
        return NextResponse.json(
          { error: 'Invalid action. Use: current, atDate, statistics, comparison' },
          { status: 400 }
        );
    }
  } catch (error) {
    console.error('Version API error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

async function getCurrentVersion(documentType: string, documentIdentifier: string) {
  const result = await callVersionManager([
    'get_current_version',
    '--document-type', documentType,
    '--document-identifier', documentIdentifier
  ]);

  return NextResponse.json(result);
}

async function getVersionAtDate(documentType: string, documentIdentifier: string, targetDate: string) {
  const result = await callVersionManager([
    'get_version_at_date',
    '--document-type', documentType,
    '--document-identifier', documentIdentifier,
    '--target-date', targetDate
  ]);

  return NextResponse.json(result);
}

async function getVersionStatistics() {
  const result = await callVersionManager(['get_statistics']);
  return NextResponse.json(result);
}

async function getVersionComparison(documentType: string, documentIdentifier: string) {
  const result = await callVersionManager([
    'get_comparison',
    '--document-type', documentType,
    '--document-identifier', documentIdentifier
  ]);

  return NextResponse.json(result);
}

async function callVersionManager(args: string[]): Promise<any> {
  return new Promise((resolve, reject) => {
    const scriptPath = path.join(process.cwd(), '..', 'services', 'version_manager.py');
    const pythonPath = path.join(process.cwd(), '..', 'venv_linux', 'Scripts', 'python.exe');

    const child = spawn(pythonPath, [scriptPath, ...args], {
      cwd: path.join(process.cwd(), '..'),
      stdio: ['pipe', 'pipe', 'pipe']
    });

    let stdout = '';
    let stderr = '';

    child.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    child.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    child.on('close', (code) => {
      if (code === 0) {
        try {
          const result = JSON.parse(stdout);
          resolve(result);
        } catch (e) {
          resolve({ success: true, data: stdout.trim() });
        }
      } else {
        reject(new Error(`Version manager failed: ${stderr}`));
      }
    });

    child.on('error', (error) => {
      reject(error);
    });
  });
}
