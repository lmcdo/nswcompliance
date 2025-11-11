/**
 * PRP-A3: Metrics counters
 * Shared counters for application metrics
 */

// Request counters
let requestTotal = 0;
let requestErrors = 0;
let databaseQueries = 0;
let databaseErrors = 0;

/**
 * Increment request counter (called by middleware)
 */
export function incrementRequestCounter() {
  requestTotal++;
}

/**
 * Increment error counter (called by error handlers)
 */
export function incrementErrorCounter() {
  requestErrors++;
}

/**
 * Increment database query counter
 */
export function incrementDatabaseQueryCounter() {
  databaseQueries++;
}

/**
 * Increment database error counter
 */
export function incrementDatabaseErrorCounter() {
  databaseErrors++;
}

/**
 * Get current counter values
 */
export function getCounterValues() {
  return {
    requestTotal,
    requestErrors,
    databaseQueries,
    databaseErrors
  };
}
