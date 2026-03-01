entrality Types: What Each Tells You

  ---
  Degree Centrality

  What it is: Count of direct connections (edges) a
  node has.

  Infers: Raw popularity, activity level, direct
  influence reach.

  Use cases:
  - Most connected lot in an adjacency network =
  best subdivision candidate
  - Most connected developer in a transaction
  network = most active buyer
  - Social: who has the most followers/contacts

  Limit: Ignores network position — a node with 10
  connections in a dense cluster may be less
  powerful than one with 5 connections bridging two
  groups.

  ---
  Betweenness Centrality

  What it is: How often a node sits on the shortest
  path between two other nodes.

  Infers: Brokerage, gatekeeping, information
  control. Nodes that bridge otherwise disconnected
  groups.

  Use cases:
  - Developer who connects two separate ownership
  clusters = potential syndicate coordinator
  - In supply chains: single-point-of-failure
  suppliers
  - Social: the person who "knows everyone" across
  different circles
  - In your plans: identifying shell company
  brokers, price-fixing agents

  Key insight: Low degree but high betweenness =
  quiet powerbroker. Very actionable.

  ---
  Closeness Centrality

  What it is: How quickly a node can reach all other
   nodes (inverse of average path length to
  everyone).

  Infers: Speed of information spread, efficiency of
   influence. How fast news/contagion/prices
  propagate from this node.

  Use cases:
  - Foreclosure cascade prediction — which lot's
  distress spreads fastest to neighbours
  - Identifying which council planning decision
  affects the most other lots soonest
  - Supply chain: which supplier disruption ripples
  fastest through the network
  - Marketing: which influencer spreads a message
  fastest

  ---
  Eigenvector Centrality

  What it is: Degree centrality weighted by the
  importance of your neighbours. You score high if
  important people are connected to you.

  Infers: Prestige, quality of connections. Being
  connected to powerful nodes amplifies your own
  score.

  Use cases:
  - Ownership networks: which owner controls parcels
   that other powerful owners also cluster around
  - Academic: whose papers are cited by the
  most-cited papers (this is essentially what Google
   PageRank is)
  - Identifying influential developers whose
  projects are near other influential developers'
  projects

  ---
  PageRank

  What it is: Eigenvector centrality adapted for
  directed graphs, with a damping factor
  (probability of "random walk" continuing).

  Infers: Authority in directed influence flows.
  Originally web links; generalises to any directed
  network.

  Use cases:
  - Directed transaction networks: who receives
  money/transfers from high-value sources
  - DA networks: which planning decisions reference
  (are influenced by) the most precedent decisions
  - Identifying which lots or owners attract the
  most directed attention/investment

  Difference from eigenvector: PageRank handles
  directionality and avoids rank sinks. Better for
  asymmetric relationships.

  ---
  Clustering Coefficient

  What it is: Proportion of a node's neighbours that
   are also connected to each other. (This is the
  egocentric density you asked about earlier.)

  Infers: Local cohesion, clique membership. High =
  your neighbours all know each other. Low = you
  bridge disconnected groups (structural holes).

  Use cases:
  - Low clustering + high betweenness = classic
  broker/arbitrageur position
  - High clustering = tight-knit developer syndicate
   or ownership cartel
  - Property: lots in a dense cluster of mutual
  adjacency = coordinated development zone

  ---
  HITS (Hubs and Authorities)

  What it is: Two scores per node — Hub score (links
   to good authorities) and Authority score (linked
  to by good hubs).

  Infers: Separates aggregators (hubs) from sources
  of truth (authorities). Useful when roles in a
  network are asymmetric.

  Use cases:
  - Real estate: agents (hubs) who consistently list
   properties from high-value developers
  (authorities)
  - Research: journals (authorities) vs review
  papers (hubs)
  - Property networks: developers who aggregate lots
   from authoritative land holders

  ---
  Harmonic Centrality

  What it is: Like closeness but handles
  disconnected graphs properly (uses harmonic mean
  of distances).

  Infers: Same as closeness — reach efficiency — but
   works on fragmented networks where some nodes
  aren't reachable.

  Use cases: Any real-world network where the graph
  isn't fully connected (most of them). Safer
  default than closeness for property/transaction
  data.

  ---
  Quick Reference

  ┌───────────┬──────────────────┬─────────────┐
  │ Centralit │  Core question   │  Property   │
  │     y     │                  │  use case   │
  ├───────────┼──────────────────┼─────────────┤
  │           │ How many         │ Active buye │
  │ Degree    │ connections?     │ rs/corner   │
  │           │                  │ lots        │
  ├───────────┼──────────────────┼─────────────┤
  │           │                  │ Shell       │
  │ Betweenne │ Who's the broker │ companies,  │
  │ ss        │ /gatekeeper?     │ price       │
  │           │                  │ fixers      │
  ├───────────┼──────────────────┼─────────────┤
  │           │                  │ Foreclosure │
  │ Closeness │ How fast can you │  cascade,   │
  │           │  reach everyone? │ influence   │
  │           │                  │ spread      │
  ├───────────┼──────────────────┼─────────────┤
  │ Eigenvect │ How important    │ Prestige    │
  │ or        │ are your         │ ownership   │
  │           │ neighbours?      │ clusters    │
  ├───────────┼──────────────────┼─────────────┤
  │           │ Who gets         │ Investment  │
  │ PageRank  │ directed to by   │ attraction, │
  │           │ powerful nodes?  │  DA         │
  │           │                  │ precedent   │
  ├───────────┼──────────────────┼─────────────┤
  │           │ How tight is     │ Syndicate   │
  │ Clusterin │ your             │ detection,  │
  │ g coeff   │ neighbourhood?   │ structural  │
  │           │                  │ holes       │
  ├───────────┼──────────────────┼─────────────┤
  │ HITS      │ Hub vs authority │ Agents vs   │
  │           │  role?           │ developers  │
  ├───────────┼──────────────────┼─────────────┤
  │           │                  │ Any         │
  │ Harmonic  │ Closeness on     │ real-world  │
  │           │ broken graphs?   │ sparse      │
  │           │                  │ network     │
  └───────────┴──────────────────┴─────────────┘

  ---
  For your Newcastle/DCDB pipeline: Betweenness and
  clustering coefficient together are the most
  powerful combo — betweenness finds the brokers,
  low clustering confirms they're bridging gaps
  rather than just part of a clique.
