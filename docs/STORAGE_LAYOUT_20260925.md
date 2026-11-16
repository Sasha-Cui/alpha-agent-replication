# AlphaEvolve storage layout — September 25, 2026

The canonical physical checkout is `/nfs/roberts/project/pi_jss233/zc362/alpha_evolve`. The former `/nfs/roberts/project/pi_btk22/zc362/alpha_evolve` path is a compatibility symlink to it. Work directly in the JSS checkout for new work.

The migration moved 1,210 selected items containing 424,591,190,600 logical bytes. Dedicated runtime prefixes live under `/nfs/roberts/project/pi_jss233/zc362/environments`, with their original BTK project paths retained as compatibility aliases. Attributed Slurm assets live under `alpha_evolve/slurm`. The 127 former scratch roots now live under `alpha_evolve/relocated_scratch`; their old scratch paths are absent and have no compatibility symlinks. Historical manifests retain original path names intentionally.

Shared KnowledgeTemplate and JKP inputs, generic caches and unrelated runtime prefixes remain with their owners. Use the exact mapping in the migration completion receipt; do not move or delete shared trees by association.

Cutover job 27480268 completed with exit 0 on September 25 at 17:08 UTC. Independent verification passed at 20:49 UTC: all 1,083 project aliases, absence of old scratch and retired paths, 17,840 symlinks, 1,210 bound prior SHA-256 receipts, critical ledger/manuscript/account/helper hashes and primary archive metadata/readback receipts. All 32 bare interpreter startup results matched the pre-migration baseline (12 successful and 20 unchanged historical loader failures); all five supported version wrappers passed. These are storage and startup checks, not new scientific runs or a claim that every historical bare environment is self-contained.

Audit and exact mappings: `/nfs/roberts/project/pi_jss233/zc362/_workspace/storage_operations/2026-09-24-alpha-evolve-migration/`. The final migration receipt is in `migration_cutover_v7/migration_complete.json`; independent verification is in `postmigration_verification_v1/validation.json`. Earlier failures, diagnostics, metadata and checksum receipts remain preserved.

Only the seven explicitly authorized installer/build cache roots are eligible for cleanup, after provenance preservation and fresh dependency/hash checks. Cleanup job 27527518 completed successfully, removing 12,584,898,540 logical cache bytes after preserving and verifying 10,210 provenance files. Exact manifests and storage measurements remain under `cache_cleanup_after_migration_v1`. Research histories, ledger/response caches, providers, pinned runtime installations and backups are retained.

The manuscript and both original archive bundles remain sealed. Private copy job 27549793 and final release closure are complete. The current manifest is paper_runs/fidelity_completion_v2/release_completion_v1.json. Copies within the JSS allocation do not provide separate-allocation or off-cluster fault isolation. All scientific limitations and the requirement for external human review remain unchanged.
