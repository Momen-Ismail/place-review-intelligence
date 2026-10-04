# Future Development

This file records opportunities that are **not yet implemented**. Phase 1 is complete without them.

## Main Opportunity — POS / Order Integration

Reviews answer:

> What are customers talking about?

POS or order data answers:

> What are customers actually buying?

Combining the two would distinguish customer attention from commercial performance. A future integration could add:

- dish
- category
- quantity sold
- revenue
- price
- discount
- cancellation or refund
- food versus drinks
- cost
- margin

That data could support this analysis matrix:

| | High review attention | Low review attention |
| --- | --- | --- |
| **High sales** | High sales + high review attention | High sales + low review attention |
| **Low sales** | Low sales + high review attention | Low sales + low review attention |

Possible uses include finding popular but under-discussed products, highly discussed products with weak sales, margin opportunities, discount dependence, and discrepancies between customer conversation and purchasing behavior.

No POS or order integration currently exists, so Phase 1 dish mentions must not be interpreted as sales volume.

## Other Optional Improvements

- incremental scheduled review refresh
- management KPI dashboard
- automated before/after comparison
- competitor field research
- project command center or `manage.py`
- additional restaurants

Each item should be scoped, validated, and added only when the business need is clear. None should require moving the current source modules or databases merely for structural consistency.
