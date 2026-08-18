# Architecture

NetSentinel separates adapters from domain decisions and persistence. Inputs cross validation boundaries before reaching the core. The core returns explicit evidence rather than hiding uncertainty. Storage is replaceable, and network/provider side effects are injectable so tests remain deterministic.

## Data flow
1. An operator or client submits bounded input.
2. The adapter validates syntax and authorization context.
3. The domain engine performs the operation and assigns an explicit state.
4. Evidence is persisted or returned in a structured response.
5. Callers decide notification and operational escalation policy.
