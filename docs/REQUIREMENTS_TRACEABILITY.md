# Requirements traceability

Every requirement of the OpsDesk document mapped to the code that implements it and the test that proves it.

| Requirement | What | Implemented in | Verified by |
|---|---|---|---|
| FR-01..03 | find_customer / get_order / get_customer / list_customer_orders | servers/orders_server.py | test_servers: find_customer_*, get_customer_masks_and_flags, list_customer_orders_only_own |
| FR-04..08 | create / get / update / list tickets, audit trail | servers/orders_server.py, common/repositories/tickets.py | test_servers: ticket_lifecycle_*, ticket_errors_*, update_status_is_idempotent, list_tickets_* |
| FR-09 | check_refund rules R1-R9 in order | common/rules.py | test_rules (30) |
| FR-10..13 | issue_refund re-checks, idempotent, incident block, audit | servers/orders_server.py | test_servers: refund_*, blocked_and_issued_refunds_are_audited; scenarios S10, S20 |
| FR-14..17 | policy resources, section lookup, search, internal rules unreachable | servers/knowledge_server.py, common/stores/policy_store.py | test_servers: policy_text_and_sections, search_policy, internal_rules_are_unreachable |
| FR-18..24 | deployments, metrics, spike, logs, links, rollback proposal, incidents, runbook | servers/ops_server.py | test_servers: deployments_*, metrics_and_spike, search_logs_*, log_resource_*, link_tickets_*, rollback_* |
| FR-25..26 | 3 prompts + reply templates resource | servers/*.py, common/prompts.py, common/templates.py | test_servers: *_prompt, reply_template_resource_and_prompt, all_seven_templates_are_short |
| FR-27..41 | Graph A behaviours | agent/graph_ticket.py, agent/nodes/ticket/* | test_scenarios S1-S14, S19-S23 |
| FR-42..48 | Graph B behaviours | agent/graph_incident.py, agent/nodes/incident/* | test_scenarios S15, S16, S17, S24 |
| FR-49 | run_queue.py prints the section 16.2 summary | run_queue.py, agent/report.py | manual: run `python run_queue.py` with an API key; compare with section 16.2 |
| NFR-01 | no secrets in code | common/config.py, .gitignore, .env.example | test_architecture: no_secrets_in_source_files, env_file_is_git_ignored |
| NFR-02..03 | internal files unreachable; allow-lists | common/stores/* | test_servers: internal_rules_are_unreachable, log_resource_is_allow_listed, unknown_service_is_refused |
| NFR-04 | PII masked in the server | common/masking.py | test_servers: get_customer_masks_and_flags; test_architecture: agent_never_sees_raw_pii |
| NFR-05 | writes idempotent or checked | servers/*, common/repositories/* | test_servers + scenario S20 |
| NFR-06 | least privilege per node | agent/mcp_utils.py (ToolBelt), ALLOWED_TOOLS in every node | test_architecture: every_node_only_gets_the_tools..., tool_belt_blocks_other_tools |
| NFR-07 | untrusted data | common/prompts.py, agent/llm/guardrails.py | scenarios S6, S17; test_llm: cannot_be_talked_out_of_an_injection |
| NFR-08 | deterministic business decisions | common/rules.py | test_rules |
| NFR-09 | errors returned, never crash | common/responses.py | scenario S21; test_servers *_errors |
| NFR-10 | resume with same thread_id; cancel pays nothing | agent/runtime.py, approval_gate.py | scenarios S3, S19 |
| NFR-11 | tests run offline without a key (the product itself needs OpenAI or Groq) | tests/stub_llm.py (test-only) | pytest -q |
| NFR-12 | queue under 30 s | run_queue.py | measured about 4 s with the test stand-in; with a real LLM it depends on API latency |
| NFR-13 | audit rows | common/db.py audit() | test_servers: blocked_and_issued_refunds_are_audited, ticket_lifecycle |
| NFR-14 | type hints + docstrings, one file per server | all files | test_architecture: every_tool_has_a_docstring_and_type_hints |
| NFR-15 | setup.sh works on a clean checkout | app/setup.sh | verified from a fresh clone (see README section 7) |
| NFR-16 | at most 2 LLM calls per ticket; token usage printed | agent/llm/real.py, run_queue.py | test_llm: at_most_two_calls_per_ticket_in_the_ticket_graph |
| NFR-17 | approval card readable in 15 s | agent/nodes/ticket/approval_gate.py | manual (see run_queue --interactive) |
| NFR-18 | who approved which refund | refunds.approvals + audit detail | scenario S10 |

## Scenarios

| Scenario | Test (tests/test_scenarios.py unless noted) |
|---|---|
| S1 | test_s1_order_status |
| S2/S8/S14 | test_s2_s8_s14_small_refunds_are_automatic |
| S3 | test_s3_one_lead_approves..., _reject_..., _edit_amount_down_... |
| S4 | test_s4_duplicate_refund_is_explained |
| S5 | test_s5_late_refund_is_declined_with_the_reason |
| S6 | test_s6_injection_is_not_obeyed |
| S7 | test_s7_policy_answer_cites_the_rule |
| S9 | test_s9_boundary_2001_needs_a_lead |
| S10 | test_s10_two_approvers_lead_then_finance |
| S11 | test_s11_ambiguous_customer_then_clarified |
| S12 | test_s12_fraud_flag_needs_a_lead_and_is_never_mentioned |
| S13 | test_s13_privacy_request_is_refused_without_personal_data |
| S15/S17 | test_s15_s17_incident_flow |
| S16 | test_s16_rollback_is_proposed_once_and_never_executed |
| S18 | test_servers.py::test_internal_rules_are_unreachable |
| S19 | test_s19_cancel_leaves_ticket_pending_and_resumable |
| S20 | test_s20_running_the_same_ticket_twice_pays_once |
| S21 | test_s21_unknown_order_is_escalated_without_crashing |
| S22 | test_s22_edit_above_price_is_refused |
| S23 | test_s23_new_ticket_handled_then_rechecked_later |
| S24 | test_s24_linked_ticket_gets_incident_message_and_no_refund |
