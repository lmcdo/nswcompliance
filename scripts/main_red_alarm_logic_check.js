// Extracts the `Assess main` script out of the workflow YAML and runs it
// against mocked Octokit responses. Catches syntax errors and logic bugs
// before the thing is merged, which matters here because this workflow only
// runs on main and its last twelve runs were all silent failures.
const fs = require('fs');

const yamlPath = process.argv[2];
const raw = fs.readFileSync(yamlPath, 'utf8');

// Pull the first `script: |` block (the Assess step) and dedent it.
const lines = raw.split(/\r?\n/);
const start = lines.findIndex((l) => /^\s*script:\s*\|\s*$/.test(l));
if (start < 0) throw new Error('no script block found');
const indent = lines[start + 1].match(/^\s*/)[0].length;
const body = [];
for (let i = start + 1; i < lines.length; i++) {
  const l = lines[i];
  if (l.trim() !== '' && l.match(/^\s*/)[0].length < indent) break;
  body.push(l.slice(indent));
}
const src = body.join('\n');

const HOUR = 3600000;
const iso = (msAgo) => new Date(Date.now() - msAgo).toISOString();

function makeCtx({ runs, headSha, headDate }) {
  const out = {};
  const logs = [];
  let failed = null;
  const core = {
    setOutput: (k, v) => { out[k] = v; },
    info: (m) => logs.push(m),
    setFailed: (m) => { failed = m; },
  };
  const github = {
    rest: {
      actions: { listWorkflowRuns: async () => ({ data: { workflow_runs: runs } }) },
      repos: {
        getCommit: async () => ({
          data: { sha: headSha, commit: { committer: { date: headDate } } },
        }),
      },
    },
  };
  const context = { repo: { owner: 'lmcdo', repo: 'nswcompliance' } };
  return { out, logs, core, github, context, failed: () => failed };
}

async function run(name, fixture, expectState) {
  const ctx = makeCtx(fixture);
  const fn = new Function('github', 'core', 'context', `return (async () => { ${src} })()`);
  await fn(ctx.github, ctx.core, ctx.context);
  const got = ctx.out.state;
  const ok = got === expectState;
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}\n      expected=${expectState} got=${got}\n      detail=${(ctx.out.detail || '').slice(0, 110)}`);
  return ok;
}

const GREEN = (sha, updatedAgoH) => ([{
  conclusion: 'success', html_url: 'https://x/run/1', head_sha: sha,
  updated_at: iso(updatedAgoH * HOUR),
}]);
const RED = (sha) => ([{
  conclusion: 'failure', html_url: 'https://x/run/2', head_sha: sha,
  updated_at: iso(1 * HOUR),
}]);

(async () => {
  const results = [];

  // 1. Nothing has ever run — unknown must be treated as broken.
  results.push(await run('no completed gates run at all', {
    runs: [], headSha: 'aaaaaaaa1111', headDate: iso(1 * HOUR),
  }, 'broken'));

  // 2. The gate actually failed.
  results.push(await run('latest gates run concluded failure', {
    runs: RED('aaaaaaaa1111'), headSha: 'aaaaaaaa1111', headDate: iso(1 * HOUR),
  }, 'broken'));

  // 3. THE CASE THAT IS TRUE RIGHT NOW: green run on the current HEAD.
  results.push(await run('green run on current HEAD (today\'s real state)', {
    runs: GREEN('e1fa65ae0000', 2), headSha: 'e1fa65ae0000', headDate: iso(2 * HOUR),
  }, 'ok'));

  // 4. Green, but an old HEAD that nothing has verified.
  results.push(await run('HEAD newer than last run, 9h old — unverified', {
    runs: GREEN('bbbbbbbb2222', 10), headSha: 'cccccccc3333', headDate: iso(9 * HOUR),
  }, 'broken'));

  // 5. Green, HEAD newer but the run is plausibly still in flight.
  results.push(await run('HEAD newer but only 1h old — in flight, stay quiet', {
    runs: GREEN('bbbbbbbb2222', 2), headSha: 'cccccccc3333', headDate: iso(1 * HOUR),
  }, 'ok'));

  // 6. Future-dated committer date must not buy an unbounded grace period.
  results.push(await run('HEAD committer date in the FUTURE — fail closed', {
    runs: GREEN('bbbbbbbb2222', 2), headSha: 'cccccccc3333', headDate: iso(-5 * HOUR),
  }, 'broken'));

  // 7 & 8. THE HOLE A CROSS-REVIEW FOUND, 2026-08-12.
  // hoursSince originally returned NaN for a missing or malformed timestamp.
  // NaN < 0 is false AND NaN > 3 is false, so an unverified HEAD fell straight
  // through both guards to state=ok, reporting "NaNh". A watchdog failing
  // OPEN — the one direction it must never fail. These two pin it shut.
  results.push(await run('HEAD committer date MISSING — must not fall through to ok', {
    runs: GREEN('bbbbbbbb2222', 2), headSha: 'cccccccc3333', headDate: undefined,
  }, 'broken'));

  results.push(await run('HEAD committer date MALFORMED — must not fall through to ok', {
    runs: GREEN('bbbbbbbb2222', 2), headSha: 'cccccccc3333', headDate: 'not-a-date',
  }, 'broken'));

  // 9. The same malformed-timestamp class on the RUN side must not crash or
  // silence the genuine failure it is reporting.
  results.push(await run('run updated_at malformed, gates failed — still broken', {
    runs: [{ conclusion: 'failure', html_url: 'https://x/run/3', head_sha: 'dddddddd4444', updated_at: 'garbage' }],
    headSha: 'dddddddd4444', headDate: iso(1 * HOUR),
  }, 'broken'));

  const passed = results.filter(Boolean).length;
  console.log(`\n${passed}/${results.length} passed`);
  process.exit(passed === results.length ? 0 : 1);
})();
