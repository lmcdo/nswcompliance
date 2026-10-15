/** An HCA's own rules reach only that HCA; ANY_HCA rules reach every HCA lot, never a lone heritage item. */
import { ANY_HCA, hcaTagSql } from '@/lib/provision-sql-filters';

it('a heritage item in no HCA sees only untagged rules', () => {
  expect(hcaTagSql(null)).toBe('rp.v2_heritage_hca IS NULL');
  expect(hcaTagSql(null, 'v2_heritage_hca')).not.toContain(ANY_HCA);
});

it('an HCA lot sees untagged, its own and any-HCA rules', () => {
  const sql = hcaTagSql(3);
  expect(sql).toContain('rp.v2_heritage_hca = $3');
  expect(sql).toContain(`'${ANY_HCA}'`);
});
