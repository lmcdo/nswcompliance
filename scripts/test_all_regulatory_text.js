/**
 * Comprehensive test for all regulatory text extraction
 * Tests height, FSR, and setbacks across all areas
 */

const { spawn } = require('child_process');
const path = require('path');

async function testAllRegulatoryText() {
  console.log('🧪 Testing All Regulatory Text Extraction');
  console.log('=' .repeat(60));
  
  const results = {
    height: null,
    fsr: null,
    setbacks: {}
  };
  
  // Test LEP Height
  console.log('\n📏 Testing LEP Height Requirements:');
  try {
    const heightResult = await queryScript('direct_lep_access.py', 'height');
    if (heightResult && heightResult.includes('Inner West LEP 2022')) {
      console.log('✅ Height: WORKING');
      console.log(`   ${heightResult}`);
      results.height = 'WORKING';
    } else {
      console.log('❌ Height: FAILED');
      results.height = 'FAILED';
    }
  } catch (error) {
    console.log('❌ Height: ERROR -', error.message);
    results.height = 'ERROR';
  }
  
  // Test LEP FSR
  console.log('\n📊 Testing LEP FSR Requirements:');
  try {
    const fsrResult = await queryScript('direct_lep_access.py', 'fsr');
    if (fsrResult && fsrResult.includes('Inner West LEP 2022')) {
      console.log('✅ FSR: WORKING');
      console.log(`   ${fsrResult}`);
      results.fsr = 'WORKING';
    } else {
      console.log('❌ FSR: FAILED');
      results.fsr = 'FAILED';
    }
  } catch (error) {
    console.log('❌ FSR: ERROR -', error.message);
    results.fsr = 'ERROR';
  }
  
  // Test DCP Setbacks for all areas
  const areas = ['Ashfield', 'Leichhardt', 'Marrickville'];
  const setbackTypes = ['front', 'side', 'rear'];
  
  console.log('\n📐 Testing DCP Setback Requirements:');
  
  for (const area of areas) {
    console.log(`\n  ${area} DCP:`);
    results.setbacks[area] = {};
    
    for (const setbackType of setbackTypes) {
      try {
        const setbackResult = await queryScript('direct_dcp_access.py', area, setbackType);
        if (setbackResult && setbackResult.includes('DCP') && setbackResult.includes('minimum')) {
          console.log(`    ✅ ${setbackType.charAt(0).toUpperCase() + setbackType.slice(1)}: WORKING`);
          console.log(`       ${setbackResult}`);
          results.setbacks[area][setbackType] = 'WORKING';
        } else {
          console.log(`    ❌ ${setbackType.charAt(0).toUpperCase() + setbackType.slice(1)}: FAILED`);
          results.setbacks[area][setbackType] = 'FAILED';
        }
      } catch (error) {
        console.log(`    ❌ ${setbackType.charAt(0).toUpperCase() + setbackType.slice(1)}: ERROR - ${error.message}`);
        results.setbacks[area][setbackType] = 'ERROR';
      }
    }
  }
  
  // Summary Report
  console.log('\n' + '=' .repeat(60));
  console.log('📋 COMPREHENSIVE TEST SUMMARY:');
  console.log('=' .repeat(60));
  
  console.log(`\n🏗️  LEP Requirements:`);
  console.log(`   Height: ${getStatusEmoji(results.height)} ${results.height}`);
  console.log(`   FSR:    ${getStatusEmoji(results.fsr)} ${results.fsr}`);
  
  console.log(`\n🏠 DCP Setback Requirements:`);
  let totalSetbacks = 0;
  let workingSetbacks = 0;
  
  for (const area of areas) {
    console.log(`   ${area}:`);
    for (const setbackType of setbackTypes) {
      const status = results.setbacks[area][setbackType];
      console.log(`     ${setbackType.charAt(0).toUpperCase() + setbackType.slice(1)}: ${getStatusEmoji(status)} ${status}`);
      totalSetbacks++;
      if (status === 'WORKING') workingSetbacks++;
    }
  }
  
  // Overall Success Rate
  const overallTests = 2 + totalSetbacks; // height + fsr + all setbacks
  let overallWorking = 0;
  if (results.height === 'WORKING') overallWorking++;
  if (results.fsr === 'WORKING') overallWorking++;
  overallWorking += workingSetbacks;
  
  const successRate = (overallWorking / overallTests * 100).toFixed(1);
  
  console.log(`\n🎯 OVERALL SUCCESS RATE: ${overallWorking}/${overallTests} (${successRate}%)`);
  
  if (successRate === '100.0') {
    console.log('\n🎉 SUCCESS: All regulatory text extraction working perfectly!');
    console.log('✅ Height/FSR/setbacks now return real regulatory text');
    console.log('✅ Foundation ready for "can I build a duplex?" functionality');
    return true;
  } else {
    console.log(`\n⚠️  PARTIAL SUCCESS: ${successRate}% working`);
    console.log('❌ Some regulatory text extraction still needs fixes');
    return false;
  }
}

function getStatusEmoji(status) {
  switch (status) {
    case 'WORKING': return '✅';
    case 'FAILED': return '❌';
    case 'ERROR': return '🚨';
    default: return '❓';
  }
}

function queryScript(scriptName, ...args) {
  return new Promise((resolve, reject) => {
    const scriptPath = path.join(process.cwd(), 'scripts', scriptName);
    const python = spawn('C:\\Users\\lawre\\.pyenv\\pyenv-win\\versions\\3.11.0\\python.exe', [scriptPath, ...args]);
    
    let output = '';
    let error = '';
    
    python.stdout.on('data', (data) => {
      output += data.toString();
    });
    
    python.stderr.on('data', (data) => {
      error += data.toString();
    });
    
    python.on('close', (code) => {
      if (code === 0 && output.trim()) {
        resolve(output.trim());
      } else {
        reject(new Error(error || 'Process failed'));
      }
    });
    
    // Timeout after 10 seconds
    setTimeout(() => {
      python.kill();
      reject(new Error('Timeout'));
    }, 10000);
  });
}

// Run the comprehensive test
testAllRegulatoryText().then(success => {
  console.log('\n' + '=' .repeat(60));
  if (success) {
    console.log('🚀 PRP-001 COMPLETED: Direct DCP Storage Access Implementation');
    console.log('🎯 Ready to proceed with PRP-002: SEPP Integration');
  } else {
    console.log('🔧 Additional fixes needed before proceeding');
  }
  process.exit(success ? 0 : 1);
}).catch(error => {
  console.error('\n❌ Test execution failed:', error);
  process.exit(1);
});