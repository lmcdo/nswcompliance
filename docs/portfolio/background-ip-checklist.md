<!-- prior-art-checked: new business/legal checklist for contract negotiations; no existing surface covers contracting terms -->
# Background IP Protection — Contract Checklist

The single biggest IP risk to the product is not code theft — it is a
client contract that assigns or encumbers what you've already built.
Use this checklist in every engagement negotiation. **This is a prompt
sheet for a conversation with an Australian IP/contracts lawyer, not
legal advice** — pay for one review of your standard terms; it costs
less than one bad clause.

## Require (walk away without these)

1. **Background IP schedule.** The contract defines Background IP and
   *names yours in a schedule*: "the [product name] platform, including
   its regulatory-provision database, extraction and verification
   pipelines, monitoring systems and related tooling, and all
   improvements to them." Unnamed background IP is arguable background
   IP.
2. **Ownership stays with you; client gets a licence to deliverables.**
   Client owns (or gets a broad licence to) the *specific deliverables*
   you build for them. Anything pre-existing, and any general-purpose
   tools/skills/methods used or improved along the way, remain yours.
3. **Improvements carve-out.** If delivering the work improves your
   background IP (a better extraction gate, a faster verifier), those
   improvements are yours. Client gets the benefit in their deliverable,
   not ownership of the technique.
4. **Licence-back if needed.** If a deliverable necessarily embeds your
   background IP, the client receives a non-exclusive licence to use it
   *within the deliverable* — never a transfer, never exclusivity.

## Refuse (red lines)

1. **Present assignment of everything**: "Contractor hereby assigns all
   IP conceived or reduced to practice during the term." During-the-term
   language captures your nights-and-weekends product work. Limit
   assignment to IP created *in performance of the services*.
2. **Field-of-use or non-compete restrictions** covering planning,
   property data, compliance tech, or AI verification — your entire
   future. A narrow "won't build [client's named product] for [client's
   named competitor] for 6–12 months" may be liveable; a field
   restriction is not.
3. **Exclusivity over your methods or data.** No client owns your
   corpus, your gates, or exclusive access to them (sell premium
   *service* tiers, never method exclusivity).
4. **Moral-rights consents / attribution waivers bundled with broad
   assignments** — read what the assignment actually attaches to before
   consenting.
5. **"Work made for hire" style language imported from US templates**
   without a background IP schedule attached.

## Practice (habits that make the paper defensible)

- Keep product development in its own repos/accounts; never commit
  product code from a client's machine, VPN or tenancy.
- Timestamped provenance already exists (repo history, the published
  case study, prose-gate release) — it documents that the platform
  predates every engagement. Keep publishing dates.
- In every SOW, one sentence: "This engagement uses Contractor's
  Background IP as defined in Schedule X; nothing in this SOW transfers
  it."
- If a client wants "everything you build" — quote a price for bespoke
  work-for-hire that reflects giving up reuse, i.e., 3–5×. Ownership is
  a product; sell it as one or not at all.
- Re-read the IP clause on *renewals and amendments* too; terms drift.
