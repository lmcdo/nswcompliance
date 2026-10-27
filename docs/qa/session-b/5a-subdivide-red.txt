FAIL __tests__/lib/can-subdivide-lep-min-lot-size.test.ts
  ● canSubdivide uses the LEP minimum lot size › shows subdivision rules for a 300 m² lot where the LEP minimum is 200 m²

    expect(received).toBe(expected) // Object.is equality

    Expected: true
    Received: false

      at Object.toBe (__tests__/lib/C:/Users/lawre/Downloads/solvyra/projects/compliance engine/compliance-engine/.claude/worktrees/fix-subdivide-lep-min/frontend-nextjs/__tests__/lib/can-subdivide-lep-min-lot-size.test.ts:10:36)

  ● canSubdivide uses the LEP minimum lot size › hides them for a 500 m² lot where the LEP minimum is 600 m²

    expect(received).toBe(expected) // Object.is equality

    Expected: false
    Received: true

      at Object.toBe (__tests__/lib/C:/Users/lawre/Downloads/solvyra/projects/compliance engine/compliance-engine/.claude/worktrees/fix-subdivide-lep-min/frontend-nextjs/__tests__/lib/can-subdivide-lep-min-lot-size.test.ts:14:36)

  ● canSubdivide uses the LEP minimum lot size › shows them when the LEP minimum is unknown, whatever the lot size

    expect(received).toBe(expected) // Object.is equality

    Expected: true
    Received: false

      at Object.toBe (__tests__/lib/C:/Users/lawre/Downloads/solvyra/projects/compliance engine/compliance-engine/.claude/worktrees/fix-subdivide-lep-min/frontend-nextjs/__tests__/lib/can-subdivide-lep-min-lot-size.test.ts:18:37)

Test Suites: 1 failed, 1 total
Tests:       3 failed, 2 passed, 5 total
Snapshots:   0 total
Time:        0.882 s
Ran all test suites matching __tests__/lib/can-subdivide-lep-min-lot-size.test.ts.
