# Original section 51 — every go-live acceptance check

15 September 2026. Evidence applies to the uncommitted local candidate. “COMPLETE” is the bounded software check, not a live deployment claim. Required remote/hardware checks remain open.

| Required check | Status | Evidence / remaining acceptance |
|---|---|---|
| Backend tests PASS | COMPLETE | 317 backend/deployment tests, 11 deprecation warnings. |
| Frontend tests PASS | COMPLETE | 81 frontend tests; lint/typecheck/build exit 0. Final logs in evidence/. |
| Lint PASS | COMPLETE | 81 frontend tests; lint/typecheck/build exit 0. Final logs in evidence/. |
| TypeScript PASS | COMPLETE | 81 frontend tests; lint/typecheck/build exit 0. Final logs in evidence/. |
| Production build PASS | COMPLETE | 81 frontend tests; lint/typecheck/build exit 0. Final logs in evidence/. |
| Secret scan PASS | COMPLETE | Final redacted history/working-tree gitleaks and policies passed; pip/npm zero known vulnerabilities. |
| Dependency/security gate PASS or approved documented exception | COMPLETE | Final redacted history/working-tree gitleaks and policies passed; pip/npm zero known vulnerabilities. |
| Alembic has exactly one head | COMPLETE | One head: 20260910_0053; complete empty-database replay passed. |
| Fresh database migration PASS | COMPLETE | Local automated suite/database coverage; see final-backend.txt and final browser evidence. |
| Existing database migration PASS | COMPLETE | Synthetic store at 0048 retained after upgrade to 0053. Actual production-clone rehearsal remains external. |
| Docker test build PASS | COMPLETE | Final test and production Compose builds passed; production was not started. |
| Docker production build PASS | COMPLETE | Final test and production Compose builds passed; production was not started. |
| Test deployment PASS | PARTIAL | Local isolated Compose health/login/workflows passed; remote exact committed candidate remains unverified. |
| Login PASS | COMPLETE | Local automated suite/database coverage; see final-backend.txt and final browser evidence. |
| Owner PASS | PARTIAL | Backend authorization tests pass; local owner browser workflows pass. Full hands-on role acceptance remains. |
| Manager PASS | PARTIAL | Backend authorization tests pass; local owner browser workflows pass. Full hands-on role acceptance remains. |
| Cashier PASS | PARTIAL | Backend authorization tests pass; local owner browser workflows pass. Full hands-on role acceptance remains. |
| Store isolation PASS | COMPLETE | Local automated suite/database coverage; see final-backend.txt and final browser evidence. |
| Category creation PASS | PARTIAL | Catalog/service/schema tests and synthetic fixtures pass; complete manual metadata CRUD acceptance on remote TEST remains. |
| Brand creation PASS | PARTIAL | Catalog/service/schema tests and synthetic fixtures pass; complete manual metadata CRUD acceptance on remote TEST remains. |
| Product creation PASS | PARTIAL | Catalog/service/schema tests and synthetic fixtures pass; complete manual metadata CRUD acceptance on remote TEST remains. |
| Variant creation PASS | PARTIAL | Catalog/service/schema tests and synthetic fixtures pass; complete manual metadata CRUD acceptance on remote TEST remains. |
| Unique barcode PASS | COMPLETE | Local automated suite/database coverage; see final-backend.txt and final browser evidence. |
| Shared barcode PASS | COMPLETE | Local automated suite/database coverage; see final-backend.txt and final browser evidence. |
| Shared barcode size selection PASS | COMPLETE | Local automated suite/database coverage; see final-backend.txt and final browser evidence. |
| Barcode sale PASS | COMPLETE | Local automated suite/database coverage; see final-backend.txt and final browser evidence. |
| Category-based non-barcode sale PASS | COMPLETE | Completed local Chromium/WebKit browser transactions; physical scanner remains separate. |
| Search-based sale PASS | COMPLETE | Completed local Chromium/WebKit browser transactions; physical scanner remains separate. |
| Stock scan PASS | COMPLETE | Local automated suite/database coverage; see final-backend.txt and final browser evidence. |
| Quick Stock Entry PASS | COMPLETE | Local automated suite/database coverage; see final-backend.txt and final browser evidence. |
| Draft stock recovery PASS | COMPLETE | Local automated suite/database coverage; see final-backend.txt and final browser evidence. |
| Opening-stock pilot PASS | COMPLETE | Local automated suite/database coverage; see final-backend.txt and final browser evidence. |
| Opening-stock reconciliation PASS | COMPLETE | Local automated suite/database coverage; see final-backend.txt and final browser evidence. |
| Quick Purchase PASS | COMPLETE | Local automated suite/database coverage; see final-backend.txt and final browser evidence. |
| Formal Purchase PASS | COMPLETE | Local automated suite/database coverage; see final-backend.txt and final browser evidence. |
| Purchase confirmation increases exact variant PASS | COMPLETE | Local automated suite/database coverage; see final-backend.txt and final browser evidence. |
| Sale reduces exact variant PASS | COMPLETE | Local automated suite/database coverage; see final-backend.txt and final browser evidence. |
| Insufficient stock blocked PASS | COMPLETE | Local automated suite/database coverage; see final-backend.txt and final browser evidence. |
| Discount PASS | COMPLETE | Local automated suite/database coverage; see final-backend.txt and final browser evidence. |
| Cash PASS | COMPLETE | Local automated suite/database coverage; see final-backend.txt and final browser evidence. |
| UPI PASS | COMPLETE | Local automated suite/database coverage; see final-backend.txt and final browser evidence. |
| Card PASS | COMPLETE | Local automated suite/database coverage; see final-backend.txt and final browser evidence. |
| Bank PASS | COMPLETE | Local automated suite/database coverage; see final-backend.txt and final browser evidence. |
| Receipt print PASS | EXTERNAL VERIFICATION REQUIRED | Both browser previews pass. Physical paper/alignment/scannability not verified. |
| Barcode label print PASS | EXTERNAL VERIFICATION REQUIRED | Both browser previews pass. Physical paper/alignment/scannability not verified. |
| Return PASS | COMPLETE | Local automated suite/database coverage; see final-backend.txt and final browser evidence. |
| Exchange PASS | COMPLETE | Local automated suite/database coverage; see final-backend.txt and final browser evidence. |
| Sale void PASS | COMPLETE | Local automated suite/database coverage; see final-backend.txt and final browser evidence. |
| Purchase Return PASS | COMPLETE | Local automated suite/database coverage; see final-backend.txt and final browser evidence. |
| Stock correction PASS | COMPLETE | Local automated suite/database coverage; see final-backend.txt and final browser evidence. |
| Inventory Integrity = no unexplained discrepancies | COMPLETE | 57→55→56→54→59 exact-size regression, concurrency and restored synthetic database all reconcile without unexplained differences. |
| Day Closing PASS | COMPLETE | Local automated suite/database coverage; see final-backend.txt and final browser evidence. |
| DB backup PASS | COMPLETE | Fresh isolated Docker-data backup and restore passed at 0053; 14 media files hash-equal. Production/offsite evidence is separate. |
| Offsite backup PASS | EXTERNAL VERIFICATION REQUIRED | Requires actual target configuration/access and current evidence; not executed. |
| Database restore PASS | COMPLETE | Fresh isolated Docker-data backup and restore passed at 0053; 14 media files hash-equal. Production/offsite evidence is separate. |
| Uploads/images restore PASS | COMPLETE | Fresh isolated Docker-data backup and restore passed at 0053; 14 media files hash-equal. Production/offsite evidence is separate. |
| Disk alert PASS | EXTERNAL VERIFICATION REQUIRED | Requires actual target configuration/access and current evidence; not executed. |
| Backup alert PASS | EXTERNAL VERIFICATION REQUIRED | Requires actual target configuration/access and current evidence; not executed. |
| Chrome PASS | COMPLETE | Completed local Chromium/WebKit browser transactions; physical scanner remains separate. |
| Safari PASS | EXTERNAL VERIFICATION REQUIRED | WebKit and tablet/phone viewport automation passed; actual shop Safari/tablet and staff trial pending. |
| Tablet PASS | EXTERNAL VERIFICATION REQUIRED | WebKit and tablet/phone viewport automation passed; actual shop Safari/tablet and staff trial pending. |
| Production health check PASS. | EXTERNAL VERIFICATION REQUIRED | Requires actual target configuration/access and current evidence; not executed. |

Final recommendation: **NO-GO**.
