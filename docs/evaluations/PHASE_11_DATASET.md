> Publication note: this inherited document records private-baseline phase evolution/evidence. Paths and commit references were sanitized. Current portfolio behavior is summarized in README and docs/portfolio; fresh-copy verification is in PHASE_13A. Historical source hashes are not a new certification of this sanitized snapshot.

# Phase 11 versioned evaluation dataset

Version `1.0`; deterministic synthetic seed `northstar/stable_id/v1`. The catalog is `backend/app/evaluations/datasets/v1.json`. It binds 601 unique scenario IDs to existing and new assertion-bearing pytest cases across 193 test functions. It excludes the 81 mechanical state-transition pairs from the scenario total. Full regression still runs those tests.

This extends the existing PostgreSQL fixture/evaluation system rather than creating another agent simulator. Role, resource, fault, schema and channel variants exercise different gates; these are not claimed to be 601 independent vulnerabilities. The 30 new injection cases combine six content boundaries with five distinct attack objectives, and 15 new authenticated cases independently cross each lifecycle boundary. Expected labels for dynamic planning and policy cases remain in their existing versioned datasets/tests, not derived from the model response. The catalog expected text names the boundary invariant; exact status, reason, row state and effect assertions reside in its bound test.

| Category | Scenarios |
| --- | ---: |
| approval_execution | 73 |
| authorization_tenancy | 127 |
| evidence_policy | 87 |
| operations_audit | 52 |
| ordinary_success | 21 |
| planner_injection | 129 |
| reliability_recovery | 112 |

## Reproduction

From `backend/`, with optional test dependencies installed:

```sh
TEST_DATABASE_URL=postgresql+psycopg://northstar:synthetic-local-only@localhost:55432/northstar_test .venv/bin/python -m app.evaluations.red_team --regression --output /tmp/northstar-phase11-evaluation
.venv/bin/python -m app.evaluations.red_team --list --category planner_injection
.venv/bin/python -m app.evaluations.red_team --scenario p11-b0e98a8ca953c333 --output /tmp/northstar-phase11-single
```

The scenario command also requires TEST_DATABASE_URL. Category/scenario selections may repeat. Unknown/empty selections fail. Standard runs are mock-only, with real HTTP transport disabled; optional adapter cases explicitly use mock HTTP transport. Never run two destructive fixture suites against one database; an advisory lock now enforces this.

## Scenario index

Each binding is unique. Exact status/reason/state assertions are in the bound tests. Three supplemental cases explicitly verify a concurrent independent-approval race and actual citations from another investigation/tenant.

| ID | Category | Mechanism / variant | Binding |
| --- | --- | --- | --- |
| p11-b0e98a8ca953c333 | ordinary_success | real scenarios / 0-COMPLETED-completed | `tests/test_agents.py::test_real_scenarios[0-COMPLETED-completed]` |
| p11-dfff79bec2bb3d70 | ordinary_success | real scenarios / 1-NEEDS_REVIEW-security_review_required | `tests/test_agents.py::test_real_scenarios[1-NEEDS_REVIEW-security_review_required]` |
| p11-d73fd7376b4679dc | ordinary_success | real scenarios / 2-COMPLETED-completed | `tests/test_agents.py::test_real_scenarios[2-COMPLETED-completed]` |
| p11-15f6cfadc7c0e7a0 | ordinary_success | real scenarios / 3-COMPLETED-completed | `tests/test_agents.py::test_real_scenarios[3-COMPLETED-completed]` |
| p11-3bad286370b63fce | ordinary_success | real scenarios / 4-NEEDS_REVIEW-conflicting_evidence | `tests/test_agents.py::test_real_scenarios[4-NEEDS_REVIEW-conflicting_evidence]` |
| p11-93cdfebbbc37756c | ordinary_success | real scenarios / 5-NEEDS_REVIEW-unsupported_scenario | `tests/test_agents.py::test_real_scenarios[5-NEEDS_REVIEW-unsupported_scenario]` |
| p11-22606f8d3da15247 | planner_injection | planner is deterministic and ignores goal text / base | `tests/test_agents.py::test_planner_is_deterministic_and_ignores_goal_text` |
| p11-e0aeba0f1f8e6b2f | planner_injection | budgets preserve safe evidence / limits0-step_limit | `tests/test_agents.py::test_budgets_preserve_safe_evidence[limits0-step_limit]` |
| p11-494c63d41fd50eac | planner_injection | budgets preserve safe evidence / limits1-tool_call_limit | `tests/test_agents.py::test_budgets_preserve_safe_evidence[limits1-tool_call_limit]` |
| p11-74e4eb9f22a21738 | planner_injection | budgets preserve safe evidence / limits2-planning_iteration_limit | `tests/test_agents.py::test_budgets_preserve_safe_evidence[limits2-planning_iteration_limit]` |
| p11-e51861dc8e2a7ae3 | planner_injection | budgets preserve safe evidence / limits3-observation_size_limit | `tests/test_agents.py::test_budgets_preserve_safe_evidence[limits3-observation_size_limit]` |
| p11-60f4448941b7b8b2 | planner_injection | foreign customer denied / 0 | `tests/test_agents.py::test_foreign_customer_denied[0]` |
| p11-a967b328ca0ffb88 | planner_injection | foreign customer denied / 1 | `tests/test_agents.py::test_foreign_customer_denied[1]` |
| p11-da70e25df30befba | planner_injection | optional foreign ticket not followed / base | `tests/test_agents.py::test_optional_foreign_ticket_not_followed` |
| p11-39c390e46c56d9f0 | planner_injection | unauthenticated and permission denied / base | `tests/test_agents.py::test_unauthenticated_and_permission_denied` |
| p11-74eef895c0d69727 | planner_injection | request schema / extra0 | `tests/test_agents.py::test_request_schema[extra0]` |
| p11-e63cc7b0f380c4e4 | planner_injection | request schema / extra1 | `tests/test_agents.py::test_request_schema[extra1]` |
| p11-e14641ae0fdc8e4c | planner_injection | request schema / extra2 | `tests/test_agents.py::test_request_schema[extra2]` |
| p11-576936579797abde | planner_injection | request schema / extra3 | `tests/test_agents.py::test_request_schema[extra3]` |
| p11-ff894b0a5fd108b9 | planner_injection | request schema / extra4 | `tests/test_agents.py::test_request_schema[extra4]` |
| p11-b96c365da70f658b | planner_injection | api csrf size get isolation / base | `tests/test_agents.py::test_api_csrf_size_get_isolation` |
| p11-6367b9619547e2ef | planner_injection | invalid plan fails closed / planner0-unknown_tool | `tests/test_agents.py::test_invalid_plan_fails_closed[planner0-unknown_tool]` |
| p11-e27ce4d6d696e35e | planner_injection | invalid plan fails closed / planner1-invalid_tool_arguments | `tests/test_agents.py::test_invalid_plan_fails_closed[planner1-invalid_tool_arguments]` |
| p11-4ffb12d1beef4d2f | planner_injection | invalid plan fails closed / planner2-unsupported_version | `tests/test_agents.py::test_invalid_plan_fails_closed[planner2-unsupported_version]` |
| p11-3d5ced15c2262f93 | planner_injection | invalid plan fails closed / planner3-resource_outside_investigation | `tests/test_agents.py::test_invalid_plan_fails_closed[planner3-resource_outside_investigation]` |
| p11-8b95034677440a05 | planner_injection | invalid plan fails closed / planner4-resource_outside_investigation | `tests/test_agents.py::test_invalid_plan_fails_closed[planner4-resource_outside_investigation]` |
| p11-8f5b966714db4269 | planner_injection | unauthorized definition / base | `tests/test_agents.py::test_unauthorized_definition` |
| p11-34b6453318eec776 | planner_injection | repeated calls / base | `tests/test_agents.py::test_repeated_calls` |
| p11-f6fc313a93c94a59 | planner_injection | planner failure and timeout / base | `tests/test_agents.py::test_planner_failure_and_timeout` |
| p11-b35c82516924650d | planner_injection | cancellation and capacity / base | `tests/test_agents.py::test_cancellation_and_capacity` |
| p11-1830779fffb6afa1 | planner_injection | prompt injection ignored and no business writes / base | `tests/test_agents.py::test_prompt_injection_ignored_and_no_business_writes` |
| p11-75bc1d5a8f5f28f6 | planner_injection | missing evidence / base | `tests/test_agents.py::test_missing_evidence` |
| p11-e78b9a3765944c67 | planner_injection | stale role cannot start tools / base | `tests/test_agents.py::test_stale_role_cannot_start_tools` |
| p11-7bd51d6abadbd1f2 | planner_injection | store retention and actor ownership / base | `tests/test_agents.py::test_store_retention_and_actor_ownership` |
| p11-f615c3e36a42e819 | planner_injection | invalid initial plan and ungrounded interpretation / base | `tests/test_agents.py::test_invalid_initial_plan_and_ungrounded_interpretation` |
| p11-8826c0b6245c39b5 | planner_injection | provider cannot mutate collected evidence / base | `tests/test_agents.py::test_provider_cannot_mutate_collected_evidence` |
| p11-c5a4f19541e8ecb5 | planner_injection | real tool failures / exception | `tests/test_agents.py::test_real_tool_failures[exception]` |
| p11-9646584272a85843 | planner_injection | real tool failures / timeout | `tests/test_agents.py::test_real_tool_failures[timeout]` |
| p11-cb8cda8ed959e99b | planner_injection | empty policy evidence is not fabricated / base | `tests/test_agents.py::test_empty_policy_evidence_is_not_fabricated` |
| p11-0eefc691cd3afb1f | planner_injection | observations reference policy versions / base | `tests/test_agents.py::test_observations_reference_policy_versions` |
| p11-15c224fc8f7368f2 | planner_injection | database failure stops without evidence / base | `tests/test_agents.py::test_database_failure_stops_without_evidence` |
| p11-903020f33c01bab4 | planner_injection | cancellation drains actual tool / base | `tests/test_agents.py::test_cancellation_drains_actual_tool` |
| p11-c9e770e338532848 | planner_injection | history pagination is bounded / base | `tests/test_agents.py::test_history_pagination_is_bounded` |
| p11-10481e5b2c7b74a4 | authorization_tenancy | login and me / base | `tests/test_authentication.py::test_login_and_me` |
| p11-a194afbb41fa53bf | authorization_tenancy | cookie properties / base | `tests/test_authentication.py::test_cookie_properties` |
| p11-eb28a53c6b7587b5 | authorization_tenancy | https cookie flag / base | `tests/test_authentication.py::test_https_cookie_flag` |
| p11-ea5f120ee13739d0 | authorization_tenancy | generic invalid credentials / operator.0@example.com | `tests/test_authentication.py::test_generic_invalid_credentials[operator.0@example.com]` |
| p11-25d12e517fa720f5 | authorization_tenancy | generic invalid credentials / missing@example.com | `tests/test_authentication.py::test_generic_invalid_credentials[missing@example.com]` |
| p11-ee2fd4a8e7b0a8c2 | authorization_tenancy | invalidated session / expired | `tests/test_authentication.py::test_invalidated_session[expired]` |
| p11-54880ed49d1ad52b | authorization_tenancy | invalidated session / revoked | `tests/test_authentication.py::test_invalidated_session[revoked]` |
| p11-5aac8d466f089678 | authorization_tenancy | invalidated session / disabled | `tests/test_authentication.py::test_invalidated_session[disabled]` |
| p11-e9452a22108f0c53 | authorization_tenancy | logout revokes cookie and replay / base | `tests/test_authentication.py::test_logout_revokes_cookie_and_replay` |
| p11-e2acd316049b59d1 | authorization_tenancy | login rotates browser session / base | `tests/test_authentication.py::test_login_rotates_browser_session` |
| p11-06aabaa66bde5e63 | authorization_tenancy | csrf login rejected / None | `tests/test_authentication.py::test_csrf_login_rejected[None]` |
| p11-d9d55b5233c32eba | authorization_tenancy | csrf login rejected / null | `tests/test_authentication.py::test_csrf_login_rejected[null]` |
| p11-dda37c9f9cbc24df | authorization_tenancy | csrf login rejected / https://attacker.example.com | `tests/test_authentication.py::test_csrf_login_rejected[https://attacker.example.com]` |
| p11-ff4a79d8f8c6913f | authorization_tenancy | csrf login rejected / http://localhost:3000.attacker.example.com | `tests/test_authentication.py::test_csrf_login_rejected[http://localhost:3000.attacker.example.com]` |
| p11-546342a48a3d6259 | authorization_tenancy | csrf logout cannot revoke session / base | `tests/test_authentication.py::test_csrf_logout_cannot_revoke_session` |
| p11-9781ca9330a42e7a | authorization_tenancy | cross site fetch rejected / base | `tests/test_authentication.py::test_cross_site_fetch_rejected` |
| p11-fcb15c675dbb9753 | authorization_tenancy | failed login limit and window / base | `tests/test_authentication.py::test_failed_login_limit_and_window` |
| p11-fe9018a3afb6e22b | authorization_tenancy | client limit blocks unknown identity spray / base | `tests/test_authentication.py::test_client_limit_blocks_unknown_identity_spray` |
| p11-441e6b13175baad5 | authorization_tenancy | server side permissions / operator-403-403 | `tests/test_authentication.py::test_server_side_permissions[operator-403-403]` |
| p11-e23c5420e8efe19c | authorization_tenancy | server side permissions / reviewer-403-200 | `tests/test_authentication.py::test_server_side_permissions[reviewer-403-200]` |
| p11-be7397ee2bf210c8 | authorization_tenancy | server side permissions / admin-200-200 | `tests/test_authentication.py::test_server_side_permissions[admin-200-200]` |
| p11-55efe3ca2584e327 | authorization_tenancy | server side permissions / auditor-403-403 | `tests/test_authentication.py::test_server_side_permissions[auditor-403-403]` |
| p11-0efb926952f3c59d | authorization_tenancy | exact permission matrix / operator-expected0 | `tests/test_authentication.py::test_exact_permission_matrix[operator-expected0]` |
| p11-d7544b428dfa3cd5 | authorization_tenancy | exact permission matrix / reviewer-expected1 | `tests/test_authentication.py::test_exact_permission_matrix[reviewer-expected1]` |
| p11-2c234c7f6ef3b586 | authorization_tenancy | exact permission matrix / admin-expected2 | `tests/test_authentication.py::test_exact_permission_matrix[admin-expected2]` |
| p11-e99a67996671e4b3 | authorization_tenancy | exact permission matrix / auditor-expected3 | `tests/test_authentication.py::test_exact_permission_matrix[auditor-expected3]` |
| p11-8157929205043083 | authorization_tenancy | privilege and tenant escalation rejected / base | `tests/test_authentication.py::test_privilege_and_tenant_escalation_rejected` |
| p11-f7c495e16fe0cc29 | authorization_tenancy | roles are revalidated from database / base | `tests/test_authentication.py::test_roles_are_revalidated_from_database` |
| p11-609d0681e6350972 | authorization_tenancy | tenant isolation and non disclosing 404 / customers-customer-10 | `tests/test_authentication.py::test_tenant_isolation_and_non_disclosing_404[customers-customer-10]` |
| p11-0b3e8ff4b3071f96 | authorization_tenancy | tenant isolation and non disclosing 404 / accounts-account-10 | `tests/test_authentication.py::test_tenant_isolation_and_non_disclosing_404[accounts-account-10]` |
| p11-27e049ea7471702b | authorization_tenancy | tenant isolation and non disclosing 404 / tickets-ticket-15 | `tests/test_authentication.py::test_tenant_isolation_and_non_disclosing_404[tickets-ticket-15]` |
| p11-d8c31f1771cfb9a3 | authorization_tenancy | unauthenticated rejected / customers | `tests/test_authentication.py::test_unauthenticated_rejected[customers]` |
| p11-c9e3b003e65986d0 | authorization_tenancy | unauthenticated rejected / accounts | `tests/test_authentication.py::test_unauthenticated_rejected[accounts]` |
| p11-a226151bdf60541c | authorization_tenancy | unauthenticated rejected / tickets | `tests/test_authentication.py::test_unauthenticated_rejected[tickets]` |
| p11-2475251805fe7362 | authorization_tenancy | unauthenticated rejected / customers/00000000-0000-0000-0000-000000000000 | `tests/test_authentication.py::test_unauthenticated_rejected[customers/00000000-0000-0000-0000-000000000000]` |
| p11-6b25a7684e14c6c5 | authorization_tenancy | unauthenticated rejected / auth/me | `tests/test_authentication.py::test_unauthenticated_rejected[auth/me]` |
| p11-b6b5182d423a2f3c | authorization_tenancy | pagination validation / limit=0 | `tests/test_authentication.py::test_pagination_validation[limit=0]` |
| p11-2e23a8ff7bfb9ac4 | authorization_tenancy | pagination validation / limit=101 | `tests/test_authentication.py::test_pagination_validation[limit=101]` |
| p11-6a007259a3156f56 | authorization_tenancy | pagination validation / offset=-1 | `tests/test_authentication.py::test_pagination_validation[offset=-1]` |
| p11-fb0e28a13db0f1b3 | authorization_tenancy | pagination validation / offset=10001 | `tests/test_authentication.py::test_pagination_validation[offset=10001]` |
| p11-bbd91eff8566521a | authorization_tenancy | pagination validation / limit=not-a-number | `tests/test_authentication.py::test_pagination_validation[limit=not-a-number]` |
| p11-6d78e954042e545a | authorization_tenancy | pagination validation / role=admin | `tests/test_authentication.py::test_pagination_validation[role=admin]` |
| p11-5f750525e0ab2350 | authorization_tenancy | invalid uuid and no pii response / base | `tests/test_authentication.py::test_invalid_uuid_and_no_pii_response` |
| p11-fde3b215102b125d | authorization_tenancy | tampered token rejected / base | `tests/test_authentication.py::test_tampered_token_rejected` |
| p11-b2a0861fda3803c8 | authorization_tenancy | audit secrets and append only / base | `tests/test_authentication.py::test_audit_secrets_and_append_only` |
| p11-0d6fd863d061e92e | authorization_tenancy | authentication seed idempotent / base | `tests/test_authentication.py::test_authentication_seed_idempotent` |
| p11-819b9e5d6ff2410a | authorization_tenancy | production demo seed refused / base | `tests/test_authentication.py::test_production_demo_seed_refused` |
| p11-c1c8823f7bc57825 | authorization_tenancy | production cookie configuration / base | `tests/test_authentication.py::test_production_cookie_configuration` |
| p11-acee3f1dcb36ade0 | authorization_tenancy | tenant repository is explicit / base | `tests/test_authentication.py::test_tenant_repository_is_explicit` |
| p11-6e0f093ada9b5df3 | authorization_tenancy | session tenant foreign key / base | `tests/test_authentication.py::test_session_tenant_foreign_key` |
| p11-77277ad75178bbeb | authorization_tenancy | session persists across connections / base | `tests/test_authentication.py::test_session_persists_across_connections` |
| p11-3a8d2eeb952c6450 | authorization_tenancy | upgrade from phase0 preserves data / base | `tests/test_authentication.py::test_upgrade_from_phase0_preserves_data` |
| p11-6d7dc5a7573fbfbf | authorization_tenancy | production setting cannot be bypassed by seed argument / base | `tests/test_authentication.py::test_production_setting_cannot_be_bypassed_by_seed_argument` |
| p11-46eb6d328791fe84 | authorization_tenancy | auth seed does not activate non fixture users / base | `tests/test_authentication.py::test_auth_seed_does_not_activate_non_fixture_users` |
| p11-e02063d6e270e1c2 | ordinary_success | authorized actions and replay / create_customer_note-3 | `tests/test_controlled_execution.py::test_authorized_actions_and_replay[create_customer_note-3]` |
| p11-05699e37e037e06c | ordinary_success | authorized actions and replay / add_ticket_note-3 | `tests/test_controlled_execution.py::test_authorized_actions_and_replay[add_ticket_note-3]` |
| p11-6dff1bb59fb730e4 | ordinary_success | authorized actions and replay / request_account_reactivation-3 | `tests/test_controlled_execution.py::test_authorized_actions_and_replay[request_account_reactivation-3]` |
| p11-f541b2b6a93e56c9 | ordinary_success | authorized actions and replay / reactivate_account-3 | `tests/test_controlled_execution.py::test_authorized_actions_and_replay[reactivate_account-3]` |
| p11-1e0acf21c2fae50e | ordinary_success | authorized actions and replay / close_duplicate_ticket-2 | `tests/test_controlled_execution.py::test_authorized_actions_and_replay[close_duplicate_ticket-2]` |
| p11-92539e51eddb8db7 | approval_execution | fail closed / self | `tests/test_controlled_execution.py::test_fail_closed[self]` |
| p11-51e22661b1e50c5e | approval_execution | fail closed / foreign | `tests/test_controlled_execution.py::test_fail_closed[foreign]` |
| p11-134bc4d0cfa8ff9f | approval_execution | fail closed / operator | `tests/test_controlled_execution.py::test_fail_closed[operator]` |
| p11-ff9c850680190ff3 | approval_execution | fail closed / duplicate | `tests/test_controlled_execution.py::test_fail_closed[duplicate]` |
| p11-9bdd9221d53381f1 | approval_execution | fail closed / expiry | `tests/test_controlled_execution.py::test_fail_closed[expiry]` |
| p11-f601b7072d472ae6 | approval_execution | fail closed / cancel | `tests/test_controlled_execution.py::test_fail_closed[cancel]` |
| p11-e8da65feda6125b7 | approval_execution | fail closed / resource | `tests/test_controlled_execution.py::test_fail_closed[resource]` |
| p11-38c2ae075f61ef95 | approval_execution | fail closed / policy | `tests/test_controlled_execution.py::test_fail_closed[policy]` |
| p11-235c8a0d9379381d | approval_execution | fail closed / reviewer_role | `tests/test_controlled_execution.py::test_fail_closed[reviewer_role]` |
| p11-97809b908857b7b9 | approval_execution | fail closed / reviewer_session | `tests/test_controlled_execution.py::test_fail_closed[reviewer_session]` |
| p11-2276f6d4094c2cff | approval_execution | fail closed / actor_role | `tests/test_controlled_execution.py::test_fail_closed[actor_role]` |
| p11-821afa453a9bffaa | approval_execution | fail closed / missing_approval | `tests/test_controlled_execution.py::test_fail_closed[missing_approval]` |
| p11-7dffb4f1e50d8bd8 | approval_execution | fail closed / forged_approval | `tests/test_controlled_execution.py::test_fail_closed[forged_approval]` |
| p11-d19bf58b276043e1 | approval_execution | fail closed / verification | `tests/test_controlled_execution.py::test_fail_closed[verification]` |
| p11-df3359e9b40bd9fe | approval_execution | fail closed / mutation | `tests/test_controlled_execution.py::test_fail_closed[mutation]` |
| p11-1912111a948b5dff | approval_execution | fail closed / stale_evidence | `tests/test_controlled_execution.py::test_fail_closed[stale_evidence]` |
| p11-78fe3a2aeea7e8d5 | approval_execution | concurrent duplicate / base | `tests/test_controlled_execution.py::test_concurrent_duplicate` |
| p11-eac5be17f26963ce | approval_execution | http approval and execution / base | `tests/test_controlled_execution.py::test_http_approval_and_execution` |
| p11-2bd673c46f599fea | approval_execution | deadline crossing rolls back / base | `tests/test_controlled_execution.py::test_deadline_crossing_rolls_back` |
| p11-c9b4fac13f6390e8 | approval_execution | database statement failure rolls back / base | `tests/test_controlled_execution.py::test_database_statement_failure_rolls_back` |
| p11-4b6177898351654d | approval_execution | forged execution fields rejected / tenant_id | `tests/test_controlled_execution.py::test_forged_execution_fields_rejected[tenant_id]` |
| p11-355edc33822952ea | approval_execution | forged execution fields rejected / actor_id | `tests/test_controlled_execution.py::test_forged_execution_fields_rejected[actor_id]` |
| p11-28a554dcf2debfd3 | approval_execution | forged execution fields rejected / reviewer_id | `tests/test_controlled_execution.py::test_forged_execution_fields_rejected[reviewer_id]` |
| p11-9f50e33699dc1f21 | approval_execution | forged execution fields rejected / permissions | `tests/test_controlled_execution.py::test_forged_execution_fields_rejected[permissions]` |
| p11-a17c5a6e57b71d9d | approval_execution | changed proposal invalidates approval / base | `tests/test_controlled_execution.py::test_changed_proposal_invalidates_approval` |
| p11-1193e01e52a25714 | approval_execution | response lost after commit reconciles by same key / base | `tests/test_controlled_execution.py::test_response_lost_after_commit_reconciles_by_same_key` |
| p11-4f8a3baa316246da | approval_execution | verifier rejects unintended effects / unintended_customer_change | `tests/test_controlled_execution.py::test_verifier_rejects_unintended_effects[unintended_customer_change]` |
| p11-cacd558640e043ec | approval_execution | verifier rejects unintended effects / wrong_record_kind | `tests/test_controlled_execution.py::test_verifier_rejects_unintended_effects[wrong_record_kind]` |
| p11-387dbce86a5b6e8f | approval_execution | duplicate policy checks parent account state / states0-REQUIRE_APPROVAL | `tests/test_controlled_execution.py::test_duplicate_policy_checks_parent_account_state[states0-REQUIRE_APPROVAL]` |
| p11-4c7a639f38cc014c | approval_execution | duplicate policy checks parent account state / states1-DENY | `tests/test_controlled_execution.py::test_duplicate_policy_checks_parent_account_state[states1-DENY]` |
| p11-1e6468a9c08aa2a8 | reliability_recovery | reliability matrix / success-create_customer_note-3 | `tests/test_durable_jobs.py::test_reliability_matrix[success-create_customer_note-3]` |
| p11-ca87e5afc3eea646 | reliability_recovery | reliability matrix / success-add_ticket_note-3 | `tests/test_durable_jobs.py::test_reliability_matrix[success-add_ticket_note-3]` |
| p11-0c6a9da4c3132da4 | reliability_recovery | reliability matrix / success-request_account_reactivation-3 | `tests/test_durable_jobs.py::test_reliability_matrix[success-request_account_reactivation-3]` |
| p11-40bf9ebd161be320 | reliability_recovery | reliability matrix / success-reactivate_account-3 | `tests/test_durable_jobs.py::test_reliability_matrix[success-reactivate_account-3]` |
| p11-9e3d2ddc57421afd | reliability_recovery | reliability matrix / success-close_duplicate_ticket-2 | `tests/test_durable_jobs.py::test_reliability_matrix[success-close_duplicate_ticket-2]` |
| p11-82b800018db032cc | reliability_recovery | reliability matrix / before_execution-create_customer_note-3 | `tests/test_durable_jobs.py::test_reliability_matrix[before_execution-create_customer_note-3]` |
| p11-5b3766d94a874ece | reliability_recovery | reliability matrix / before_execution-add_ticket_note-3 | `tests/test_durable_jobs.py::test_reliability_matrix[before_execution-add_ticket_note-3]` |
| p11-cd498679f764e617 | reliability_recovery | reliability matrix / before_execution-request_account_reactivation-3 | `tests/test_durable_jobs.py::test_reliability_matrix[before_execution-request_account_reactivation-3]` |
| p11-30399442d3973c69 | reliability_recovery | reliability matrix / before_execution-reactivate_account-3 | `tests/test_durable_jobs.py::test_reliability_matrix[before_execution-reactivate_account-3]` |
| p11-d7fb983d295b4ba6 | reliability_recovery | reliability matrix / before_execution-close_duplicate_ticket-2 | `tests/test_durable_jobs.py::test_reliability_matrix[before_execution-close_duplicate_ticket-2]` |
| p11-0c65704a193fc318 | reliability_recovery | reliability matrix / after_commit-create_customer_note-3 | `tests/test_durable_jobs.py::test_reliability_matrix[after_commit-create_customer_note-3]` |
| p11-7b6430d070433287 | reliability_recovery | reliability matrix / after_commit-add_ticket_note-3 | `tests/test_durable_jobs.py::test_reliability_matrix[after_commit-add_ticket_note-3]` |
| p11-2944d226f7a8493c | reliability_recovery | reliability matrix / after_commit-request_account_reactivation-3 | `tests/test_durable_jobs.py::test_reliability_matrix[after_commit-request_account_reactivation-3]` |
| p11-e776e491ae64cc70 | reliability_recovery | reliability matrix / after_commit-reactivate_account-3 | `tests/test_durable_jobs.py::test_reliability_matrix[after_commit-reactivate_account-3]` |
| p11-58d939e58b0dd351 | reliability_recovery | reliability matrix / after_commit-close_duplicate_ticket-2 | `tests/test_durable_jobs.py::test_reliability_matrix[after_commit-close_duplicate_ticket-2]` |
| p11-ad64f8d869e0fd0d | reliability_recovery | reliability matrix / lease_expiry-create_customer_note-3 | `tests/test_durable_jobs.py::test_reliability_matrix[lease_expiry-create_customer_note-3]` |
| p11-f08559f964f08f7d | reliability_recovery | reliability matrix / lease_expiry-add_ticket_note-3 | `tests/test_durable_jobs.py::test_reliability_matrix[lease_expiry-add_ticket_note-3]` |
| p11-5dfdddf1b7caddb2 | reliability_recovery | reliability matrix / lease_expiry-request_account_reactivation-3 | `tests/test_durable_jobs.py::test_reliability_matrix[lease_expiry-request_account_reactivation-3]` |
| p11-0a6b1dfee505c963 | reliability_recovery | reliability matrix / lease_expiry-reactivate_account-3 | `tests/test_durable_jobs.py::test_reliability_matrix[lease_expiry-reactivate_account-3]` |
| p11-5315a778948db133 | reliability_recovery | reliability matrix / lease_expiry-close_duplicate_ticket-2 | `tests/test_durable_jobs.py::test_reliability_matrix[lease_expiry-close_duplicate_ticket-2]` |
| p11-b6032b89c6bd12fa | reliability_recovery | reliability matrix / session_expiry-create_customer_note-3 | `tests/test_durable_jobs.py::test_reliability_matrix[session_expiry-create_customer_note-3]` |
| p11-53dee15338779fde | reliability_recovery | reliability matrix / session_expiry-add_ticket_note-3 | `tests/test_durable_jobs.py::test_reliability_matrix[session_expiry-add_ticket_note-3]` |
| p11-c50432782f461bf0 | reliability_recovery | reliability matrix / session_expiry-request_account_reactivation-3 | `tests/test_durable_jobs.py::test_reliability_matrix[session_expiry-request_account_reactivation-3]` |
| p11-a604f58eb02c549f | reliability_recovery | reliability matrix / session_expiry-reactivate_account-3 | `tests/test_durable_jobs.py::test_reliability_matrix[session_expiry-reactivate_account-3]` |
| p11-a40fb35cced2cf4c | reliability_recovery | reliability matrix / session_expiry-close_duplicate_ticket-2 | `tests/test_durable_jobs.py::test_reliability_matrix[session_expiry-close_duplicate_ticket-2]` |
| p11-ae7574c783df0209 | reliability_recovery | reliability matrix / role_revoked-create_customer_note-3 | `tests/test_durable_jobs.py::test_reliability_matrix[role_revoked-create_customer_note-3]` |
| p11-373fb16e091f0486 | reliability_recovery | reliability matrix / role_revoked-add_ticket_note-3 | `tests/test_durable_jobs.py::test_reliability_matrix[role_revoked-add_ticket_note-3]` |
| p11-6957defcf3ce19b1 | reliability_recovery | reliability matrix / role_revoked-request_account_reactivation-3 | `tests/test_durable_jobs.py::test_reliability_matrix[role_revoked-request_account_reactivation-3]` |
| p11-d9f22029e124dea4 | reliability_recovery | reliability matrix / role_revoked-reactivate_account-3 | `tests/test_durable_jobs.py::test_reliability_matrix[role_revoked-reactivate_account-3]` |
| p11-0709d49cd8e3c1a4 | reliability_recovery | reliability matrix / role_revoked-close_duplicate_ticket-2 | `tests/test_durable_jobs.py::test_reliability_matrix[role_revoked-close_duplicate_ticket-2]` |
| p11-df84e8917b363a7a | reliability_recovery | reliability matrix / policy_changed-create_customer_note-3 | `tests/test_durable_jobs.py::test_reliability_matrix[policy_changed-create_customer_note-3]` |
| p11-d4a2c70506f5e588 | reliability_recovery | reliability matrix / policy_changed-add_ticket_note-3 | `tests/test_durable_jobs.py::test_reliability_matrix[policy_changed-add_ticket_note-3]` |
| p11-32f4b6aa6c2fcf25 | reliability_recovery | reliability matrix / policy_changed-request_account_reactivation-3 | `tests/test_durable_jobs.py::test_reliability_matrix[policy_changed-request_account_reactivation-3]` |
| p11-26dd720630c51420 | reliability_recovery | reliability matrix / policy_changed-reactivate_account-3 | `tests/test_durable_jobs.py::test_reliability_matrix[policy_changed-reactivate_account-3]` |
| p11-3f44488e5e5d348d | reliability_recovery | reliability matrix / policy_changed-close_duplicate_ticket-2 | `tests/test_durable_jobs.py::test_reliability_matrix[policy_changed-close_duplicate_ticket-2]` |
| p11-e21c6bd12fa38ef5 | reliability_recovery | reliability matrix / resource_changed-create_customer_note-3 | `tests/test_durable_jobs.py::test_reliability_matrix[resource_changed-create_customer_note-3]` |
| p11-e87db8bf7e2f267e | reliability_recovery | reliability matrix / resource_changed-add_ticket_note-3 | `tests/test_durable_jobs.py::test_reliability_matrix[resource_changed-add_ticket_note-3]` |
| p11-5d660b1be04df370 | reliability_recovery | reliability matrix / resource_changed-request_account_reactivation-3 | `tests/test_durable_jobs.py::test_reliability_matrix[resource_changed-request_account_reactivation-3]` |
| p11-46b946db969f5eb5 | reliability_recovery | reliability matrix / resource_changed-reactivate_account-3 | `tests/test_durable_jobs.py::test_reliability_matrix[resource_changed-reactivate_account-3]` |
| p11-a18ed87ead10f29b | reliability_recovery | reliability matrix / resource_changed-close_duplicate_ticket-2 | `tests/test_durable_jobs.py::test_reliability_matrix[resource_changed-close_duplicate_ticket-2]` |
| p11-48b80941b36b6119 | reliability_recovery | reliability matrix / cancel-create_customer_note-3 | `tests/test_durable_jobs.py::test_reliability_matrix[cancel-create_customer_note-3]` |
| p11-052a2c050bfa44f0 | reliability_recovery | reliability matrix / cancel-add_ticket_note-3 | `tests/test_durable_jobs.py::test_reliability_matrix[cancel-add_ticket_note-3]` |
| p11-82ae84e8d369bdac | reliability_recovery | reliability matrix / cancel-request_account_reactivation-3 | `tests/test_durable_jobs.py::test_reliability_matrix[cancel-request_account_reactivation-3]` |
| p11-c1c1ad6b1e37e493 | reliability_recovery | reliability matrix / cancel-reactivate_account-3 | `tests/test_durable_jobs.py::test_reliability_matrix[cancel-reactivate_account-3]` |
| p11-1bf6fde74f8896aa | reliability_recovery | reliability matrix / cancel-close_duplicate_ticket-2 | `tests/test_durable_jobs.py::test_reliability_matrix[cancel-close_duplicate_ticket-2]` |
| p11-62551026d7a49b24 | reliability_recovery | reliability matrix / serialization-create_customer_note-3 | `tests/test_durable_jobs.py::test_reliability_matrix[serialization-create_customer_note-3]` |
| p11-599aceefa8ed3d2f | reliability_recovery | reliability matrix / serialization-add_ticket_note-3 | `tests/test_durable_jobs.py::test_reliability_matrix[serialization-add_ticket_note-3]` |
| p11-9237e80c9ccc9107 | reliability_recovery | reliability matrix / serialization-request_account_reactivation-3 | `tests/test_durable_jobs.py::test_reliability_matrix[serialization-request_account_reactivation-3]` |
| p11-5bc31b99b7c98ae9 | reliability_recovery | reliability matrix / serialization-reactivate_account-3 | `tests/test_durable_jobs.py::test_reliability_matrix[serialization-reactivate_account-3]` |
| p11-092bf188b704fcb6 | reliability_recovery | reliability matrix / serialization-close_duplicate_ticket-2 | `tests/test_durable_jobs.py::test_reliability_matrix[serialization-close_duplicate_ticket-2]` |
| p11-86d0f99ccb951e37 | reliability_recovery | reliability matrix / exhaustion-create_customer_note-3 | `tests/test_durable_jobs.py::test_reliability_matrix[exhaustion-create_customer_note-3]` |
| p11-4a8786c2f2408cff | reliability_recovery | reliability matrix / exhaustion-add_ticket_note-3 | `tests/test_durable_jobs.py::test_reliability_matrix[exhaustion-add_ticket_note-3]` |
| p11-64ad87cda5c3a40d | reliability_recovery | reliability matrix / exhaustion-request_account_reactivation-3 | `tests/test_durable_jobs.py::test_reliability_matrix[exhaustion-request_account_reactivation-3]` |
| p11-26f4c9b1def346fe | reliability_recovery | reliability matrix / exhaustion-reactivate_account-3 | `tests/test_durable_jobs.py::test_reliability_matrix[exhaustion-reactivate_account-3]` |
| p11-b5bd6d09a236e4f4 | reliability_recovery | reliability matrix / exhaustion-close_duplicate_ticket-2 | `tests/test_durable_jobs.py::test_reliability_matrix[exhaustion-close_duplicate_ticket-2]` |
| p11-7ae522abcbda6c99 | reliability_recovery | expired approval queued / base | `tests/test_durable_jobs.py::test_expired_approval_queued` |
| p11-45fec91fbbfce0cd | reliability_recovery | two workers fencing and cancellation race / base | `tests/test_durable_jobs.py::test_two_workers_fencing_and_cancellation_race` |
| p11-754ba91ab646388a | reliability_recovery | lease expiration fences stale worker / base | `tests/test_durable_jobs.py::test_lease_expiration_fences_stale_worker` |
| p11-65eaea95bff713b5 | reliability_recovery | ambiguous consumption no blind retry / base | `tests/test_durable_jobs.py::test_ambiguous_consumption_no_blind_retry` |
| p11-251ae77d1dc1125a | reliability_recovery | http contracts cross tenant and csrf / base | `tests/test_durable_jobs.py::test_http_contracts_cross_tenant_and_csrf` |
| p11-f52ab07e2d59cfc8 | reliability_recovery | breaker and real connection outage / base | `tests/test_durable_jobs.py::test_breaker_and_real_connection_outage` |
| p11-1bd08753ac6ad9a0 | reliability_recovery | backoff and terminal states / base | `tests/test_durable_jobs.py::test_backoff_and_terminal_states` |
| p11-85624cbad9d493f8 | reliability_recovery | manual retry authority and budget / base | `tests/test_durable_jobs.py::test_manual_retry_authority_and_budget` |
| p11-a793ff24b25e5c9a | reliability_recovery | running cooperative cancel before mutation / base | `tests/test_durable_jobs.py::test_running_cooperative_cancel_before_mutation` |
| p11-95cfddfb4ae74842 | reliability_recovery | after commit cancel cannot claim rollback / base | `tests/test_durable_jobs.py::test_after_commit_cancel_cannot_claim_rollback` |
| p11-25ddd6ff34363052 | reliability_recovery | tenant concurrency and strict submission / base | `tests/test_durable_jobs.py::test_tenant_concurrency_and_strict_submission` |
| p11-3021236b5a4e141e | reliability_recovery | submission backpressure / MAX_QUEUE_DEPTH | `tests/test_durable_jobs.py::test_submission_backpressure[MAX_QUEUE_DEPTH]` |
| p11-5f100216b22eaf19 | reliability_recovery | submission backpressure / SUBMISSIONS_PER_MINUTE | `tests/test_durable_jobs.py::test_submission_backpressure[SUBMISSIONS_PER_MINUTE]` |
| p11-a34b9ff32d9218e3 | reliability_recovery | connection loss after commit reconciles / base | `tests/test_durable_jobs.py::test_connection_loss_after_commit_reconciles` |
| p11-8f3c5192826daeba | reliability_recovery | lease deadline during mutation rolls back / base | `tests/test_durable_jobs.py::test_lease_deadline_during_mutation_rolls_back` |
| p11-c10562738d80ce7e | reliability_recovery | retry window exhausted without execution / base | `tests/test_durable_jobs.py::test_retry_window_exhausted_without_execution` |
| p11-ba42fe1e58a1e39f | reliability_recovery | global capacity and cross tenant fairness / 1 | `tests/test_durable_jobs.py::test_global_capacity_and_cross_tenant_fairness[1]` |
| p11-fddc7aa1371b9495 | reliability_recovery | global capacity and cross tenant fairness / 4 | `tests/test_durable_jobs.py::test_global_capacity_and_cross_tenant_fairness[4]` |
| p11-6fbdaa7b7367fab8 | reliability_recovery | serialization inside mutation rolls back then retries / base | `tests/test_durable_jobs.py::test_serialization_inside_mutation_rolls_back_then_retries` |
| p11-10b9a265f4e47c25 | planner_injection | strict decision rejects unstructured authority / payload0 | `tests/test_dynamic_planning.py::test_strict_decision_rejects_unstructured_authority[payload0]` |
| p11-407928ada26a1a94 | planner_injection | strict decision rejects unstructured authority / payload1 | `tests/test_dynamic_planning.py::test_strict_decision_rejects_unstructured_authority[payload1]` |
| p11-b0001bdd32655f65 | planner_injection | strict decision rejects unstructured authority / payload2 | `tests/test_dynamic_planning.py::test_strict_decision_rejects_unstructured_authority[payload2]` |
| p11-90fda4c199d0d31e | planner_injection | strict decision rejects unstructured authority / payload3 | `tests/test_dynamic_planning.py::test_strict_decision_rejects_unstructured_authority[payload3]` |
| p11-3b64c4f501bd7bcf | planner_injection | strict decision rejects unstructured authority / payload4 | `tests/test_dynamic_planning.py::test_strict_decision_rejects_unstructured_authority[payload4]` |
| p11-44e100e3fe0624f3 | planner_injection | strict decision rejects unstructured authority / payload5 | `tests/test_dynamic_planning.py::test_strict_decision_rejects_unstructured_authority[payload5]` |
| p11-cc4ab122eb0d99ff | planner_injection | provider default and explicit configuration / base | `tests/test_dynamic_planning.py::test_provider_default_and_explicit_configuration` |
| p11-2518cdabbdaf28a3 | planner_injection | provider transport failure is safe / http-provider_unavailable | `tests/test_dynamic_planning.py::test_provider_transport_failure_is_safe[http-provider_unavailable]` |
| p11-07c5afd8a92ca228 | planner_injection | provider transport failure is safe / redirect-provider_unavailable | `tests/test_dynamic_planning.py::test_provider_transport_failure_is_safe[redirect-provider_unavailable]` |
| p11-70dfad450b373bcf | planner_injection | provider transport failure is safe / timeout-provider_timeout | `tests/test_dynamic_planning.py::test_provider_transport_failure_is_safe[timeout-provider_timeout]` |
| p11-4ca638b1c0e745c6 | planner_injection | provider transport failure is safe / size-planner_response_limit | `tests/test_dynamic_planning.py::test_provider_transport_failure_is_safe[size-planner_response_limit]` |
| p11-3269108f1f24eb45 | planner_injection | provider transport failure is safe / refusal-invalid_planner_decision | `tests/test_dynamic_planning.py::test_provider_transport_failure_is_safe[refusal-invalid_planner_decision]` |
| p11-9708816b8a13884c | planner_injection | provider transport failure is safe / malformed-invalid_planner_decision | `tests/test_dynamic_planning.py::test_provider_transport_failure_is_safe[malformed-invalid_planner_decision]` |
| p11-34e1a6be1582f79c | planner_injection | provider valid decision uses no network / base | `tests/test_dynamic_planning.py::test_provider_valid_decision_uses_no_network` |
| p11-5a84173740457a44 | planner_injection | dynamic evaluation / payment-0 | `tests/test_dynamic_planning.py::test_dynamic_evaluation[payment-0]` |
| p11-76883bc5604944cb | planner_injection | dynamic evaluation / security-0 | `tests/test_dynamic_planning.py::test_dynamic_evaluation[security-0]` |
| p11-e7ce3d0dbac87522 | planner_injection | dynamic evaluation / duplicate-0 | `tests/test_dynamic_planning.py::test_dynamic_evaluation[duplicate-0]` |
| p11-4a41d84d83000e02 | planner_injection | dynamic evaluation / reactivation-0 | `tests/test_dynamic_planning.py::test_dynamic_evaluation[reactivation-0]` |
| p11-c59c93ff92e932d9 | planner_injection | dynamic evaluation / conflict-0 | `tests/test_dynamic_planning.py::test_dynamic_evaluation[conflict-0]` |
| p11-4de22ddcbdff2abd | planner_injection | dynamic evaluation / untrusted_cross_request-0 | `tests/test_dynamic_planning.py::test_dynamic_evaluation[untrusted_cross_request-0]` |
| p11-9293bc4b1a06a1ef | planner_injection | dynamic evaluation / payment-1 | `tests/test_dynamic_planning.py::test_dynamic_evaluation[payment-1]` |
| p11-07c06cf5968df37b | planner_injection | dynamic evaluation / security-1 | `tests/test_dynamic_planning.py::test_dynamic_evaluation[security-1]` |
| p11-2a84b8ce12d5e8a4 | planner_injection | dynamic evaluation / duplicate-1 | `tests/test_dynamic_planning.py::test_dynamic_evaluation[duplicate-1]` |
| p11-bca5c118fabda8d8 | planner_injection | dynamic evaluation / reactivation-1 | `tests/test_dynamic_planning.py::test_dynamic_evaluation[reactivation-1]` |
| p11-231739313d937fcd | planner_injection | dynamic evaluation / conflict-1 | `tests/test_dynamic_planning.py::test_dynamic_evaluation[conflict-1]` |
| p11-8150e88eaf5f92b6 | planner_injection | dynamic evaluation / untrusted_cross_request-1 | `tests/test_dynamic_planning.py::test_dynamic_evaluation[untrusted_cross_request-1]` |
| p11-cd55dd43b33d5b02 | planner_injection | dynamic evaluation / missing_policy | `tests/test_dynamic_planning.py::test_dynamic_evaluation[missing_policy]` |
| p11-f0f861dba3a89fb2 | planner_injection | dynamic evaluation / future_superseded | `tests/test_dynamic_planning.py::test_dynamic_evaluation[future_superseded]` |
| p11-98cf68ae9243a227 | planner_injection | dynamic evaluation / missing_transactions | `tests/test_dynamic_planning.py::test_dynamic_evaluation[missing_transactions]` |
| p11-8e87a28798f45fae | planner_injection | dynamic evaluation / ticket_injection | `tests/test_dynamic_planning.py::test_dynamic_evaluation[ticket_injection]` |
| p11-474280e0c925d926 | planner_injection | dynamic evaluation / policy_injection | `tests/test_dynamic_planning.py::test_dynamic_evaluation[policy_injection]` |
| p11-e176b38033443a69 | planner_injection | dynamic evaluation / cross_tenant | `tests/test_dynamic_planning.py::test_dynamic_evaluation[cross_tenant]` |
| p11-d6fbc523b3196ec3 | planner_injection | dynamic evaluation / unknown_tool | `tests/test_dynamic_planning.py::test_dynamic_evaluation[unknown_tool]` |
| p11-6f93cef124db5ea2 | planner_injection | dynamic evaluation / write_tool | `tests/test_dynamic_planning.py::test_dynamic_evaluation[write_tool]` |
| p11-22b08292d72f0ab1 | planner_injection | dynamic evaluation / invalid_version | `tests/test_dynamic_planning.py::test_dynamic_evaluation[invalid_version]` |
| p11-ab2c077d374571fc | planner_injection | dynamic evaluation / invalid_arguments | `tests/test_dynamic_planning.py::test_dynamic_evaluation[invalid_arguments]` |
| p11-fb516ed52fe33c8f | planner_injection | dynamic evaluation / forged_context | `tests/test_dynamic_planning.py::test_dynamic_evaluation[forged_context]` |
| p11-c52ab0c2028cbcc4 | planner_injection | dynamic evaluation / repeated | `tests/test_dynamic_planning.py::test_dynamic_evaluation[repeated]` |
| p11-935dfe7f7af32717 | planner_injection | dynamic evaluation / no_progress | `tests/test_dynamic_planning.py::test_dynamic_evaluation[no_progress]` |
| p11-13fa028c82ae0857 | planner_injection | dynamic evaluation / planner_timeout | `tests/test_dynamic_planning.py::test_dynamic_evaluation[planner_timeout]` |
| p11-6ea49585764ee16a | planner_injection | dynamic evaluation / provider_failure | `tests/test_dynamic_planning.py::test_dynamic_evaluation[provider_failure]` |
| p11-4a66349c0c3b3534 | planner_injection | dynamic evaluation / provider_timeout | `tests/test_dynamic_planning.py::test_dynamic_evaluation[provider_timeout]` |
| p11-8bf0af7d297ddc41 | planner_injection | dynamic evaluation / oversized_provider | `tests/test_dynamic_planning.py::test_dynamic_evaluation[oversized_provider]` |
| p11-521d32c9fe40c6e4 | planner_injection | dynamic evaluation / tool_budget | `tests/test_dynamic_planning.py::test_dynamic_evaluation[tool_budget]` |
| p11-cca6e1e201b1ebb8 | planner_injection | dynamic evaluation / planning_budget | `tests/test_dynamic_planning.py::test_dynamic_evaluation[planning_budget]` |
| p11-cde057003cb6adc4 | planner_injection | dynamic evaluation / cancel | `tests/test_dynamic_planning.py::test_dynamic_evaluation[cancel]` |
| p11-4c395e390fae80d3 | planner_injection | dynamic evaluation / recovery | `tests/test_dynamic_planning.py::test_dynamic_evaluation[recovery]` |
| p11-35c2e97ae7ee88f6 | planner_injection | dynamic evaluation / corrupt_checkpoint | `tests/test_dynamic_planning.py::test_dynamic_evaluation[corrupt_checkpoint]` |
| p11-caac1bf0a13d3375 | planner_injection | dynamic evaluation / database_failure | `tests/test_dynamic_planning.py::test_dynamic_evaluation[database_failure]` |
| p11-79bf5e003650ebac | planner_injection | dynamic evaluation / partial_persistence | `tests/test_dynamic_planning.py::test_dynamic_evaluation[partial_persistence]` |
| p11-e491f64b8fd9f6fe | planner_injection | dynamic evaluation / lease_loss | `tests/test_dynamic_planning.py::test_dynamic_evaluation[lease_loss]` |
| p11-8349411d0ca97aed | planner_injection | untrusted terminal claims fail closed / text-unsupported_finding | `tests/test_dynamic_planning.py::test_untrusted_terminal_claims_fail_closed[text-unsupported_finding]` |
| p11-a4ecade3c74ba670 | planner_injection | untrusted terminal claims fail closed / citation-unsupported_citation | `tests/test_dynamic_planning.py::test_untrusted_terminal_claims_fail_closed[citation-unsupported_citation]` |
| p11-4bd73aaaf68aa758 | planner_injection | context is minimized and mutation cannot change evidence / base | `tests/test_dynamic_planning.py::test_context_is_minimized_and_mutation_cannot_change_evidence` |
| p11-e425605a42e52321 | planner_injection | provider budget reservations are durable / request-provider_request_limit | `tests/test_dynamic_planning.py::test_provider_budget_reservations_are_durable[request-provider_request_limit]` |
| p11-e58d3cc3ee1db988 | planner_injection | provider budget reservations are durable / tokens-provider_token_limit | `tests/test_dynamic_planning.py::test_provider_budget_reservations_are_durable[tokens-provider_token_limit]` |
| p11-b164b4688c654dbb | planner_injection | provider budget reservations are durable / cost-provider_cost_limit | `tests/test_dynamic_planning.py::test_provider_budget_reservations_are_durable[cost-provider_cost_limit]` |
| p11-0b62bfbbcd3f5324 | planner_injection | revocation during dynamic planning prevents dispatch / base | `tests/test_dynamic_planning.py::test_revocation_during_dynamic_planning_prevents_dispatch` |
| p11-8f9626cfaeb3b9b5 | planner_injection | changed observation changes selection for same request / base | `tests/test_dynamic_planning.py::test_changed_observation_changes_selection_for_same_request` |
| p11-2a1955aa85fed8f5 | planner_injection | escalation reason requires supporting facts / base | `tests/test_dynamic_planning.py::test_escalation_reason_requires_supporting_facts` |
| p11-e0b056eeb5755d3e | planner_injection | escalation cannot cite unrelated valid evidence / 1-security_review_required | `tests/test_dynamic_planning.py::test_escalation_cannot_cite_unrelated_valid_evidence[1-security_review_required]` |
| p11-7c340f8792789898 | planner_injection | escalation cannot cite unrelated valid evidence / 4-conflicting_evidence | `tests/test_dynamic_planning.py::test_escalation_cannot_cite_unrelated_valid_evidence[4-conflicting_evidence]` |
| p11-35ee23ed82953106 | evidence_policy | sources grounding and durable apis / base | `tests/test_evidence.py::test_sources_grounding_and_durable_apis` |
| p11-28e1d963ff4f2945 | evidence_policy | freshness / 0-CURRENT | `tests/test_evidence.py::test_freshness[0-CURRENT]` |
| p11-5a1efb59aac1a952 | evidence_policy | freshness / 86401-STALE | `tests/test_evidence.py::test_freshness[86401-STALE]` |
| p11-96310a024995d5fa | evidence_policy | freshness / -1-UNKNOWN | `tests/test_evidence.py::test_freshness[-1-UNKNOWN]` |
| p11-18d817481efd00b8 | evidence_policy | legacy envelope readable / base | `tests/test_evidence.py::test_legacy_envelope_readable` |
| p11-bae0cfecbea7199b | evidence_policy | unsupported findings rejected / False | `tests/test_evidence.py::test_unsupported_findings_rejected[False]` |
| p11-61cfb76ecfe31b55 | evidence_policy | unsupported findings rejected / True | `tests/test_evidence.py::test_unsupported_findings_rejected[True]` |
| p11-96a587335afb8dea | evidence_policy | empty retrieval gaps / base | `tests/test_evidence.py::test_empty_retrieval_gaps` |
| p11-0e3cd82ec5127cbc | evidence_policy | duplicate stable evidence and injection / base | `tests/test_evidence.py::test_duplicate_stable_evidence_and_injection` |
| p11-6476a46068b257f2 | evidence_policy | effective policy selection / base | `tests/test_evidence.py::test_effective_policy_selection` |
| p11-5a304286f08392c1 | evidence_policy | search safe and bounded / zzzznotfound | `tests/test_evidence.py::test_search_safe_and_bounded[zzzznotfound]` |
| p11-fb35a0450df3bcc6 | evidence_policy | search safe and bounded / ' OR 1=1 -- | `tests/test_evidence.py::test_search_safe_and_bounded[' OR 1=1 --]` |
| p11-2b67ded73be67767 | evidence_policy | search safe and bounded / security; DROP TABLE policies | `tests/test_evidence.py::test_search_safe_and_bounded[security; DROP TABLE policies]` |
| p11-6090d972a4a074f9 | evidence_policy | missing transaction and block reason / base | `tests/test_evidence.py::test_missing_transaction_and_block_reason` |
| p11-3b802de31c26c727 | evidence_policy | strict source contract / base | `tests/test_evidence.py::test_strict_source_contract` |
| p11-1331c1b66c1b65d6 | evidence_policy | account state conflicts require current observations / False-True | `tests/test_evidence.py::test_account_state_conflicts_require_current_observations[False-True]` |
| p11-c76aeaed5407caf2 | evidence_policy | account state conflicts require current observations / True-False | `tests/test_evidence.py::test_account_state_conflicts_require_current_observations[True-False]` |
| p11-d43dbd057cae2f76 | evidence_policy | ticket resolution conflict has both sources / base | `tests/test_evidence.py::test_ticket_resolution_conflict_has_both_sources` |
| p11-b3cc2993c04bb690 | evidence_policy | overlapping policy observations not silently selected / base | `tests/test_evidence.py::test_overlapping_policy_observations_not_silently_selected` |
| p11-a6ae182713d4e93c | evidence_policy | evidence api requires investigator / None-401 | `tests/test_evidence.py::test_evidence_api_requires_investigator[None-401]` |
| p11-881624b7c5993b18 | evidence_policy | evidence api requires investigator / auditor-403 | `tests/test_evidence.py::test_evidence_api_requires_investigator[auditor-403]` |
| p11-c29ebb7b6163dfe0 | evidence_policy | corrupted source tenant fails closed / base | `tests/test_evidence.py::test_corrupted_source_tenant_fails_closed` |
| p11-777daeac5cb91783 | evidence_policy | transaction creation is not source update / base | `tests/test_evidence.py::test_transaction_creation_is_not_source_update` |
| p11-45334ec0df0a74c4 | ordinary_success | execution security case / authorized-operator-create_customer_note-3 | `tests/test_execution_eval.py::test_execution_security_case[authorized-operator-create_customer_note-3]` |
| p11-ea130a29e05f6170 | ordinary_success | execution security case / authorized-operator-add_ticket_note-3 | `tests/test_execution_eval.py::test_execution_security_case[authorized-operator-add_ticket_note-3]` |
| p11-a526885a8b06ea9f | ordinary_success | execution security case / authorized-operator-request_account_reactivation-3 | `tests/test_execution_eval.py::test_execution_security_case[authorized-operator-request_account_reactivation-3]` |
| p11-2f41aed9ea3e0595 | ordinary_success | execution security case / authorized-operator-reactivate_account-3 | `tests/test_execution_eval.py::test_execution_security_case[authorized-operator-reactivate_account-3]` |
| p11-b9210ed748939b2c | ordinary_success | execution security case / authorized-operator-close_duplicate_ticket-2 | `tests/test_execution_eval.py::test_execution_security_case[authorized-operator-close_duplicate_ticket-2]` |
| p11-014b58a10e414693 | ordinary_success | execution security case / authorized-admin-create_customer_note-3 | `tests/test_execution_eval.py::test_execution_security_case[authorized-admin-create_customer_note-3]` |
| p11-1b7e0b8d186e5ac9 | ordinary_success | execution security case / authorized-admin-add_ticket_note-3 | `tests/test_execution_eval.py::test_execution_security_case[authorized-admin-add_ticket_note-3]` |
| p11-420b23317f1b59be | ordinary_success | execution security case / authorized-admin-request_account_reactivation-3 | `tests/test_execution_eval.py::test_execution_security_case[authorized-admin-request_account_reactivation-3]` |
| p11-0d0174c31d6b9838 | ordinary_success | execution security case / authorized-admin-reactivate_account-3 | `tests/test_execution_eval.py::test_execution_security_case[authorized-admin-reactivate_account-3]` |
| p11-0b89127fac2257b6 | ordinary_success | execution security case / authorized-admin-close_duplicate_ticket-2 | `tests/test_execution_eval.py::test_execution_security_case[authorized-admin-close_duplicate_ticket-2]` |
| p11-d42b2b25d26287c7 | approval_execution | execution security case / unauthorized-reviewer-create_customer_note-3 | `tests/test_execution_eval.py::test_execution_security_case[unauthorized-reviewer-create_customer_note-3]` |
| p11-2dde96919fc077dd | approval_execution | execution security case / unauthorized-reviewer-add_ticket_note-3 | `tests/test_execution_eval.py::test_execution_security_case[unauthorized-reviewer-add_ticket_note-3]` |
| p11-54013cb6b2a67efd | approval_execution | execution security case / unauthorized-reviewer-request_account_reactivation-3 | `tests/test_execution_eval.py::test_execution_security_case[unauthorized-reviewer-request_account_reactivation-3]` |
| p11-421d69647a213966 | approval_execution | execution security case / unauthorized-reviewer-reactivate_account-3 | `tests/test_execution_eval.py::test_execution_security_case[unauthorized-reviewer-reactivate_account-3]` |
| p11-40ad4b32c4433003 | approval_execution | execution security case / unauthorized-reviewer-close_duplicate_ticket-2 | `tests/test_execution_eval.py::test_execution_security_case[unauthorized-reviewer-close_duplicate_ticket-2]` |
| p11-0e5829fe8171c9b5 | approval_execution | execution security case / unauthorized-auditor-create_customer_note-3 | `tests/test_execution_eval.py::test_execution_security_case[unauthorized-auditor-create_customer_note-3]` |
| p11-6b96d9ba3ebef860 | approval_execution | execution security case / unauthorized-auditor-add_ticket_note-3 | `tests/test_execution_eval.py::test_execution_security_case[unauthorized-auditor-add_ticket_note-3]` |
| p11-8f5eb8895532bc71 | approval_execution | execution security case / unauthorized-auditor-request_account_reactivation-3 | `tests/test_execution_eval.py::test_execution_security_case[unauthorized-auditor-request_account_reactivation-3]` |
| p11-80452e0ab0178fb8 | approval_execution | execution security case / unauthorized-auditor-reactivate_account-3 | `tests/test_execution_eval.py::test_execution_security_case[unauthorized-auditor-reactivate_account-3]` |
| p11-80fea5ce60a180c8 | approval_execution | execution security case / unauthorized-auditor-close_duplicate_ticket-2 | `tests/test_execution_eval.py::test_execution_security_case[unauthorized-auditor-close_duplicate_ticket-2]` |
| p11-72ea81ffc0a54017 | approval_execution | execution security case / foreign-operator-create_customer_note-3 | `tests/test_execution_eval.py::test_execution_security_case[foreign-operator-create_customer_note-3]` |
| p11-121c6c2a93ff23e2 | approval_execution | execution security case / foreign-operator-add_ticket_note-3 | `tests/test_execution_eval.py::test_execution_security_case[foreign-operator-add_ticket_note-3]` |
| p11-8bdf9e522b5cd9d6 | approval_execution | execution security case / foreign-operator-request_account_reactivation-3 | `tests/test_execution_eval.py::test_execution_security_case[foreign-operator-request_account_reactivation-3]` |
| p11-1f1c70c62d99cf67 | approval_execution | execution security case / foreign-operator-reactivate_account-3 | `tests/test_execution_eval.py::test_execution_security_case[foreign-operator-reactivate_account-3]` |
| p11-de3ef5ac099fdc5b | approval_execution | execution security case / foreign-operator-close_duplicate_ticket-2 | `tests/test_execution_eval.py::test_execution_security_case[foreign-operator-close_duplicate_ticket-2]` |
| p11-f83da88621f802e0 | approval_execution | execution security case / resource-operator-create_customer_note-3 | `tests/test_execution_eval.py::test_execution_security_case[resource-operator-create_customer_note-3]` |
| p11-84dd9d39f790fb85 | approval_execution | execution security case / resource-operator-add_ticket_note-3 | `tests/test_execution_eval.py::test_execution_security_case[resource-operator-add_ticket_note-3]` |
| p11-9ebf8670f801764e | approval_execution | execution security case / resource-operator-request_account_reactivation-3 | `tests/test_execution_eval.py::test_execution_security_case[resource-operator-request_account_reactivation-3]` |
| p11-2fb3e43156d0ca7f | approval_execution | execution security case / resource-operator-reactivate_account-3 | `tests/test_execution_eval.py::test_execution_security_case[resource-operator-reactivate_account-3]` |
| p11-0ae53b7cf145a73e | approval_execution | execution security case / resource-operator-close_duplicate_ticket-2 | `tests/test_execution_eval.py::test_execution_security_case[resource-operator-close_duplicate_ticket-2]` |
| p11-5622c038b5f7436b | approval_execution | execution security case / verification-operator-create_customer_note-3 | `tests/test_execution_eval.py::test_execution_security_case[verification-operator-create_customer_note-3]` |
| p11-24624048719186da | approval_execution | execution security case / verification-operator-add_ticket_note-3 | `tests/test_execution_eval.py::test_execution_security_case[verification-operator-add_ticket_note-3]` |
| p11-04b3939d5887eea6 | approval_execution | execution security case / verification-operator-request_account_reactivation-3 | `tests/test_execution_eval.py::test_execution_security_case[verification-operator-request_account_reactivation-3]` |
| p11-17dcb46c0100befc | approval_execution | execution security case / verification-operator-reactivate_account-3 | `tests/test_execution_eval.py::test_execution_security_case[verification-operator-reactivate_account-3]` |
| p11-d257a8e63218c090 | approval_execution | execution security case / verification-operator-close_duplicate_ticket-2 | `tests/test_execution_eval.py::test_execution_security_case[verification-operator-close_duplicate_ticket-2]` |
| p11-d9ab347e1ded50c6 | approval_execution | execution security case / replay-operator-create_customer_note-3 | `tests/test_execution_eval.py::test_execution_security_case[replay-operator-create_customer_note-3]` |
| p11-05af0ca0a9bda644 | approval_execution | execution security case / replay-operator-add_ticket_note-3 | `tests/test_execution_eval.py::test_execution_security_case[replay-operator-add_ticket_note-3]` |
| p11-6e4c3f9ad77aae29 | approval_execution | execution security case / replay-operator-request_account_reactivation-3 | `tests/test_execution_eval.py::test_execution_security_case[replay-operator-request_account_reactivation-3]` |
| p11-d82a2c66b8fe9f99 | approval_execution | execution security case / replay-operator-reactivate_account-3 | `tests/test_execution_eval.py::test_execution_security_case[replay-operator-reactivate_account-3]` |
| p11-237b122e068d44b9 | approval_execution | execution security case / replay-operator-close_duplicate_ticket-2 | `tests/test_execution_eval.py::test_execution_security_case[replay-operator-close_duplicate_ticket-2]` |
| p11-9151a2058b8b16e9 | approval_execution | execution security case / expiry-operator-request_account_reactivation-3 | `tests/test_execution_eval.py::test_execution_security_case[expiry-operator-request_account_reactivation-3]` |
| p11-2bb7580d8cc045df | approval_execution | execution security case / expiry-operator-reactivate_account-3 | `tests/test_execution_eval.py::test_execution_security_case[expiry-operator-reactivate_account-3]` |
| p11-3c4d1ceeb4f3884f | approval_execution | execution security case / expiry-operator-close_duplicate_ticket-2 | `tests/test_execution_eval.py::test_execution_security_case[expiry-operator-close_duplicate_ticket-2]` |
| p11-5786ab05c56adf5a | approval_execution | execution security case / policy-operator-request_account_reactivation-3 | `tests/test_execution_eval.py::test_execution_security_case[policy-operator-request_account_reactivation-3]` |
| p11-fa185cc57d38ee40 | approval_execution | execution security case / policy-operator-reactivate_account-3 | `tests/test_execution_eval.py::test_execution_security_case[policy-operator-reactivate_account-3]` |
| p11-8da26ad10afdc67c | approval_execution | execution security case / policy-operator-close_duplicate_ticket-2 | `tests/test_execution_eval.py::test_execution_security_case[policy-operator-close_duplicate_ticket-2]` |
| p11-f6536c9e47a2fed1 | approval_execution | execution security case / security-operator-override_security_block-1 | `tests/test_execution_eval.py::test_execution_security_case[security-operator-override_security_block-1]` |
| p11-4f8459536f665ac0 | approval_execution | execution security case / security-reviewer-override_security_block-1 | `tests/test_execution_eval.py::test_execution_security_case[security-reviewer-override_security_block-1]` |
| p11-a6b67628d667da26 | approval_execution | execution security case / security-admin-override_security_block-1 | `tests/test_execution_eval.py::test_execution_security_case[security-admin-override_security_block-1]` |
| p11-14e5d3c411aaddd0 | approval_execution | execution security case / security-auditor-override_security_block-1 | `tests/test_execution_eval.py::test_execution_security_case[security-auditor-override_security_block-1]` |
| p11-5b7ff0568e6dc434 | approval_execution | execution security case / self-reviewer-reactivate_account-3 | `tests/test_execution_eval.py::test_execution_security_case[self-reviewer-reactivate_account-3]` |
| p11-842befeb2dd15b55 | approval_execution | execution security case / self-admin-reactivate_account-3 | `tests/test_execution_eval.py::test_execution_security_case[self-admin-reactivate_account-3]` |
| p11-77b517fd6f485980 | operations_audit | operations evaluation / dead-operator | `tests/test_operations.py::test_operations_evaluation[dead-operator]` |
| p11-e7d8ac8c54b415e2 | operations_audit | operations evaluation / dead-reviewer | `tests/test_operations.py::test_operations_evaluation[dead-reviewer]` |
| p11-0382d3b2c6be6785 | operations_audit | operations evaluation / dead-admin | `tests/test_operations.py::test_operations_evaluation[dead-admin]` |
| p11-28a0b555602fe53b | operations_audit | operations evaluation / dead-auditor | `tests/test_operations.py::test_operations_evaluation[dead-auditor]` |
| p11-da471dc479006147 | operations_audit | operations evaluation / recon-operator | `tests/test_operations.py::test_operations_evaluation[recon-operator]` |
| p11-88962667bf3dfa6c | operations_audit | operations evaluation / recon-reviewer | `tests/test_operations.py::test_operations_evaluation[recon-reviewer]` |
| p11-82c9b5f91ce24a37 | operations_audit | operations evaluation / recon-admin | `tests/test_operations.py::test_operations_evaluation[recon-admin]` |
| p11-c1ce664b5d29b2ad | operations_audit | operations evaluation / recon-auditor | `tests/test_operations.py::test_operations_evaluation[recon-auditor]` |
| p11-db11b28bd8311041 | operations_audit | operations evaluation / queued-operator | `tests/test_operations.py::test_operations_evaluation[queued-operator]` |
| p11-676e9ac5e20964f7 | operations_audit | operations evaluation / queued-reviewer | `tests/test_operations.py::test_operations_evaluation[queued-reviewer]` |
| p11-06796bf5b0743c8d | operations_audit | operations evaluation / queued-admin | `tests/test_operations.py::test_operations_evaluation[queued-admin]` |
| p11-abe5356e12a0ad79 | operations_audit | operations evaluation / queued-auditor | `tests/test_operations.py::test_operations_evaluation[queued-auditor]` |
| p11-b61130e3a4a96b55 | operations_audit | operations evaluation / completed-operator | `tests/test_operations.py::test_operations_evaluation[completed-operator]` |
| p11-df5b385528f46613 | operations_audit | operations evaluation / completed-reviewer | `tests/test_operations.py::test_operations_evaluation[completed-reviewer]` |
| p11-2969e75fa07a946e | operations_audit | operations evaluation / completed-admin | `tests/test_operations.py::test_operations_evaluation[completed-admin]` |
| p11-0102330b2baa7497 | operations_audit | operations evaluation / completed-auditor | `tests/test_operations.py::test_operations_evaluation[completed-auditor]` |
| p11-788015d79586b34e | operations_audit | operations evaluation / failed-operator | `tests/test_operations.py::test_operations_evaluation[failed-operator]` |
| p11-3f7b8da9cfcb1473 | operations_audit | operations evaluation / failed-reviewer | `tests/test_operations.py::test_operations_evaluation[failed-reviewer]` |
| p11-e0a8d683f94729c7 | operations_audit | operations evaluation / failed-admin | `tests/test_operations.py::test_operations_evaluation[failed-admin]` |
| p11-7baa5f6829eaf98b | operations_audit | operations evaluation / failed-auditor | `tests/test_operations.py::test_operations_evaluation[failed-auditor]` |
| p11-2b50068f6400a1a6 | operations_audit | operations evaluation / retry-operator | `tests/test_operations.py::test_operations_evaluation[retry-operator]` |
| p11-5023bc64eb0f3b92 | operations_audit | operations evaluation / retry-reviewer | `tests/test_operations.py::test_operations_evaluation[retry-reviewer]` |
| p11-a02c3b7165c12497 | operations_audit | operations evaluation / retry-admin | `tests/test_operations.py::test_operations_evaluation[retry-admin]` |
| p11-3391a9847386e1bf | operations_audit | operations evaluation / retry-auditor | `tests/test_operations.py::test_operations_evaluation[retry-auditor]` |
| p11-1a6a30f8e3eed495 | operations_audit | operations evaluation / empty-operator | `tests/test_operations.py::test_operations_evaluation[empty-operator]` |
| p11-c631c94520b8fb3d | operations_audit | operations evaluation / empty-reviewer | `tests/test_operations.py::test_operations_evaluation[empty-reviewer]` |
| p11-73922799a8257feb | operations_audit | operations evaluation / empty-admin | `tests/test_operations.py::test_operations_evaluation[empty-admin]` |
| p11-d810a2c313ab61ce | operations_audit | operations evaluation / empty-auditor | `tests/test_operations.py::test_operations_evaluation[empty-auditor]` |
| p11-8ce16615b17cadf0 | operations_audit | operations evaluation / foreign-operator | `tests/test_operations.py::test_operations_evaluation[foreign-operator]` |
| p11-8f1a6d6427af1b51 | operations_audit | operations evaluation / foreign-reviewer | `tests/test_operations.py::test_operations_evaluation[foreign-reviewer]` |
| p11-518c564b1497eac0 | operations_audit | operations evaluation / foreign-admin | `tests/test_operations.py::test_operations_evaluation[foreign-admin]` |
| p11-6d7c538cd171b8f4 | operations_audit | operations evaluation / foreign-auditor | `tests/test_operations.py::test_operations_evaluation[foreign-auditor]` |
| p11-827e3f7720b9f193 | operations_audit | operations evaluation / response-operator | `tests/test_operations.py::test_operations_evaluation[response-operator]` |
| p11-22a28b566f233d7a | operations_audit | operations evaluation / response-reviewer | `tests/test_operations.py::test_operations_evaluation[response-reviewer]` |
| p11-2bce481e46de7d66 | operations_audit | operations evaluation / response-admin | `tests/test_operations.py::test_operations_evaluation[response-admin]` |
| p11-3a498ba617753b58 | operations_audit | operations evaluation / response-auditor | `tests/test_operations.py::test_operations_evaluation[response-auditor]` |
| p11-6fe7eea37ebd0602 | operations_audit | operations evaluation / denials-operator | `tests/test_operations.py::test_operations_evaluation[denials-operator]` |
| p11-ccc97f2d9cd9860b | operations_audit | operations evaluation / denials-reviewer | `tests/test_operations.py::test_operations_evaluation[denials-reviewer]` |
| p11-7f6637a171708763 | operations_audit | operations evaluation / denials-admin | `tests/test_operations.py::test_operations_evaluation[denials-admin]` |
| p11-2e248517f87fe14e | operations_audit | operations evaluation / denials-auditor | `tests/test_operations.py::test_operations_evaluation[denials-auditor]` |
| p11-be696a9719b4da56 | operations_audit | empty and http bounds / base | `tests/test_operations.py::test_empty_and_http_bounds` |
| p11-d9edf2a494e35ab7 | operations_audit | worker health thresholds and config / base | `tests/test_operations.py::test_worker_health_thresholds_and_config` |
| p11-0f1f96f35ad4ae44 | operations_audit | incident assignment immutability and foreign / base | `tests/test_operations.py::test_incident_assignment_immutability_and_foreign` |
| p11-7afcfaacee2ddadf | operations_audit | query budget ordering windows and pagination / base | `tests/test_operations.py::test_query_budget_ordering_windows_and_pagination` |
| p11-dfb1b90b13a99bff | operations_audit | repeated lease detection uses durable events / base | `tests/test_operations.py::test_repeated_lease_detection_uses_durable_events` |
| p11-20fb7f22ce45bc83 | operations_audit | persistent failure detection does not change business / base | `tests/test_operations.py::test_persistent_failure_detection_does_not_change_business` |
| p11-e74374fc25112819 | operations_audit | invalidated approval detection / base | `tests/test_operations.py::test_invalidated_approval_detection` |
| p11-a9c2e6270eaee32d | operations_audit | operations rate limit / base | `tests/test_operations.py::test_operations_rate_limit` |
| p11-2a8757d0e2c9e85c | operations_audit | live role revalidation and migration signal / base | `tests/test_operations.py::test_live_role_revalidation_and_migration_signal` |
| p11-ac3b92bd70a26484 | operations_audit | numeric duration samples and read only metrics / base | `tests/test_operations.py::test_numeric_duration_samples_and_read_only_metrics` |
| p11-ec3a52945f4357a1 | operations_audit | bounded detection progress and incident trace / base | `tests/test_operations.py::test_bounded_detection_progress_and_incident_trace` |
| p11-c0044a6d8a91e848 | operations_audit | correlation ids are followed only through persisted links / base | `tests/test_operations.py::test_correlation_ids_are_followed_only_through_persisted_links` |
| p11-569c5b68d7b35f3c | reliability_recovery | durable result events evidence and repository recreation / base | `tests/test_persistence.py::test_durable_result_events_evidence_and_repository_recreation` |
| p11-7fb8e2325bc0f974 | reliability_recovery | checkpoint validation / schema_version-2 | `tests/test_persistence.py::test_checkpoint_validation[schema_version-2]` |
| p11-d927464628c14054 | reliability_recovery | checkpoint validation / planner_version-9.0 | `tests/test_persistence.py::test_checkpoint_validation[planner_version-9.0]` |
| p11-7717a3f8f0935588 | reliability_recovery | checkpoint validation / step_index-2 | `tests/test_persistence.py::test_checkpoint_validation[step_index-2]` |
| p11-0dafddfd067fa038 | reliability_recovery | checkpoint validation / last_event_sequence-0 | `tests/test_persistence.py::test_checkpoint_validation[last_event_sequence-0]` |
| p11-cad73fad526bda44 | reliability_recovery | checkpoint validation / unexpected-True | `tests/test_persistence.py::test_checkpoint_validation[unexpected-True]` |
| p11-35da7e46cfee292e | reliability_recovery | idempotent creation and payload conflict / base | `tests/test_persistence.py::test_idempotent_creation_and_payload_conflict` |
| p11-bcf570ff04f39964 | reliability_recovery | concurrent duplicate creation / base | `tests/test_persistence.py::test_concurrent_duplicate_creation` |
| p11-cedb1a09f8f7c39b | reliability_recovery | lease race and expiry / base | `tests/test_persistence.py::test_lease_race_and_expiry` |
| p11-849097b9d0bf3105 | reliability_recovery | optimistic lock and atomic rollback / base | `tests/test_persistence.py::test_optimistic_lock_and_atomic_rollback` |
| p11-0235977d0fdce7ed | reliability_recovery | database unique sequence guards / event | `tests/test_persistence.py::test_database_unique_sequence_guards[event]` |
| p11-46d4fa68e4380da5 | reliability_recovery | database unique sequence guards / checkpoint | `tests/test_persistence.py::test_database_unique_sequence_guards[checkpoint]` |
| p11-b7f33eb722df0243 | reliability_recovery | safe recovery restores completed step without replay / False | `tests/test_persistence.py::test_safe_recovery_restores_completed_step_without_replay[False]` |
| p11-54aedb269b950f71 | reliability_recovery | safe recovery restores completed step without replay / True | `tests/test_persistence.py::test_safe_recovery_restores_completed_step_without_replay[True]` |
| p11-fb1101e77883f375 | reliability_recovery | interrupted tool is never blindly replayed / base | `tests/test_persistence.py::test_interrupted_tool_is_never_blindly_replayed` |
| p11-17c5dbe6c53c1c22 | reliability_recovery | recovery preserves budget / base | `tests/test_persistence.py::test_recovery_preserves_budget` |
| p11-1b021b773edc4377 | reliability_recovery | corrupt checkpoint fails closed / checksum | `tests/test_persistence.py::test_corrupt_checkpoint_fails_closed[checksum]` |
| p11-94bf063bff987e5b | reliability_recovery | corrupt checkpoint fails closed / version | `tests/test_persistence.py::test_corrupt_checkpoint_fails_closed[version]` |
| p11-5a17d9f396b3cf0c | reliability_recovery | persistent cancellation pending and terminal protection / base | `tests/test_persistence.py::test_persistent_cancellation_pending_and_terminal_protection` |
| p11-1f970a7edf08ca63 | reliability_recovery | active cancellation between boundaries / base | `tests/test_persistence.py::test_active_cancellation_between_boundaries` |
| p11-2885fb708772eb0d | reliability_recovery | history and evidence owner isolation / 1-operator | `tests/test_persistence.py::test_history_and_evidence_owner_isolation[1-operator]` |
| p11-5c498e30cede7100 | reliability_recovery | history and evidence owner isolation / 0-reviewer | `tests/test_persistence.py::test_history_and_evidence_owner_isolation[0-reviewer]` |
| p11-3c6f2d152bf2bc70 | reliability_recovery | history api idempotency pagination and csrf / base | `tests/test_persistence.py::test_history_api_idempotency_pagination_and_csrf` |
| p11-495cbc8cd8f1130f | reliability_recovery | history application append only / update-InvestigationEvent | `tests/test_persistence.py::test_history_application_append_only[update-InvestigationEvent]` |
| p11-2eb066e11edacdf3 | reliability_recovery | history application append only / update-InvestigationCheckpoint | `tests/test_persistence.py::test_history_application_append_only[update-InvestigationCheckpoint]` |
| p11-0a4a560c554a316d | reliability_recovery | history application append only / update-InvestigationEvidence | `tests/test_persistence.py::test_history_application_append_only[update-InvestigationEvidence]` |
| p11-eedc41639632e9b8 | reliability_recovery | history application append only / delete-InvestigationEvent | `tests/test_persistence.py::test_history_application_append_only[delete-InvestigationEvent]` |
| p11-32c5f6f7bec632da | reliability_recovery | history application append only / delete-InvestigationCheckpoint | `tests/test_persistence.py::test_history_application_append_only[delete-InvestigationCheckpoint]` |
| p11-57ebbe8427cfe474 | reliability_recovery | history application append only / delete-InvestigationEvidence | `tests/test_persistence.py::test_history_application_append_only[delete-InvestigationEvidence]` |
| p11-6e1f748bc0f271b5 | reliability_recovery | recovery charges elapsed time and fences old owner / base | `tests/test_persistence.py::test_recovery_charges_elapsed_time_and_fences_old_owner` |
| p11-5ac17f741374e57e | reliability_recovery | heartbeat renewal and no budget reset / base | `tests/test_persistence.py::test_heartbeat_renewal_and_no_budget_reset` |
| p11-eab92e44430deeb5 | reliability_recovery | live authorization required for recovery / base | `tests/test_persistence.py::test_live_authorization_required_for_recovery` |
| p11-c94cedfd7a92826c | reliability_recovery | invalid state transition rolls back / base | `tests/test_persistence.py::test_invalid_state_transition_rolls_back` |
| p11-ae64fe729a15413a | reliability_recovery | tenant foreign key rejects history attachment / base | `tests/test_persistence.py::test_tenant_foreign_key_rejects_history_attachment` |
| p11-5257a315d95a2051 | reliability_recovery | final result cannot disagree with durable evidence / base | `tests/test_persistence.py::test_final_result_cannot_disagree_with_durable_evidence` |
| p11-88617a61c821a1e3 | reliability_recovery | checkpoint parent metadata mismatch stops recovery / base | `tests/test_persistence.py::test_checkpoint_parent_metadata_mismatch_stops_recovery` |
| p11-c8e153ff825818f7 | reliability_recovery | concurrent history reads never observe mixed checkpoint versions / base | `tests/test_persistence.py::test_concurrent_history_reads_never_observe_mixed_checkpoint_versions` |
| p11-efdef80f51ca6e36 | reliability_recovery | corruption marker survives crash during recovery / base | `tests/test_persistence.py::test_corruption_marker_survives_crash_during_recovery` |
| p11-fd8ead1c746ec86f | evidence_policy | policy cases / duplicate_eligible | `tests/test_policy_engine.py::test_policy_cases[duplicate_eligible]` |
| p11-e4315179efd022e8 | evidence_policy | policy cases / note_allowed | `tests/test_policy_engine.py::test_policy_cases[note_allowed]` |
| p11-faf9812359b4f720 | evidence_policy | policy cases / ticket_note_allowed | `tests/test_policy_engine.py::test_policy_cases[ticket_note_allowed]` |
| p11-2cdab30c75ea0cce | evidence_policy | policy cases / request_eligible | `tests/test_policy_engine.py::test_policy_cases[request_eligible]` |
| p11-2992aade17bd3574 | evidence_policy | policy cases / reactivate_eligible | `tests/test_policy_engine.py::test_policy_cases[reactivate_eligible]` |
| p11-c1dad869a4dde392 | evidence_policy | policy cases / override_denied | `tests/test_policy_engine.py::test_policy_cases[override_denied]` |
| p11-ad79f18e03f50b1a | evidence_policy | policy cases / request_security | `tests/test_policy_engine.py::test_policy_cases[request_security]` |
| p11-557765bbad3bea53 | evidence_policy | policy cases / reactivate_security | `tests/test_policy_engine.py::test_policy_cases[reactivate_security]` |
| p11-5057abf7a97d8936 | evidence_policy | policy cases / request_conflict | `tests/test_policy_engine.py::test_policy_cases[request_conflict]` |
| p11-456284ea5ca451a6 | evidence_policy | policy cases / reactivate_conflict | `tests/test_policy_engine.py::test_policy_cases[reactivate_conflict]` |
| p11-240031d6268db8d4 | evidence_policy | policy cases / request_unpaid | `tests/test_policy_engine.py::test_policy_cases[request_unpaid]` |
| p11-9f1f2ccc239581db | evidence_policy | policy cases / reactivate_unpaid | `tests/test_policy_engine.py::test_policy_cases[reactivate_unpaid]` |
| p11-e33b50751618eb39 | evidence_policy | policy cases / request_active | `tests/test_policy_engine.py::test_policy_cases[request_active]` |
| p11-1b1450c966257c65 | evidence_policy | policy cases / reactivate_active | `tests/test_policy_engine.py::test_policy_cases[reactivate_active]` |
| p11-98b0d8fd2d427703 | evidence_policy | policy cases / unknown | `tests/test_policy_engine.py::test_policy_cases[unknown]` |
| p11-554572132e9d1548 | evidence_policy | policy cases / invalid_version | `tests/test_policy_engine.py::test_policy_cases[invalid_version]` |
| p11-21d6cc2da4b3e121 | evidence_policy | policy cases / empty_note | `tests/test_policy_engine.py::test_policy_cases[empty_note]` |
| p11-f616ca0a03cdcfa9 | evidence_policy | policy cases / short_note | `tests/test_policy_engine.py::test_policy_cases[short_note]` |
| p11-855a2bd9ce380ada | evidence_policy | policy cases / oversize_note | `tests/test_policy_engine.py::test_policy_cases[oversize_note]` |
| p11-6bb460f5fb1b5cba | evidence_policy | policy cases / extra_argument | `tests/test_policy_engine.py::test_policy_cases[extra_argument]` |
| p11-e20e3819d7c6a6ff | evidence_policy | policy cases / injection | `tests/test_policy_engine.py::test_policy_cases[injection]` |
| p11-a067926122432f58 | evidence_policy | policy cases / script | `tests/test_policy_engine.py::test_policy_cases[script]` |
| p11-a6cbf657ec9ef442 | evidence_policy | policy cases / secret | `tests/test_policy_engine.py::test_policy_cases[secret]` |
| p11-86a01d28385bf63b | evidence_policy | policy cases / forged_ref | `tests/test_policy_engine.py::test_policy_cases[forged_ref]` |
| p11-df5130ecc39289e0 | evidence_policy | policy cases / cross_tenant_customer | `tests/test_policy_engine.py::test_policy_cases[cross_tenant_customer]` |
| p11-736495e22dd0ff48 | evidence_policy | policy cases / cross_tenant_account | `tests/test_policy_engine.py::test_policy_cases[cross_tenant_account]` |
| p11-0c7eb604f00cf3a4 | evidence_policy | policy cases / wrong_customer | `tests/test_policy_engine.py::test_policy_cases[wrong_customer]` |
| p11-b42094e95eb7db78 | evidence_policy | policy cases / wrong_account | `tests/test_policy_engine.py::test_policy_cases[wrong_account]` |
| p11-7db2148143f4e5d2 | evidence_policy | changes / expiry | `tests/test_policy_engine.py::test_changes[expiry]` |
| p11-420c5dd966083950 | evidence_policy | changes / resource | `tests/test_policy_engine.py::test_changes[resource]` |
| p11-76764ed3eb0dbf19 | evidence_policy | changes / policy | `tests/test_policy_engine.py::test_changes[policy]` |
| p11-874fe2bf4a7893bd | evidence_policy | changes / evidence | `tests/test_policy_engine.py::test_changes[evidence]` |
| p11-7bf76729d6e3e016 | evidence_policy | changes / authorization | `tests/test_policy_engine.py::test_changes[authorization]` |
| p11-6488db7faea575b4 | evidence_policy | changes / future | `tests/test_policy_engine.py::test_changes[future]` |
| p11-8bd60eef2ea27e58 | evidence_policy | changes / expired_policy | `tests/test_policy_engine.py::test_changes[expired_policy]` |
| p11-ecd86eb341f3d145 | evidence_policy | changes / ambiguous | `tests/test_policy_engine.py::test_changes[ambiguous]` |
| p11-d32ee7f3c1cbdb2e | evidence_policy | changes / policy_injection | `tests/test_policy_engine.py::test_changes[policy_injection]` |
| p11-f7114deb2ff17eda | evidence_policy | changes / missing_evidence | `tests/test_policy_engine.py::test_changes[missing_evidence]` |
| p11-8ae35b623274dad9 | evidence_policy | changes / closed_ticket | `tests/test_policy_engine.py::test_changes[closed_ticket]` |
| p11-ad2c9b31eb39b600 | evidence_policy | changes / duplicate_missing_original | `tests/test_policy_engine.py::test_changes[duplicate_missing_original]` |
| p11-b99622d2f276d023 | evidence_policy | changes / security_override | `tests/test_policy_engine.py::test_changes[security_override]` |
| p11-afd95b4e867592cf | evidence_policy | roles / operator | `tests/test_policy_engine.py::test_roles[operator]` |
| p11-9aad3ecfb7a3ac4b | evidence_policy | roles / reviewer | `tests/test_policy_engine.py::test_roles[reviewer]` |
| p11-abf80be2f58ecb70 | evidence_policy | roles / admin | `tests/test_policy_engine.py::test_roles[admin]` |
| p11-bc96d25911c093b6 | evidence_policy | roles / auditor | `tests/test_policy_engine.py::test_roles[auditor]` |
| p11-6a52ddf36260e7b8 | evidence_policy | forged context / actor_id | `tests/test_policy_engine.py::test_forged_context[actor_id]` |
| p11-8bf5dfb95fccdf4f | evidence_policy | forged context / tenant_id | `tests/test_policy_engine.py::test_forged_context[tenant_id]` |
| p11-06a8277d9be18279 | evidence_policy | forged context / permissions | `tests/test_policy_engine.py::test_forged_context[permissions]` |
| p11-e692f372498562d1 | evidence_policy | api and concurrent revalidation / base | `tests/test_policy_engine.py::test_api_and_concurrent_revalidation` |
| p11-10d6eb1adf166c27 | evidence_policy | no business mutations and agent handoff / base | `tests/test_policy_engine.py::test_no_business_mutations_and_agent_handoff` |
| p11-398c275c3f0b265d | evidence_policy | role can propose note / operator | `tests/test_policy_engine.py::test_role_can_propose_note[operator]` |
| p11-24b8ad9a30142ebf | evidence_policy | role can propose note / reviewer | `tests/test_policy_engine.py::test_role_can_propose_note[reviewer]` |
| p11-b385c90ccd1cc2d2 | evidence_policy | role can propose note / admin | `tests/test_policy_engine.py::test_role_can_propose_note[admin]` |
| p11-71fb71e5b09df487 | evidence_policy | policy dates and untrusted description / future_higher | `tests/test_policy_engine.py::test_policy_dates_and_untrusted_description[future_higher]` |
| p11-42e63285185c6d88 | evidence_policy | policy dates and untrusted description / expired_higher | `tests/test_policy_engine.py::test_policy_dates_and_untrusted_description[expired_higher]` |
| p11-04860d9a812a32b6 | evidence_policy | policy dates and untrusted description / description_injection | `tests/test_policy_engine.py::test_policy_dates_and_untrusted_description[description_injection]` |
| p11-e12585bbcae0615a | evidence_policy | api rejects body and origin / base | `tests/test_policy_engine.py::test_api_rejects_body_and_origin` |
| p11-7508b8c856cf0764 | evidence_policy | invalid checkpoint cannot grant eligibility / base | `tests/test_policy_engine.py::test_invalid_checkpoint_cannot_grant_eligibility` |
| p11-b932af092c568a99 | evidence_policy | expiry is audited once on status read / base | `tests/test_policy_engine.py::test_expiry_is_audited_once_on_status_read` |
| p11-9f2c8367a9cabccf | evidence_policy | policy rule shapes are strict / numeric_boolean | `tests/test_policy_engine.py::test_policy_rule_shapes_are_strict[numeric_boolean]` |
| p11-e84f3b46d11383e3 | evidence_policy | policy rule shapes are strict / string_scenarios | `tests/test_policy_engine.py::test_policy_rule_shapes_are_strict[string_scenarios]` |
| p11-4822095a807e8777 | planner_injection | injection boundaries / write-customer_message | `tests/test_red_team.py::test_injection_boundaries[write-customer_message]` |
| p11-1ff7f9c9bf590876 | planner_injection | injection boundaries / write-ticket_description | `tests/test_red_team.py::test_injection_boundaries[write-ticket_description]` |
| p11-d66810cf58d95b05 | planner_injection | injection boundaries / write-policy_text | `tests/test_red_team.py::test_injection_boundaries[write-policy_text]` |
| p11-a3f79c2ae03093b4 | planner_injection | injection boundaries / write-tool_response | `tests/test_red_team.py::test_injection_boundaries[write-tool_response]` |
| p11-03671cb0e18fa21e | planner_injection | injection boundaries / write-retrieved_evidence | `tests/test_red_team.py::test_injection_boundaries[write-retrieved_evidence]` |
| p11-15863fa4480252da | planner_injection | injection boundaries / write-crm_record | `tests/test_red_team.py::test_injection_boundaries[write-crm_record]` |
| p11-c42c8e7b34cf9517 | planner_injection | injection boundaries / identity-customer_message | `tests/test_red_team.py::test_injection_boundaries[identity-customer_message]` |
| p11-421147ee477e89ad | planner_injection | injection boundaries / identity-ticket_description | `tests/test_red_team.py::test_injection_boundaries[identity-ticket_description]` |
| p11-7412ff8d0e6e72da | planner_injection | injection boundaries / identity-policy_text | `tests/test_red_team.py::test_injection_boundaries[identity-policy_text]` |
| p11-82eb88d1170cd8a5 | planner_injection | injection boundaries / identity-tool_response | `tests/test_red_team.py::test_injection_boundaries[identity-tool_response]` |
| p11-12b252b2ce1c236e | planner_injection | injection boundaries / identity-retrieved_evidence | `tests/test_red_team.py::test_injection_boundaries[identity-retrieved_evidence]` |
| p11-18fae7e4cf8d3e78 | planner_injection | injection boundaries / identity-crm_record | `tests/test_red_team.py::test_injection_boundaries[identity-crm_record]` |
| p11-16060d1cb3032bac | planner_injection | injection boundaries / approval-customer_message | `tests/test_red_team.py::test_injection_boundaries[approval-customer_message]` |
| p11-beb2d0bc7e4982de | planner_injection | injection boundaries / approval-ticket_description | `tests/test_red_team.py::test_injection_boundaries[approval-ticket_description]` |
| p11-98123630c9c77d61 | planner_injection | injection boundaries / approval-policy_text | `tests/test_red_team.py::test_injection_boundaries[approval-policy_text]` |
| p11-d54822ef76386772 | planner_injection | injection boundaries / approval-tool_response | `tests/test_red_team.py::test_injection_boundaries[approval-tool_response]` |
| p11-500522caa3e86d7c | planner_injection | injection boundaries / approval-retrieved_evidence | `tests/test_red_team.py::test_injection_boundaries[approval-retrieved_evidence]` |
| p11-488c7323ff083809 | planner_injection | injection boundaries / approval-crm_record | `tests/test_red_team.py::test_injection_boundaries[approval-crm_record]` |
| p11-42726e2afe2e8013 | planner_injection | injection boundaries / audit-customer_message | `tests/test_red_team.py::test_injection_boundaries[audit-customer_message]` |
| p11-96d97a979ebdfb1b | planner_injection | injection boundaries / audit-ticket_description | `tests/test_red_team.py::test_injection_boundaries[audit-ticket_description]` |
| p11-304f420ea1b1217d | planner_injection | injection boundaries / audit-policy_text | `tests/test_red_team.py::test_injection_boundaries[audit-policy_text]` |
| p11-6936de02a4946af8 | planner_injection | injection boundaries / audit-tool_response | `tests/test_red_team.py::test_injection_boundaries[audit-tool_response]` |
| p11-268b09bc0c41f667 | planner_injection | injection boundaries / audit-retrieved_evidence | `tests/test_red_team.py::test_injection_boundaries[audit-retrieved_evidence]` |
| p11-23effe3f3c6a490d | planner_injection | injection boundaries / audit-crm_record | `tests/test_red_team.py::test_injection_boundaries[audit-crm_record]` |
| p11-71dd8ff7192df14e | planner_injection | injection boundaries / citation-customer_message | `tests/test_red_team.py::test_injection_boundaries[citation-customer_message]` |
| p11-a7aab090a234c80b | planner_injection | injection boundaries / citation-ticket_description | `tests/test_red_team.py::test_injection_boundaries[citation-ticket_description]` |
| p11-936a496fa17022f1 | planner_injection | injection boundaries / citation-policy_text | `tests/test_red_team.py::test_injection_boundaries[citation-policy_text]` |
| p11-9dc7292190d7a1c1 | planner_injection | injection boundaries / citation-tool_response | `tests/test_red_team.py::test_injection_boundaries[citation-tool_response]` |
| p11-d7c52d2d6e1addc4 | planner_injection | injection boundaries / citation-retrieved_evidence | `tests/test_red_team.py::test_injection_boundaries[citation-retrieved_evidence]` |
| p11-a55263a9807a7c81 | planner_injection | injection boundaries / citation-crm_record | `tests/test_red_team.py::test_injection_boundaries[citation-crm_record]` |
| p11-33910426ecb8f39a | authorization_tenancy | authenticated foreign lifecycle / customer | `tests/test_red_team.py::test_authenticated_foreign_lifecycle[customer]` |
| p11-be826b364d3d689b | authorization_tenancy | authenticated foreign lifecycle / account | `tests/test_red_team.py::test_authenticated_foreign_lifecycle[account]` |
| p11-768b28913eeab95c | authorization_tenancy | authenticated foreign lifecycle / ticket | `tests/test_red_team.py::test_authenticated_foreign_lifecycle[ticket]` |
| p11-0bc7816a8b2a293a | authorization_tenancy | authenticated foreign lifecycle / transactions | `tests/test_red_team.py::test_authenticated_foreign_lifecycle[transactions]` |
| p11-a26975485c090d02 | authorization_tenancy | authenticated foreign lifecycle / policies | `tests/test_red_team.py::test_authenticated_foreign_lifecycle[policies]` |
| p11-af923728b44077ff | authorization_tenancy | authenticated foreign lifecycle / investigation | `tests/test_red_team.py::test_authenticated_foreign_lifecycle[investigation]` |
| p11-ef3c3d6d4d788dca | authorization_tenancy | authenticated foreign lifecycle / evidence | `tests/test_red_team.py::test_authenticated_foreign_lifecycle[evidence]` |
| p11-99f4704529e7594b | authorization_tenancy | authenticated foreign lifecycle / proposal | `tests/test_red_team.py::test_authenticated_foreign_lifecycle[proposal]` |
| p11-5d4ebffdad2ac209 | authorization_tenancy | authenticated foreign lifecycle / decision | `tests/test_red_team.py::test_authenticated_foreign_lifecycle[decision]` |
| p11-f18ba42bab3a0c29 | authorization_tenancy | authenticated foreign lifecycle / approval | `tests/test_red_team.py::test_authenticated_foreign_lifecycle[approval]` |
| p11-6bd007253251f495 | authorization_tenancy | authenticated foreign lifecycle / execution | `tests/test_red_team.py::test_authenticated_foreign_lifecycle[execution]` |
| p11-822ddfd564d18666 | authorization_tenancy | authenticated foreign lifecycle / job | `tests/test_red_team.py::test_authenticated_foreign_lifecycle[job]` |
| p11-5a3bd7eecfb178ef | authorization_tenancy | authenticated foreign lifecycle / incident | `tests/test_red_team.py::test_authenticated_foreign_lifecycle[incident]` |
| p11-8cfe9af700d0fab5 | authorization_tenancy | authenticated foreign lifecycle / metrics | `tests/test_red_team.py::test_authenticated_foreign_lifecycle[metrics]` |
| p11-3c190bc9bba80310 | authorization_tenancy | authenticated foreign lifecycle / correlation | `tests/test_red_team.py::test_authenticated_foreign_lifecycle[correlation]` |
| p11-70d8dbd77596dd7e | evidence_policy | retrieval evaluation / base | `tests/test_retrieval_evaluation.py::test_retrieval_evaluation` |
| p11-e4dd5fd8216ebe93 | authorization_tenancy | registry contracts / base | `tests/test_tools.py::test_registry_contracts` |
| p11-1306eb43b364ee16 | authorization_tenancy | registry rejects unsafe definitions / changes0 | `tests/test_tools.py::test_registry_rejects_unsafe_definitions[changes0]` |
| p11-e7aaf7db12ecdabf | authorization_tenancy | registry rejects unsafe definitions / changes1 | `tests/test_tools.py::test_registry_rejects_unsafe_definitions[changes1]` |
| p11-a979d0acea925681 | authorization_tenancy | registry rejects unsafe definitions / changes2 | `tests/test_tools.py::test_registry_rejects_unsafe_definitions[changes2]` |
| p11-b2c491f56289cacf | authorization_tenancy | registry rejects unsafe definitions / changes3 | `tests/test_tools.py::test_registry_rejects_unsafe_definitions[changes3]` |
| p11-84fb92450555a068 | authorization_tenancy | registry rejects loose schemas / base | `tests/test_tools.py::test_registry_rejects_loose_schemas` |
| p11-6fabc6d9caff8cfc | authorization_tenancy | listing requires authentication and is permission filtered / base | `tests/test_tools.py::test_listing_requires_authentication_and_is_permission_filtered` |
| p11-0f1d2058c41fe4f4 | authorization_tenancy | executor revalidates real role not forged identity / base | `tests/test_tools.py::test_executor_revalidates_real_role_not_forged_identity` |
| p11-4602656e43c811f6 | authorization_tenancy | central permission gate / operator-403 | `tests/test_tools.py::test_central_permission_gate[operator-403]` |
| p11-641b0d6a684ea5ec | authorization_tenancy | central permission gate / reviewer-200 | `tests/test_tools.py::test_central_permission_gate[reviewer-200]` |
| p11-c360d410dd8d3eb2 | authorization_tenancy | central permission gate / admin-200 | `tests/test_tools.py::test_central_permission_gate[admin-200]` |
| p11-004d76d30c9d2506 | authorization_tenancy | central permission gate / auditor-403 | `tests/test_tools.py::test_central_permission_gate[auditor-403]` |
| p11-d173d0d34b5ebbaa | authorization_tenancy | six tools and audit / get_customer-args0-customer_id | `tests/test_tools.py::test_six_tools_and_audit[get_customer-args0-customer_id]` |
| p11-ec35ba69f1a83dc1 | authorization_tenancy | six tools and audit / get_account_status-args1-account_id | `tests/test_tools.py::test_six_tools_and_audit[get_account_status-args1-account_id]` |
| p11-4203cfba94327f1a | authorization_tenancy | six tools and audit / get_ticket-args2-ticket_id | `tests/test_tools.py::test_six_tools_and_audit[get_ticket-args2-ticket_id]` |
| p11-bc31874ec29afcd3 | authorization_tenancy | six tools and audit / list_customer_tickets-args3-items | `tests/test_tools.py::test_six_tools_and_audit[list_customer_tickets-args3-items]` |
| p11-99391c6b8d9c3967 | authorization_tenancy | six tools and audit / list_recent_transactions-args4-items | `tests/test_tools.py::test_six_tools_and_audit[list_recent_transactions-args4-items]` |
| p11-ef7a5e536b617aa4 | authorization_tenancy | six tools and audit / search_policy-args5-items | `tests/test_tools.py::test_six_tools_and_audit[search_policy-args5-items]` |
| p11-2a4cacb84f7c8803 | authorization_tenancy | cross tenant and missing ids identical / 0-get_customer-customer_id-customer | `tests/test_tools.py::test_cross_tenant_and_missing_ids_identical[0-get_customer-customer_id-customer]` |
| p11-2ad9ab0337f228ec | authorization_tenancy | cross tenant and missing ids identical / 0-get_account_status-account_id-account | `tests/test_tools.py::test_cross_tenant_and_missing_ids_identical[0-get_account_status-account_id-account]` |
| p11-6fafcc82734ff90e | authorization_tenancy | cross tenant and missing ids identical / 0-get_ticket-ticket_id-ticket | `tests/test_tools.py::test_cross_tenant_and_missing_ids_identical[0-get_ticket-ticket_id-ticket]` |
| p11-26399904d7392fbe | authorization_tenancy | cross tenant and missing ids identical / 0-list_customer_tickets-customer_id-customer | `tests/test_tools.py::test_cross_tenant_and_missing_ids_identical[0-list_customer_tickets-customer_id-customer]` |
| p11-1a6ddb0f181e3d2d | authorization_tenancy | cross tenant and missing ids identical / 0-list_recent_transactions-account_id-account | `tests/test_tools.py::test_cross_tenant_and_missing_ids_identical[0-list_recent_transactions-account_id-account]` |
| p11-2c458fa6f182e6cf | authorization_tenancy | cross tenant and missing ids identical / 1-get_customer-customer_id-customer | `tests/test_tools.py::test_cross_tenant_and_missing_ids_identical[1-get_customer-customer_id-customer]` |
| p11-d5eb3af41a9757bf | authorization_tenancy | cross tenant and missing ids identical / 1-get_account_status-account_id-account | `tests/test_tools.py::test_cross_tenant_and_missing_ids_identical[1-get_account_status-account_id-account]` |
| p11-72683a90c63b42c8 | authorization_tenancy | cross tenant and missing ids identical / 1-get_ticket-ticket_id-ticket | `tests/test_tools.py::test_cross_tenant_and_missing_ids_identical[1-get_ticket-ticket_id-ticket]` |
| p11-5d458fc860118ddf | authorization_tenancy | cross tenant and missing ids identical / 1-list_customer_tickets-customer_id-customer | `tests/test_tools.py::test_cross_tenant_and_missing_ids_identical[1-list_customer_tickets-customer_id-customer]` |
| p11-51fcfac339ebd275 | authorization_tenancy | cross tenant and missing ids identical / 1-list_recent_transactions-account_id-account | `tests/test_tools.py::test_cross_tenant_and_missing_ids_identical[1-list_recent_transactions-account_id-account]` |
| p11-43ca24007ca16054 | authorization_tenancy | strict arguments rejected and audited / args0 | `tests/test_tools.py::test_strict_arguments_rejected_and_audited[args0]` |
| p11-93d566b544bb6c05 | authorization_tenancy | strict arguments rejected and audited / args1 | `tests/test_tools.py::test_strict_arguments_rejected_and_audited[args1]` |
| p11-76cc15c42bd74dbd | authorization_tenancy | strict arguments rejected and audited / args2 | `tests/test_tools.py::test_strict_arguments_rejected_and_audited[args2]` |
| p11-9cd45f1678d96f81 | authorization_tenancy | strict arguments rejected and audited / args3 | `tests/test_tools.py::test_strict_arguments_rejected_and_audited[args3]` |
| p11-efa773562a5d6cca | authorization_tenancy | strict arguments rejected and audited / args4 | `tests/test_tools.py::test_strict_arguments_rejected_and_audited[args4]` |
| p11-157107f6494e4d65 | authorization_tenancy | strict arguments rejected and audited / args5 | `tests/test_tools.py::test_strict_arguments_rejected_and_audited[args5]` |
| p11-ecc2e165381bc4cc | authorization_tenancy | strict arguments rejected and audited / args6 | `tests/test_tools.py::test_strict_arguments_rejected_and_audited[args6]` |
| p11-5964f5beae02cd36 | authorization_tenancy | strict arguments rejected and audited / args7 | `tests/test_tools.py::test_strict_arguments_rejected_and_audited[args7]` |
| p11-8e4f299bba810e42 | authorization_tenancy | strict arguments rejected and audited / args8 | `tests/test_tools.py::test_strict_arguments_rejected_and_audited[args8]` |
| p11-99ffe14354830e80 | authorization_tenancy | strict limits / 0 | `tests/test_tools.py::test_strict_limits[0]` |
| p11-97fd86b13e61f4f6 | authorization_tenancy | strict limits / 21 | `tests/test_tools.py::test_strict_limits[21]` |
| p11-3ecb30f29eb4b63c | authorization_tenancy | strict limits / 2 | `tests/test_tools.py::test_strict_limits[2]` |
| p11-eaad0ac89527fcb6 | authorization_tenancy | strict limits / True | `tests/test_tools.py::test_strict_limits[True]` |
| p11-f75e7b3a4dce2ac8 | authorization_tenancy | strict limits / 1.5 | `tests/test_tools.py::test_strict_limits[1.5]` |
| p11-fce063bd76477045 | authorization_tenancy | unknown version mode size and csrf / base | `tests/test_tools.py::test_unknown_version_mode_size_and_csrf` |
| p11-f45c43dbaf244882 | authorization_tenancy | chunked body bound / base | `tests/test_tools.py::test_chunked_body_bound` |
| p11-db5185adf5dbcd68 | authorization_tenancy | stable order and empty results / base | `tests/test_tools.py::test_stable_order_and_empty_results` |
| p11-ebc7741b6d15230f | authorization_tenancy | policy scope parameterization and untrusted text / base | `tests/test_tools.py::test_policy_scope_parameterization_and_untrusted_text` |
| p11-e177e3590c72da40 | authorization_tenancy | bad outputs and safe failures / <lambda>-output_invalid0 | `tests/test_tools.py::test_bad_outputs_and_safe_failures[<lambda>-output_invalid0]` |
| p11-110f4c411faf7e62 | authorization_tenancy | bad outputs and safe failures / <lambda>-output_invalid1 | `tests/test_tools.py::test_bad_outputs_and_safe_failures[<lambda>-output_invalid1]` |
| p11-5681b681f734cc99 | authorization_tenancy | bad outputs and safe failures / <lambda>-internal_error | `tests/test_tools.py::test_bad_outputs_and_safe_failures[<lambda>-internal_error]` |
| p11-7071077354e4a4c1 | authorization_tenancy | result byte bound / base | `tests/test_tools.py::test_result_byte_bound` |
| p11-24ffd9b3fa1dd27a | authorization_tenancy | read only database prevents accidental business write / base | `tests/test_tools.py::test_read_only_database_prevents_accidental_business_write` |
| p11-594b29320a852b86 | authorization_tenancy | timeout cleanup and pool settings / base | `tests/test_tools.py::test_timeout_cleanup_and_pool_settings` |
| p11-56c7e695faa37791 | authorization_tenancy | cancellation audit and slot held until real cleanup / base | `tests/test_tools.py::test_cancellation_audit_and_slot_held_until_real_cleanup` |
| p11-4409d222639872f3 | authorization_tenancy | context immutable and ignores client header scope / base | `tests/test_tools.py::test_context_immutable_and_ignores_client_header_scope` |
| p11-5f408f3b9f7bb7bb | authorization_tenancy | revoked session and forged server scope / base | `tests/test_tools.py::test_revoked_session_and_forged_server_scope` |
| p11-fc82fd7a071ef3eb | authorization_tenancy | rate limit persists between executors / base | `tests/test_tools.py::test_rate_limit_persists_between_executors` |
| p11-2efc17c6f1a32e63 | authorization_tenancy | audit failure never returns success / base | `tests/test_tools.py::test_audit_failure_never_returns_success` |
| p11-ddcda29099f67b61 | authorization_tenancy | database failure safe classification / base | `tests/test_tools.py::test_database_failure_safe_classification` |
| p11-b786368711c538c4 | evidence_policy | actual investigation citation is not transferable / other-investigation | `tests/test_phase11_boundaries.py::test_actual_investigation_citation_is_not_transferable[other-investigation]` |
| p11-9e8ca4318c4b599e | evidence_policy | actual investigation citation is not transferable / other-tenant-investigation | `tests/test_phase11_boundaries.py::test_actual_investigation_citation_is_not_transferable[other-tenant-investigation]` |
| p11-7f6d11270361115d | approval_execution | concurrent independent approval race / two distinct authorized reviewers | `tests/test_phase11_boundaries.py::test_concurrent_independent_approvals_have_one_durable_winner` |
