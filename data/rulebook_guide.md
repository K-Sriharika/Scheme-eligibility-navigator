# The editable rulebook

`data/schemes.json` is the rulebook. It is deliberately kept as plain, structured
data so that a **domain expert can change the agent's behaviour without touching
any code** and the change takes effect on the very next run.

## Add a scheme
Append an object to the `schemes` array:

```json
{
  "id": "my_new_scheme",
  "name": "My New Scheme",
  "category": "Education",
  "summary": "One line a citizen would understand.",
  "benefit": "What they get.",
  "documents": ["Aadhaar", "Income certificate"],
  "apply_url": "https://example.gov.in",
  "criteria": [
    {"field": "age", "op": ">=", "value": 18},
    {"field": "annual_income", "op": "<=", "value": 250000}
  ]
}
```

## Criteria language
Each criterion is either a **leaf** or an **any_of** group (logical OR).

Leaf: `{"field": <attribute>, "op": <operator>, "value": <value>}`

Operators: `==  !=  <  <=  >  >=  in`

`any_of`: `{"any_of": [ <leaf>, <leaf>, ... ]}` — satisfied if any child is.

A person is eligible only if **all** top-level criteria are satisfied. If the
person's profile does not mention a field a criterion needs, that criterion is
treated as not satisfied (we never assume eligibility on missing information).

## Attributes a profile can have
`age` (int), `gender` ("female"/"male"/"other"), `annual_income` (rupees, int),
`occupation` (e.g. "farmer", "student", "entrepreneur", "street_vendor",
"salaried", "retired", "daily_wage"), `category` ("SC"/"ST"/"OBC"/"General"/"EWS"),
`residence` ("rural"/"urban"), `has_land` (bool), `owns_pucca_house` (bool).

You can introduce a new attribute simply by referencing it in a criterion and in
the test cases; no code change is needed.

## Why this matters
There are two ways to improve this agent:
1. The **optimizer** rewrites the agent's system prompt automatically.
2. A **human domain expert** edits this rulebook directly.

Both take effect immediately. That is the "no developer bottleneck" idea in
practice.
