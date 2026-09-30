# Study data: intentionally not acquired yet

There is no new observational cohort or source-record table in this migration. Do not populate them with fixtures or legacy generated products to make the factory pass.

Follow P01–P05 in `plan.md`: feasible sources/rights, immutable raw acquisition, decoded records, threshold/onset/coverage evidence, availability filtration and independent splits. Record IDs must map losslessly to real parent bytes/rows; copying IDs does not create independence.

Raw data, normalized caches and large checkpoints are excluded from Git. Track lawful manifests, schemas, selection/conversion code, checksums and approved small release subsets. Preserve required research attempts/data vintages under the explicit archive policy. Constructed tests live in `source/tests/`, not in observational data tables.
