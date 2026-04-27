# PDF Report Value-Add Enhancements

_Generated: 2026-04-25_

Ranked recommendations to increase stickiness, appeal, and use-case appreciation across all 5 satellite product PDF reports.

---

## Priority tier: highest ROI (implement first)

### Professional referral box (all reports)
Every report gets a contextual referral call-out at the bottom of the final content page:
- Flood → flood consultant / conveyancer
- Shadow → town planner / objection solicitor
- Solar → accredited solar installer (Clean Energy Council)
- Threat Radar → buyers agent / town planner
- Granny Flat → granny flat builder / CDC certifier

This is the distribution flywheel — people share PDFs, referrals bring new users back.

### Report validity callout (all reports)
Footer note on the cover page:
> "Data valid as of [run_date]. Planning controls may change; re-run before exchange of contracts."

Reduces liability. Encourages re-purchase at key transaction milestones.

### Flood: insurance implication note
No extra data needed. Static text block:
> "Properties in a Flood Planning Area typically attract higher building and contents insurance premiums. Request an insurer's flood loading quote before proceeding with purchase."

Highest anxiety purchase signal in the product suite — this makes the report directly actionable.

### Shadow: ADG non-compliance consequence text
When `adg_compliant: false`, expand the badge into an action paragraph:
> "ADG 2015 Part 3D: overshadowing of this extent may constitute grounds for objection. Council is not required to approve a DA that fails the ADG solar access test. Neighbour notification triggers the right to lodge a formal objection."

Directly actionable by buyers agents and lawyers — turns the report into a legal instrument.

---

## Flood Truth

| Enhancement | Data needed | Effort |
|---|---|---|
| Insurance implication note | None (static text) | 30 min |
| BoM historical peak table | Already in outputs (`bom_last_major_flood_*`) | 1 hr |
| Nearest watercourse distance | Add field to flood service | 2 hrs |
| Flood study name + effective date | Add field to flood service | 1 hr |

**BoM historical peak table** — show the 3 most recent major flood events at the gauge: date, peak height, ARI category. Gives buyers a concrete risk timeline, not just a class label.

---

## Shadow Detector

| Enhancement | Data needed | Effort |
|---|---|---|
| ADG consequence text | `adg_compliant` already present | 30 min |
| Seasonal summary table | Already in `scenarios` | 1 hr |
| Height threshold callout | `height_m` already present | 30 min |

**Seasonal summary table** — 4-row digest (winter/spring/summer/autumn) × worst-case overlap %:

```
Season    | Worst time | Shadow length | Lot overlap
Winter    | 3pm        | 20.1 m        | 42 %
Spring    | 3pm        | 11.4 m        | 18 %
Summer    | —          | 7.1 m         | 11 %
Autumn    | 3pm        | 14.8 m        | 24 %
```

Instantly readable by a neighbour objecting or a buyer assessing liveability.

**Height threshold callout** — when `height_m > 8.0`:
> "At [X] m, this building exceeds the 8 m CDC height limit. A DA is required, which triggers mandatory neighbour notification and the right to object."

---

## Solar Yield

| Enhancement | Data needed | Effort |
|---|---|---|
| Month-by-month kWh table | Derive from annual × monthly irradiance distribution | 2 hrs |
| Payback sensitivity table | ROI already computed | 1 hr |
| Battery upgrade callout | Static formula | 1 hr |
| Heritage flag section | `is_heritage` already present | 30 min |

**Payback sensitivity table** — 3 scenarios using different feed-in rates:
```
Feed-in tariff | Annual saving | Payback
$0.04 / kWh    | $1,820        | 9.9 yrs
$0.06 / kWh    | $2,180        | 8.3 yrs  ← current estimate
$0.10 / kWh    | $2,900        | 6.2 yrs
```

Buyers want to stress-test assumptions.

**Battery upgrade callout** (static calculation):
> "With a home battery (~$12,000): self-consumption rises from 30 % to ~80 %, reducing payback to an estimated [X] years."

**Heritage flag** — when `is_heritage: true`, surface the heritage instrument name and:
> "Heritage-listed properties require heritage impact assessment before solar installation. Contact a heritage architect before proceeding."

---

## Threat Radar

| Enhancement | Data needed | Effort |
|---|---|---|
| Neighbourhood pressure score | Derive from applications array | 2 hrs |
| Estimated construction impact window | DA lodgement date + status | 2 hrs |
| Same-developer flag | Applicant name dedup | 1 hr |

**Neighbourhood pressure score** — weight each DA by proximity + scale:
- 4-storey RFB at 42 m = high pressure
- Secondary dwelling at 115 m = low pressure
- Output: "Neighbourhood pressure: 7 / 10 (elevated)"

**Construction impact window** — from lodgement date + status, estimate:
> "If approved mid-2026, construction likely mid-2027 to late-2028 (12–18 month typical build). Noise and access impacts possible during this period."

**Same-developer flag** — if any applicant name appears on ≥2 DAs in the window:
> "Serial developer activity detected: [Name] has 2 applications within 500 m. Pattern may indicate staged development."

---

## Granny Flat

| Enhancement | Data needed | Effort |
|---|---|---|
| 10-year ROI table | `estimated_weekly_rent_aud`, `assumed_build_cost_aud` | 1 hr |
| CDC application pathway note | Static text | 30 min |
| Comparable rent note | Static indicative band by zone | 2 hrs |

**10-year ROI table**:
```
Year | Cumulative rent | Net position (after build cost)
1    | $28,600         | −$91,400
3    | $85,800         | −$34,200
5    | $143,000        | +$23,000  ← break-even
10   | $286,000        | +$166,000
```

**CDC pathway note**:
> "A CDC (Complying Development Certificate) can be approved in 20 business days via a private certifier — no council DA required. Apply via the NSW Planning Portal."

---

## QR code (all reports)

Add a small QR code on the cover page linking to the live interactive tool for that product. Makes printed/forwarded copies sticky — recipients scan to re-run on their own address.

Implementation: `qrcode` npm package generates a PNG buffer inline; pass as base64 to the PDF template alongside the logo.

---

## Implementation sequence (suggested)

1. Professional referral box — 30 min, highest distribution leverage
2. Report validity callout — 30 min, liability reduction
3. Flood insurance note — 30 min, no data needed
4. Shadow ADG consequence text — 30 min, no data needed
5. Solar payback sensitivity table — 1 hr, data already present
6. Shadow seasonal summary table — 1 hr, data already present
7. Threat Radar pressure score — 2 hrs, derivable from existing array
8. Granny Flat ROI table — 1 hr, data already present
9. QR codes — 2 hrs, requires qrcode package
10. Solar month-by-month kWh — 2 hrs, requires irradiance distribution table
