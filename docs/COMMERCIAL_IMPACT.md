# Commercial Impact (v0.1)

Commercial impact is recorded separately from, and independently of,
technical and public-safety clearance. It never changes what is scientifically
or technically true about an artifact.

## Classes

| Class | Meaning | Rule |
| --- | --- | --- |
| `NONE` | No foreseeable commercial effect. | May proceed if every other dimension passes. |
| `COMPLEMENTARY` | Free availability supports other work. | Moat review required; may proceed if every other dimension passes. |
| `LEAD_GENERATING` | Free availability may create interest in other offerings. | Moat review required; may proceed if every other dimension passes. |
| `UNCERTAIN` | Effect not yet understood. | **Fails closed** for exports from private origins until an explicit commercial review resolves it. The lint rejects it for every release. |
| `CANNIBALIZATION_RISK` | Could displace something of commercial value. | Moat review **and** recorded explicit human authorization required. |
| `CORE_DIFFERENTIATOR` | Gives away a central differentiator. | Moat review **and** recorded explicit human authorization required. |

## Minimum-viable-moat review

For every commercially adjacent class (`COMPLEMENTARY`, `LEAD_GENERATING`,
`CANNIBALIZATION_RISK`, `CORE_DIFFERENTIATOR`) the clearance receipt must
answer:

> AFTER THIS ARTIFACT IS AVAILABLE FOR FREE, WHAT ECONOMICALLY VALUABLE
> FUNCTION REMAINS?

The receipt lists the retained surfaces, chosen from: managed hosting,
operation at scale, enterprise integrations, identity integration, private
deployment, policy management, managed provenance, continuously refreshed
intelligence, proprietary adapters, support, reliability, SLAs, professional
implementation, organization-wide governance, assurance services, hardware,
network effects, or other.

"Nothing remains" is **not** an automatic rejection. It requires an explicit
strategic review, recorded in the receipt. Giving a complete capability away
is allowed; it must simply never happen by accident.

## Open primitive, paid operationalization

Commons supports, but does not require, this pattern:

```
FREE:      a local tool (for example, a receipt validator)
POSSIBLY PAID ELSEWHERE:
           organization-wide operation, managed policy, identity integration,
           hosting, private deployment, reporting, support, SLAs
```

Commons tools are never deliberately weakened to create artificial scarcity.

## Who decides

The commercial dimension is owned or advised by the organization's
commercial-review function when an export comes from a private origin. That
function decides commercial impact only. It has no authority over scientific
truth, over originating projects, or over the other clearance dimensions.

For `COMMONS_NATIVE` artifacts with commercial impact `NONE`, no commercial
review is needed and the dimension may be recorded as not applicable.

## Ecosystem signals

Stars, forks, issues, contributions and download counts may be observed. They
are demand signals at most. They do not establish willingness to pay,
profitability or product-market fit, and Commons is not a product, sales
funnel or profit center.
