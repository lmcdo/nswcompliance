import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';

export async function GET(request: NextRequest) {
 try {
 const searchParams = request.nextUrl.searchParams;
 const zone = searchParams.get('zone');
 const developmentType = searchParams.get('development_type');
 const lga = searchParams.get('lga');

 if (!zone || !developmentType) {
 return NextResponse.json(
 { error: 'Zone and development_type are required parameters' },
 { status: 400 }
 );
 }

 // Call Python parking rates fetcher
 const scriptPath = path.join(
 process.cwd(),
 '..',
 'services',
 'parking_rates_fetcher.py'
 );

 const args = [
 scriptPath,
 '--zone', zone,
 '--development-type', developmentType,
 '--format', 'json'
 ];

 if (lga) {
 args.push('--lga', lga);
 }

 return new Promise((resolve) => {
 const pythonProcess = spawn('python', args);

 let stdout = '';
 let stderr = '';

 pythonProcess.stdout.on('data', (data) => {
 stdout += data.toString();
 });

 pythonProcess.stderr.on('data', (data) => {
 stderr += data.toString();
 });

 pythonProcess.on('close', (code) => {
 if (code === 0) {
 try {
 const result = JSON.parse(stdout);
 resolve(NextResponse.json(result));
 } catch (parseError) {
 resolve(NextResponse.json({
 found: false,
 error: 'Failed to parse parking rates response',
 message: 'Unable to fetch parking rates from database. Enter rate manually from council DCP.'
 }));
 }
 } else {
 console.error('Parking rates fetcher error:', stderr);
 resolve(NextResponse.json({
 found: false,
 error: stderr || 'Failed to fetch parking rates',
 message: 'Database unavailable. Please enter parking rate manually from council DCP.'
 }));
 }
 });

 pythonProcess.on('error', (error) => {
 console.error('Failed to start parking rates fetcher:', error);
 resolve(NextResponse.json({
 found: false,
 error: error.message,
 message: 'Service unavailable. Please enter parking rate manually from council DCP.'
 }));
 });
 });

 } catch (error) {
 console.error('Parking rates API error:', error);
 return NextResponse.json(
 {
 found: false,
 error: 'Internal server error',
 message: 'Unable to fetch parking rates. Please enter manually from council DCP.'
 },
 { status: 500 }
 );
 }
}