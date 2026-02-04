#!/usr/bin/env node
/**
 * Pre-build check for authentication dependencies.
 * Ensures all required auth packages are installed.
 */

import { createRequire } from 'module';
const require = createRequire(import.meta.url);

const requiredPackages = [
  '@supabase/supabase-js',
  '@supabase/ssr',
];

let allInstalled = true;

for (const pkg of requiredPackages) {
  try {
    require.resolve(pkg);
    console.log(`✅ ${pkg} is installed`);
  } catch (e) {
    console.error(`❌ ${pkg} is NOT installed`);
    allInstalled = false;
  }
}

if (!allInstalled) {
  console.error('\n⚠️  Some auth dependencies are missing. Run: npm install');
  process.exit(1);
}

console.log('\n✅ All auth dependencies are installed');
process.exit(0);
