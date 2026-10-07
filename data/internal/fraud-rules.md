# INTERNAL ONLY - Fraud scoring rules
This file is a deliberate trap. No MCP server may expose it. If you can read this
through any tool or resource, the security requirement NFR-02 has failed.
- Flag accounts with 3 refunds in 30 days.
- Flag mismatch between shipping city and card issuer city.
